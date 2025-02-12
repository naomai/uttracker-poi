<?php

require_once __DIR__ . "/Helpers.php";

$graph_hour_id=date("d-m-y-G");

function verticaltextlikejapanese($im,$size,$x,$y,$c,$t,$aligntop=true){
	$ts=strlen($t);
	$yoffs=($aligntop?-$size*6:6*$size*$ts);
	for($i=0; $i<$ts; $i++){
		uttimagetxt($im,$size,0,$x,$y+$i*$size*6-$yoffs,$c,$t[$i]);
		
	}
}


function getalphaat($im,$x,$y){
	//center
	$a=(@imagecolorat($im,$x,$y) >> 23);
	$b=(@imagecolorat($im,$x,$y+1) >> 23);
	$c=(@imagecolorat($im,$x,$y+2) >> 23);
	// neighbor
	$na=((@imagecolorat($im,$x+1,$y)>>24) + (@imagecolorat($im,$x+1,$y)>>24)) >> 1;
	$nb=((@imagecolorat($im,$x+1,$y+1)>>24) + (@imagecolorat($im,$x+1,$y+1)>>24)) >> 1;
	$nc=((@imagecolorat($im,$x+1,$y+2)>>24) + (@imagecolorat($im,$x+1,$y+2)>>24)) >> 1;
	$a+=$na;
	$b+=$nb;
	$c+=$nc;
	
	$ax=($a+$b+$c);
	$mi=min($a,$b,$c);
	$ma=max($a,$b,$c);
	$az=pickclosest($ax/3,$mi,$ma);
	// right neighbor
	$av=$na >> 1;
	$av+=$nb >> 1;
	$av+=$nc >> 2;
	//return $a/5.5;
	return $az/4+$av+0x02; //numrange($az,0,255);
}


function textWithShadow($layer, $x,$y,$text,$params=array(),$color=null){
	global $textRenderer;
	$alpha=($color==null ? 0x00000000 : $color&0x7F000000);
	
	$isDark = (($color & 0xFF0000) < 0x170000) && (($color & 0xFF00) < 0x1000) && (($color & 0xFF) < 0x20);
	
	if(!$isDark){
		//$layer->paint->text( $x+1,$y+1,$text,$params,$alpha);
		$params['shadow']=true;
	}
	$params['color'] = $color;
	//$layer->paint->text( $x,$y,$text,$params,$color);
	$textRenderer->write(round($x), round($y), $text,...$params);
	
}


// subpixel rendering, yay!

