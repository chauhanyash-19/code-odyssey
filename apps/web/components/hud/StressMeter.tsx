'use client';
import React, { useEffect, useRef } from 'react';

interface Props {
  tremorEnergy: number;
  isDspEnabled?: boolean;
}

export default function StressMeter({ tremorEnergy, isDspEnabled = false }: Props) {
  const fillRef = useRef<HTMLDivElement>(null);
  const currentEnergy = useRef(0);

  useEffect(() => {
    if (!isDspEnabled) return; // Don't animate when DSP is disabled

    let animationId: number;

    const animate = () => {
      currentEnergy.current += (tremorEnergy - currentEnergy.current) * 0.1;
      
      if (fillRef.current) {
        // Display up to 0.5 as 100% for better visual scaling
        const percent = Math.min((currentEnergy.current / 0.5) * 100, 100);
        fillRef.current.style.height = `${percent}%`;
        
        // Color transition: low stress (green) to high stress (red)
        if (currentEnergy.current > 0.15) {
          fillRef.current.className = 'w-full absolute bottom-0 transition-colors duration-200 bg-red-500';
        } else {
          fillRef.current.className = 'w-full absolute bottom-0 transition-colors duration-200 bg-green-500';
        }
      }
      
      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => cancelAnimationFrame(animationId);
  }, [tremorEnergy, isDspEnabled]);

  return (
    <div className="w-full h-full min-h-[300px] flex flex-col items-center justify-center bg-gray-900 rounded-xl overflow-hidden border border-gray-800 p-6 shadow-inner relative">
      <div className="absolute top-4 left-4 z-10 text-gray-400 font-mono text-sm tracking-wider uppercase">
        Physiological Tremor (8-12Hz)
      </div>

      {isDspEnabled ? (
        <>
          <div className="flex-1 w-full flex items-center justify-center mt-6">
            <div className="w-16 h-48 bg-gray-800 rounded-full overflow-hidden relative shadow-inner border border-gray-700">
              <div ref={fillRef} className="w-full absolute bottom-0 bg-green-500 transition-colors duration-200" style={{ height: '0%' }} />
              
              {/* Threshold marker */}
              <div className="absolute w-full h-0.5 bg-red-500/50 z-10" style={{ bottom: '30%' }} />
            </div>
          </div>
          
          <div className="mt-4 font-mono text-xl">
            <span className={tremorEnergy > 0.15 ? 'text-red-400' : 'text-green-400'}>
              {tremorEnergy.toFixed(4)}
            </span>
          </div>
        </>
      ) : (
        // DSP disabled notice — matches legacy/frontend/index.html behaviour
        <div className="flex flex-col items-center justify-center gap-3 text-center px-4">
          <span className="text-3xl opacity-40">〰️</span>
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

