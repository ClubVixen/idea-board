import React, { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import html2canvas from 'html2canvas';
import { BoardNode, Connection, NodeType } from './types.tsx';
import { ConnectionLine } from './components/ConnectionLine.tsx';
import { BoardItem } from './components/BoardItem.tsx';
import { ImageCropper } from './components/ImageCropper.tsx';
import { Plus, Image as ImageIcon, StickyNote, FileText, Link2Off, Loader2, MousePointer2, Camera } from 'lucide-react';
import { brainstormConnections } from './services/geminiService.tsx';

const App: React.FC = () => {
  const [nodes, setNodes] = useState<BoardNode[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [connectingFromId, setConnectingFromId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [cursorMode, setCursorMode] = useState<'select' | 'connect'>('select');
  
  // Cropping State
  const [croppingNodeId, setCroppingNodeId] = useState<string | null>(null);
  const [cropImageUrl, setCropImageUrl] = useState<string | null>(null);

  const boardRef = useRef<HTMLDivElement>(null);

  // Load initial demo data
  useEffect(() => {
    const demoNodes: BoardNode[] = [
      {
        id: '1',
        type: 'image',
        content: 'https://picsum.photos/300/200',
        x: 100,
        y: 100,
        width: 300,
        height: 250,
        rotation: -2,
        title: 'Suspect A'
      },
      {
        id: '2',
        type: 'note',
        content: 'Where was he on the night of the 15th?',
        x: 500,
        y: 150,
        width: 200,
        height: 200,
        rotation: 3,
        color: '#fef3c7'
      },
      {
        id: '3',
        type: 'evidence',
        content: 'WITNESS REPORT: Saw a blue sedan leaving the scene at approx 11:00 PM.',
        x: 300,
        y: 450,
        width: 280,
        height: 180,
        rotation: 1
      }
    ];
    
    const demoConnections: Connection[] = [
      { id: 'c1', from: '1', to: '2', color: 'red' },
      { id: 'c2', from: '1', to: '3', color: 'red' }
    ];

    setNodes(demoNodes);
    setConnections(demoConnections);
  }, []);

  const addNode = (type: NodeType, content: string = '') => {
    const id = uuidv4();
    const centerX = window.innerWidth / 2 - 100 + (Math.random() * 50 - 25);
    const centerY = window.innerHeight / 2 - 100 + (Math.random() * 50 - 25);

    const newNode: BoardNode = {
      id,
      type,
      content: content || (type === 'note' ? 'New Idea' : 'Description text...'),
      x: centerX,
      y: centerY,
      width: type === 'image' ? 300 : 200,
      height: type === 'image' ? 0 : (type === 'evidence' ? 150 : 200), // Height 0 for image means auto
      rotation: Math.random() * 6 - 3,
      color: type === 'note' ? ['#fef3c7', '#fee2e2', '#dcfce7'][Math.floor(Math.random() * 3)] : undefined,
      title: type === 'image' ? 'Unknown' : undefined
    };
    setNodes([...nodes, newNode]);
    setSelectedId(id);
  };

  const handleDuplicate = (node: BoardNode) => {
    const id = uuidv4();
    const newNode: BoardNode = {
      ...node,
      id,
      x: node.x + 40, // Offset slightly
      y: node.y + 40,
      rotation: node.rotation + (Math.random() * 4 - 2), // Slight rotation variance
    };
    setNodes(prev => [...prev, newNode]);
    setSelectedId(id);
  };

  const handleCropStart = (node: BoardNode) => {
    setCroppingNodeId(node.id);
    setCropImageUrl(node.content);
  };

  const handleCropSave = (newContent: string) => {
    if (croppingNodeId) {
      setNodes(prev => prev.map(n => n.id === croppingNodeId ? { ...n, content: newContent } : n));
    }
    setCroppingNodeId(null);
    setCropImageUrl(null);
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        addNode('image', reader.result as string);
      };
      reader.readAsDataURL(file);
    }
    // Reset input
    e.target.value = '';
  };

  // DRAG AND DROP HANDLERS
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    
    // Check for files
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      Array.from(e.dataTransfer.files).forEach(file => {
        if (file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = () => {
             // Randomize position slightly
             const id = uuidv4();
             const centerX = e.clientX - 150; // Center under mouse roughly
             const centerY = e.clientY - 100;
             
             const newNode: BoardNode = {
               id,
               type: 'image',
               content: reader.result as string,
               x: centerX,
               y: centerY,
               width: 300,
               height: 0,
               rotation: Math.random() * 6 - 3,
               title: file.name.split('.')[0]
             };
             setNodes(prev => [...prev, newNode]);
             setSelectedId(id);
          };
          reader.readAsDataURL(file);
        }
      });
      e.dataTransfer.clearData();
    }
  };

  const handleMove = useCallback((id: string, x: number, y: number) => {
    setNodes(prev => prev.map(node => 
      node.id === id ? { ...node, x, y } : node
    ));
  }, []);

  const handleRotate = useCallback((id: string, rotation: number) => {
    setNodes(prev => prev.map(node => 
      node.id === id ? { ...node, rotation } : node
    ));
  }, []);

  const handleDelete = (id: string) => {
    setNodes(prev => prev.filter(n => n.id !== id));
    setConnections(prev => prev.filter(c => c.from !== id && c.to !== id));
    if (selectedId === id) setSelectedId(null);
  };

  const handleConnect = (targetId: string) => {
    if (connectingFromId && connectingFromId !== targetId) {
      // Check if connection already exists
      const exists = connections.some(
        c => (c.from === connectingFromId && c.to === targetId) || 
             (c.from === targetId && c.to === connectingFromId)
      );

      if (!exists) {
        setConnections(prev => [...prev, {
          id: uuidv4(),
          from: connectingFromId,
          to: targetId,
          color: 'red'
        }]);
      }
      setConnectingFromId(null);
      setCursorMode('select');
    } else {
      setConnectingFromId(targetId);
      setCursorMode('connect');
    }
  };

  const handleBrainstorm = async (node: BoardNode) => {
    if (isProcessing) return;
    setIsProcessing(true);

    // Get context from other nodes to help Gemini
    const context = nodes
      .filter(n => n.id !== node.id && (n.type === 'note' || n.type === 'evidence'))
      .map(n => n.content)
      .slice(0, 5); // Limit context

    const ideas = await brainstormConnections(node.content, context);

    if (ideas.length > 0) {
      const newNodes: BoardNode[] = [];
      const newConnections: Connection[] = [];
      
      // Calculate positions in a semi-circle around the source node
      const radius = 300;
      const startAngle = -Math.PI / 2; // Up
      const angleStep = Math.PI / (ideas.length + 1);

      ideas.forEach((idea, index) => {
        const id = uuidv4();
        const angle = startAngle + (index + 1) * angleStep + (Math.random() * 0.5 - 0.25);
        
        const newX = node.x + Math.cos(angle) * radius;
        const newY = node.y + Math.sin(angle) * radius;

        newNodes.push({
          id,
          type: 'note',
          content: idea,
          x: newX,
          y: newY,
          width: 200,
          height: 200,
          rotation: Math.random() * 10 - 5,
          color: '#fee2e2' // Light red for AI suggestions
        });

        newConnections.push({
          id: uuidv4(),
          from: node.id,
          to: id,
          color: 'red'
        });
      });

      setNodes(prev => [...prev, ...newNodes]);
      setConnections(prev => [...prev, ...newConnections]);
    }

    setIsProcessing(false);
  };

  // Background click to deselect
  const handleBgClick = () => {
    setSelectedId(null);
    setConnectingFromId(null);
    setCursorMode('select');
  };

  // Update text content
  const handleContentUpdate = (id: string, newContent: string) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, content: newContent } : n));
  };
  
  const handleTitleUpdate = (id: string, newTitle: string) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, title: newTitle } : n));
  };

  const handleExport = async () => {
    if (!boardRef.current) return;
    
    // 1. Deselect everything so UI controls don't show up
    setSelectedId(null);
    setConnectingFromId(null);
    
    // Wait for state update to clear selection (brief delay)
    await new Promise(resolve => setTimeout(resolve, 100));

    try {
      const canvas = await html2canvas(boardRef.current, {
        backgroundColor: null, // Transparent background
        scale: 2, // Higher resolution
        useCORS: true, // Handle cross-origin images like picsum
        logging: false,
      });

      const link = document.createElement('a');
      link.download = `detective-board-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error) {
      console.error("Export failed:", error);
      alert("Failed to export image. Check console for details.");
    }
  };

  return (
    <div 
      className={`relative w-full h-screen bg-zinc-950 text-zinc-200 overflow-hidden bg-texture ${cursorMode === 'connect' ? 'cursor-crosshair' : ''}`}
      onPointerDown={(e) => {
        if (e.target === e.currentTarget) handleBgClick();
      }}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Background Grid/Noise (Outside boardRef so it's not captured if we want transparency) */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-zinc-900/50 to-transparent opacity-50" />

      {/* Board Content Wrapper for Export */}
      <div ref={boardRef} className="absolute inset-0 w-full h-full">
        {/* Connection Layer (SVG) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible">
          {connections.map(conn => {
            const fromNode = nodes.find(n => n.id === conn.from);
            const toNode = nodes.find(n => n.id === conn.to);
            if (!fromNode || !toNode) return null;
            return <ConnectionLine key={conn.id} fromNode={fromNode} toNode={toNode} active={conn.id === selectedId} />;
          })}
        </svg>

        {/* Nodes Layer */}
        {nodes.map(node => (
          <BoardItem
            key={node.id}
            node={node}
            isSelected={selectedId === node.id}
            isConnecting={cursorMode === 'connect'}
            onSelect={setSelectedId}
            onMove={handleMove}
            onRotate={handleRotate}
            onDelete={handleDelete}
            onDuplicate={handleDuplicate}
            onConnectStart={handleConnect}
            onBrainstorm={handleBrainstorm}
            onCropStart={handleCropStart}
          />
        ))}
      </div>

      {/* Edit Panel (if text node selected) */}
      {selectedId && nodes.find(n => n.id === selectedId)?.type !== 'image' && (
        <div className="absolute top-4 right-4 z-50 bg-zinc-900/90 backdrop-blur border border-zinc-700 p-4 rounded-lg shadow-2xl w-80">
          <h3 className="text-zinc-400 text-xs font-bold uppercase tracking-wider mb-2">Edit Content</h3>
          <textarea
            className="w-full bg-zinc-800 border border-zinc-700 p-2 rounded text-zinc-200 focus:outline-none focus:border-red-500 font-hand text-lg"
            rows={4}
            value={nodes.find(n => n.id === selectedId)?.content || ''}
            onChange={(e) => handleContentUpdate(selectedId, e.target.value)}
          />
        </div>
      )}

      {/* Image Title Edit Panel */}
      {selectedId && nodes.find(n => n.id === selectedId)?.type === 'image' && (
        <div className="absolute top-4 right-4 z-50 bg-zinc-900/90 backdrop-blur border border-zinc-700 p-4 rounded-lg shadow-2xl w-80">
          <h3 className="text-zinc-400 text-xs font-bold uppercase tracking-wider mb-2">Edit Image Label</h3>
          <input
            type="text"
            className="w-full bg-zinc-800 border border-zinc-700 p-2 rounded text-zinc-200 focus:outline-none focus:border-red-500 font-typewriter"
            value={nodes.find(n => n.id === selectedId)?.title || ''}
            onChange={(e) => handleTitleUpdate(selectedId, e.target.value)}
          />
        </div>
      )}

      {/* Crop Modal */}
      {cropImageUrl && (
        <ImageCropper 
            imageUrl={cropImageUrl}
            onCancel={() => {
                setCropImageUrl(null);
                setCroppingNodeId(null);
            }}
            onSave={handleCropSave}
        />
      )}

      {/* Toolbar */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 bg-zinc-900/90 backdrop-blur px-6 py-3 rounded-2xl border border-zinc-800 shadow-2xl">
        <div className="flex gap-2 border-r border-zinc-700 pr-4">
           {/* Add Note */}
          <button 
            onClick={() => addNode('note')}
            className="p-2 hover:bg-zinc-800 rounded-lg text-yellow-200 transition-colors tooltip-trigger"
            title="Add Sticky Note"
          >
            <StickyNote />
          </button>
          
          {/* Add Evidence Text */}
          <button 
            onClick={() => addNode('evidence')}
            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 transition-colors"
            title="Add Evidence/Report"
          >
            <FileText />
          </button>

          {/* Add Image */}
          <label className="p-2 hover:bg-zinc-800 rounded-lg text-blue-300 transition-colors cursor-pointer" title="Upload Image">
            <ImageIcon />
            <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
          </label>
        </div>

        <div className="flex gap-2 border-r border-zinc-700 pr-4">
           {/* Connection Mode Toggle */}
           <button 
            onClick={() => {
              setCursorMode(prev => prev === 'select' ? 'connect' : 'select');
              setConnectingFromId(null);
            }}
            className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${cursorMode === 'connect' ? 'bg-red-900/50 text-red-400' : 'hover:bg-zinc-800 text-zinc-400'}`}
          >
            {cursorMode === 'connect' ? <Link2Off /> : <MousePointer2 />}
            <span className="text-sm font-bold hidden md:inline">{cursorMode === 'connect' ? 'Linking' : 'Select'}</span>
          </button>
        </div>

        <div>
           {/* Export Button */}
           <button 
            onClick={handleExport}
            className="p-2 hover:bg-zinc-800 rounded-lg text-green-400 transition-colors"
            title="Save as Transparent PNG"
          >
            <Camera />
          </button>
        </div>

        {isProcessing && (
          <div className="border-l border-zinc-700 pl-4 flex items-center gap-2 text-purple-400 animate-pulse">
            <Loader2 className="animate-spin" size={18} />
            <span className="text-xs font-bold uppercase">AI Analyzing...</span>
          </div>
        )}
      </div>

      {/* Hints */}
      <div className="absolute top-4 left-4 text-zinc-600 text-sm font-typewriter pointer-events-none select-none">
        <p>CASE FILE: #992-AZ</p>
        <p className="text-xs opacity-50 mt-1">Drag to move. Click nodes to edit. Drag bottom handle to rotate.</p>
        <p className="text-xs opacity-50">Drag & Drop images here.</p>
      </div>

      {connectingFromId && (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-red-900/80 text-white px-4 py-1 rounded-full text-sm font-bold animate-pulse pointer-events-none border border-red-500">
          Select target to connect...
        </div>
      )}

    </div>
  );
};

export default App;