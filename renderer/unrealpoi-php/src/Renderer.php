<?php

require_once __DIR__ . "/../vendor/autoload.php";
require_once __DIR__ . "/RendererConfig.php";
require_once __DIR__ . "/Debug.php";
require_once __DIR__ . "/Helpers.php";
require_once __DIR__ . "/ActorOps.php";
require_once __DIR__ . "/VectorOps.php";
require_once __DIR__ . "/Graphics.php";
require_once __DIR__ . "/SpriteBlitter.php";
require_once __DIR__ . "/ColorSchemes.php";
require_once __DIR__ . "/Projection.php";

use Naomai\PHPLayers as GDW;
use Naomai\PHPLayers\Image;

ini_set('memory_limit', '512M');

define('UTT_RENDERER_VER', "0.2.0");

logWrite("UnrealPOI renderer v".UTT_RENDERER_VER."\r\n");



$opts = getopt("", [
    "input:",
    "output:",
    "scheme:",
    "projection:",
    "fhd",
    "redraw"
]);

if(!isset($opts['input']) || !isset($opts['output'])) {
    echo "USAGE: \r\n";
    $execName = basename(__FILE__);
    echo "  $execName --input=<map_file_json> --output=<output_dir> [--scheme=<colorscheme> --projection=<projection_mode> --fhd --redraw]\r\n";
    exit;
}

$mapFile = $opts['input'];
$mapName = pathinfo($mapFile, PATHINFO_FILENAME);
$cacheFileSuffix="";

$colorSchemeName = $defaultColorScheme;
if(isset($opts['scheme']) && isset($colorSchemes[$opts['scheme']])) {
    $colorSchemeName = $opts['scheme'];
}

logWrite("Processing map: $mapName");


$projectionModeName = $defaultProjectionMode;
if(isset($opts['projection']) && isset($renderModes[$opts['projection']])) {
    $projectionModeName=$renderModes[$opts['projection']];
}

$mapWorkingDir = $opts['output'];


$debug_checkpoint = true;



$scheme = $colorSchemes[$colorSchemeName];
$projectionFunction="proj_$projectionModeName"; // must be callable!
$projectionAdjustVirtFunction="projav_$projectionModeName";



$cacheFileSuffix=$projectionModeName;


if(isset($opts['fhd'])) {
    $SCREENX = $imageSizeBigX;
    $SCREENY = $imageSizeBigY;
    $cacheFileSuffix.="-fhd";
} else {
    $SCREENX = $imageSizeNormalX;
    $SCREENY = $imageSizeNormalY;
}

    $cacheFileSuffix .= "-".$colorSchemeName;


$layoutTargetFile = $mapWorkingDir . "/layout_{$cacheFileSuffix}.png";
if(file_exists($layoutTargetFile) && !isset($opts['redraw'])){
    logWrite("Aborted: Already rendered.");
    exit;
}
$reportTargetFile = $mapWorkingDir ."/report.json";

if(!file_exists($mapFile)) {
    polysFailure("Map layout not found");
    exit;
}

error_reporting(E_ALL);

$emptyCoord=array("X"=>0,"Y"=>0,"Z"=>0);

$image = new GDW\Image($SCREENX, $SCREENY);
//$image->setComposer(new GDW\Composers\TiledComposer($image)); // testing some new stuff from gdw

$bgLayer = $image->getLayerByIndex(0);
$worldLayer = $image->newLayer("World");
$linesLayer = $image->newLayer("Lines");
$spritesLayer = $image->newLayer("Sprites");
$labelsLayer = $image->newLayer("Labels");
$importantSpritesLayer = $image->newLayer("importantSpritesLayer");
$overlayLayer = $image->newLayer("text");
$legendLayer = $image->newLayer("LegendLayer");

$overlayGD = $overlayLayer->getGDHandle();
$linesGD = $linesLayer->getGDHandle();
$linesPainter = $linesLayer->paint();
$spritesGD = $spritesLayer->getGDHandle();
$importantSpritesGD = $importantSpritesLayer->getGDHandle();
$worldGD = $worldLayer->getGDHandle(); // it's faster to do regular imagepolygon instead of bloated gdwrapper 

$textRenderer = new GDW\Generators\NonOverlappingText();
$labelsLayer->setGenerator($textRenderer);

$blitter    = new GDW\SpriteBlitter($spritesLayer);
$blitterImp = new GDW\SpriteBlitter($importantSpritesLayer); // blitter for objective related objects (e.g FlagBase or MonsterEnd)
$sprites    = array();
$spritesImp = array();
$spritesLegend = array();
$spriteLoc = __DIR__ . "/sprites";
$spriteDir = opendir($spriteLoc);
while(($spriteFile=readdir($spriteDir))!==false) {
    $spritePath = "$spriteLoc/$spriteFile";
    if(filetype($spritePath)=='file') {
        $spriteId = pathinfo($spritePath, PATHINFO_FILENAME);
        $sprites[$spriteId]    = $blitter->addSprite($spritePath);
        $spritesImp[$spriteId] = $blitterImp->addSprite($spritePath);
    }
    
}


utt_checkpoint("Begin");
//imagefill($img,0,0,0x000000);
$bgLayer->fill($scheme['background']);

utt_checkpoint("BeginParse");

if(file_exists($mapFile)) {
    $actors=json_decode(file_get_contents($mapFile), true);
    if(!count($actors)){
        polysFailure("Empty JSON poly file: " . realpath($mapFile));
        exit;
    }
} else {
    polysFailure("Couldn't find polys for map. Open Mappage and run mapdlcron.", 12);
    exit;
}
utt_checkpoint("EndParse");

