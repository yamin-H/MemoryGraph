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
  Lock,
  Unlock,
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

const TYPE_CONFIG: Record<string, { color: string; darkColor: string; val: number; label: string }> = {
  Entity:          { color: '#0284c7', darkColor: '#38bdf8', val: 18, label: 'Entity Hub' },
  Fact:            { color: '#059669', darkColor: '#10b981', val: 12, label: 'Fact (Active)' },
  FactSuperseded:  { color: '#dc2626', darkColor: '#f43f5e', val: 10, label: 'Fact (Superseded)' },
  Session:         { color: '#6366f1', darkColor: '#818cf8', val: 14, label: 'Session Turn' },
  Summary:         { color: '#9333ea', darkColor: '#c084fc', val: 11, label: 'Summary' },
  Message:         { color: '#64748b', darkColor: '#94a3b8', val: 6,  label: 'Raw Message' },
};

const EDGE_COLORS_DARK: Record<string, string> = {
  SUPERSEDES:     '#f43f5e',
  INVALIDATED_BY: '#fb7185',
  CONTAINS:       '#818cf8aa',
  MENTIONS:       '#38bdf8aa',
  OCCURRED_IN:    '#10b981aa',
  HAS_SUMMARY:    '#c084fcaa',
};

const EDGE_COLORS_LIGHT: Record<string, string> = {
  SUPERSEDES:     '#dc2626',
  INVALIDATED_BY: '#e11d48',
  CONTAINS:       '#6366f199',
  MENTIONS:       '#0284c799',
  OCCURRED_IN:    '#05966999',
  HAS_SUMMARY:    '#9333ea99',
};

