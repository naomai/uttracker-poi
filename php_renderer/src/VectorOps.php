<?php
// various functions related to 3D and 2D manipulation

define("UNR_ROT_TO_RAD",M_PI/32768);

/* 3D functions 
 * 
 * vec3 is a position, offset and scale vector - 3-element assoc array with keys: X,Y,Z.
 * vec3rot is a rotation vector with keys: Roll,Pitch,Yaw.
 * */

// vec3 vec3Sum(vec3 c1, vec3 c2)
function vec3Sum($c1,$c2){ 
	return array("X"=>$c1['X']+$c2['X'],"Y"=>$c1['Y']+$c2['Y'],"Z"=>$c1['Z']+$c2['Z']);
}

// vec3 vec3Diff(vec3 c1, vec3 c2)
function vec3Diff($c1,$c2){
	return array("X"=>$c1['X']-$c2['X'],"Y"=>$c1['Y']-$c2['Y'],"Z"=>$c1['Z']-$c2['Z']);
}

// !! not a cross multiplication !!
// vec3 vec3Mul(vec3 c1, vec3 c2)
function vec3Mul($c1,$c2){
	return array("X"=>$c1['X']*$c2['X'],"Y"=>$c1['Y']*$c2['Y'],"Z"=>$c1['Z']*$c2['Z']);
}

// scalar multiplication
// scalar vec3MulScal(vec3 c1, scalar s)
function vec3MulScal($c1,$s){
	return array("X"=>$c1['X']*$s,"Y"=>$c1['Y']*$s,"Z"=>$c1['Z']*$s);
}

// perform a callback function on each of the vector elements
// vec3 vec3Op(vec3 c1, vec3 c2, callable function)
function vec3Op($c1,$c2,$function){
	$res['X']=$function($c1['X'],$c2['X']);
	$res['Y']=$function($c1['Y'],$c2['Y']);
	$res['Z']=$function($c1['Z'],$c2['Z']);
	return $res;
}

// scalar vec3Distance(vec3 v1, vec3 v2)
function vec3Distance($v1,$v2){ // in unreal units!!!
	$res=array();
	$re=vec3Diff($v2,$v1);
	$dist=pow(pow($re['X'],2) + pow($re['Y'],2) + pow($re['Z'],2),1/2);
	
	return $dist;
}

// scalar vec3Angle(vec3 v1, vec3 v2)
function vec3Angle($v1,$v2){ // in radians
	$res=array();
	$re=vec3Diff($v2,$v1);
	// ROLL
	$res['Roll']=atan2($re['Z'],$re['Y']);
	// PITCH
	$res['Pitch']=atan2($re['X'],$re['Z']);
	// YAW
	$res['Yaw']=atan2($re['Y'],$re['X']);
	return $res;
}

// old function for transforming the vertices
// THE MATRICES BELOW ARE PROBABLY INCORRECT, 
// SEE qb_UEVertTransform INSTEAD
function rotate($re,$rot){
	$yaw=((float)$rot['Yaw'])/32768*M_PI;
	$pitch=((float)$rot['Pitch'])/32768*M_PI;
	$roll=((float)$rot['Roll'])/32768*M_PI;
	
	
	$sina=sin($yaw); $cosa=cos($yaw);
	$sinb=sin($pitch); $cosb=cos($pitch);
	$sing=sin($roll); $cosg=cos($roll);
	
	/* time for some math:
		roll  matrix: ((1,0,0,0),(0,cos(g),-sin(g),0),(0,sin(g),cos(g),0),(0,0,0,1))
		pitch matrix: ((cos(b),0,sin(b),0),(0,1,0,0),(-sin(b),0,cos(b),0),(0,0,0,1))
		yaw   matrix: ((cos(a),sin(a),0,0),(-sin(a),cos(a),0,0),(0,0,1,0),(0,0,0,1))
	 */
	
	$nre['X'] = $re['X']*($cosa*$cosb) + $re['Y']*($cosa*$sinb*$sing-$sina*$cosg) + $re['Z']*(-$cosa*$sinb*$cosg-$sina*$sing);
	$nre['Y'] = $re['X']*($sina*$cosb) + $re['Y']*($sina*$sinb*$sing+$cosa*$cosg) + $re['Z']*(-$sina*$sinb*$cosg+$cosa*$sing);
	$nre['Z'] = $re['X']*(   $sinb   ) + $re['Y']*(    -$cosb    *     $sing    ) + $re['Z']*(     $cosb    *    $cosg     );
	
	
	return $nre;
}