/* Detect gamemode */

$mhendList = getActorsByClass($actors, "MonsterEnd");
$isMH = count($mhendList) > 0;
$flagList = getActorsByClass($actors, "FlagBase");
$isCTF = !$isMH && (bool)count($flagList);


$subtractiveBrushes = getActorsByPropertyValue($actors, "CsgOper", "CSG_Subtract");
$restricted=count($subtractiveBrushes) == 0;
if($restricted) { // all the brushes has been removed from map to protect it from editing
    polysFailure("Map layout was restricted by the author. World geometry won't be shown.");
}

$boundsTemplate=array('topleft'=>array("X"=>32768.0,"Y"=>32768.0,"Z"=>32768.0),'bottomright'=>array("X"=>-32768.0,"Y"=>-32768.0,"Z"=>-32768.0));
$boundsLevel=$boundsTemplate;
$boundsGeometry=$boundsTemplate;

utt_checkpoint("BeginBoundaries");
$skyboxIsPartOfMap=false;
foreach($actors as $act) {
    /* FIRST ITERATION
    Find level boundaries to move & zoom our view perfectly 
    */
    $class=isset($act['Class'])?$act['Class']:"None";

    $isInterestingClass = $class=="PathNode" || $class=="PlayerStart" 
        || $class=="JBPlayerStart" || isset($act['markedItem']) 
        || $class=="InventorySpot" || $class=="Mover" || isset($act['FootRegion']) 
        || isset($act['Paths(0)']) || $class=="Brush";

    $isOutsideLevel = !isset($act['Region']['iLeaf']) || $act['Region']['iLeaf']=="-1";
    // actors with iLeaf == -1 are outside the level (including the subtractive brushes)

    $existsInSpace = isset($act['Location']);

    if(!$isInterestingClass || $isOutsideLevel || !$existsInSpace) {
        continue;
    }
    
    if(isset($act['Region']['Zone']) && $act['Region']['Zone']['importType']=="SkyZoneInfo"){
        // if there are pathnode-like actors in skyzone, it indicates the skybox is also a playable part of map
        if(isset($act['Paths(0)'])) {
            $skyboxIsPartOfMap=true; 
        } else {
            continue;
        }
    }
    if(isset($act['CsgOper']) && $act['CsgOper']=="CSG_Add") {
        continue;
    }

    $actVect=getCoordProperty($act, 'Location');
    $actVect['Z']=-$actVect['Z'];
    $boundsLevel['topleft']=vec3Op($actVect,$boundsLevel['topleft'],'min');
    $boundsLevel['bottomright']=vec3Op($actVect,$boundsLevel['bottomright'],'max');
}
$boundsLevel['topleft']['Z']=-$boundsLevel['topleft']['Z'];
$boundsLevel['bottomright']['Z']=-$boundsLevel['bottomright']['Z'];

$mapSizeX=$boundsLevel['bottomright']['X']-$boundsLevel['topleft']['X'];
$mapSizeY=$boundsLevel['bottomright']['Y']-$boundsLevel['topleft']['Y'];
$mapSizeZ=$boundsLevel['topleft']['Z']-$boundsLevel['bottomright']['Z'];

$dispOffset=vec3Diff($boundsLevel['topleft'], $boundsLevel['bottomright']);

$projectionAdjustVirtFunction();

$scaleX=$SCREENX / $virtW;
$scaleY=$SCREENY / $virtH;
$scale=abs(min($scaleX,$scaleY)*0.8);
$offsetX = 0;
$offsetY = 0;

$bound1=$projectionFunction($boundsLevel['bottomright']);
$bound2=$projectionFunction($boundsLevel['topleft']);


$offsetX=(  (-$bound2['X'])) + ($SCREENX - $bound1['X']+$bound2['X'])/2;
$offsetY=(  (-$bound2['Y'])) + ($SCREENY - $bound1['Y']+$bound2['Y'])/2;

utt_checkpoint("EndBoundaries");

utt_checkpoint("BeginDrawWorld");


$report=[
    'reportVersion'=>UTT_MAPREPORT_VER,
    'monstercount'=>0,
    'medboxcount'=>0,
    'mapsizeX'=>$mapSizeX,
    'mapsizeY'=>$mapSizeY,
    'mapsizeZ'=>$mapSizeZ,
    'brushcsgaddcount'=>0,
    'brushcsgsubcount'=>0,
    'moverscount'=>0,
    'lightWattage'=>0,
    'usedTextures'=>array()
];

