'use client';

import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { api } from '@/lib/api';
import { GraphData, GraphNode } from '@/lib/types';
import { useTheme } from './ThemeProvider';
import {
  X,
  Network,
  Filter,
  RefreshCw,
  Eye,
  ZoomIn,
  ZoomOut,
  Maximize2,
  CheckCircle2,
  AlertTriangle,
  Layers,
  History,
  Target,
} from 'lucide-react';
import { EmptyState } from './EmptyState';

interface MemoryGraphProps {
  entityName?: string;
  sessionId?: string;
  userId?: string;
}

interface TimelineStep {
  nodeId: string;
  label: string;
  content: string;
  isCurrent: boolean;
  confidence: number;
  sessionId: string;
  createdAt: string;
  supersededBy?: string | null;
}

const TYPE_CONFIG: Record<string, { color: string; val: number; label: string }> = {
  Entity: { color: '#0284c7', val: 18, label: 'Entity Hub' },
  Fact: { color: '#059669', val: 12, label: 'Fact (Active)' },
  FactSuperseded: { color: '#dc2626', val: 10, label: 'Fact (Superseded)' },
  Session: { color: '#6366f1', val: 14, label: 'Session Turn' },
  Summary: { color: '#9333ea', val: 11, label: 'Summary' },
  Message: { color: '#64748b', val: 6, label: 'Raw Message' },
};

const EDGE_COLORS_DARK: Record<string, string> = {
  SUPERSEDES: '#f43f5e',
  INVALIDATED_BY: '#fb7185',
  CONTAINS: '#818cf8aa',
  MENTIONS: '#38bdf8aa',
  OCCURRED_IN: '#10b981aa',
  HAS_SUMMARY: '#c084fcaa',
};

const EDGE_COLORS_LIGHT: Record<string, string> = {
  SUPERSEDES: '#dc2626',
  INVALIDATED_BY: '#e11d48',
  CONTAINS: '#6366f199',
  MENTIONS: '#0284c799',
  OCCURRED_IN: '#05966999',
  HAS_SUMMARY: '#9333ea99',
};

