export type NodeType = 'image' | 'note' | 'evidence';

export interface BoardNode {
  id: string;
  type: NodeType;
  content: string; // Text content or Image URL
  title?: string; // Optional title for evidence
  x: number;
  y: number;
  width?: number; // Optional, mostly for images
  height?: number;
  rotation: number;
  color?: string; // For sticky notes
}

export interface Connection {
  id: string;
  from: string; // Node ID
  to: string;   // Node ID
  color: string;
}

export interface DragOffset {
  x: number;
  y: number;
}