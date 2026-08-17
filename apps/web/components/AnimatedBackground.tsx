'use client';

import { useEffect, useRef } from 'react';

/* ─────────────────────────────────────────────
   Drop this once in your root layout:
   <AnimatedBackground />
   <main>{children}</main>
───────────────────────────────────────────── */
export function AnimatedBackground() {
  const grainRef  = useRef<HTMLCanvasElement>(null);
  const frameRef  = useRef<number>(0);
  const timeRef   = useRef<number>(0);

  /* ── Animated grain canvas ── */
  useEffect(() => {
    const canvas = grainRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let raf: number;

    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const paint = () => {
      const { width, height } = canvas;
      const imageData = ctx.createImageData(width, height);
      const data      = imageData.data;
      timeRef.current += 0.5;
      const t = timeRef.current;

      for (let i = 0; i < data.length; i += 4) {
        /* pseudo-random noise that shifts over time */
        const x    = (i / 4) % width;
        const y    = Math.floor((i / 4) / width);
        const rand = Math.sin(x * 0.17 + t * 0.03) *
                     Math.cos(y * 0.13 + t * 0.02) *
                     Math.sin((x + y) * 0.07 + t * 0.04);
        const n    = ((rand + 1) / 2) * 255;
        data[i]     = n;   // R
        data[i + 1] = n;   // G
        data[i + 2] = n;   // B
        data[i + 3] = 18;  // alpha — keep subtle
      }
      ctx.putImageData(imageData, 0, 0);
      raf = requestAnimationFrame(paint);
    };

    /* Run grain at ~24fps to keep GPU happy */
    let last = 0;
    const throttled = (ts: number) => {
      if (ts - last > 42) { last = ts; paint(); }
      raf = requestAnimationFrame(throttled);
    };
    raf = requestAnimationFrame(throttled);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

    return (
        <>
            <style>{`
        /* ── Root canvas background ── */
        .bg-root {
          position: fixed;
          inset: 0;
          z-index: -1;
          background: #04070f;
          overflow: hidden;
        }

        /* ── Aurora orbs ── */
        .aurora-orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(90px);
          will-change: transform, opacity;
        }
        .aurora-1 {
          width: 700px; height: 600px;
          top: -160px; right: -120px;
          background: radial-gradient(circle at 40% 40%,
            rgba(245,158,11,0.13) 0%,
            rgba(251,191,36,0.07) 40%,
            transparent 70%);
          animation: aurora-drift-1 18s ease-in-out infinite alternate;
        }
        .aurora-2 {
          width: 600px; height: 500px;
          bottom: -140px; left: -80px;
          background: radial-gradient(circle at 60% 60%,
            rgba(14,165,233,0.10) 0%,
            rgba(16,185,129,0.06) 40%,
            transparent 70%);
          animation: aurora-drift-2 22s ease-in-out infinite alternate;
        }
        .aurora-3 {
          width: 400px; height: 400px;
          top: 40%; left: 35%;
          background: radial-gradient(circle at 50% 50%,
            rgba(99,102,241,0.08) 0%,
            transparent 65%);
          animation: aurora-drift-3 26s ease-in-out infinite alternate;
        }
        .aurora-4 {
          width: 320px; height: 320px;
          top: 20%; left: 10%;
          background: radial-gradient(circle at 50% 50%,
            rgba(244,63,94,0.06) 0%,
            transparent 65%);
          animation: aurora-drift-4 20s ease-in-out infinite alternate;
        }

        @keyframes aurora-drift-1 {
          0%   { transform: translate(0,    0)    scale(1);    opacity: .9; }
          33%  { transform: translate(-60px, 40px) scale(1.08); opacity: .7; }
          66%  { transform: translate(30px,-50px) scale(0.95); opacity: 1;  }
          100% { transform: translate(-30px, 20px) scale(1.05); opacity: .8; }
        }
        @keyframes aurora-drift-2 {
          0%   { transform: translate(0,    0)    scale(1);    opacity: .8; }
          40%  { transform: translate(50px,-40px) scale(1.1);  opacity: 1;  }
          70%  { transform: translate(-30px, 30px) scale(0.9); opacity: .75;}
          100% { transform: translate(20px,-20px) scale(1.05); opacity: .9; }
        }
        @keyframes aurora-drift-3 {
          0%   { transform: translate(0,    0)   scale(1);    opacity: .6; }
          50%  { transform: translate(-40px,-30px) scale(1.12); opacity: .9;}
          100% { transform: translate(30px, 20px) scale(0.92); opacity: .5; }
        }
        @keyframes aurora-drift-4 {
          0%   { transform: translate(0,   0)   scale(1);   opacity: .5; }
          50%  { transform: translate(40px,30px) scale(1.1); opacity: .8; }
          100% { transform: translate(-20px,-10px) scale(0.9); opacity: .4;}
        }

        /* ── Perspective grid ── */
        .grid-perspective {
          position: absolute;
          inset: 0;
          overflow: hidden;
        }
        .grid-perspective svg {
          position: absolute;
          bottom: 0;
          left: 50%;
          transform: translateX(-50%);
          width: 180%;
          max-width: 1800px;
          opacity: 0.055;
        }
        .grid-line-h { animation: grid-scroll 8s linear infinite; }
        .grid-line-v { /* static, only horizontals scroll */ }

        @keyframes grid-scroll {
          from { stroke-dashoffset: 0; }
          to   { stroke-dashoffset: -60; }
        }

        /* ── Grain canvas ── */
        .grain-canvas {
          position: absolute;
          inset: 0;
          pointer-events: none;
          mix-blend-mode: overlay;
        }

        /* ── Vignette ── */
        .vignette {
          position: absolute;
          inset: 0;
          background: radial-gradient(ellipse 80% 80% at 50% 50%,
            transparent 40%,
            rgba(4,7,15,0.55) 100%);
          pointer-events: none;
        }

        /* ── Edge flare ── */
        .edge-flare-top {
          position: absolute;
          top: 0; left: 0; right: 0;
          height: 1px;
          background: linear-gradient(90deg,
            transparent 0%,
            rgba(245,158,11,0.25) 30%,
            rgba(251,191,36,0.40) 50%,
            rgba(245,158,11,0.25) 70%,
            transparent 100%);
          animation: flare-pulse 4s ease-in-out infinite;
        }
        @keyframes flare-pulse {
          0%,100% { opacity: .5; }
          50%      { opacity: 1;  }
        }
      `}</style>

            <div className="bg-root" aria-hidden="true">
                {/* Aurora colour blobs */}
                <div className="aurora-orb aurora-1" />
                <div className="aurora-orb aurora-2" />
                <div className="aurora-orb aurora-3" />
                <div className="aurora-orb aurora-4" />

                {/* Perspective grid */}
                <div className="grid-perspective">
                    <svg
                        viewBox="0 0 1200 600"
                        xmlns="http://www.w3.org/2000/svg"
                        preserveAspectRatio="xMidYMax meet"
                    >
                        <defs>
                            <linearGradient id="grid-fade" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="white" stopOpacity="0" />
                                <stop offset="60%" stopColor="white" stopOpacity="1" />
                                <stop offset="100%" stopColor="white" stopOpacity="1" />
                            </linearGradient>
                            <mask id="grid-mask">
                                <rect width="1200" height="600" fill="url(#grid-fade)" />
                            </mask>
                        </defs>

                        <g mask="url(#grid-mask)" stroke="rgba(148,163,184,1)" strokeWidth="0.6" fill="none">
                            {/* Horizontal lines — these animate (scrolling toward camera) */}
                            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((i) => {
                                const t = i / 12;
                                const e = Math.pow(t, 2.2);
                                const y = 600 - e * 600;
                                const xl = 600 - e * 580;
                                const xr = 600 + e * 580;
                                return (
                                    <line
                                        key={i}
                                        x1={xl} y1={y} x2={xr} y2={y}
                                        className="grid-line-h"
                                        strokeDasharray="9999"
                                        strokeDashoffset="0"
                                        style={{ animationDuration: `${7 + i * 0.18}s` }}
                                    />
                                );
                            })}

                            {/* Vertical/perspective rays — static */}
                            {[-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5].map((i) => {
                                const spread = i / 5;
                                const x1 = 600;
                                const y1 = 0;
                                const x2 = 600 + spread * 580;
                                const y2 = 600;
                                return (
                                    <line
                                        key={i}
                                        x1={x1} y1={y1} x2={x2} y2={y2}
                                        className="grid-line-v"
                                    />
                                );
                            })}
                        </g>
                    </svg>
                </div>

                {/* Animated grain canvas */}
                <canvas ref={grainRef} className="grain-canvas" />

                {/* Radial vignette — keeps edges dark */}
                <div className="vignette" />

                {/* Top-edge amber flare */}
                <div className="edge-flare-top" />
            </div>
        </>
    );
}