foreach($actors as $act){
    /* SECOND ITERATION
    Draw world geometry 
    */

    $hasCsgOper = isset($act['CsgOper']);
    $isBrushlike = ($act['Class']=="Brush" && $hasCsgOper) || $act['Class']=="Mover";
    $hasPolyList = isset($act['PolyList']) && count($act['PolyList']);
    $isInSkyBox = isset($act['Region']['Zone']) && $act['Region']['Zone']['importType']=="SkyZoneInfo" && !$skyboxIsPartOfMap;
    
    if(!$isBrushlike || !$hasPolyList || $isInSkyBox) {
        continue;
    }

    $polyList=$act['PolyList'];
    
    $brushOffset=getCoordProperty($act, 'Location');

    if($act['Class']=="Mover"){
        $polyBaseColor=$scheme['brushMover'];
        $brushType=4;
        $report['moverscount']++;
    }else{
        $brushOp=$act['CsgOper'];
        
        if($brushOp=="CSG_Subtract") {
            $polyBaseColor=$scheme['brushSubtract'];
            $brushType=0;
            $report['brushcsgsubcount']++;
        }else if($brushOp=="CSG_Add") {
            $polyBaseColor=$scheme['brushAdd'];
            $brushType=1;
            $report['brushcsgaddcount']++;
        }else if($brushOp=="CSG_Active") {
            $polyBaseColor=$scheme['brushActive'];
            $brushType=2;
            continue; // remove if you want to draw red builder brush
        }else{
            continue;
        }
        
        if(isset($act['PolyFlags'])){
            $flags=$act['PolyFlags'];
            if($flags & 0x00000001){ // invisible
                continue;
            }else if($flags & 0x00000008){ //non-solid
                $polyBaseColor = $scheme['brushNonSolid'];
            }else if($flags & 0x00000020){ //semi-solid
                $polyBaseColor = $scheme['brushSemiSolid'];
            }else if($flags & 0x04000000){ //zone portal
                //$polyBaseColor = $scheme['brushZonePortal'];
                continue;
            }
        }
    }
    
    // Pivot point for rotation
    $pivot=getCoordProperty($act, "PrePivot");
    $rotation=getRotationProperty($act, "Rotation");
    
    // every brush can be resized with 3 separate properties
    $mainScaleVec=getScaleProperty($act,"MainScale");
    $postScaleVec=getScaleProperty($act,"PostScale");
    $tempScaleVec=getScaleProperty($act,"TempScale");

    foreach($polyList as $polyNum=>$pol){
        

        $vertList=array(); // imagefilledpolygon-compatible list
        
        $transformedVerts=array();
        $verts=array();

        
        
        if(isset($pol['Texture'])){
            if(isset($report['usedTextures'][$pol['Texture']])) $report['usedTextures'][$pol['Texture']]++;
            else $report['usedTextures'][$pol['Texture']]=1;
        }
        
        foreach($pol['Vertex'] as $vertNum=>$vert){
            if(is_array($vert)){
                $verts[]=vec3ToFlatvec3($vert+$emptyCoord);
            }else{
                echo "Warn: act#{$act['Name']}/pol$polyNum/vert#$vertNum !is_array\r\n";
            }
        }

        UEVertTransform(
            $verts, $mainScaleVec, $postScaleVec, $tempScaleVec,
            $rotation, $pivot, $brushOffset
        );

        foreach($verts as $v){
            $utVert=flatvec3ToVec3($v);
            $transformedVerts[]=$utVert;
            
            $v2=$projectionFunction($utVert);
            $vertList[]=round($v2['X']);
            $vertList[]=round($v2['Y']);
            
            if($brushType==0){
                $actVert=$utVert;
                $actVert['Z']=-$actVert['Z'];
                $boundsGeometry['topleft']=vec3Op($actVert,$boundsGeometry['topleft'],'min');
                $boundsGeometry['bottomright']=vec3Op($actVert,$boundsGeometry['bottomright'],'max');
            }
        }

        $nonsensePoly = count($transformedVerts) < 3;
        
        if($nonsensePoly || isPolyOffscreen($vertList)) {
            // Nonsense! We can't have polygons with less than 3 verices.
            continue;

        }

        // Determine if polygon is facing our way
        // Assume the brush is additive
        // Draw two lines from center of the polygon C to two consecutive 
        // vertices A, B. Project them on the screen.
        // Take the smaller angle between them. If BC is farther clockwise
        // than AC, draw the poly. 
        // Negate for subtractive brushes.
        

        $polyCenter=$emptyCoord;
        // Sum, then divide
        foreach($transformedVerts as $vert){
            $polyCenter=vec3Sum($polyCenter,$vert);
        }
        $polyVertNum=count($transformedVerts);
        $polyCenter=vec3Op($polyCenter, $emptyCoord, fn($a,$b)=> $a / ($polyVertNum));
    
        // Project points A,B,C on screen
        $centerCoords=$projectionFunction($polyCenter);
        $vertACoords=$projectionFunction($transformedVerts[0]);
        $vertBCoords=$projectionFunction($transformedVerts[1]);
        
        $angleA=vec2Angle($centerCoords,$vertACoords)/M_PI;
        $angleB=vec2Angle($centerCoords,$vertBCoords)/M_PI;
        
        // Angle between AC, BC
        $angleDiff=$angleB-$angleA;

        // if you don't have a clue what's going on here, those might help a little:
        // red=AC, yellow=BC
        /*
        imageline($overlayGD,$centerCoords['X'],$centerCoords['Y'],$vertACoords['X'],$vertACoords['Y'],0xFF0000);
        imageline($overlayGD,$centerCoords['X'],$centerCoords['Y'],$vertBCoords['X'],$vertBCoords['Y'],0xFFFF00);
        //*/

        // visible range: (-1, 0) , (1, 2)
        if($brushType==0){ // subtractive brush
            if($angleDiff > 0 && $angleDiff < 1 || $angleDiff < -1){
                continue;
            }
        }else{ // additive
            if(-$angleDiff > 0 && -$angleDiff < 1 || -$angleDiff < -1){
                continue;
            }
        }

        // Draw polygon (base color and border)
        
        $polyColor = $polyBaseColor|0x70000000;
        $polyBorderColor = $polyBaseColor|0x70000000;
        imagefilledpolygon($worldGD,$vertList,$polyColor);
        imagepolygon($worldGD,$vertList,$polyBorderColor);

        // Polygon shading
        $angR=vec3Angle($polyCenter,$transformedVerts[0]);
        $angRX=($angR['Roll']+$angR['Pitch'])/(M_PI);
        

        $shadeColor = round(128 * fmod($angRX-0.5, 1));
        $shadeColor *= 0x010101;
        $shadeColor += 0x3f3f3f;
        $shadeColor |= 0x60000000;
        if($act['Class']!="Mover") {
            imagefilledpolygon($worldGD,$vertList,$shadeColor);
        }
        
    }
}
$report['worldBounds']=$boundsGeometry;
$report['worldSizeX']=$boundsGeometry['bottomright']['X']-$boundsGeometry['topleft']['X'];
$report['worldSizeY']=$boundsGeometry['bottomright']['Y']-$boundsGeometry['topleft']['Y'];
$report['worldSizeZ']=$boundsGeometry['bottomright']['Z']-$boundsGeometry['topleft']['Z'];