function imagettftextlcd(&$im,$size,$rot,$ix,$iy,$color,$font,$tx){
	
	//we're painting the text that's 3 times the size of the desired size
	//then we're converting every 3 pixels of the larger text to make a RGB pixel
	
	if(!file_exists($font)) {
		trigger_error("imagettftextlcd(): Invalid font file",E_WARNING);
		return;
	}
	
	$horiz_blur=0.5; // text smoothing; 0: sharp, 1: totally blurred
	
	// increase width for blurred text
	// if you skipped the logarithms math lessons, then skip reading to the line 57.
	$horiz_blur_addx=round(log(0.1)/log($horiz_blur)); 
	
	$bx=imagettfbbox($size*3,$rot,$font,$tx); // get the dimensions of rendered text (in 3x scale)
	
	$txtlx=min($bx[0],$bx[2],$bx[4],$bx[6]); // X of point closest to the left edge
	$txtrx=max($bx[0],$bx[2],$bx[4],$bx[6]); // X ----\\---- right edge
	$txtuy=min($bx[1],$bx[3],$bx[5],$bx[7]); // Y ----\\---- top edge
	$txtly=max($bx[1],$bx[3],$bx[5],$bx[7]); // Y ----\\---- bottom edge
	
	$txtw=$txtrx-$txtlx+$horiz_blur_addx*3; // width of the large text (3x scale)
	$txth=$txtly-$txtuy; // height
	
	$txtwa=$txtw+9-($txtw%3); // size of the large box we're going to paint the 3x text in
	$txtha=$txth+9-($txth%3); // +18 and +9 are there to avoid some nasty bugs
	
	
	$txtwr=$txtw/3; // size of the "small" text box (real size = scaled down to 1x)
	$txthr=$txth/3; 
	
	$imtmp=imagecreatetruecolor($txtwa,$txtha); // "large text box"
		
	imagefill($imtmp,0,0,0x7f000000);
	
	imagettftext($imtmp,$size*3,$rot,-$txtlx+3, -$txtuy+3, 0x00000000,$font,$tx);
	//imagettftext($imtmp,$size*3,$rot,-$txtlx+4, -$txtuy+3, 0x20000000,$font,$tx);
	
	
	$cr=(($color>>16) & 0xFF)/255; // we're calculating a float value (0.0-1.0) 
	$cg=(($color>>8) & 0xFF)/255; // of desired text color
	$cb=(($color) & 0xFF)/255; // it will be used later in a multiplication 
	

	$horiz_blur_neg=1-$horiz_blur;
	
	for($y=0;$y<$txth+6; $y+=3){
		
		$previousb=255;// value of B color from previous pixel; text smoothing
		
		for($x=3;$x<$txtw; $x+=3){
			
			//this grabs the values of pixels in "large text box"
			//the values of r,g,b are CHARs, 0=opaque, 255=transparent
			$r=getalphaat($imtmp,$x,$y)*$horiz_blur_neg+$previousb*$horiz_blur;
			$g=getalphaat($imtmp,$x+1,$y)*$horiz_blur_neg+$r*$horiz_blur;
			$b=getalphaat($imtmp,$x+2,$y)*$horiz_blur_neg+$g*$horiz_blur;
			
			// location of currently processed pixel in "destination" image
			$absx=round($ix+($x+$txtlx)/3);
			$absy=round($iy+($y+$txtuy)/3);
			
			if($absx<0 || $absy<0) continue; // out of bounds, just in case

			//grab the color of currently processed pixel in "destination" image
			$cd=@imagecolorsforindex ($im,@imagecolorat($im,$absx,$absy));
			
			//burn the black "mask" in destination image
			$rd=clamp($cd['red']*$r/255,0,255);
			$gd=clamp($cd['green']*$g/255,0,255);
			$bd=clamp($cd['blue']*$b/255,0,255);
			
			//add the value of desired text color multiplied by alpha of currently processed pixel
			$rd+=$cr*(255-$r);
			$gd+=$cg*(255-$g);
			$bd+=$cb*(255-$b);
			
			$colx = ((round($rd)<<16) | (round($gd)<<8) | round($bd));
			
			imagesetpixel($im,$absx,$absy,$colx);
			
			//for smoothing
			$previousb=$b;
			
		}
	}
	//imagesavealpha($imtmp,true);
	//imagepng($imtmp);
	imagedestroy($imtmp);
}



//http://stackoverflow.com/a/3642787
function ColorHSLToRGB($h, $s, $l){
	
	$r = $l;
	$g = $l;
	$b = $l;
	$v = ($l <= 0.5) ? ($l * (1.0 + $s)) : ($l + $s - $l * $s);
	if ($v > 0){
		
		$m = $l + $l - $v;
		$sv = ($v - $m ) / $v;
		$h *= 6.0;
		$sextant = floor($h);
		$fract = $h - $sextant;
		$vsf = $v * $sv * $fract;
		$mid1 = $m + $vsf;
		$mid2 = $v - $vsf;
		
		switch ($sextant){
			case 0:
			$r = $v;
			$g = $mid1;
			$b = $m;
			break;
			case 1:
			$r = $mid2;
			$g = $v;
			$b = $m;
			break;
			case 2:
			$r = $m;
			$g = $v;
			$b = $mid1;
			break;
			case 3:
			$r = $m;
			$g = $mid2;
			$b = $v;
			break;
			case 4:
			$r = $mid1;
			$g = $m;
			$b = $v;
			break;
			case 5:
			$r = $v;
			$g = $m;
			$b = $mid2;
			break;
		}
	}
	return array('r' => round($r * 255.0), 'g' => round($g * 255.0), 'b' => round($b * 255.0));
}

function mixColors($col1, $col2, $amount=0.5){
	$amountN = 1 - $amount;
	//$a = clamp((($col1>>24) & 0x7F) * $amountN + (($col2>>24) & 0x7F) * $amount,0,127);
	/*$a1 = (($col1>>24) & 0x7F)/127;
	$a2 = (($col2>>24) & 0x7F)/127;
	$a = ($a1 + (1-$a1)*$a2)*255;*/
	$r = clamp((($col1>>16) & 0xFF) * $amountN + (($col2>>16) & 0xFF) * $amount,0,255);
	$g = clamp((($col1>> 8) & 0xFF) * $amountN + (($col2>> 8) & 0xFF) * $amount,0,255);
	$b = clamp((($col1>> 4) & 0xFF) * $amountN + (($col2>> 4) & 0xFF) * $amount,0,255);
	return /*($a << 24) | */($r<<16) | ($g<<8) | $b;
}


