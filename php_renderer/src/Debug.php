<?php



function utt_checkpoint($name="") {
	static $cpStart = 0, $cp = 0;
	if(!$GLOBALS['debug_checkpoint']) return;
	$timeStop=microtime(true);
	$lineNum = debug_backtrace()[0]['line'];
	if($cp!=0){
		logWrite( "Checkpoint $name#$lineNum: ".round(($timeStop-$cpStart)*1000)."ms (+".round(($timeStop-$cp)*1000)."ms)");
	}else{
		$cpStart=microtime(true);
	}
	$cp=microtime(true);
}


function logWrite($text) {
	$timestamp = (new DateTime())->format("Y.m.d H:i:s.v");
	echo "[$timestamp] $text\r\n";
}