'use client';

import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { api } from '@/lib/api';
import { GraphData, GraphNode } from '@/lib/types';
import { X, Network, Filter, RefreshCw, Eye, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { EmptyState } from './EmptyState';

interface MemoryGraphProps {
  entityName?: string;
  sessionId?: string;
}

const TYPE_CONFIG: Record<string, { color: string; val: number; label: string }> = {
  Session: { color: '#3b82f6', val: 14, label: 'Session' },
  Fact: { color: '#f59e0b', val: 10, label: 'Fact' },
  Entity: { color: '#10b981', val: 18, label: 'Entity' },
  Summary: { color: '#8b5cf6', val: 12, label: 'Summary' },
  Message: { color: '#64748b', val: 6, label: 'Message' },
};

const EDGE_COLORS: Record<string, string> = {
  SUPERSEDES: '#ef4444',
  INVALIDATED_BY: '#f43f5e',
  CONTAINS: '#3b82f6aa',
  MENTIONS: '#10b981aa',
  OCCURRED_IN: '#f59e0baa',
  HAS_SUMMARY: '#8b5cf6aa',
};

export function MemoryGraph({ entityName, sessionId }: MemoryGraphProps) {
  const [rawData, setRawData] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [visibleTypes, setVisibleTypes] = useState<Record<string, boolean>>({
    Session: true,
    Fact: true,
    Entity: true,
    Summary: true,
    Message: false,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    try {
      let data: GraphData;
      if (entityName) {
        data = await api.getEntityGraph(entityName);
      } else if (sessionId) {
        data = await api.getSessionGraph(sessionId);
      } else {
        data = await api.getAllGraphs();
      }
      setRawData(data || { nodes: [], edges: [] });
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
      setRawData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  }, [entityName, sessionId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Filter nodes & edges dynamically
  const filteredGraphData = useMemo(() => {
    const activeNodes = rawData.nodes.filter(
      (node) => visibleTypes[node.type] !== false
    );
    const activeNodeIds = new Set(activeNodes.map((n) => String(n.id)));

    const activeLinks = rawData.edges
      .filter(
        (edge) =>
          activeNodeIds.has(String(edge.source)) &&
          activeNodeIds.has(String(edge.target))
      )
      .map((edge) => ({
        source: String(edge.source),
        target: String(edge.target),
        type: edge.type,
        color: EDGE_COLORS[edge.type] || '#475569',
        width: edge.type === 'SUPERSEDES' ? 2.5 : 1.5,
      }));

    const formattedNodes = activeNodes.map((node) => ({
      id: String(node.id),
      label: node.label,
      type: node.type,
      data: node.data,
      color: TYPE_CONFIG[node.type]?.color || '#94a3b8',
      val: TYPE_CONFIG[node.type]?.val || 8,
    }));

    return { nodes: formattedNodes, links: activeLinks };
  }, [rawData, visibleTypes]);

  // Initialize and mount ForceGraph via Canvas 2D
  useEffect(() => {
    if (loading || rawData.nodes.length === 0) return;

    let isMounted = true;
    let graphInstance: any = null;
    let resizeObserver: ResizeObserver | null = null;

    const initGraph = async () => {
      if (!containerRef.current) return;

      const ForceGraphFactory = (await import('force-graph')).default;
      if (!isMounted || !containerRef.current) return;

      // Clear previous canvas
      containerRef.current.innerHTML = '';

      const width = containerRef.current.clientWidth || window.innerWidth;
      const height = containerRef.current.clientHeight || window.innerHeight;

      graphInstance = (ForceGraphFactory as any)()(containerRef.current)
        .width(width)
        .height(height)
        .backgroundColor('#080b11')
        .enableNodeDrag(true)
        .linkDirectionalParticles((link: any) => (link.type === 'SUPERSEDES' ? 4 : 1))
        .linkDirectionalParticleSpeed(0.006)
        .linkDirectionalParticleWidth((link: any) => (link.type === 'SUPERSEDES' ? 3 : 2))
        .linkColor((link: any) => link.color || '#475569')
        .linkWidth((link: any) => link.width || 1.5)
        .nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const label = node.label || node.id || '';
          const radius = Math.max(4, (node.val || 8) * 0.7);
          const color = node.color || '#94a3b8';

          // Node Outer Glow
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + 2, 0, 2 * Math.PI, false);
          ctx.fillStyle = `${color}33`;
          ctx.fill();

          // Node Main Body
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.lineWidth = 1.5 / globalScale;
          ctx.strokeStyle = '#ffffff88';
          ctx.stroke();

          // Node Label
          if (globalScale > 0.6) {
            const fontSize = Math.max(10 / globalScale, 9);
            ctx.font = `600 ${fontSize}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#f8fafc';
            ctx.shadowColor = '#000000';
            ctx.shadowBlur = 4;
            ctx.fillText(label, node.x, node.y + radius + fontSize * 0.8);
            ctx.shadowBlur = 0; // reset
          }
        })
        .nodePointerAreaPaint((node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const radius = Math.max(4, (node.val || 8) * 0.7) + 3;
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
          ctx.fillStyle = color;
          ctx.fill();
        })
        .onNodeClick((node: any) => {
          setSelectedNode(node);
        })
        .onBackgroundClick(() => {
          setSelectedNode(null);
        });

      graphRef.current = graphInstance;

      // Pass cloned data
      graphInstance.graphData({
        nodes: filteredGraphData.nodes.map((n) => ({ ...n })),
        links: filteredGraphData.links.map((l) => ({ ...l })),
      });

      // Fit view
      setTimeout(() => {
        if (graphInstance && filteredGraphData.nodes.length > 0) {
          graphInstance.zoomToFit(600, 40);
        }
      }, 300);

      // Handle viewport resizing
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width: w, height: h } = entry.contentRect;
          if (w > 0 && h > 0 && graphInstance) {
            graphInstance.width(w);
            graphInstance.height(h);
          }
        }
      });

      resizeObserver.observe(containerRef.current);
    };

    initGraph();

    return () => {
      isMounted = false;
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (graphInstance) {
        graphInstance._destructor?.();
      }
      graphRef.current = null;
    };
  }, [loading, rawData.nodes.length === 0]);

  // Update dynamic graph dataset on filter toggle without remounting canvas
  useEffect(() => {
    if (graphRef.current && filteredGraphData) {
      graphRef.current.graphData({
        nodes: filteredGraphData.nodes.map((n) => ({ ...n })),
        links: filteredGraphData.links.map((l) => ({ ...l })),
      });
    }
  }, [filteredGraphData]);

  const toggleType = (type: string) => {
    setVisibleTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  const handleZoomIn = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() * 1.3, 300);
    }
  };

  const handleZoomOut = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() / 1.3, 300);
    }
  };

  const handleFit = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 40);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-slate-950/70">
        <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-3 animate-spin">
          <RefreshCw size={20} className="text-amber-400" />
        </div>
        <p className="text-xs font-semibold text-slate-300">Loading graph topology...</p>
        <p className="text-[11px] text-slate-500 mt-1">Connecting node relationships in HydraDB</p>
      </div>
    );
  }

  if (rawData.nodes.length === 0) {
    return (
      <EmptyState
        icon={Network}
        title="No graph entities found"
        description="The memory graph is currently empty. Ingest conversation sessions to see nodes, entities, and temporal facts appear."
        action={{
          label: 'Refresh Graph',
          onClick: fetchGraph,
        }}
      />
    );
  }

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden select-none">
      {/* Interactive Force Graph Canvas */}
      <div ref={containerRef} className="w-full h-full absolute inset-0" />

      {/* Floating Toolbar & Node Legend */}
      <div className="absolute top-4 left-4 flex flex-col gap-2.5 z-10">
        {/* Type toggle filters */}
        <div className="glass-card p-3 space-y-2 backdrop-blur-xl border border-white/[0.08] shadow-2xl">
          <div className="flex items-center justify-between gap-3 pb-1.5 border-b border-white/5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Filter size={11} /> Filters
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              {filteredGraphData.nodes.length} nodes
            </span>
          </div>

          <div className="flex flex-col gap-1.5">
            {Object.entries(TYPE_CONFIG).map(([type, cfg]) => {
              const active = visibleTypes[type] !== false;
              return (
                <button
                  key={type}
                  onClick={() => toggleType(type)}
                  className={`flex items-center justify-between gap-3 text-xs px-2 py-1 rounded-lg transition-all ${
                    active
                      ? 'bg-white/[0.06] text-slate-200 hover:bg-white/[0.1]'
                      : 'opacity-40 text-slate-500 hover:opacity-70'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cfg.color }} />
                    <span className="font-medium text-[11px]">{cfg.label}</span>
                  </div>
                  <Eye size={12} className={active ? 'text-slate-400' : 'text-slate-600'} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Relationship color reference */}
        <div className="glass-card p-3 space-y-1.5 backdrop-blur-xl border border-white/[0.08]">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block pb-1 border-b border-white/5">
            Edges
          </span>
          <div className="text-[10px] text-slate-400 space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-rose-500 rounded-full" />
              <span>SUPERSEDES (Update)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-emerald-500 rounded-full" />
              <span>MENTIONS (Entity)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-blue-500 rounded-full" />
              <span>CONTAINS (Session)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Controls (Zoom & Fit) */}
      <div className="absolute bottom-4 right-4 flex items-center gap-1.5 z-10 glass-card p-1.5 border border-white/[0.08] shadow-2xl">
        <button
          onClick={handleZoomIn}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          title="Zoom In"
        >
          <ZoomIn size={15} />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          title="Zoom Out"
        >
          <ZoomOut size={15} />
        </button>
        <button
          onClick={handleFit}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          title="Fit to Screen"
        >
          <Maximize2 size={15} />
        </button>
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div className="absolute top-4 right-4 w-80 glass-card p-4 z-20 backdrop-blur-2xl border border-white/[0.12] shadow-2xl animate-[slideInRight_0.2s_ease-out]">
          <div className="flex items-start justify-between gap-2 pb-2.5 border-b border-white/10">
            <div>
              <span
                className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md font-mono"
                style={{
                  backgroundColor: `${TYPE_CONFIG[selectedNode.type]?.color}20`,
                  color: TYPE_CONFIG[selectedNode.type]?.color || '#fff',
                }}
              >
                {selectedNode.type} Node
              </span>
              <h4 className="text-xs font-semibold text-slate-100 mt-1.5 leading-snug break-words">
                {selectedNode.label}
              </h4>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-white/5"
            >
              <X size={15} />
            </button>
          </div>

          <div className="py-3 space-y-2.5 text-xs text-slate-300 max-h-[380px] overflow-y-auto">
            {selectedNode.data?.content && (
              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-500 block mb-0.5">Content</span>
                <p className="p-2.5 rounded-lg bg-black/40 border border-white/5 leading-relaxed text-slate-200 font-mono text-[11px]">
                  {selectedNode.data.content}
                </p>
              </div>
            )}

            {selectedNode.data?.confidence !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-medium">Confidence:</span>
                <span className="font-mono font-semibold text-amber-400">
                  {Math.round(selectedNode.data.confidence * 100)}%
                </span>
              </div>
            )}

            {selectedNode.data?.is_current !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-medium">Status:</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                    selectedNode.data.is_current
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-rose-500/10 text-rose-400'
                  }`}
                >
                  {selectedNode.data.is_current ? 'Current Fact' : 'Superseded'}
                </span>
              </div>
            )}

            {selectedNode.data?.session_id && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-medium">Session:</span>
                <span className="font-mono text-slate-300 text-[11px]">{selectedNode.data.session_id}</span>
              </div>
            )}

            {selectedNode.data?.created_at && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-medium">Timestamp:</span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {new Date(selectedNode.data.created_at).toLocaleString('en-US', {
                    timeZone: 'UTC',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