const EMPTY_GRAPH = Object.freeze({ nodes: [], links: [] });

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
  const isDraggingRef = useRef(false);

  // Track which nodes are pinned (via drag) so user can see pin state
  const [pinnedNodes, setPinnedNodes] = useState<Set<string>>(new Set());

  // Animation tick for breathing glow effect
  const animFrameRef = useRef<number>(0);
  const tickRef = useRef(0);

  // Breathing animation loop — drives subtle glow pulsation
  useEffect(() => {
    const animate = () => {
      tickRef.current += 1;
      animFrameRef.current = requestAnimationFrame(animate);
    };
    animFrameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, []);

  // ─── Container sizing (must depend on loading so it measures when DOM mounts) ───
  useEffect(() => {
    if (loading || !containerRef.current) return;
    const el = containerRef.current;
    
    const updateSize = () => {
      if (el && el.clientWidth > 0 && el.clientHeight > 0) {
        setDimensions({
          width: el.clientWidth,
          height: el.clientHeight,
        });
      }
    };

    updateSize();

    const observer = new ResizeObserver((entries) => {
      if (entries[0] && entries[0].contentRect.width > 0) {
        setDimensions({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height,
        });
      }
    });
    observer.observe(el);

    return () => observer.disconnect();
  }, [loading]);

  const setContainerRef = useCallback((node: HTMLDivElement | null) => {
    containerRef.current = node;
    if (node && node.clientWidth > 0 && node.clientHeight > 0) {
      setDimensions({
        width: node.clientWidth,
        height: node.clientHeight,
      });
    }
  }, []);

  // ─── Fetch graph data ───
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
      setPinnedNodes(new Set());
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

  // ─── Filtered + formatted graph data (React-managed, never mutated by D3) ───
  const filteredGraphData = useMemo(() => {
    if (!rawData || !rawData.nodes) return { nodes: [], links: [] };
    const activeNodes = rawData.nodes.filter((node) => visibleTypes[node.type] !== false);
    const activeNodeIds = new Set(activeNodes.map((n) => String(n.id)));
    const edgeColors = isDark ? EDGE_COLORS_DARK : EDGE_COLORS_LIGHT;

    const formattedNodes = activeNodes.map((node) => {
      const isFact = node.type === 'Fact';
      const isCurrent = node.data?.is_current !== false;
      let color = (isDark ? TYPE_CONFIG[node.type]?.darkColor : TYPE_CONFIG[node.type]?.color) || '#94a3b8';
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

    const formattedLinks = rawData.edges
      .filter((e) => activeNodeIds.has(String(e.source)) && activeNodeIds.has(String(e.target)))
      .map((e) => ({
        source: String(e.source),
        target: String(e.target),
        type: e.type,
        color: edgeColors[e.type] || (isDark ? '#475569' : '#94a3b8'),
      }));

    return { nodes: formattedNodes, links: formattedLinks };
  }, [rawData, visibleTypes, isDark]);



  // ─── Timeline chain for node inspector ───
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

  // ─── Focus + zoom to a specific node ───
  const focusNodeOnCanvas = useCallback((nodeId: string) => {
    if (!graphRef.current) return;
    const currentNodes = graphRef.current.graphData()?.nodes || [];
    const targetNode = currentNodes.find((n: any) => String(n.id) === String(nodeId));
    if (targetNode && typeof targetNode.x === 'number') {
      graphRef.current.centerAt(targetNode.x, targetNode.y, 800);
      graphRef.current.zoom(2.4, 800);
      setSelectedNode(targetNode);
    }
  }, []);

  // ─── Unpin all nodes ───
  const unpinAllNodes = useCallback(() => {
    if (!graphRef.current) return;
    const data = graphRef.current.graphData();
    if (data?.nodes) {
      data.nodes.forEach((node: any) => {
        node.fx = undefined;
        node.fy = undefined;
      });
    }
    setPinnedNodes(new Set());
    graphRef.current.d3ReheatSimulation();
  }, []);

  // ─── Toggle filter ───
  const toggleType = (type: string) => {
    setVisibleTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  // ─── Loading state ───
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-slate-50 dark:bg-[#090d16]">
        <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center mb-3 animate-spin">
          <RefreshCw size={20} className="text-amber-500" />
        </div>
        <p className="text-xs font-bold text-slate-800 dark:text-slate-200 font-heading">Loading HydraDB Graph Topology...</p>
        <p className="text-[11px] text-slate-500 mt-1 font-mono">Traversing temporal edges &amp; supersedence paths</p>
      </div>
    );
  }

  // ─── Empty state ───
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
      <div ref={setContainerRef} className="w-full h-full absolute inset-0">
        {dimensions.width > 0 && dimensions.height > 0 && filteredGraphData.nodes.length > 0 && (
          <ForceGraph2D
            ref={graphRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={filteredGraphData}
            backgroundColor={canvasBg}

            // ── Simulation tuning ──
            d3VelocityDecay={0.3}
            d3AlphaDecay={0.02}
            cooldownTime={5000}

            // ── Interaction flags ──
            enableNodeDrag={true}
            enableZoomInteraction={true}
            enablePanInteraction={true}

            // ── Edge styling ──
            linkColor={(link: any) => link.color}
            linkWidth={(link: any) => (link.type === 'SUPERSEDES' ? 2.5 : link.type === 'INVALIDATED_BY' ? 2 : 1)}
            linkDirectionalArrowLength={(link: any) => (link.type === 'SUPERSEDES' || link.type === 'INVALIDATED_BY' ? 6 : 3.5)}
            linkDirectionalArrowRelPos={1}
            linkDirectionalArrowColor={(link: any) => link.color}
            // Animated particles on SUPERSEDES edges
            linkDirectionalParticles={(link: any) => (link.type === 'SUPERSEDES' ? 3 : link.type === 'MENTIONS' ? 1 : 0)}
            linkDirectionalParticleWidth={(link: any) => (link.type === 'SUPERSEDES' ? 3 : 1.5)}
            linkDirectionalParticleSpeed={0.005}
            linkDirectionalParticleColor={(link: any) => link.color}
            linkCurvature={(link: any) => (link.type === 'SUPERSEDES' ? 0.15 : 0)}
            linkLineDash={(link: any) => (link.type === 'INVALIDATED_BY' ? [4, 4] : null)}

            // ── Node events ──
            onNodeHover={(node: any) => {
              hoveredNodeRef.current = node || null;
              if (containerRef.current) {
                containerRef.current.style.cursor = node ? 'grab' : 'default';
              }
            }}

            // ─── DRAG HANDLERS (core fix) ───
            onNodeDrag={(node: any) => {
              isDraggingRef.current = true;
              if (containerRef.current) {
                containerRef.current.style.cursor = 'grabbing';
              }
              // Pin the node to follow the cursor exactly
              node.fx = node.x;
              node.fy = node.y;
            }}
            onNodeDragEnd={(node: any) => {
              isDraggingRef.current = false;
              if (containerRef.current) {
                containerRef.current.style.cursor = 'grab';
              }
              // Keep the node pinned where the user dropped it
              node.fx = node.x;
              node.fy = node.y;
              setPinnedNodes((prev) => {
                const next = new Set(prev);
                next.add(String(node.id));
                return next;
              });
            }}

            onNodeClick={(node: any) => {
              if (isDraggingRef.current) return; // Don't select while dragging
              setSelectedNode(node);
            }}

            // Double-click to unpin a node
            onNodeRightClick={(node: any) => {
              node.fx = undefined;
              node.fy = undefined;
              setPinnedNodes((prev) => {
                const next = new Set(prev);
                next.delete(String(node.id));
                return next;
              });
              if (graphRef.current) {
                graphRef.current.d3ReheatSimulation();
              }
            }}

            onBackgroundClick={() => {
              setSelectedNode(null);
            }}

            // ── Custom node rendering ──
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              try {
                if (!node || typeof node.x !== 'number' || typeof node.y !== 'number' || isNaN(node.x) || isNaN(node.y)) {
                  return;
                }

                const rawLabel = node.label || node.id || '';
                const radius = Math.max(6, (node.val || 8) * 0.85);
                const isEntity = node.type === 'Entity';
                const isFact = node.type === 'Fact';
                const isSuperseded = isFact && node.isCurrent === false;
                const isPinned = node.fx !== undefined && node.fy !== undefined;

                const isSelected = selectedNode && String(selectedNode.id) === String(node.id);
                const isHovered = hoveredNodeRef.current && String(hoveredNodeRef.current.id) === String(node.id);

                const scale = Math.max(0.1, globalScale || 1);
                const t = tickRef.current;

                // ─── Breathing glow aura ───
                const breathePhase = Math.sin(t * 0.03) * 0.5 + 0.5; // 0..1 oscillation
                const glowRadius = radius + (isSelected ? 8 : isHovered ? 6 : 3) + (isEntity ? breathePhase * 3 : 0);
                const glowAlpha = isSelected ? 0.45 : isHovered ? 0.35 : (0.15 + breathePhase * 0.1);

                ctx.beginPath();
                ctx.arc(node.x, node.y, glowRadius, 0, 2 * Math.PI, false);
                if (isSuperseded) {
                  ctx.fillStyle = isDark ? `rgba(244, 63, 94, ${glowAlpha})` : `rgba(220, 38, 38, ${glowAlpha * 0.7})`;
                } else if (isFact) {
                  ctx.fillStyle = isDark ? `rgba(16, 185, 129, ${glowAlpha})` : `rgba(5, 150, 105, ${glowAlpha * 0.7})`;
                } else if (isEntity) {
                  ctx.fillStyle = isDark ? `rgba(56, 189, 248, ${glowAlpha + 0.1})` : `rgba(2, 132, 199, ${glowAlpha * 0.8})`;
                } else {
                  ctx.fillStyle = `${node.color}${Math.round(glowAlpha * 255).toString(16).padStart(2, '0')}`;
                }
                ctx.fill();

                // ─── Node body ───
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);

                // Gradient fill for richer look
                const grad = ctx.createRadialGradient(
                  node.x - radius * 0.3, node.y - radius * 0.3, radius * 0.1,
                  node.x, node.y, radius
                );
                grad.addColorStop(0, lightenColor(node.color, 30));
                grad.addColorStop(1, node.color);
                ctx.fillStyle = grad;
                ctx.fill();

                // ─── Border ring ───
                ctx.beginPath();
                ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
                if (isSuperseded) {
                  ctx.setLineDash([3 / scale, 3 / scale]);
                  ctx.strokeStyle = isDark ? '#f43f5e' : '#dc2626';
                  ctx.lineWidth = 2.5 / scale;
                } else if (isSelected) {
                  ctx.setLineDash([]);
                  ctx.strokeStyle = '#f59e0b';
                  ctx.lineWidth = 3.5 / scale;
                } else if (isHovered) {
                  ctx.setLineDash([]);
                  ctx.strokeStyle = '#fbbf24';
                  ctx.lineWidth = 2.5 / scale;
                } else {
                  ctx.setLineDash([]);
                  ctx.strokeStyle = isDark ? '#ffffff55' : '#0f172a44';
                  ctx.lineWidth = 1.2 / scale;
                }
                ctx.stroke();
                ctx.setLineDash([]);

                // ─── Pin indicator ───
                if (isPinned) {
                  const pinRadius = 3 / scale;
                  ctx.beginPath();
                  ctx.arc(node.x + radius * 0.75, node.y - radius * 0.75, pinRadius, 0, 2 * Math.PI);
                  ctx.fillStyle = '#f59e0b';
                  ctx.fill();
                  ctx.strokeStyle = isDark ? '#090d16' : '#ffffff';
                  ctx.lineWidth = 1 / scale;
                  ctx.stroke();
                }

                // ─── Label badge ───
                const shouldShowLabel = isEntity || isSelected || isHovered || scale > 2.2;
                if (shouldShowLabel) {
                  const displayLabel = rawLabel.length > 28 ? `${rawLabel.slice(0, 26)}…` : rawLabel;
                  const fontSize = isEntity ? Math.max(12 / scale, 10) : Math.max(10 / scale, 8);
                  ctx.font = isEntity ? `bold ${fontSize}px Inter, system-ui, sans-serif` : `500 ${fontSize}px Inter, system-ui, sans-serif`;
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';

                  const textWidth = ctx.measureText(displayLabel).width;
                  const padX = 7 / scale;
                  const padY = 3.5 / scale;
                  const textY = node.y + radius + fontSize * 1.1;
                  const badgeW = textWidth + padX * 2;
                  const badgeH = fontSize + padY * 2;
                  const cornerR = 4 / scale;

                  // Rounded rect badge background
                  ctx.beginPath();
                  roundRect(ctx, node.x - badgeW / 2, textY - badgeH / 2, badgeW, badgeH, cornerR);
                  ctx.fillStyle = isDark ? 'rgba(9, 13, 22, 0.92)' : 'rgba(255, 255, 255, 0.95)';
                  ctx.fill();

                  // Badge border
                  ctx.strokeStyle = isEntity
                    ? (isDark ? '#38bdf855' : '#0284c755')
                    : (isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)');
                  ctx.lineWidth = 0.8 / scale;
                  ctx.stroke();

                  // Badge shadow
                  ctx.shadowColor = isDark ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.1)';
                  ctx.shadowBlur = 4 / scale;
                  ctx.shadowOffsetY = 1 / scale;

                  // Text
                  ctx.fillStyle = isEntity
                    ? (isDark ? '#38bdf8' : '#0284c7')
                    : isSuperseded
                    ? (isDark ? '#fda4af' : '#b91c1c')
                    : (isDark ? '#f1f5f9' : '#0f172a');
                  ctx.fillText(displayLabel, node.x, textY);

                  // Reset shadow
                  ctx.shadowColor = 'transparent';
                  ctx.shadowBlur = 0;
                  ctx.shadowOffsetY = 0;

                  // Strikethrough for superseded facts
                  if (isSuperseded) {
                    ctx.beginPath();
                    ctx.strokeStyle = isDark ? '#f43f5e' : '#dc2626';
                    ctx.lineWidth = 1.2 / scale;
                    ctx.moveTo(node.x - textWidth / 2, textY);
                    ctx.lineTo(node.x + textWidth / 2, textY);
                    ctx.stroke();
                  }
                }
              } catch {
                // Silently ignore render errors for stability
              }
            }}
            nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
              const radius = Math.max(8, (node.val || 8) * 0.85 + 4);
              ctx.beginPath();
              ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
              ctx.fillStyle = color;
              ctx.fill();
            }}
            onEngineStop={() => {
              if (graphRef.current) {
                graphRef.current.zoomToFit(400, 40);
              }
            }}
          />
        )}
      </div>

      {/* ──── Floating Toolbar & Node Legend ──── */}
      <div className="absolute top-4 left-4 flex flex-col gap-3 z-10 pointer-events-none">
        {/* Type toggle filters */}
        <div className="glass-panel p-3.5 space-y-2.5 shadow-2xl rounded-2xl max-w-xs border border-slate-200 dark:border-white/[0.08] pointer-events-auto animate-fade-in-up">
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
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer ${
                      isVisible
                        ? 'bg-slate-100 dark:bg-white/[0.06] text-slate-900 dark:text-white border border-slate-200 dark:border-white/[0.08]'
                        : 'text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 opacity-40 hover:opacity-75'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full shadow-sm flex-shrink-0 transition-transform duration-200 ${isVisible ? 'scale-100' : 'scale-75'}`}
                        style={{ backgroundColor: isDark ? config.darkColor : config.color }}
                      />
                      <span className="text-xs">{config.label}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-md bg-slate-200/50 dark:bg-black/40 text-slate-600 dark:text-slate-400">
                        {count}
                      </span>
                      <Eye size={12} className={`transition-opacity duration-200 ${isVisible ? 'text-slate-700 dark:text-slate-300 opacity-100' : 'text-slate-400 opacity-40'}`} />
                    </div>
                  </button>
                );
              })}

            {/* Superseded fact indicator */}
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
        <div className="glass-panel p-3 shadow-xl rounded-2xl max-w-xs border border-slate-200 dark:border-white/[0.08] space-y-2 pointer-events-auto animate-fade-in-up stagger-2">
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

        {/* Interaction hints */}
        <div className="glass-panel p-2.5 shadow-xl rounded-2xl max-w-xs border border-slate-200 dark:border-white/[0.08] pointer-events-auto animate-fade-in-up stagger-3">
          <div className="grid grid-cols-1 gap-1 text-[10px] font-mono text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="text-amber-500">Drag</span> → Pin node
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-amber-500">Right-click</span> → Unpin node
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-amber-500">Click</span> → Inspect node
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-amber-500">Scroll</span> → Zoom in/out
            </div>
          </div>
        </div>
      </div>

      {/* ──── Floating Canvas Controls (Bottom Right) ──── */}
      <div className="absolute bottom-6 right-6 flex items-center gap-2 z-10 glass-panel p-1.5 rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08] animate-fade-in-up stagger-3">
        <button
          type="button"
          onClick={() => {
            if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() * 1.4, 400);
          }}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-all duration-200 cursor-pointer"
          title="Zoom In"
        >
          <ZoomIn size={16} />
        </button>
        <button
          type="button"
          onClick={() => {
            if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() / 1.4, 400);
          }}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-all duration-200 cursor-pointer"
          title="Zoom Out"
        >
          <ZoomOut size={16} />
        </button>
        <button
          type="button"
          onClick={() => {
            if (graphRef.current) graphRef.current.zoomToFit(600, 50);
          }}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-all duration-200 cursor-pointer"
          title="Fit to Screen"
        >
          <Maximize2 size={16} />
        </button>

        {pinnedNodes.size > 0 && (
          <>
            <div className="w-[1px] h-4 bg-slate-300 dark:bg-white/10 mx-0.5" />
            <button
              type="button"
              onClick={unpinAllNodes}
              className="p-2 rounded-xl text-indigo-500 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all duration-200 cursor-pointer flex items-center gap-1"
              title="Unpin All Nodes"
            >
              <Unlock size={14} />
              <span className="text-[10px] font-mono font-bold">{pinnedNodes.size}</span>
            </button>
          </>
        )}

        <div className="w-[1px] h-4 bg-slate-300 dark:bg-white/10 mx-0.5" />
        <button
          type="button"
          onClick={fetchGraph}
          className="p-2 rounded-xl text-amber-500 hover:text-amber-400 hover:bg-amber-500/10 transition-all duration-200 cursor-pointer"
          title="Reload Knowledge Graph"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* ──── Node Inspector Panel ──── */}
      {selectedNode && (
        <div
          className="absolute top-4 right-4 bottom-4 w-96 glass-panel rounded-3xl p-5 shadow-2xl border border-slate-200 dark:border-white/[0.08] flex flex-col z-20 overflow-hidden"
          style={{
            animation: 'slideInRight 0.35s cubic-bezier(0.16, 1, 0.3, 1) both',
          }}
        >
          <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-200 dark:border-white/10 flex-shrink-0">
            <div className="flex items-center gap-2.5 min-w-0">
              <span
                className="w-3.5 h-3.5 rounded-full flex-shrink-0 shadow-sm"
                style={{ backgroundColor: selectedNode.color }}
              />
              <div className="min-w-0">
                <span className="text-[10px] font-mono uppercase font-bold tracking-wider text-slate-500 block">
                  {selectedNode.type} Node
                  {pinnedNodes.has(String(selectedNode.id)) && (
                    <Lock size={9} className="inline ml-1 text-amber-500" />
                  )}
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
                  <span className="text-slate-800 dark:text-slate-200 font-semibold truncate max-w-[200px]">{selectedNode.id}</span>
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
                    <span className="text-indigo-400 truncate max-w-[180px]">{selectedNode.data.session_id}</span>
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
                  &quot;{selectedNode.data.content}&quot;
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
                  {timelineChain.map((step, idx) => {
                    const isSelectedStep = String(selectedNode.id) === String(step.nodeId);
                    return (
                      <div
                        key={step.nodeId}
                        onClick={() => focusNodeOnCanvas(step.nodeId)}
                        className={`relative p-3 rounded-2xl border transition-all duration-200 cursor-pointer ${
                          isSelectedStep
                            ? 'bg-amber-500/10 border-amber-500/40 shadow-md'
                            : 'bg-slate-100/80 dark:bg-black/20 hover:bg-slate-200 dark:hover:bg-white/5 border-slate-200 dark:border-white/5'
                        }`}
                        style={{
                          animation: `fadeInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) ${idx * 0.05}s both`,
                        }}
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

// ─── Canvas Helpers ───

/** Draw a rounded rectangle path on a Canvas 2D context */
function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number
) {
  r = Math.min(r, w / 2, h / 2);
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** Lighten a hex color by a percentage (0-100) */
function lightenColor(hex: string, percent: number): string {
  try {
    const h = hex.replace('#', '');
    const r = Math.min(255, parseInt(h.substring(0, 2), 16) + Math.round(2.55 * percent));
    const g = Math.min(255, parseInt(h.substring(2, 4), 16) + Math.round(2.55 * percent));
    const b = Math.min(255, parseInt(h.substring(4, 6), 16) + Math.round(2.55 * percent));
    return `rgb(${r},${g},${b})`;
  } catch {
    return hex;
  }
}
