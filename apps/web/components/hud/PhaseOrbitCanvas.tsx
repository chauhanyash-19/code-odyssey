'use client';
import React, { useEffect, useRef } from 'react';

interface Props {
  pdiScore: number;
  isDspEnabled?: boolean;
}

export default function PhaseOrbitCanvas({ pdiScore, isDspEnabled = false }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const currentPdi = useRef(0); // For interpolation

  useEffect(() => {
    if (!isDspEnabled) return; // Don't animate when DSP is disabled

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let t = 0;

    const draw = () => {
      // Eased interpolation towards the target pdiScore
      currentPdi.current += (pdiScore - currentPdi.current) * 0.1;
      
      const width = canvas.width;
      const height = canvas.height;
      
      ctx.clearRect(0, 0, width, height);
      
      const centerX = width / 2;
      const centerY = height / 2;
      const maxRadius = Math.min(width, height) / 2 - 20;

      // Draw orbit trails
      ctx.fillStyle = 'rgba(0, 255, 136, 0.1)';
      ctx.strokeStyle = `rgba(0, 255, 136, ${1 - currentPdi.current})`;

      ctx.beginPath();
      for (let i = 0; i < 200; i++) {
        // Scatter depends on PDI score
        const scatter = currentPdi.current * maxRadius * 0.8;
        const radius = maxRadius * 0.5 + Math.sin(i * 0.1 + t) * scatter;
        const angle = i * 0.1 + t * 0.5;
        
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;
        
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      t += 0.05;
      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [pdiScore, isDspEnabled]);

  return (
    <div className="w-full h-full min-h-[300px] flex items-center justify-center bg-gray-900 rounded-xl overflow-hidden border border-gray-800 relative shadow-inner">
      <div className="absolute top-4 left-4 z-10 text-gray-400 font-mono text-sm tracking-wider uppercase">
        Bispectrum PDI
      </div>

      {isDspEnabled ? (
        <>
          <div className="absolute top-4 right-4 z-10 font-mono text-sm">
            <span className={pdiScore > 0.6 ? 'text-red-400' : 'text-green-400'}>
              {pdiScore.toFixed(4)}
            </span>
          </div>
          <canvas
            ref={canvasRef}
            width={400}
            height={400}
            className="w-full h-full max-w-[400px] max-h-[400px]"
          />
        </>
      ) : (
        // DSP disabled notice — matches legacy/frontend/index.html behaviour
        <div className="flex flex-col items-center justify-center gap-3 text-center px-6">
          <span className="text-3xl opacity-40">📡</span>
          <p className="text-gray-400 text-sm font-mono leading-relaxed">
            DSP voice detection is <strong className="text-gray-300">disabled</strong> in this build.
          </p>
          <code className="text-xs bg-gray-800 text-amber-400 px-3 py-1.5 rounded-md border border-gray-700">
            DSP_VOICE_DETECTION_ENABLED=true
          </code>
          <p className="text-gray-600 text-xs">to enable for research use</p>
        </div>
      )}
    </div>
  );
}