utt_checkpoint("EndDrawWorld");



utt_checkpoint("BeginDrawObjects");


$displayedTags=array(); // to avoid displaying the same thing multiple times
$levelPalette=array(); 

$actorsGroupsNum=0;
$actorsGroupsFirstAct=array();

foreach($actors as $act){
    $loc=getCoordProperty($act, 'Location');
    $loc2d=null;
    $class=strtolower($act['Class']);
    $classNC=$act['Class'];

    if(!isset($report['actorsCount'][$class])) {
        $report['actorsCount'][$class]=0;
    }
    $report['actorsCount'][$class]++;
    
    if(isset($act['Region']['Zone'])) {
        $report['zones'][crc32($act['Region']['Zone']['export'])]=$act['Region']['Zone']['export'];
    }
    if($class=="levelinfo"){
        $report['title']=getProperty($act, "Title", "");
        $report['author']=getProperty($act, "Author", "");
        
        $report['ipc']=getProperty($act, "IdealPlayerCount", "");
        $report['entermsg']=getProperty($act, "LevelEnterText", "");
    }else if($class=="playerstart" || $class=="jbplayerstart" ){
        $team = getProperty($act, "TeamNumber", 0);
        if($isMH && $team!=0) {
            // MH only uses spawnpoints for team 0
            continue;
        }
        $isSecondaryMHSpawn = $isMH && isset($act['bEnabled']) && $act['bEnabled']=="False";
        $loc2d=$projectionFunction($loc);
        if($isCTF){
            if($team < 0 || $team > 3) {
                $team = 0;
            }
            $blitter->blit($sprites['teamplayerstart_'.$team],round($loc2d['X']-5),round($loc2d['Y']-4));
        }
        
        
        if($isSecondaryMHSpawn){
            $blitter->blitWithShadow($sprites['playerstart_2'],round($loc2d['X']-4),round($loc2d['Y']-7));
        }else{
            $blitter->blitWithShadow($sprites['playerstart'],round($loc2d['X']-4),round($loc2d['Y']-7));
        }
        
    }else if($class=="kicker"){
        $kickVel=getCoordProperty($act, 'KickVelocity');
        

        $kickDest=vec3Sum($loc,$kickVel);
        $loc2d=$projectionFunction($loc);
        $dest2d=$projectionFunction($kickDest);
        
        // chevron lines
        $kickAngle=-vec2Angle($dest2d,$loc2d)-M_PI/2;
        
        $arrow1X=round(sin(M_PI+$kickAngle-0.4)*7)+$dest2d['X'];
        $arrow1Y=round(cos(M_PI+$kickAngle-0.4)*7)+$dest2d['Y'];
        $arrow2X=round(sin(M_PI+$kickAngle+0.4)*7)+$dest2d['X'];
        $arrow2Y=round(cos(M_PI+$kickAngle+0.4)*7)+$dest2d['Y'];
        
        imagefilledrectangle($linesGD,$loc2d['X']-1,$loc2d['Y']-1,$loc2d['X']+1,$loc2d['Y']+1,$scheme['objKicker']);
        
        if($arrow1X!=$arrow2X && $arrow1Y!=$arrow2Y){
            
            imageLine($linesGD,$loc2d['X'],$loc2d['Y'],$dest2d['X'],$dest2d['Y'],$scheme['objKickerArrow']);
            imageLine($linesGD,$dest2d['X'],$dest2d['Y'],$arrow1X,$arrow1Y,$scheme['objKickerArrow']);
            imageLine($linesGD,$dest2d['X'],$dest2d['Y'],$arrow2X,$arrow2Y,$scheme['objKickerArrow']);
        }
        
        $kickerPresent=true;
    }else if($class=="teleporter" || $class=="favoritesteleporter" || $class=="visibleteleporter"){
        $loc2d=$projectionFunction($loc);

        $telepText="";

        if(isset($act['URL'])){
            $tdestNum=getSingleActorByTag($actors,$act['URL']);
            if($tdestNum!=null){
                $tdest=$actors[$tdestNum];
                if(!isset($tdest['Region']['iLeaf']) || $tdest['Region']['iLeaf']!=-1){
                    $teleLineColor = $scheme['lineTeleportConnection'];
                    imagesetstyle($linesGD,array($teleLineColor,$teleLineColor,$teleLineColor,$teleLineColor,$teleLineColor, IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT ));
            
                    $destLoc=getCoordProperty($tdest, 'Location');
                    
                    $dest2d=$projectionFunction($destLoc);
                    
                    $linesPainter->line($loc2d['X'],$loc2d['Y'],$dest2d['X'],$dest2d['Y'],IMG_COLOR_STYLED);
                }
                
                
            }
            $blitter->blitWithShadow($sprites['teleporter'],$loc2d['X']-4,$loc2d['Y']-6);
        }else{
            $blitter->blitWithShadow($sprites['teleporter_dest'],$loc2d['X']-4,$loc2d['Y']-6);
        }
        
        
        
        $teleporterPresent=true;
    }else if($class=="warpzoneinfo"){
        $loc2d=$projectionFunction($loc);

        $telepText="";

        if(isset($act['OtherSideURL'])){
            $tdestNums=getActorsByPropertyValue($actors,"ThisTag",$act['OtherSideURL']);
            if(isset($tdestNums[0]) && $tdestNums[0]!=null){
                $tdest=$actors[$tdestNums[0]];
                if(!isset($tdest['Region']['iLeaf']) || $tdest['Region']['iLeaf']!=-1){
                    $teleLineColor = $scheme['lineTeleportConnection'];
                    imagesetstyle($linesGD,array($teleLineColor,$teleLineColor,$teleLineColor,$teleLineColor,$teleLineColor, IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT , IMG_COLOR_TRANSPARENT ));
            
                    $destLoc=getCoordProperty($tdest, 'Location');
                    
                    $dest2d=$projectionFunction($destLoc);
                    
                    $linesPainter->line($loc2d['X'],$loc2d['Y'],$dest2d['X'],$dest2d['Y'],IMG_COLOR_STYLED);
                }
                
                
            }
            $blitter->blitWithShadow($sprites['teleporter'],$loc2d['X']-4,$loc2d['Y']-6);
        }else{
            $blitter->blitWithShadow($sprites['teleporter_dest'],$loc2d['X']-4,$loc2d['Y']-6);
        }
        
        
        
        $teleporterPresent=true;
    }else if($class=="flagbase" && !$isMH){ // CTF
        $loc2d=$projectionFunction($loc);
        
        $team=getProperty($act, "Team", 0);;
        
        if($team < 0 || $team > 3) $team = 0;
        
        switch($team){
            case 0:
                $ds="Red";
                $report['redflag']=$loc;
            break;
            case 1:
                $ds="Blue";
                $report['blueflag']=$loc;
            break;
            case 2:
                $ds="Green";
                $report['greenflag']=$loc;
            break;
            case 3:
                $ds="Gold";
                $report['goldflag']=$loc;
            break;
        }
        
        $flagsPresent=true;
        
        $blitterImp->blitWithShadow($sprites['flagbase_'.$team],$loc2d['X'],$loc2d['Y']-7);
    }else if($class=="monsterend"){ // MH
        $loc2d=$projectionFunction($loc);
        $blitterImp->blitWithShadow($sprites['monsterend'],$loc2d['X']-4,$loc2d['Y']-7);
        $monsterEndPresent=true;
    }else if($class=="warheadlauncher"){

        $loc2d=$projectionFunction($loc);
        $blitter->blitWithShadow($sprites['warheadlauncher'],$loc2d['X']-4,$loc2d['Y']-8);
        
        $redeemerPresent=true;
    }else if($class=="udamage"){

        $loc2d=$projectionFunction($loc);
        $blitter->blitWithShadow($sprites['udamage'],$loc2d['X']-4,$loc2d['Y']-8);
        
        $udamagePresent=true;

    }else if($class=="jailzone" || $class=="pressurejailzone"){ // JB
        $loc2d=$projectionFunction($loc);
        
        $team=getProperty($act, "JailedTeam", 0);
        if($team < 0 || $team > 3) {
            $team = 0;
        }
        
        switch($team){
            case 0:
                $ds="Red";
            break;
            case 1:
                $ds="Blue";
            break;
            case 2:
                $ds="Green";
            break;
            case 3:
                $ds="Gold";
            break;
        }
        $jailPresent=true;
        
        $blitterImp->blitWithShadow($sprites['jailzone_'.$team],$loc2d['X']-4,$loc2d['Y']-7);
        
    }else if($class=="teamactivatedtrigger" || $class=="teamactivateddamageatonce" || $class=="teamactivateddamagebuildup"){
        $loc2d=$projectionFunction($loc);
        
        $team=getProperty($act, "Team", 0);
        if($team < 0 || $team > 3) $team = 0;
        
        switch($team){
            case 0:
                $ds="Red";
            break;
            case 1:
                $ds="Blue";
            break;
            case 2:
                $ds="Green";
            break;
            case 3:
                $ds="Gold";
            break;
        }
        $jailSwitchPresent=true;
        
        $blitterImp->blitWithShadow($sprites['jailtrigger_'.$team],$loc2d['X']-4,$loc2d['Y']-7);
    }else if(isset($act['FootRegion'])){
        
        if($class=="cow" || $class=="babycow" || $class=="nali" || $class=="nalipriest" // scriptedpawn
            || $class=="horseflyswarm" || $class=="biterfishschool" || $class=="parentblob" // flockmasterpawn
            || $class=="bird1" || $class=="biterfish" || $class=="bloblet" || $class=="horsefly" || $class=="nalirabbit" // flockpawn
            || $class=="teamcannon" || $class=="miniguncannon" || $class=="fortstandard" // StationaryPawn
            ) continue;
        
        $drawScale=getProperty($act,'DrawScale',1)*2;
        $loc2d=$projectionFunction($loc);
        $drawScaleX=max(2,$drawScale/2);
        
        $report['monstercount']++;
        
        $monName=getProperty($act, 'MenuName', $class);
        
        $mcx=$classNC;
        if(isset($report['monsterTypesCount'][$mcx][$monName])) $report['monsterTypesCount'][$mcx][$monName]++;
        else $report['monsterTypesCount'][$mcx][$monName]=1;
        
        imagefilledellipse($spritesGD,$loc2d['X']-$drawScaleX/2,$loc2d['Y']-$drawScaleX/2,$drawScaleX,$drawScaleX,$scheme['objMonster']);
            
        if(!isset($act['uttpr_props']['partOfGroup'])){
            $otherActz=getActorsByClass($actors,$classNC);
            $closeActzRad=getActorsInRadius($otherActz,$act['Location'],40/$scale);
            $closeActzReg=getActorsInTheSameRegion($otherActz,$act,12);
            $closeActz=array_merge($closeActzRad,$closeActzReg);
            if(count($closeActz) > 2){
                
                
                
                $currentGroupNr=-1;
                foreach($closeActz as $acxId){
                    
                    if(isset($actors[$acxId]['uttpr_props']['partOfGroup'])) {
                        $currentGroupNr=max($actors[$acxId]['uttpr_props']['partOfGroup'],$currentGroupNr);
                    }
                }
                
                if($currentGroupNr==-1) {
                    $currentGroupNr=$actorsGroupsNum++;
                    
                    $act['uttpr_props']['groupSize']=0;
                    $act['uttpr_props']['partOfGroup']=$currentGroupNr;
                    $actorsGroupsFirstAct[$currentGroupNr]=$act;
                }
                
                
                foreach($closeActz as $acxId){
                    if(!isset($actors[$acxId]['uttpr_props']['partOfGroup'])){
                        $actors[$acxId]['uttpr_props']['partOfGroup']=$currentGroupNr;
                        $actorsGroupsFirstAct[$currentGroupNr]['uttpr_props']['groupSize']++;
                    }
                }
            }else{
                if($SCREENX >= 1024) {
                    $hp = isset($act['Health']) ? " (".$act['Health'].")" : "";
                    textWithShadow(
                        $labelsLayer, $loc2d['X']+2,$loc2d['Y']-2, 
                        $classNC.$hp, 
                        ["size"=>7, "font"=>$fontsLoc ."/tahoma.ttf"],
                        $scheme['objMonsterText']
                    );
                }
    
            }
        }
        $monsterPresent=true;
    }else if($class=="thingfactory" || $class=="creaturefactory"){
        if(!isset($act['prototype'])) continue;
        $tag=$act['Tag'];
        $spawns=getActorsByTag($actors,$tag);
        $cap=getProperty($act, 'capacity', 1);
        
        if(!count($spawns)){ 
            // no spawnpoints, so the factory is useless
            logWrite("'' stupid useless factory: ".$act['Name']);
            continue;
        }
        $spawnsAvgCt = 0;
        
        foreach($spawns as $spId) {
            $sp=$actors[$spId];
            if(strcasecmp($sp['Class'], "SpawnPoint")!==0) continue;
            
            $locSp=getCoordProperty($sp, 'Location');
            $locSp2d=$projectionFunction($locSp);
            
            if(!isset($spawnsLocAvg)) {
                $spawnsLocAvg = $locSp;
            } else {
                $spawnsLocAvg['X'] += $locSp['X'];
                $spawnsLocAvg['Y'] += $locSp['Y'];
                $spawnsLocAvg['Z'] += $locSp['Z'];
            }
            $spawnsAvgCt++;
            imagefilledrectangle($spritesGD,$locSp2d['X']-1,$locSp2d['Y']-1,$locSp2d['X']+1,$locSp2d['Y']+1,$scheme['objThingFactory']);
        }
        if($spawnsAvgCt==0) continue;
        $spawnsLocAvg['X'] /= $spawnsAvgCt;
        $spawnsLocAvg['Y'] /= $spawnsAvgCt;
        $spawnsLocAvg['Z'] /= $spawnsAvgCt;
        
        $thingRef = $act['prototype'];
        $package=$act['prototype']['package'];
        $thingFactPresent=true;
        $loc2d=$projectionFunction($spawnsLocAvg);
        
        if($cap <= 1000){
            $thingType=$thingRef['export'] . ' ×'.$cap;
            $report['monstercount']+=$cap;
            $mcx=$thingRef['export'];
            if(isset($report['monsterTypesCount'][$mcx]["(factory)"])) $report['monsterTypesCount'][$mcx]["(factory)"]+=$cap;
            else $report['monsterTypesCount'][$mcx]["(factory)"]=$cap;
        }else{
            $thingType=$thingRef['export'] . " ×∞"; // infinity
        }
        
        if($SCREENX >= 1024) 
            textWithShadow($labelsLayer, $loc2d['X'],$loc2d['Y'], $thingType, array("size"=>7,"font"=>$fontsLoc ."/tahoma.ttf"),$scheme['objThingFactoryText']);
    
        unset($spawnsLocAvg);
    }else if($class=="b_monsterspawner" || $class=="b_monsterloopspawner" || $class=="b_monsterwavespawner"){ // BBoyShare
    
        $tag=$act['Tag'];
        
        if(isset($displayedTags[$tag])) continue;
        
        $loc2d=$projectionFunction($loc);
        imagefilledrectangle($spritesGD,$loc2d['X']-1,$loc2d['Y']-1,$loc2d['X']+1,$loc2d['Y']+1,$scheme['objThingFactory']);

        if($class=="b_monsterwavespawner"){
            $thingType="<monster wave>";
        }else{
            if(isset($act['CreatureType'])){
                $thingType=$act['CreatureType']['export'];
            }else{
                $thingType="Brute";
            }
        }
        $tagActz=getActorsByTag($actors,$tag);
        $capacity=0;
        foreach($tagActz as $acId){
            $capacity+=getProperty($act, 'SpawnNum', 10);
        }
        $monType=$thingType;
        $thingFactPresent=true;
        
        
        if($capacity <= 1000){
            $thingType.=' ×'.$capacity;
            $report['monstercount']+=$capacity;
            $mcx=$monType;
            if(isset($report['monsterTypesCount'][$mcx]["(factory)"])) $report['monsterTypesCount'][$mcx]["(factory)"]+=$capacity;
            else $report['monsterTypesCount'][$mcx]["(factory)"]=$capacity;
        }else{
            $thingType=$thingRef['export'] . " ×∞"; // infinity
        }
        
        if($SCREENX >= 1024) 
            textWithShadow($labelsLayer, $loc2d['X'],$loc2d['Y'], $thingType, array("size"=>7,"font"=>$fontsLoc ."/tahoma.ttf"),$scheme['objThingFactoryText']);
    
        $displayedTags[$tag]=true;

    }else if($class=="zoneinfo"){
        if(!isset($act['ZoneName'])) continue;
        $desc=$act['ZoneName'];

        $loc2d=$projectionFunction($loc);
        textWithShadow($labelsLayer, $loc2d['X']+2,$loc2d['Y'], $desc, array("size"=>14,"font"=>$fontsLoc ."/segoeuib.ttf"),0x50FFFF00);

    }else if($class=="healthvial" || $class=="medbox" || $class=="healthpack"){
                
        switch($class){
            case "healthvial": $hp=5; break;
            case "medbox": $hp=20; break;
            case "healthpack": $hp=100; break;
        }

        $loc2d=$projectionFunction($loc);
        textWithShadow($labelsLayer, $loc2d['X']+2,$loc2d['Y']-2, "+", array("size"=>7,"font"=>$fontsLoc ."/tahomabd.ttf"),0x00CFFF);
        $report['medboxcount']++;
        

    }else if($class=="light"||$class=="triggerlight"){ // default settings ~= 100W light bulb

        $brightness=getProperty($act, "LightBrightness", 64);
        $radius=getProperty($act, 'LightRadius', 64);
        
        $watts=round($brightness*1.5625 * log($radius,64));
        
        $h=getProperty($act, 'LightHue', 0);
        $s=255-getProperty($act, 'LightSaturation', 255);
        $v=getProperty($act, 'LightBrightness', 64);
        
        
        $rgb=ColorHSLToRGB($h/255,$s/255,$v/255 * (255-$s/2)/255); // unreal engine uses HSV
        $rgbV=clamp($rgb['r'],0,255) << 16 | clamp($rgb['g'],0,255) << 8 | clamp($rgb['b'],0,255);
        $levelPalette[]=$rgbV;
        //imagefilledrectangle($img,count($levelPalette)*3,0,count($levelPalette)*3+2,2,$rgbV);
        $report['lightWattage']+=$watts;

    }
}