/* 2D 
 * 
 * vec2 - 2-element assoc array with keys: X,Y.
 * */

// vec2 vec2Sum(vec2 c1, vec2 c2)
function vec2Sum($c1,$c2){
	return array("X"=>$c1['X']+$c2['X'],"Y"=>$c1['Y']+$c2['Y']);
}

// vec2 vec2Mul(vec2 c1, vec2 c2)
function vec2Diff($c1,$c2){
	return array("X"=>$c1['X']-$c2['X'],"Y"=>$c1['Y']-$c2['Y']);
}

// vec2 vec2Mul(vec2 c1, vec2 c2)
function vec2Mul($c1,$c2){
	return array("X"=>$c1['X']*$c2['X'],"Y"=>$c1['Y']*$c2['Y']);
}

function vec2Angle($origin,$point){
	
	$point=vec2Diff($point,$origin);
	
	// ROLL
	//$dist=pow(pow($re['Z'],2) + pow($re['Y'],2),1/2);
	return atan2($point['Y'],$point['X']);
}

/* PHP-QB related functions 
 * 
 * QBVec3 - 3-element array (keys: 0,1,2) which can be passed as argument to qb-compiled function
 * 
 * 
 * */

// 
function vec3ToFlatvec3($c){
	return array((float)$c['X'],(float)$c['Y'],(float)$c['Z']);
}
function uescaleToScaleMatrix($c){
	return array(
		array((float)$c['X'],0,0),
		array(0,(float)$c['Y'],0),
		array(0,0,(float)$c['Z'])
	);
}

function vec3rotToFlatvec3($c){
	//return array((float)$c['Yaw']*UNR_ROT_TO_RAD,(float)$c['Pitch']*UNR_ROT_TO_RAD,(float)$c['Roll']*UNR_ROT_TO_RAD);
	return array(
		cyclicModulo($c['Yaw']  * UNR_ROT_TO_RAD, 2*M_PI),
		cyclicModulo($c['Pitch']* UNR_ROT_TO_RAD, 2*M_PI),
		cyclicModulo($c['Roll'] * UNR_ROT_TO_RAD, 2*M_PI)
	);
}
function flatvec3ToVec3($cx){
	return array("X"=>$cx[0],"Y"=>$cx[1],"Z"=>$cx[2]);
}


// AAAAND.. The most important one: 
// calculate the position of vertices according to UE Brush properties
// QBVec3 UEVertTransform(QBVec3 verts[],Vec3 mainScaleVec,Vec3 postScaleVec,
//     Vec3 tempScaleVec,Vec3rot rot,Vec3 piv,Vec3 coffset)

/* With a little help from: http://wiki.beyondunreal.com/Legacy:T3D_Brush
	FOR each vertex of each polygon of parsed brush DO:
		do MainScale ... x *= MainScale[x], y *= MainScale[y], z *= MainScale[z]
		do translation (-PrePivot[x], -PrePivot[y], -PrePivot[z])
		do rotation Yaw, Pitch, Roll
		do PostScale ... x *= PostScale[x], y *= PostScale[y], z *= PostScale[z]
		do TempScale ... x *= TempScale[x], y *= TempScale[y], z *= TempScale[z]
		do translation (Location[x], Location[y], Location[z])
	ENDFOR
	
	This is actually wrong, the prepivot translation goes before mainscale
 */
 // '16-03-25 replaced QB dependency

