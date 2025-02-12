<?php
namespace{
	//require_once __DIR__ . "/php-layers/Image.php";
}
namespace Naomai\PHPLayers{

    use GdImage;
    use Naomai\PHPLayers\SpriteBlitter\SpriteDef;
	class SpriteBlitter{
		protected $loadedSprites = array();
		public $resample = true;
		protected GdImage $destGD;
		
		public function __construct(protected Layer $destLayer) {
			$this->destGD = $destLayer->getGDHandle();

		}
		
		/*public function __destruct(){
			foreach($loadedSprites as $spriteDef){
				imagedestroy($spriteDe->gd);
			}
		}*/
		
		public function addSprite($fileName){
			$sprite = new SpriteDef($fileName);
			$loadedSprites[] = $sprite;
			return $sprite;
		}
		
		public function blit($sprite, $x, $y, $scaleX=1, $scaleY=1){
			$this->blitGD($sprite->gd,$x, $y, $scaleX, $scaleY);
		}
		
		public function blitWithShadow($sprite, $x, $y, $scaleX=1, $scaleY=1){
			$this->blitColorMask($sprite, 0x000000, $x+1, $y+1, $scaleX, $scaleY);
			$this->blit($sprite,$x, $y, $scaleX, $scaleY);
		}
		
		public function blitColorMask($sprite, $maskColor, $x, $y, $scaleX=1, $scaleY=1){
			/*if(!is_object($sprite)){
				//print_r(debug_backtrace());
				file_put_contents("bliteer.txt", json_encode(debug_backtrace()));
				//sleep(5);
			}*/
			$sprite->createColorMask($maskColor);
			
			$this->blitGD($sprite->tempMask,$x, $y, $scaleX, $scaleY);
		}
		
		protected function blitGD($gdSprite, $x, $y, $scaleX=1, $scaleY=1){
			$sx = imagesx($gdSprite);
			$sy = imagesy($gdSprite);
			
			$imageCopyParams = array(
				$this->destGD, $gdSprite, 
				round($x), round($y),
				0,0,
				$sx * $scaleX, $sy * $scaleY,
				$sx, $sy			
			);
			
			if($this->resample){
				call_user_func_array('imagecopyresampled',$imageCopyParams);
			}else{
				call_user_func_array('imagecopyresized',$imageCopyParams);
			}
		}
		public function blitIntoRichText($richText, $sprite, $scaleX=1, $scaleY=1, $withShadow=false){

			if(class_exists("\\Naomai\\PHPLayers\\Generators\\RichTextNode")){
				$spriteRT = $richText->insertNodeOfType('\\Naomai\\PHPLayers\\Generators\\SpriteNode');
				$spriteRT->sprite = $sprite;
				$spriteRT->blitter = $this;
				$spriteRT->withShadow = $withShadow;
			}
		}
		
	}
}
namespace Naomai\PHPLayers\SpriteBlitter{
	class SpriteDef{
		public $file,$name,$width,$height,$tempMaskLastColor=-1;

		public \GdImage $gd;
		public ?\GdImage $tempMask=null;
		
		
		public function __construct($fileName){
			$this->gd = self::loadImageFromAnyFormat($fileName);
			$this->file=$fileName;
			$this->name=pathinfo($fileName, PATHINFO_FILENAME);
			$this->width=imagesx($this->gd);
			$this->height=imagesy($this->gd);
		}
			
			
		public function __destruct(){
			/*if(is_resource($this->gd) && get_resource_type ($this->gd)=="gd"){
				imagedestroy($this->gd);
			}
			if(is_resource($this->tempMask) && get_resource_type ($this->tempMask)=="gd"){
				imagedestroy($this->tempMask);
			}*/
		}
		
		public function createColorMask(int $maskColor){
			if($maskColor == $this->tempMaskLastColor){
				return;
			}
			if(!is_resource($this->tempMask) || !($this->tempMask instanceof \GdImage)){
				$this->tempMask = imagecreatetruecolor($this->width, $this->height);
			}
			imagealphablending($this->tempMask, false); // overwrite old content
			$sx = $this->width;
			$sy = $this->height;
			
			$alphaMask = (0x7F - (($maskColor >> 24) & 0x7F)) / 0x7F;
					
			for($y=0; $y<$sy; $y++){
				for($x=0; $x<$sx; $x++){
					$pix = imagecolorat ($this->gd, $x, $y);
					$alpha  = 0x7F - (($pix >>24) & 0x7F);
					$alpha *= $alphaMask;
					$alpha  = 0x7F - floor($alpha);
					$newColor = $maskColor & 0xFFFFFF | ($alpha << 24);
					imagesetpixel($this->tempMask, $x, $y, $newColor);
				}
			}
			$this->tempMaskLastColor = $maskColor;
		}
		
		static protected function loadImageFromAnyFormat($fileName){
			if(is_string($fileName) && file_exists ($fileName)){
				return imagecreatefromstring(file_get_contents($fileName));
			}
		}
	}
}
namespace Naomai\PHPLayers\Generators{
	use Naomai\PHPLayers\SpriteBlitter;
	use Naomai\PHPLayers\SpriteBlitter\SpriteDef;
	if(class_exists("\\Naomai\\PHPLayers\\Generators\\RichText")){
		class SpriteNode extends RichTextNode{
			public $sprite, $blitter;
			public $scaleX=1, $scaleY=1, $withShadow=false;
			public function render(){ // no rendering here, we're just asking GDWRichText for coords
				if($this->sprite instanceof SpriteDef && $this->blitter instanceof SpriteBlitter){
					$rect = array(
						'gd'=>null, 
						'rect'=>array(
							array('x'=>0,'y'=>0,'width'=>$this->sprite->width*$this->scaleX,'height'=>$this->sprite->height*$this->scaleY)
						)
					);
					return $rect;
				}else{
					return array('gd'=>null,'rect'=>array());
				}
			}
			
			public function notifyRenderResult($rect){ // actual drawing
				//print_r($rect);die;
				$docGD = $rect['gdResult'];
				$myRect = reset($rect['rect']);
				$scaleX = $myRect['width']  / $this->sprite->width; // adjust to any changes that RichText commands us
				$scaleY = $myRect['height'] / $this->sprite->height;		
				//print_r($myRect);die;
				$blitterArgs = array($this->sprite, $myRect['layerX'], $myRect['layerY'], $scaleX, $scaleY);
				if($this->withShadow)
					call_user_func_array(array($this->blitter,'blitWithShadow'), $blitterArgs);
				else
					call_user_func_array(array($this->blitter,'blit'), $blitterArgs);
			}
			
		}
	}
}