// Actor group labels - draw only for larger resolutions
if($SCREENX >= 1024) {
    foreach($actorsGroupsFirstAct as $gn=>$ax){
        
        if(isset($ax['uttpr_props'])){
            $ct=$ax['uttpr_props']['groupSize'];
            $loc=getCoordProperty($ax, 'Location');
            $loc2d=$projectionFunction($loc);
            
            $acxDesc=$ax['Class']." ×".$ct;
            if($SCREENX >= 1024) 
                textWithShadow($labelsLayer, $loc2d['X']+2,$loc2d['Y']-2, $acxDesc, array("size"=>7,"font"=>$fontsLoc ."/tahoma.ttf"),$scheme['objMonsterGroupText']);
        }
    }
}

// Scale rulers
$scaledDistFT=pow(10,round(log(0.0625/$scale*50,10)));
$scaledDistM =pow(10,round(log(0.01905/$scale*50,10)));

$scaledDistFTToUU=$scaledDistFT/0.0625;
$scaledDistMToUU =$scaledDistM /0.01905;
if($scaledDistFTToUU*2<$scaledDistMToUU ) {$scaledDistMToUU /=2;$scaledDistM /=2;}
else if($scaledDistMToUU*2<$scaledDistFTToUU ) {$scaledDistFTToUU /=2;$scaledDistFT /=2;}