export function MemoryGraph({ entityName, sessionId, userId = 'user' }: MemoryGraphProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  const [rawData, setRawData] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleTypes, setVisibleTypes] = useState<Record<string, boolean>>({
    Entity: true,
    Fact: true,
    Session: true,
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
        data = await api.getEntityGraph(entityName, userId);
      } else if (sessionId) {
        data = await api.getSessionGraph(sessionId, userId);
      } else {
        data = await api.getAllGraphs(userId);
      }
      setRawData(data || { nodes: [], edges: [] });
      setError(null);
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
      setRawData({ nodes: [], edges: [] });
      setError('Unable to load graph data. Verify the API is running and the selected user has access.');
    } finally {
      setLoading(false);
    }
  }, [entityName, sessionId, userId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Filter nodes & edges dynamically with custom coloring for Superseded vs Active
  const filteredGraphData = useMemo(() => {
    const activeNodes = rawData.nodes.filter(
      (node) => visibleTypes[node.type] !== false
    );
    const activeNodeIds = new Set(activeNodes.map((n) => String(n.id)));
    const edgeColors = isDark ? EDGE_COLORS_DARK : EDGE_COLORS_LIGHT;

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
        color: edgeColors[edge.type] || (isDark ? '#475569' : '#94a3b8'),
        width: edge.type === 'SUPERSEDES' ? 3.5 : 1.5,
      }));

    const formattedNodes = activeNodes.map((node) => {
      const isFact = node.type === 'Fact';
      const isCurrent = node.data?.is_current !== false;
      let color = TYPE_CONFIG[node.type]?.color || '#94a3b8';

      if (isFact) {
        color = isCurrent ? (isDark ? '#10b981' : '#059669') : (isDark ? '#f43f5e' : '#dc2626');
      }

      return {
        id: String(node.id),
        label: node.label,
        type: node.type,
        data: node.data,
        isCurrent: isCurrent,
        color: color,
        val: isFact ? (isCurrent ? 13 : 9) : TYPE_CONFIG[node.type]?.val || 10,
      };
    });

    return { nodes: formattedNodes, links: activeLinks };
  }, [rawData, visibleTypes, isDark]);

  // Build the Chronological Supersedence Timeline for the currently selected node
  const timelineChain = useMemo<TimelineStep[]>(() => {
    if (!selectedNode) return [];

    const nodesMap = new Map<string, GraphNode>();
    rawData.nodes.forEach((n) => nodesMap.set(String(n.id), n));

    const supersedesEdges = rawData.edges.filter((e) => e.type === 'SUPERSEDES');

    // If selected is a fact, trace its full chain backward & forward
    if (selectedNode.type === 'Fact') {
      const chainNodeIds = new Set<string>([String(selectedNode.id)]);
      let expanded = true;
      while (expanded) {
        expanded = false;
        for (const edge of supersedesEdges) {
          const src = String(edge.source);
          const tgt = String(edge.target);
          if (chainNodeIds.has(src) && !chainNodeIds.has(tgt)) {
            chainNodeIds.add(tgt);
            expanded = true;
          }
          if (chainNodeIds.has(tgt) && !chainNodeIds.has(src)) {
            chainNodeIds.add(src);
            expanded = true;
          }
        }
      }

      const steps: TimelineStep[] = [];
      chainNodeIds.forEach((id) => {
        const node = nodesMap.get(id);
        if (node) {
          steps.push({
            nodeId: id,
            label: node.label,
            content: node.data?.content || node.label,
            isCurrent: node.data?.is_current !== false,
            confidence: node.data?.confidence || 0.9,
            sessionId: node.data?.session_id || 'session-unknown',
            createdAt: node.data?.created_at || '2024-01-01T00:00:00Z',
            supersededBy: node.data?.superseded_by,
          });
        }
      });

      steps.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
      return steps;
    }

    // If selected is an Entity, fetch all facts referencing this entity
    if (selectedNode.type === 'Entity') {
      const factEdges = rawData.edges.filter(
        (e) => e.type === 'MENTIONS' && String(e.target) === String(selectedNode.id)
      );
      const steps: TimelineStep[] = [];
      factEdges.forEach((e) => {
        const fNode = nodesMap.get(String(e.source));
        if (fNode && fNode.type === 'Fact') {
          steps.push({
            nodeId: String(fNode.id),
            label: fNode.label,
            content: fNode.data?.content || fNode.label,
            isCurrent: fNode.data?.is_current !== false,
            confidence: fNode.data?.confidence || 0.9,
            sessionId: fNode.data?.session_id || 'session-unknown',
            createdAt: fNode.data?.created_at || '2024-01-01T00:00:00Z',
            supersededBy: fNode.data?.superseded_by,
          });
        }
      });
      steps.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
      return steps;
    }

    return [];
  }, [selectedNode, rawData]);

  // Center canvas camera on a specific node ID
  const focusNodeOnCanvas = (nodeId: string) => {
    if (!graphRef.current) return;
    const targetNode = filteredGraphData.nodes.find((n) => n.id === nodeId);
    if (targetNode && (targetNode as any).x !== undefined) {
      graphRef.current.centerAt((targetNode as any).x, (targetNode as any).y, 500);
      graphRef.current.zoom(2.2, 500);
      setSelectedNode(targetNode);
    }
  };

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

      containerRef.current.innerHTML = '';
      const width = containerRef.current.clientWidth || window.innerWidth;
      const height = containerRef.current.clientHeight || window.innerHeight;

      const canvasBg = isDark ? '#090d16' : '#f8fafc';

      graphInstance = (ForceGraphFactory as any)()(containerRef.current)
        .width(width)
        .height(height)
        .backgroundColor(canvasBg)
        .enableNodeDrag(true)
        .linkDirectionalParticles((link: any) => (link.type === 'SUPERSEDES' ? 5 : 2))
        .linkDirectionalParticleSpeed((link: any) => (link.type === 'SUPERSEDES' ? 0.012 : 0.005))
        .linkDirectionalParticleWidth((link: any) => (link.type === 'SUPERSEDES' ? 4 : 2))
        .linkDirectionalParticleColor((link: any) => (link.type === 'SUPERSEDES' ? '#f43f5e' : (isDark ? '#38bdf8' : '#0284c7')))
        .linkColor((link: any) => link.color)
        .d3Force('charge', (d3: any) => d3 ? d3.forceManyBody().strength(-120).distanceMax(500) : null)
        .d3Force('link', (d3: any) => d3 ? d3.forceLink().distance(60) : null)
        .nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const rawLabel = node.label || node.id || '';
          const radius = Math.max(5, (node.val || 8) * 0.75);
          const isEntity = node.type === 'Entity';
          const isFact = node.type === 'Fact';
          const isSuperseded = isFact && node.isCurrent === false;
          const isSelected = selectedNode && String(selectedNode.id) === String(node.id);

          // 1. Outer Glow / Aura
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + (isSelected ? 6 : 3), 0, 2 * Math.PI, false);
          if (isSuperseded) {
            ctx.fillStyle = isDark ? 'rgba(244, 63, 94, 0.25)' : 'rgba(220, 38, 38, 0.2)';
          } else if (isFact) {
            ctx.fillStyle = isDark ? 'rgba(16, 185, 129, 0.3)' : 'rgba(5, 150, 105, 0.25)';
          } else {
            ctx.fillStyle = `${node.color}33`;
          }
          ctx.fill();

          // 2. Node Main Circle Body
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
          ctx.fillStyle = node.color;
          ctx.fill();

          // 3. Node Border Ring
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
          if (isSuperseded) {
            ctx.setLineDash([3 / globalScale, 3 / globalScale]);
            ctx.strokeStyle = isDark ? '#f43f5e' : '#dc2626';
            ctx.lineWidth = 2 / globalScale;
          } else if (isSelected) {
            ctx.setLineDash([]);
            ctx.strokeStyle = '#f59e0b';
            ctx.lineWidth = 3.5 / globalScale;
          } else {
            ctx.setLineDash([]);
            ctx.strokeStyle = isDark ? '#ffffffaa' : '#0f172a88';
            ctx.lineWidth = 1.5 / globalScale;
          }
          ctx.stroke();
          ctx.setLineDash([]);

          // 4. Clean Node Labels:
          // Show label if: (1) It's a key Entity node, (2) It's selected, OR (3) Zoomed in close
          const shouldShowLabel = isEntity || isSelected || globalScale > 1.6;
          if (shouldShowLabel) {
            const displayLabel = rawLabel.length > 22 ? `${rawLabel.slice(0, 20)}…` : rawLabel;
            const fontSize = isEntity ? Math.max(12 / globalScale, 10) : Math.max(10 / globalScale, 8);
            ctx.font = isEntity ? `bold ${fontSize}px sans-serif` : `${fontSize}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = isEntity
              ? '#38bdf8'
              : isSuperseded
              ? (isDark ? '#fda4af' : '#b91c1c')
              : (isDark ? '#f8fafc' : '#0f172a');
            
            ctx.shadowColor = isDark ? '#000000' : '#ffffff';
            ctx.shadowBlur = 4;
            const textY = node.y + radius + fontSize * 0.85;
            ctx.fillText(displayLabel, node.x, textY);
            ctx.shadowBlur = 0;

            // Strikethrough for superseded facts
            if (isSuperseded && shouldShowLabel) {
              const textWidth = ctx.measureText(displayLabel).width;
              ctx.beginPath();
              ctx.strokeStyle = isDark ? '#f43f5e' : '#dc2626';
              ctx.lineWidth = 1.5 / globalScale;
              ctx.moveTo(node.x - textWidth / 2, textY);
              ctx.lineTo(node.x + textWidth / 2, textY);
              ctx.stroke();
            }
          }
        })
        .nodePointerAreaPaint((node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const radius = Math.max(5, (node.val || 8) * 0.75) + 4;
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

      graphInstance.graphData({
        nodes: filteredGraphData.nodes.map((n) => ({ ...n })),
        links: filteredGraphData.links.map((l) => ({ ...l })),
      });

      setTimeout(() => {
        if (graphInstance && filteredGraphData.nodes.length > 0) {
          graphInstance.zoomToFit(600, 40);
        }
      }, 300);

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
      if (resizeObserver) resizeObserver.disconnect();
      if (graphInstance) graphInstance._destructor?.();
      graphRef.current = null;
    };
  }, [loading, rawData.nodes.length === 0, isDark]);

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
    if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() * 1.3, 300);
  };

    const handleZoomOut = () => {
        if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() / 1.3, 300);
    };

    const handleFit = () => {
        if (graphRef.current) graphRef.current.zoomToFit(400, 40);
    };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-slate-50 dark:bg-[#090d16]">
        <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center mb-3 animate-spin">
          <RefreshCw size={20} className="text-amber-500" />
        </div>
        <p className="text-xs font-bold text-slate-800 dark:text-slate-200 font-heading">Loading HydraDB Graph Topology...</p>
        <p className="text-[11px] text-slate-500 mt-1 font-mono">Traversing temporal edges & supersedence paths</p>
      </div>
    );
  }

  if (rawData.nodes.length === 0) {
    return (
      <EmptyState
        icon={Network}
        title={error ? 'Graph unavailable' : 'No graph entities found'}
        description={error || 'The memory graph is currently empty. Ingest conversation sessions to see nodes, entities, and temporal facts appear.'}
        action={{
          label: 'Refresh Graph',
          onClick: fetchGraph,
        }}
      />
    );
  }

    return (
        <div className="relative w-full h-full bg-slate-100 dark:bg-[#090d16] overflow-hidden select-none transition-colors duration-200">
            {/* Interactive Force Graph Canvas */}
            <div ref={containerRef} className="w-full h-full absolute inset-0" />

            {/* Floating Toolbar & Node Legend */}
            <div className="absolute top-4 left-4 flex flex-col gap-3 z-10">
                {/* Type toggle filters */}
                <div className="glass-panel p-3.5 space-y-2.5 shadow-2xl rounded-2xl max-w-xs border border-slate-200 dark:border-white/[0.08]">
                    <div className="flex items-center justify-between gap-3 pb-1.5 border-b border-slate-200 dark:border-white/5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 flex items-center gap-1.5 font-mono">
                            <Filter size={12} className="text-amber-500" /> Entity Filters
                        </span>
                        <span className="text-[10px] font-mono text-slate-500 font-bold">
                            {filteredGraphData.nodes.length} nodes
                        </span>
                    </div>

                    <div className="flex flex-col gap-1">
                        {Object.entries(TYPE_CONFIG).map(([type, cfg]) => {
                            const active = visibleTypes[type] !== false;
                            return (
                                <button
                                    key={type}
                                    onClick={() => toggleType(type)}
                                    className={`flex items-center justify-between gap-3 text-xs px-2.5 py-1.5 rounded-xl transition-all cursor-pointer ${active
                                            ? 'bg-slate-200/60 dark:bg-white/[0.06] text-slate-900 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-white/[0.1]'
                                            : 'opacity-40 text-slate-400 hover:opacity-70'
                                        }`}
                                >
                                    <div className="flex items-center gap-2">
                                        <span className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: cfg.color }} />
                                        <span className="font-bold text-[11px]">{cfg.label}</span>
                                    </div>
                                    <Eye size={13} className={active ? 'text-slate-600 dark:text-slate-400' : 'text-slate-400'} />
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Temporal Edge Visual Guide */}
                <div className="glass-panel p-3.5 space-y-2 shadow-2xl rounded-2xl max-w-xs border border-slate-200 dark:border-white/[0.08]">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 block pb-1 border-b border-slate-200 dark:border-white/5 font-mono">
                        Temporal Edge Legend
                    </span>
                    <div className="text-[10px] text-slate-600 dark:text-slate-400 space-y-1.5 font-semibold">
                        <div className="flex items-center gap-2">
                            <span className="w-3.5 h-1.5 bg-rose-500 rounded-full shadow-sm" />
                            <span className="text-rose-700 dark:text-rose-300 font-mono font-bold">SUPERSEDES (Update)</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="w-3.5 h-1.5 bg-sky-500 rounded-full shadow-sm" />
                            <span>MENTIONS (Entity Link)</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="w-3.5 h-1.5 bg-indigo-500 rounded-full shadow-sm" />
                            <span>CONTAINS (Session Turn)</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Navigation Controls (Zoom & Fit) */}
            <div className="absolute bottom-4 right-4 flex items-center gap-1.5 z-10 glass-panel p-1.5 rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08]">
                <button
                    onClick={handleZoomIn}
                    className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
                    title="Zoom In"
                >
                    <ZoomIn size={16} />
                </button>
                <button
                    onClick={handleZoomOut}
                    className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
                    title="Zoom Out"
                >
                    <ZoomOut size={16} />
                </button>
                <button
                    onClick={handleFit}
                    className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
                    title="Fit to Screen"
                >
                    <Maximize2 size={16} />
                </button>
            </div>

            {/* Selected Node Details & Chronological Fact Timeline Drawer */}
            {selectedNode && (
                <div className="absolute top-4 right-4 w-96 max-w-[calc(100vw-32px)] glass-panel p-5 z-20 rounded-3xl shadow-2xl border border-slate-200 dark:border-white/[0.12] animate-slide-in-right flex flex-col max-h-[calc(100vh-32px)] overflow-hidden">
                    {/* Drawer Header */}
                    <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-200 dark:border-white/10 flex-shrink-0">
                        <div>
                            <div className="flex items-center gap-2">
                                <span
                                    className="text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-lg font-mono"
                                    style={{
                                        backgroundColor: `${selectedNode.color || '#38bdf8'}25`,
                                        color: selectedNode.color || '#38bdf8',
                                    }}
                                >
                                    {selectedNode.type} Node
                                </span>
                                {selectedNode.data?.is_current !== undefined && (
                                    <span
                                        className={`text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-lg font-mono flex items-center gap-1 ${selectedNode.data.is_current
                                                ? 'bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 border border-emerald-500/30'
                                                : 'bg-rose-500/20 text-rose-800 dark:text-rose-300 border border-rose-500/30'
                                            }`}
                                    >
                                        {selectedNode.data.is_current ? (
                                            <>
                                                <CheckCircle2 size={11} /> Active
                                            </>
                                        ) : (
                                            <>
                                                <AlertTriangle size={11} /> Superseded
                                            </>
                                        )}
                                    </span>
                                )}
                            </div>
                            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-2 leading-snug break-words font-heading">
                                {selectedNode.label}
                            </h4>
                        </div>
                        <button
                            onClick={() => setSelectedNode(null)}
                            className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-white/5 transition-colors cursor-pointer"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    {/* Drawer Scrollable Content */}
                    <div className="flex-1 overflow-y-auto py-3.5 space-y-4 text-xs text-slate-700 dark:text-slate-300 pr-1">
                        {/* Fact Content */}
                        {selectedNode.data?.content && (
                            <div className="space-y-1.5">
                                <span className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1 font-mono">
                                    <Layers size={12} /> Knowledge Unit
                                </span>
                                <p className="p-3.5 rounded-2xl bg-white dark:bg-black/40 border border-slate-200 dark:border-white/5 leading-relaxed text-slate-900 dark:text-slate-200 font-medium text-xs shadow-sm">
                                    {selectedNode.data.content}
                                </p>
                            </div>
                        )}

                        {/* Quick Metrics Bar */}
                        <div className="grid grid-cols-2 gap-2.5">
                            {selectedNode.data?.confidence !== undefined && (
                                <div className="p-3 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/[0.06] shadow-sm">
                                    <span className="text-[10px] uppercase font-bold text-slate-500 block mb-0.5 font-mono">Confidence</span>
                                    <span className="font-mono font-bold text-amber-600 dark:text-amber-400 text-sm">
                                        {Math.round(selectedNode.data.confidence * 100)}%
                                    </span>
                                </div>
                            )}

                            {selectedNode.data?.session_id && (
                                <div className="p-3 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/[0.06] shadow-sm">
                                    <span className="text-[10px] uppercase font-bold text-slate-500 block mb-0.5 font-mono">Source Session</span>
                                    <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-xs truncate block">
                                        {selectedNode.data.session_id}
                                    </span>
                                </div>
                            )}
                        </div>

                        {/* Chronological Supersedence Timeline Stepper */}
                        {timelineChain.length > 0 && (
                            <div className="space-y-2.5 pt-2 border-t border-slate-200 dark:border-white/10">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1.5 font-heading">
                                        <History size={14} />
                                        Fact Evolution Timeline ({timelineChain.length})
                                    </span>
                                    <span className="text-[10px] font-mono text-slate-500 font-bold">HydraDB Lineage</span>
                                </div>

                                <div className="space-y-3 relative pl-4 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-rose-500 before:via-amber-500 before:to-emerald-500">
                                    {timelineChain.map((step, idx) => {
                                        const isStepSelected = String(selectedNode.id) === step.nodeId;
                                        return (
                                            <div
                                                key={step.nodeId}
                                                className={`relative p-3.5 rounded-2xl border text-xs space-y-2 transition-all ${isStepSelected
                                                        ? 'bg-amber-500/15 border-amber-500/40 ring-1 ring-amber-500/30 shadow-md'
                                                        : 'bg-white/80 dark:bg-slate-900/70 border-slate-200 dark:border-white/[0.06] hover:border-slate-300 dark:hover:border-white/[0.15] shadow-sm'
                                                    }`}
                                            >
                                                {/* Timeline Step Dot */}
                                                <div
                                                    className={`absolute -left-[19px] top-4 w-3.5 h-3.5 rounded-full border-2 border-white dark:border-[#090d16] ${step.isCurrent ? 'bg-emerald-500 shadow-md shadow-emerald-500/50' : 'bg-rose-500'
                                                        }`}
                                                />

                                                <div className="flex items-center justify-between">
                                                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md bg-slate-100 dark:bg-black/40 text-slate-700 dark:text-slate-300 font-mono">
                                                        Step {idx + 1} • {step.sessionId}
                                                    </span>
                                                    <span
                                                        className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded-md ${step.isCurrent
                                                                ? 'bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 border border-emerald-500/30'
                                                                : 'bg-rose-500/20 text-rose-800 dark:text-rose-300 border border-rose-500/30'
                                                            }`}
                                                    >
                                                        {step.isCurrent ? 'ACTIVE' : 'SUPERSEDED'}
                                                    </span>
                                                </div>

                                                <p className={`text-slate-900 dark:text-slate-100 font-medium ${!step.isCurrent ? 'line-through opacity-75 text-rose-900 dark:text-rose-200' : ''}`}>
                                                    {step.content}
                                                </p>

                                                <div className="flex items-center justify-between pt-1.5 border-t border-slate-200 dark:border-white/[0.04]">
                                                    <span className="text-[10px] font-mono text-slate-500">
                                                        {new Date(step.createdAt).toLocaleDateString()}
                                                    </span>
                                                    <button
                                                        onClick={() => focusNodeOnCanvas(step.nodeId)}
                                                        className="text-[11px] font-bold text-amber-600 dark:text-amber-400 hover:underline flex items-center gap-1 transition-colors cursor-pointer"
                                                    >
                                                        <Target size={12} /> Focus Node
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
