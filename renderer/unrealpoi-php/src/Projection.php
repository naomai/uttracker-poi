<?php
/* PROJECTION FUNCTIONS

projav is used to calculate the proper offset for map to be in center of viewport
TODO description
*/

function proj_isometric_30deg($vert){
	global $scale,$offsetX,$offsetY;
	$res['X']=round(($vert['X'] * 2 - $vert['Y'])*$scale+$offsetX);
	$res['Y']=round(($vert['Y']+ $vert['X'] /2 - $vert['Z']*2)*$scale+$offsetY);
	
	return $res;
}
function projav_isometric_30deg(){
	global $virtW,$virtH,$mapSizeX,$mapSizeY,$mapSizeZ,$virtOffX,$virtOffY,$dispOffset, $scale;
	$virtW=($mapSizeX*2+$mapSizeY);
	$virtH=($mapSizeY+$mapSizeX/2+$mapSizeZ);

	$virtOffX=($dispOffset['X']+$dispOffset['Y']/2);
	$virtOffY=($dispOffset['Y']+$dispOffset['X']/2+$dispOffset['Z']*2)/2;
}

function proj_orthographic($vert){
	global $scale,$offsetX,$offsetY;
	$res['X']=round(($vert['X'])*$scale+$offsetX);
	$res['Y']=round(($vert['Y'])*$scale+$offsetY);
	
	return $res;
}
function projav_orthographic(){
	global $virtW,$virtH,$mapSizeX,$mapSizeY,$mapSizeZ,$virtOffX,$virtOffY,$dispOffset;
	$virtW=($mapSizeX);
	$virtH=($mapSizeY);

	$virtOffX=($dispOffset['X']);
	$virtOffY=($dispOffset['Y']);
}

function proj_tibia($vert){
	global $scale,$offsetX,$offsetY;
	$res['X']=round(($vert['X']-$vert['Z']/2)*$scale+$offsetX);
	$res['Y']=round(($vert['Y']-$vert['Z']/2)*$scale+$offsetY);
	
	return $res;
}
function projav_tibia(){
	global $virtW,$virtH,$mapSizeX,$mapSizeY,$mapSizeZ,$virtOffX,$virtOffY,$dispOffset;
	$virtW=($mapSizeX+$mapSizeZ/2);
	$virtH=($mapSizeY+$mapSizeZ/2);

	$virtOffX=($dispOffset['X']-$dispOffset['Z']/2);
	$virtOffY=($dispOffset['Y']-$dispOffset['Z']/2);
}