$pt1=$projectionFunction(array('X'=>0,'Y'=>0,'Z'=>0));
$pt2=$projectionFunction(array('X'=>$scaledDistFTToUU,'Y'=>0,'Z'=>0));
$pt3=$projectionFunction(array('X'=>$scaledDistMToUU,'Y'=>0,'Z'=>0));


$ptDiffFT=vec2Diff($pt2,$pt1);
$ptDiffM=vec2Diff($pt3,$pt1);

$overlayLayer->paint()->line(30,$SCREENY-48,30+$ptDiffFT['X'],$SCREENY-48+$ptDiffFT['Y'],$scheme['scaleLine']);
$overlayLayer->paint()->line(30,$SCREENY-33,30+$ptDiffM['X'],$SCREENY-33+$ptDiffM['Y'],$scheme['scaleLine']);

textWithShadow($overlayLayer, 29, $SCREENY-74, "Scale:",           array("size"=>7,"font"=>$fontsLoc ."/tahoma.ttf"),$scheme['scaleText']);
textWithShadow($overlayLayer, 29, $SCREENY-59, "$scaledDistFT ft", array("size"=>7,"font"=>$fontsLoc ."/tahoma.ttf"),$scheme['scaleText']);
textWithShadow($overlayLayer, 29, $SCREENY-44, "$scaledDistM m",   array("size"=>7,"font"=>$fontsLoc ."/tahoma.ttf"),$scheme['scaleText']);



