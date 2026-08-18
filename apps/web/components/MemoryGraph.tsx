'use client';

import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
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

export function MemoryGraph({ entityName, sessionId, userId = 'alex' }: MemoryGraphProps) {
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

  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const hoveredNodeRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        setDimensions({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    
    // Initial size
    setDimensions({
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });
    
    return () => observer.disconnect();
  }, []);

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

  const filteredGraphData = useMemo(() => {
    const activeNodes = rawData.nodes.filter((node) => visibleTypes[node.type] !== false);
    const activeNodeIds = new Set(activeNodes.map((n) => String(n.id)));
    const edgeColors = isDark ? EDGE_COLORS_DARK : EDGE_COLORS_LIGHT;

    const activeLinks = rawData.edges
      .filter((e) => activeNodeIds.has(String(e.source)) && activeNodeIds.has(String(e.target)))
      .map((e) => ({
        source: String(e.source),
        target: String(e.target),
        type: e.type,
        color: edgeColors[e.type] || (isDark ? '#475569' : '#94a3b8'),
      }));

    const formattedNodes = activeNodes.map((node) => {
      const isFact = node.type === 'Fact';
      const isCurrent = node.data?.is_current !== false;
      let color = TYPE_CONFIG[node.type]?.color || '#94a3b8';
      if (isFact) {
        color = isCurrent ? (isDark ? '#10b981' : '#059669') : (isDark ? '#f43f5e' : '#dc2626');
      }
      return {
        ...node,
        id: String(node.id),
        label: node.label,
        type: node.type,
        data: node.data,
        isCurrent: isCurrent,
        color: color,
        val: isFact ? (isCurrent ? 12 : 9) : TYPE_CONFIG[node.type]?.val || 10,
      };
    });

    return { nodes: formattedNodes, links: activeLinks };
  }, [rawData, visibleTypes, isDark]);

  const timelineChain = useMemo<TimelineStep[]>(() => {
    if (!selectedNode) return [];
    const nodesMap = new Map<string, GraphNode>();
    rawData.nodes.forEach((n) => nodesMap.set(String(n.id), n));
    const supersedesEdges = rawData.edges.filter((e) => e.type === 'SUPERSEDES');

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

    if (selectedNode.type === 'Entity') {
      const factEdges = rawData.edges.filter((e) => e.type === 'MENTIONS' && String(e.target) === String(selectedNode.id));
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

  const focusNodeOnCanvas = useCallback((nodeId: string) => {
    if (!graphRef.current) return;
    const currentNodes = graphRef.current.graphData()?.nodes || [];
    const targetNode = currentNodes.find((n: any) => String(n.id) === String(nodeId));
    if (targetNode && typeof targetNode.x === 'number') {
      graphRef.current.centerAt(targetNode.x, targetNode.y, 600);
      graphRef.current.zoom(2.4, 600);
      setSelectedNode(targetNode);
    }
  }, []);

  useEffect(() => {
    if (graphRef.current && filteredGraphData.nodes.length > 0) {
      // Deep clone nodes and links so D3 mutations NEVER leak back into React's useMemo state
      const nodes = filteredGraphData.nodes.map((n) => ({ ...n }));
      const links = filteredGraphData.links.map((l) => ({ ...l }));
      
      graphRef.current.graphData({ nodes, links });

      setTimeout(() => {
        if (graphRef.current) {
          graphRef.current.zoomToFit(400, 50);
        }
      }, 300);
    }
  }, [filteredGraphData]);

  const toggleType = (type: string) => {
    setVisibleTypes((prev) => ({ ...prev, [type]: !prev[type] }));
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
        action={{ label: 'Refresh Graph', onClick: fetchGraph }}
      />
    );
  }

  const canvasBg = isDark ? '#090d16' : '#f8fafc';

  return (
    <div className="relative w-full h-full bg-slate-100 dark:bg-[#090d16] overflow-hidden select-none transition-colors duration-200">
      <div ref={containerRef} className="w-full h-full absolute inset-0">
        {dimensions.width > 0 && dimensions.height > 0 && (
          <ForceGraph2D
            ref={graphRef}
            width={dimensions.width}
            height={dimensions.height}
            // By passing a static empty object to React, we prevent React from EVER 
            // re-initializing the D3 simulation on re-renders. 
            // The actual data is synced manually via the useEffect above!
            graphData={{ nodes: [], links: [] }}
            backgroundColor={canvasBg}
            d3VelocityDecay={0.3}
            cooldownTime={4000}
            enableNodeDrag={true}
            enableZoomInteraction={true}
            enablePanInteraction={true}
            linkColor={(link: any) => link.color}
            linkWidth={(link: any) => (link.type === 'SUPERSEDES' ? 3 : 1)}
            onNodeHover={(node: any) => {
              hoveredNodeRef.current = node || null;
              if (containerRef.current) {
                containerRef.current.style.cursor = node ? 'pointer' : 'default';
              }
            }}
            onNodeClick={(node: any) => {
              setSelectedNode(node);
            }}
            onBackgroundClick={() => {
              setSelectedNode(null);
            }}
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              try {
                // If D3 poisons coordinates with NaN during a drag collision, safely ignore the node
                // instead of crashing the entire canvas loop.
                if (!node || typeof node.x !== 'number' || typeof node.y !== 'number' || isNaN(node.x) || isNaN(node.y)) {
                  return;
                }
                
                const rawLabel = node.label || node.id || '';
                const radius = Math.max(6, (node.val || 8) * 0.85);
                const isEntity = node.type === 'Entity';
                const isFact = node.type === 'Fact';
                const isSuperseded = isFact && node.isCurrent === false;
                
                const isSelected = selectedNode && String(selectedNode.id) === String(node.id);
                const isHovered = hoveredNodeRef.current && String(hoveredNodeRef.current.id) === String(node.id);

                // 1. Outer Glow Aura
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius + (isSelected ? 7 : isHovered ? 5 : 2.5), 0, 2 * Math.PI, false);
                if (isSuperseded) {
                  ctx.fillStyle = isDark ? 'rgba(244, 63, 94, 0.35)' : 'rgba(220, 38, 38, 0.25)';
                } else if (isFact) {
                  ctx.fillStyle = isDark ? 'rgba(16, 185, 129, 0.35)' : 'rgba(5, 150, 105, 0.25)';
                } else if (isEntity) {
                  ctx.fillStyle = isDark ? 'rgba(56, 189, 248, 0.4)' : 'rgba(2, 132, 199, 0.3)';
                } else {
                  ctx.fillStyle = `${node.color}44`;
                }
                ctx.fill();

                // 2. Node Main Body
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
                ctx.fillStyle = node.color;
                ctx.fill();

                // 3. Node Border Ring
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
                const scale = Math.max(0.1, globalScale || 1);
                if (isSuperseded) {
                  ctx.setLineDash([3 / scale, 3 / scale]);
                  ctx.strokeStyle = isDark ? '#f43f5e' : '#dc2626';
                  ctx.lineWidth = 2.5 / scale;
                } else if (isSelected || isHovered) {
                  ctx.setLineDash([]);
                  ctx.strokeStyle = '#f59e0b';
                  ctx.lineWidth = 3.5 / scale;
                } else {
                  ctx.setLineDash([]);
                  ctx.strokeStyle = isDark ? '#ffffffbb' : '#0f172a99';
                  ctx.lineWidth = 1.5 / scale;
                }
                ctx.stroke();
                ctx.setLineDash([]);

                // 4. Node Label Pill Badges
                const shouldShowLabel = isEntity || isSelected || isHovered || scale > 2.2;
                if (shouldShowLabel) {
                  const displayLabel = rawLabel.length > 25 ? `${rawLabel.slice(0, 23)}…` : rawLabel;
                  const fontSize = isEntity ? Math.max(13 / scale, 11) : Math.max(11 / scale, 9);
                  ctx.font = isEntity ? `bold ${fontSize}px sans-serif` : `${fontSize}px sans-serif`;
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';

                  const textWidth = ctx.measureText(displayLabel).width;
                  const paddingX = 6 / scale;
                  const paddingY = 3 / scale;
                  const textY = node.y + radius + fontSize * 0.95;
                  const badgeW = textWidth + paddingX * 2;
                  const badgeH = fontSize + paddingY * 2;

                  ctx.beginPath();
                  ctx.fillStyle = isDark ? 'rgba(12, 18, 32, 0.85)' : 'rgba(255, 255, 255, 0.9)';
                  ctx.fillRect(node.x - badgeW / 2, textY - badgeH / 2, badgeW, badgeH);
                  ctx.strokeStyle = isEntity ? (isDark ? '#38bdf888' : '#0284c788') : (isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)');
                  ctx.lineWidth = 1 / scale;
                  ctx.strokeRect(node.x - badgeW / 2, textY - badgeH / 2, badgeW, badgeH);

                  ctx.fillStyle = isEntity
                    ? (isDark ? '#38bdf8' : '#0284c7')
                    : isSuperseded
                    ? (isDark ? '#fda4af' : '#b91c1c')
                    : (isDark ? '#f8fafc' : '#0f172a');
                  ctx.fillText(displayLabel, node.x, textY);

                  if (isSuperseded) {
                    ctx.beginPath();
                    ctx.strokeStyle = isDark ? '#f43f5e' : '#dc2626';
                    ctx.lineWidth = 1.5 / scale;
                    ctx.moveTo(node.x - textWidth / 2, textY);
                    ctx.lineTo(node.x + textWidth / 2, textY);
                    ctx.stroke();
                  }
                }
              } catch (e) {
                // Ignore safe fallback errors
              }
            }}
          />
        )}
      </div>

      {/* Floating Toolbar & Node Legend */}
      <div className="absolute top-4 left-4 flex flex-col gap-3 z-10 pointer-events-none">
        {/* Type toggle filters */}
        <div className="glass-panel p-3.5 space-y-2.5 shadow-2xl rounded-2xl max-w-xs border border-slate-200 dark:border-white/[0.08] pointer-events-auto">
          <div className="flex items-center justify-between gap-3 pb-1.5 border-b border-slate-200 dark:border-white/5">
            <span className="text-[11px] font-bold font-mono tracking-wider text-slate-500 dark:text-slate-400 uppercase flex items-center gap-1.5">
              <Filter size={12} className="text-amber-500" />
              Entity Filters
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              {rawData.nodes.length} nodes
            </span>
          </div>

          <div className="flex flex-col gap-1.5">
            {Object.entries(TYPE_CONFIG)
              .filter(([type]) => type !== 'FactSuperseded')
              .map(([type, config]) => {
                const isVisible = visibleTypes[type] !== false;
                const count = rawData.nodes.filter((n) => n.type === type).length;
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => toggleType(type)}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                      isVisible
                        ? 'bg-slate-100 dark:bg-white/[0.06] text-slate-900 dark:text-white border border-slate-200 dark:border-white/[0.08]'
                        : 'text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 opacity-40 hover:opacity-75'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full shadow-sm flex-shrink-0"
                        style={{ backgroundColor: config.color }}
                      />
                      <span className="text-xs">{config.label}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-md bg-slate-200/50 dark:bg-black/40 text-slate-600 dark:text-slate-400">
                        {count}
                      </span>
                      <Eye size={12} className={isVisible ? 'text-slate-700 dark:text-slate-300' : 'text-slate-400'} />
                    </div>
                  </button>
                );
              })}

            {/* Superseded fact item indicator */}
            <div className="flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs bg-rose-500/5 border border-rose-500/20 text-rose-600 dark:text-rose-400 font-medium">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 flex-shrink-0 border border-dashed border-rose-300" />
                <span className="text-xs">Fact (Superseded)</span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-rose-500/10 text-rose-500">
                {rawData.nodes.filter((n) => n.type === 'Fact' && n.data?.is_current === false).length}
              </span>
            </div>
          </div>
        </div>

        {/* Edge color legend */}
        <div className="glass-panel p-3 shadow-xl rounded-2xl max-w-xs border border-slate-200 dark:border-white/[0.08] space-y-2 pointer-events-auto">
          <span className="text-[10px] font-bold font-mono tracking-wider text-slate-500 dark:text-slate-400 uppercase flex items-center gap-1.5">
            <Layers size={11} className="text-indigo-400" />
            Temporal Edge Legend
          </span>
          <div className="grid grid-cols-1 gap-1 text-[11px] font-mono text-slate-600 dark:text-slate-400">
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 rounded-full bg-rose-500" />
              <span><strong className="text-rose-500">SUPERSEDES</strong> (Update)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 rounded-full bg-sky-400" />
              <span>MENTIONS (Entity Link)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 rounded-full bg-indigo-400" />
              <span>CONTAINS (Session Turn)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Floating Canvas Controls (Bottom Right) */}
      <div className="absolute bottom-6 right-6 flex items-center gap-2 z-10 glass-panel p-1.5 rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08]">
        <button
          type="button"
          onClick={() => {
            if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() * 1.3, 300);
          }}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
          title="Zoom In"
        >
          <ZoomIn size={16} />
        </button>
        <button
          type="button"
          onClick={() => {
            if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() / 1.3, 300);
          }}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
          title="Zoom Out"
        >
          <ZoomOut size={16} />
        </button>
        <button
          type="button"
          onClick={() => {
            if (graphRef.current) graphRef.current.zoomToFit(400, 40);
          }}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
          title="Fit to Screen"
        >
          <Maximize2 size={16} />
        </button>
        <div className="w-[1px] h-4 bg-slate-300 dark:bg-white/10 mx-0.5" />
        <button
          type="button"
          onClick={fetchGraph}
          className="p-2 rounded-xl text-amber-500 hover:text-amber-400 hover:bg-amber-500/10 transition-colors cursor-pointer"
          title="Reload Knowledge Graph"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Slide-out Node Inspector & Supersedence Timeline */}
      {selectedNode && (
        <div className="absolute top-4 right-4 bottom-4 w-96 glass-panel rounded-3xl p-5 shadow-2xl border border-slate-200 dark:border-white/[0.08] flex flex-col z-20 overflow-hidden animate-in slide-in-from-right-5 duration-200">
          <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-200 dark:border-white/10 flex-shrink-0">
            <div className="flex items-center gap-2.5 min-w-0">
              <span
                className="w-3.5 h-3.5 rounded-full flex-shrink-0 shadow-sm"
                style={{ backgroundColor: selectedNode.color }}
              />
              <div className="min-w-0">
                <span className="text-[10px] font-mono uppercase font-bold tracking-wider text-slate-500 block">
                  {selectedNode.type} Node
                </span>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                  {selectedNode.label}
                </h3>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSelectedNode(null)}
              className="p-1.5 rounded-xl hover:bg-slate-200 dark:hover:bg-white/10 text-slate-500 hover:text-slate-800 dark:hover:text-white transition-colors cursor-pointer flex-shrink-0"
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
            {selectedNode.type === 'Fact' && (
              <div
                className={`p-3 rounded-2xl border flex items-center gap-3 ${
                  selectedNode.data?.is_current !== false
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
                }`}
              >
                {selectedNode.data?.is_current !== false ? (
                  <CheckCircle2 size={18} className="flex-shrink-0" />
                ) : (
                  <AlertTriangle size={18} className="flex-shrink-0" />
                )}
                <div className="text-xs">
                  <span className="font-bold block">
                    {selectedNode.data?.is_current !== false ? 'Active Truth Fact' : 'Superseded (Invalidated)'}
                  </span>
                  <span className="text-[11px] opacity-80">
                    {selectedNode.data?.is_current !== false
                      ? 'This fact is current and trusted by MemoryGraph.'
                      : 'This fact was updated or invalidated in a later session.'}
                  </span>
                </div>
              </div>
            )}

            <div className="p-3.5 rounded-2xl bg-slate-100 dark:bg-black/30 border border-slate-200 dark:border-white/5 space-y-2.5">
              <span className="text-[10px] font-mono uppercase font-bold text-slate-500 block">
                Node Properties
              </span>
              <div className="space-y-1.5 text-xs font-mono">
                <div className="flex justify-between gap-2">
                  <span className="text-slate-500">ID:</span>
                  <span className="text-slate-800 dark:text-slate-200 font-semibold">{selectedNode.id}</span>
                </div>
                {selectedNode.data?.confidence !== undefined && (
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500">Confidence:</span>
                    <span className="text-amber-500 font-semibold">
                      {(selectedNode.data.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
                {selectedNode.data?.session_id && (
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500">Session ID:</span>
                    <span className="text-indigo-400 truncate">{selectedNode.data.session_id}</span>
                  </div>
                )}
                {selectedNode.data?.created_at && (
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500">Created:</span>
                    <span className="text-slate-400">
                      {new Date(selectedNode.data.created_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {selectedNode.data?.content && (
              <div className="p-3.5 rounded-2xl bg-slate-100 dark:bg-black/30 border border-slate-200 dark:border-white/5 space-y-1.5">
                <span className="text-[10px] font-mono uppercase font-bold text-slate-500 block">
                  Fact Statement
                </span>
                <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-sans">
                  "{selectedNode.data.content}"
                </p>
              </div>
            )}

            {timelineChain.length > 0 && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                    <History size={13} className="text-amber-500" />
                    Temporal History Chain
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 font-bold">
                    {timelineChain.length} revisions
                  </span>
                </div>

                <div className="relative pl-5 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-200 dark:before:bg-white/10">
                  {timelineChain.map((step) => {
                    const isSelectedStep = String(selectedNode.id) === String(step.nodeId);
                    return (
                      <div
                        key={step.nodeId}
                        onClick={() => focusNodeOnCanvas(step.nodeId)}
                        className={`relative p-3 rounded-2xl border transition-all cursor-pointer ${
                          isSelectedStep
                            ? 'bg-amber-500/10 border-amber-500/40 shadow-md'
                            : 'bg-slate-100/80 dark:bg-black/20 hover:bg-slate-200 dark:hover:bg-white/5 border-slate-200 dark:border-white/5'
                        }`}
                      >
                        <div
                          className={`absolute -left-[19px] top-3.5 w-2.5 h-2.5 rounded-full border-2 ${
                            step.isCurrent
                              ? 'bg-emerald-500 border-emerald-300'
                              : 'bg-rose-500 border-rose-300'
                          }`}
                        />

                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span
                            className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-md ${
                              step.isCurrent
                                ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                                : 'bg-rose-500/15 text-rose-600 dark:text-rose-400 line-through'
                            }`}
                          >
                            {step.isCurrent ? 'Current' : 'Superseded'}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {new Date(step.createdAt).toLocaleDateString()}
                          </span>
                        </div>

                        <p
                          className={`text-xs ${
                            step.isCurrent
                              ? 'text-slate-800 dark:text-slate-200 font-medium'
                              : 'text-slate-500 dark:text-slate-400 line-through'
                          }`}
                        >
                          {step.content}
                        </p>

                        <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-slate-500">
                          <span>Session: {step.sessionId}</span>
                          <span className="text-amber-500 flex items-center gap-1">
                            <Target size={10} /> Focus
                          </span>
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

