<?php

function clamp($v,$min,$max){
	return max($min,min($max,$v));	
}

function pickclosest($ref,$a,$b){
	return (abs($ref-$a)<abs($ref-$b)?$a:$b);
}