$report['levelPalette']=array_unique ($levelPalette);
utt_checkpoint("EndDrawObjects");


$legend = new GDW\Generators\RichText();
$legendLayer->setGenerator($legend);
$legend->position=array("x"=>$SCREENX-250,"y"=>0,"width"=>250,"height"=>'auto');
$legend->margin=array('left'=>8, 'right'=>8,'top'=>8,'bottom'=>8);
$legend->backgroundColor = $scheme['legendBackground'];
$legend->textColor = $scheme['legendTitle'];
$legend->fontSize = 10;
$legend->font = "Tahoma";
$legend->fontBold = true;

$par = $legend->newParagraph();
$par->lineHeight = 20;
$legend->write("Legend:");

$legend->newParagraph();
$legend->fontBold = false;
$legend->textColor = $scheme['legendText'];
$legend->fontSize = 7;
$blitter->blitIntoRichText($legend,$sprites['playerstart'],1,1,true);
$legend->write(" player spawns");
if($isMH){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['playerstart_2'],1,1,true);
    $legend->write(" additional respawn points");
}
if(isset($flagsPresent)){
    $legend->newParagraph();
    if(isset($report['redflag'])){
        //$legend->newParagraph();
        $blitter->blitIntoRichText($legend,$sprites['flagbase_0'],1,1,true);
        //$legend->write(" red flag");
    }
    if(isset($report['blueflag'])){
        //$legend->newParagraph();
        $blitter->blitIntoRichText($legend,$sprites['flagbase_1'],1,1,true);
        //$legend->write(" blue flag");
    }
    if(isset($report['greenflag'])){
        //$legend->newParagraph();
        $blitter->blitIntoRichText($legend,$sprites['flagbase_2'],1,1,true);
        //$legend->write(" green flag");
    }
    if(isset($report['goldflag'])){
        //$legend->newParagraph();
        $blitter->blitIntoRichText($legend,$sprites['flagbase_3'],1,1,true);
        //$legend->write(" gold flag");
    }
    $legend->write(" team flags");
}

