import React, { useRef, useState } from 'react';
import { BoardNode } from '../types.tsx';
import { X, Sparkles, Link, Copy, Crop, RotateCw } from 'lucide-react';

interface BoardItemProps {
  node: BoardNode;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onMove: (id: string, x: number, y: number) => void;
  onRotate: (id: string, angle: number) => void;
  onDelete: (id: string) => void;
  onDuplicate: (node: BoardNode) => void;
  onConnectStart: (id: string) => void;
  onBrainstorm: (node: BoardNode) => void;
  onCropStart: (node: BoardNode) => void;
  isConnecting: boolean;
}

export const BoardItem: React.FC<BoardItemProps> = ({
  node,
  isSelected,
  onSelect,
  onMove,
  onRotate,
  onDelete,
  onDuplicate,
  onConnectStart,
  onBrainstorm,
  onCropStart,
  isConnecting
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isRotating, setIsRotating] = useState(false);
  
  const dragStartPos = useRef<{ x: number; y: number } | null>(null);
  const elementRef = useRef<HTMLDivElement>(null);

  // --- Drag Logic ---
  const handlePointerDown = (e: React.PointerEvent) => {
    // Ignore if clicking specific controls
    if ((e.target as HTMLElement).closest('button') || (e.target as HTMLElement).closest('.rotate-handle')) return;
    
    e.stopPropagation();
    onSelect(node.id);
    
    if (isConnecting) {
      onConnectStart(node.id);
      return;
    }

    setIsDragging(true);
    dragStartPos.current = { x: e.clientX - node.x, y: e.clientY - node.y };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (isDragging && dragStartPos.current) {
      e.stopPropagation();
      const newX = e.clientX - dragStartPos.current.x;
      const newY = e.clientY - dragStartPos.current.y;
      onMove(node.id, newX, newY);
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    setIsDragging(false);
    dragStartPos.current = null;
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
  };

  // --- Rotate Logic ---
  const handleRotateStart = (e: React.PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setIsRotating(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handleRotateMove = (e: React.PointerEvent) => {
    if (!isRotating || !elementRef.current) return;
    e.stopPropagation();

    // Calculate center of the element
    const rect = elementRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Calculate angle
    const mouseX = e.clientX;
    const mouseY = e.clientY;
    
    // Math.atan2 returns angle in radians (-PI to PI)
    // Convert to degrees
    const radians = Math.atan2(mouseY - centerY, mouseX - centerX);
    const degrees = radians * (180 / Math.PI);
    
    // Offset by 90 degrees because 0 degrees is usually "3 o'clock" but our handle is at "12 o'clock" relative to rotation 0
    // Actually, just syncing it to the mouse position is enough.
    // Let's add 90 deg so dragging from top feels natural
    onRotate(node.id, degrees + 90);
  };

  const handleRotateEnd = (e: React.PointerEvent) => {
    setIsRotating(false);
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
  };


  // Styles based on node type
  const baseStyles = "absolute flex flex-col shadow-xl transition-shadow duration-200 group";
  const selectedStyles = isSelected ? "ring-2 ring-red-500 z-50" : "z-10 hover:z-40";
  const rotationStyle = { transform: `rotate(${node.rotation}deg)` };

  return (
    <div
      ref={elementRef}
      className={`${baseStyles} ${selectedStyles} cursor-grab active:cursor-grabbing`}
      style={{
        left: node.x,
        top: node.y,
        width: node.width,
        height: node.height || 'auto',
        ...rotationStyle
      }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      {/* Controls (visible on hover or selection) */}
      {(isSelected || isDragging) && !isConnecting && (
        <>
            {/* Top Toolbar */}
            <div className="absolute -top-12 left-1/2 -translate-x-1/2 flex justify-center gap-1 z-50 p-2">
            <button 
                onClick={() => onConnectStart(node.id)}
                className="p-1.5 bg-zinc-800 text-red-400 rounded-full hover:bg-zinc-700 shadow-lg border border-zinc-600 transition-transform hover:scale-110"
                title="Link"
            >
                <Link size={14} />
            </button>
            
            <button 
                onClick={() => onDuplicate(node)}
                className="p-1.5 bg-zinc-800 text-blue-400 rounded-full hover:bg-zinc-700 shadow-lg border border-zinc-600 transition-transform hover:scale-110"
                title="Duplicate"
            >
                <Copy size={14} />
            </button>

            {node.type === 'image' && (
                <button 
                onClick={() => onCropStart(node)}
                className="p-1.5 bg-zinc-800 text-green-400 rounded-full hover:bg-zinc-700 shadow-lg border border-zinc-600 transition-transform hover:scale-110"
                title="Crop Image"
                >
                <Crop size={14} />
                </button>
            )}

            {node.type === 'note' && (
                <button 
                onClick={() => onBrainstorm(node)}
                className="p-1.5 bg-zinc-800 text-purple-400 rounded-full hover:bg-zinc-700 shadow-lg border border-zinc-600 transition-transform hover:scale-110"
                title="Brainstorm"
                >
                <Sparkles size={14} />
                </button>
            )}
            
            <button 
                onClick={() => onDelete(node.id)}
                className="p-1.5 bg-zinc-800 text-zinc-400 rounded-full hover:text-red-500 hover:bg-zinc-700 shadow-lg border border-zinc-600 transition-transform hover:scale-110"
                title="Delete"
            >
                <X size={14} />
            </button>
            </div>

            {/* Rotation Handle (Bottom Center) */}
            <div 
                className="rotate-handle absolute -bottom-8 left-1/2 -translate-x-1/2 cursor-crosshair group/rotate"
                onPointerDown={handleRotateStart}
                onPointerMove={handleRotateMove}
                onPointerUp={handleRotateEnd}
            >
                <div className="w-1 h-6 bg-red-500/50 mx-auto group-hover/rotate:bg-red-500"></div>
                <div className="w-6 h-6 bg-zinc-800 rounded-full border border-zinc-600 flex items-center justify-center shadow-lg text-zinc-400 group-hover/rotate:text-white group-hover/rotate:border-red-500">
                    <RotateCw size={12} />
                </div>
            </div>
        </>
      )}

      {/* Content Renderer */}
      {node.type === 'image' && (
        <div className="relative p-2 bg-white/90 backdrop-blur-sm shadow-sm border border-zinc-300 transform transition-transform">
          {/* Tape effect */}
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-24 h-8 bg-yellow-100/40 rotate-1 backdrop-blur-sm border border-white/20 shadow-sm z-20 pointer-events-none"></div>
          
          <img 
            src={node.content} 
            alt="Evidence" 
            className="w-full h-auto object-cover pointer-events-none sepia-[0.2] contrast-[1.1]"
            draggable={false}
          />
          {node.title && (
             <div className="mt-2 text-center font-typewriter font-bold text-zinc-900 bg-zinc-100 p-1 uppercase tracking-widest text-sm border border-zinc-300">
               {node.title}
             </div>
          )}
        </div>
      )}

      {node.type === 'note' && (
        <div 
          className="relative p-4 h-full shadow-inner flex items-center justify-center text-center leading-tight"
          style={{ backgroundColor: node.color || '#fef3c7' }}
        >
          {/* Pin */}
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-red-800 shadow-md border border-red-950 z-20"></div>
          
          <p className="font-hand text-xl text-zinc-900 w-full break-words select-none">
            {node.content}
          </p>
        </div>
      )}

      {node.type === 'evidence' && (
        <div className="bg-zinc-900 border-2 border-zinc-700 p-3 shadow-2xl">
          <div className="flex items-center gap-2 mb-2 border-b border-zinc-700 pb-1">
            <span className="font-typewriter text-red-500 text-xs font-bold uppercase tracking-wider">Top Secret</span>
          </div>
          <p className="font-typewriter text-zinc-300 text-sm leading-relaxed">
            {node.content}
          </p>
        </div>
      )}
    </div>
  );
};