function UEVertTransform(&$verts, $mainScaleVec, $postScaleVec, $tempScaleVec,
		$rot, $piv, $coffset){
	
	$rotFlat = vec3rotToFlatvec3($rot);
	$pivotFlat = vec3ToFlatvec3($piv);
	$offsetFlat = vec3ToFlatvec3($coffset);

	for($i=0; $i<count($verts); $i++){
		$verts[$i][0]-=$pivotFlat[0];
		$verts[$i][1]-=$pivotFlat[1];
		$verts[$i][2]-=$pivotFlat[2];
	}
	$verts=matrixMult($verts,uescaleToScaleMatrix($mainScaleVec));
	
	$sina=sin($rotFlat[0]); $cosa=cos($rotFlat[0]); // yaw
	$sinb=sin($rotFlat[1]); $cosb=cos($rotFlat[1]); // pitch
	$sing=sin($rotFlat[2]); $cosg=cos($rotFlat[2]); // roll
	
	$rotMatrixA = array( //{{cosa,sina,0},{-sina,cosa,0},{0,0,1}}
		array( $cosa,  $sina,  0    ),
		array(-$sina,  $cosa,  0    ),
		array( 0    ,  0    ,  1    )
	);
	$rotMatrixB = array( //{{cosb,0,sinb},{0,1,0},{-sinb,0,cosb}}
		array( $cosb,  0    ,  $sinb),
		array( 0    ,  1    ,  0    ),
		array(-$sinb,  0    ,  $cosb),
	);
	$rotMatrixG = array( //{{1,0,0},{0,cosg,-sing},{0,sing,cosg}}
		array( 1    ,  0    ,  0    ),
		array( 0    ,  $cosg,  $sing),
		array( 0    , -$sing,  $cosg)
	);

	$rotMatrix = matrixMult(matrixMult($rotMatrixB, $rotMatrixG),$rotMatrixA);

	$verts=matrixMult($verts,$rotMatrix);

	$verts=matrixMult($verts,uescaleToScaleMatrix($postScaleVec));
	$verts=matrixMult($verts,uescaleToScaleMatrix($tempScaleVec));
	//print_r($verts);
	
	for($i=0; $i<count($verts); $i++){
		$verts[$i][0]+=$offsetFlat[0];
		$verts[$i][1]+=$offsetFlat[1];
		$verts[$i][2]+=$offsetFlat[2];
	}
}



function matrixMult($m1, $m2){ // MINIMAL CHECKING!!
	
	$m1Rows = count($m1);    // n
	$m1Cols = count($m1[0]); // m
	$m2Rows = count($m2);    // m
	$m2Cols = count($m2[0]); // p

	
	
	if($m1Cols != $m2Rows){
		// TODO error sizes not matching
	}
	
	//$result = new SplFixedArray($m1Rows); //a bit slower than array (850ms vs 780ms) (as of PHP7.0.5)
	$result = array();

	for($i = 0; $i < $m1Rows; $i++){
		//$result[$i] = new SplFixedArray($m2Cols);
		$result[$i] = array();

		for($j = 0; $j < $m1Cols; $j++){
			$result[$i][$j] = 0;
			for($r = 0; $r < $m2Rows; $r++){
				$result[$i][$j] += $m1[$i][$r] * $m2[$r][$j];
			}
		}

	}
	
	return $result;
}

function drawMat($m){
	$colsWidth = array();
	for($y = 0; $y < count($m); $y++){
		for($x = 0; $x < count($m); $x++){
			if(!isset($colsWidth[$x])) 
				$colsWidth[$x]=0;
			
			$colsWidth[$x] = max($colsWidth[$x],strlen($m[$y][$x]));
			
		}
	}
	
	for($y = 0; $y < count($m); $y++){
		echo "|";
		for($x = 0; $x < count($m); $x++){
			echo str_pad($m[$y][$x],$colsWidth[$x]+1," ",STR_PAD_LEFT);
			
		}
		echo "| \n";
	}
	
	
}
function drawVec($m){
	$colWidth = 0;
	for($y = 0; $y < count($m); $y++){
		$colWidth = max($colWidth,strlen($m[$y]));
	}
	
	for($y = 0; $y < count($m); $y++){
		echo "|";
		echo str_pad($m[$y],$colWidth+1," ",STR_PAD_LEFT);

		echo "| \n";
	}
	
	
}


//http://php.net/manual/en/function.fmod.php#110824
function cyclicModulo($a, $b) { 
    return $a - $b * floor($a / $b);
} 