if(isset($jailPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['jailzone_255'],1,1,true);
    $legend->write(" team jails - color of jailed team");
}
if(isset($jailSwitchPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['jailtrigger_255'],1,1,true);
    $legend->write(" release switch - opens jail of the same color");
}
if(isset($monsterEndPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['monsterend'],1,1,true);
    $legend->write(" end of the map");
}
if(isset($teleporterPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['teleporter'],1,1,true);
    $legend->write(" teleporter connected with ");
    $blitter->blitIntoRichText($legend,$sprites['teleporter_dest'],1,1,true);
    $legend->write(" destination by dashed line");
}if(isset($kickerPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['kicker'],1,1,true);
    $legend->write(" kicker");
}
if(isset($monsterPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['monster'],1,1,true);
    $legend->write(" monster (different sizes)");
}
if(isset($thingFactPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['thingfactory'],1,1,true);
    $legend->write(" monsters respawn point (\"factory\")");
}
if(isset($redeemerPresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['warheadlauncher'],1,1,true);
    $legend->write(" redeemer");
}
if(isset($udamagePresent)){
    $legend->newParagraph();
    $blitter->blitIntoRichText($legend,$sprites['udamage'],1,1,true);
    $legend->write(" damage amp");
}

finishImage($image);
$export = $image->export();

//echo "<img src=\"".$export->asDataUrl()."\"/>";
logWrite("Exporting...");

$export->asFile($layoutTargetFile, quality: 9);
logWrite("Saved POI map at '{$layoutTargetFile}'");

file_put_contents($reportTargetFile,json_encode($report));
logWrite("Saved map report at '{$reportTargetFile}'");



function isPolyOffscreen($vert){
    for($i=0;$i<count($vert); $i+=2){
        if($vert[$i] >=0 && $vert[$i]<$GLOBALS['SCREENX'] && $vert[$i+1] >=0 && $vert[$i+1]<$GLOBALS['SCREENY']) return false;
        //echo "VOFF:{$vert[$i]},{$vert[$i+1]}\n";
    }
    return true;
}

function coordRound($coord) {
    return [
        'X'=>round($coord['X']),
        'Y'=>round($coord['Y']),
    ];
}

function finishImage(Image $img){
    global $report, $scheme,$fontsLoc,$mapName;
    logWrite("Finishing image...");
    $GLOBALS['watermarkFunction']($img);
    $mapTitle=(isset($report['title']) && $report['title']?$report['title']:$mapName);
    $finalLayer = $img->getLayerByIndex(-1);
    $gd = $finalLayer->getGDHandle();
    imagettftextlcd($gd,12,0,4,17,$scheme['mapName'],$fontsLoc ."/segoeuib.ttf",$mapTitle);
    if(isset($report['author'])) {
        imagettftextlcd($gd,9,0,4,30,$scheme['mapName'],$fontsLoc ."/segoeuib.ttf"," by {$report['author']}");
    }

}


function polysFailure(string $reason){
    global $mapWorkingDir;
    file_put_contents($mapWorkingDir . "/poly_fail.txt", $reason);
    logWrite("Processing failed with message: $reason");
}