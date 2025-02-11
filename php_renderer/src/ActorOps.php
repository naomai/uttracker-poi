<?php



// NEW BEHAVIOR: RETURNS IDX NRS INSTEAD OF ACTOR REFERENCES!!
function getActorsByPropertyValue($actors,$propName,$propVal){
	$actres=array();
	foreach($actors as $actNum=>$act){ // we can't use &act, iterators don't support references
		if(is_numeric($act)) { 
			$actNum=$act; 
			$act=$GLOBALS['actors'][$act]; 
		}

		
		if(
			(isset($act[$propName]) && strcasecmp($act[$propName],$propVal)===0) ||
			(!isset($act[$propName]) && $propVal==null)
		){
			//$actres[]=&$actors[$actNum];
			$actres[]=$actNum;
		}
	}
	$arr=SplFixedArray::fromArray($actres);
	return $arr;
}
function getActorsByTag(&$actors,$tag){
	return getActorsByPropertyValue($actors,"Tag",$tag);
}

function getSingleActorByTag(&$actors,$tag){
	$actres=array();
	foreach($actors as $actNum=>$act){
		if(is_numeric($act)) { $actNum=$act; $act=$GLOBALS['actors'][$act]; }
		if(isset($act['Tag']) && strcasecmp($act['Tag'],$tag)===0){
			//$actres[]=&$act;
			return $actNum;
		}
	}
	return null;
}

function getActorsByClass(&$actors,$class){
	return getActorsByPropertyValue($actors,"Class",$class);
}

function getActorsInRadius(&$actors,$coords,$rad){
	$actres=array();

	$coordsFilled = $coords+$GLOBALS['emptyCoord'];

	foreach($actors as $actNum=>$act){
		if(is_numeric($act)) { $actNum=$act; $act=$GLOBALS['actors'][$act]; }
		if(!isset($act['Location'])) continue;
		$aloc=$act['Location']+$GLOBALS['emptyCoord'];
		if(vec3Distance($aloc,$coordsFilled)<=$rad){
			$actres[]=$actNum;
		}
	}
	return $actres;
}

function getActorsInTheSameRegion(&$actors,&$refActor,$maxLeafDistance=0){
	$actres=array();
	$ileafRef=(isset($refActor['Region']['iLeaf'])?$refActor['Region']['iLeaf']:0);
	foreach($actors as $actNum=>$act){
		if(is_numeric($act)) { $actNum=$act; $act=$GLOBALS['actors'][$act]; }
		$ileafAct=(isset($act['Region']['iLeaf'])?$act['Region']['iLeaf']:0);
		if(abs($ileafRef-$ileafAct) <= $maxLeafDistance){
			$actres[]=$actNum;
		}
	}
	return $actres;
}

function getCoordProperty(array $actor, string $propName) {
	static $emptyCoord=array("X"=>0,"Y"=>0,"Z"=>0);
	if(!isset($actor[$propName])){
		return $emptyCoord;
	}
	return $actor[$propName] + $emptyCoord;
}

function getScaleProperty(array $actor, string $propName) {
	static $emptyScaleVec=array("X"=>1,"Y"=>1,"Z"=>1);
	if(!isset($actor[$propName]["Scale"])){
		return $emptyScaleVec;
	}
	return $actor[$propName]["Scale"] + $emptyScaleVec;
}

function getRotationProperty(array $actor, string $propName) {
	static $emptyRot=array("Pitch"=>0,"Yaw"=>0,"Roll"=>0);
	if(!isset($actor[$propName])){
		return $emptyRot;
	}
	return $actor[$propName] + $emptyRot;
}

function getProperty(array $actor, string $propName, $default=null) {
	if(!isset($actor[$propName])){
		return $default;
	}
	return $actor[$propName];
}