import React from 'react';
import { BoardNode } from '../types.tsx';

interface ConnectionLineProps {
  fromNode: BoardNode;
  toNode: BoardNode;
  active?: boolean;
}

export const ConnectionLine: React.FC<ConnectionLineProps> = ({ fromNode, toNode, active }) => {
  // Calculate centers
  const startX = fromNode.x + (fromNode.width || 200) / 2;
  const startY = fromNode.y + (fromNode.height || 200) / 2;
  const endX = toNode.x + (toNode.width || 200) / 2;
  const endY = toNode.y + (toNode.height || 200) / 2;

  // Calculate distance for slack effect
  const dx = endX - startX;
  const dy = endY - startY;
  const distance = Math.sqrt(dx * dx + dy * dy);
  
  // "Gravity" effect for the string - longer strings droop more
  const slack = Math.min(distance * 0.2, 100); 
  const midX = (startX + endX) / 2;
  const midY = (startY + endY) / 2 + slack;

  return (
    <g>
      {/* Shadow/Outline for visibility on dark photos */}
      <path
        d={`M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`}
        fill="none"
        stroke="rgba(0,0,0,0.5)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      {/* The main string */}
      <path
        d={`M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`}
        fill="none"
        stroke={active ? "#ef4444" : "#b91c1c"} // Red-500 active, Red-700 inactive
        strokeWidth="2"
        strokeLinecap="round"
        className="pointer-events-none drop-shadow-md"
        style={{ filter: 'drop-shadow(0px 2px 2px rgba(0,0,0,0.5))' }}
      />
      {/* Pin heads */}
      <circle cx={startX} cy={startY} r="4" fill="#7f1d1d" />
      <circle cx={endX} cy={endY} r="4" fill="#7f1d1d" />
    </g>
  );
};