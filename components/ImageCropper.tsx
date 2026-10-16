import React, { useState, useRef } from 'react';
import ReactCrop, { Crop, PixelCrop, centerCrop, makeAspectCrop } from 'react-image-crop';
import { Check, X } from 'lucide-react';

interface ImageCropperProps {
  imageUrl: string;
  onCancel: () => void;
  onSave: (croppedImageUrl: string) => void;
}

// Helper to center the crop initially
function centerAspectCrop(mediaWidth: number, mediaHeight: number, aspect?: number) {
  const targetAspect = aspect || 16 / 9;
  const crop = makeAspectCrop(
    {
      unit: '%',
      width: 90
    },
    targetAspect,
    mediaWidth,
    mediaHeight
  );
  
  return centerCrop(crop, mediaWidth, mediaHeight);
}

export const ImageCropper: React.FC<ImageCropperProps> = ({ imageUrl, onCancel, onSave }) => {
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const imgRef = useRef<HTMLImageElement>(null);

  const onImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { width, height } = e.currentTarget;
    setCrop(centerAspectCrop(width, height, undefined));
  };

  const handleSave = () => {
    if (completedCrop && imgRef.current) {
      const canvas = document.createElement('canvas');
      const scaleX = imgRef.current.naturalWidth / imgRef.current.width;
      const scaleY = imgRef.current.naturalHeight / imgRef.current.height;
      const ctx = canvas.getContext('2d');

      if (!ctx) return;

      const pixelRatio = window.devicePixelRatio;
      canvas.width = completedCrop.width * scaleX;
      canvas.height = completedCrop.height * scaleY;

      ctx.imageSmoothingQuality = 'high';

      const cropX = completedCrop.x * scaleX;
      const cropY = completedCrop.y * scaleY;
      const cropWidth = completedCrop.width * scaleX;
      const cropHeight = completedCrop.height * scaleY;

      ctx.drawImage(
        imgRef.current,
        cropX,
        cropY,
        cropWidth,
        cropHeight,
        0,
        0,
        cropWidth,
        cropHeight
      );

      const base64 = canvas.toDataURL('image/png');
      onSave(base64);
    } else {
        // If no crop happened, just return original
        onSave(imageUrl);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-8 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-700 p-4 rounded-xl shadow-2xl flex flex-col gap-4 max-h-[90vh] max-w-[90vw]">
        <div className="flex justify-between items-center border-b border-zinc-800 pb-2">
            <h3 className="font-typewriter text-zinc-100">CROP EVIDENCE</h3>
            <div className="flex gap-2">
                <button onClick={onCancel} className="p-2 hover:bg-zinc-800 rounded text-red-400">
                    <X size={20} />
                </button>
                <button onClick={handleSave} className="p-2 bg-zinc-800 hover:bg-zinc-700 rounded text-green-400">
                    <Check size={20} />
                </button>
            </div>
        </div>
        
        <div className="overflow-auto flex-1 flex justify-center bg-zinc-950/50 rounded border border-zinc-800 p-2">
            <ReactCrop 
                crop={crop} 
                onChange={(c) => setCrop(c)} 
                onComplete={(c) => setCompletedCrop(c)}
                className="max-h-[70vh]"
            >
                <img 
                    ref={imgRef} 
                    src={imageUrl} 
                    alt="Crop me" 
                    onLoad={onImageLoad}
                    className="max-w-full max-h-[70vh] object-contain"
                />
            </ReactCrop>
        </div>
        <p className="text-zinc-500 text-xs text-center font-mono">Drag to crop. Click Check to save.</p>
      </div>
    </div>
  );
};