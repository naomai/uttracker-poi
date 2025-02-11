<?php
//require_once __DIR__ . "/../config.php";

use Naomai\PHPLayers\Image;

// FONTS
$fontsPathWWW = __DIR__ . "/fonts";

$fontsLoc=$fontsPathWWW;

// OPTIONS
$defaultProjectionMode = "isometric_30deg";
$defaultColorScheme = "classic";
$imageSizeNormalX = 864;
$imageSizeNormalY = 486;
$imageSizeBigX = 2560;
$imageSizeBigY = 1440;

// add watermark to image
$watermarkFunction = function(Image $img){
	$watermarkLayer = $img->newLayer()->importFromFile(__DIR__ . "/watermark.png");
	$watermarkLayer
		->selectSurface()
		->move(anchor: "bottom right", x: -20, y: -20)
		->apply();
};

// PROJECTION MODE CALLBACKS
$renderModes=array(
	"ort"=>"orthographic",
	"iso3"=>"isometric_30deg",
	"tibia"=>"tibia"
);

// MISC
$debug_checkpoint=false;
$dateformat="d-m-Y H:i";

const UTT_MAPREPORT_VER=200;
