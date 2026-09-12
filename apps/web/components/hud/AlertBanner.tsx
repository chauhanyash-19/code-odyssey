'use client';
import React, { useState } from 'react';
import { AlertStatus } from '../../lib/types/protocol';

interface Props {
  status: AlertStatus;
  message?: string;
}

export default function AlertBanner({ status, message }: Props) {
  const [isMuted, setIsMuted] = useState(false);

  const getStatusConfig = () => {
    switch (status) {
      case 'critical':
        return {
          bg: 'bg-red-600',
          text: 'text-white',
          border: 'border-red-400',
          pulse: 'animate-pulse',
          icon: '⚠️',
          label: 'CRITICAL WARNING: LIKELY SCAM'
        };
      case 'uncertain':
        return {
          bg: 'bg-amber-500',
          text: 'text-black',
          border: 'border-amber-300',
          pulse: '',
          icon: '🤔',
          label: 'UNCERTAIN: PROCEED WITH CAUTION'
        };
      case 'safe':
        return {
          bg: 'bg-green-600',
          text: 'text-white',
          border: 'border-green-400',
          pulse: '',
          icon: '✅',
          label: 'SAFE: NO SCAM DETECTED'
        };
      case 'verifying':
        return {
          bg: 'bg-blue-600',
          text: 'text-white',
          border: 'border-blue-400',
          pulse: 'animate-pulse',
          icon: '🔍',
          label: 'VERIFYING CLAIMS...'
        };
      case 'limited':
        return {
          bg: 'bg-purple-700',
          text: 'text-white',
          border: 'border-purple-500',
          pulse: '',
          icon: '⚡',
          label: 'LIMITED MODE: LOCAL CHECKS ONLY'
        };
      case 'idle':
      default:
        return {
          bg: 'bg-gray-800',
          text: 'text-gray-400',
          border: 'border-gray-700',
          pulse: '',
          icon: '⏸️',
          label: 'SYSTEM IDLE'
        };
    }
  };

  const config = getStatusConfig();
  const showPrimaryBadge = status !== 'idle';

  return (
    <div className={`w-full p-6 rounded-xl border-4 ${config.bg} ${config.text} ${config.border} ${config.pulse} transition-all duration-300 shadow-2xl relative`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1">
          <span className="text-4xl">{config.icon}</span>
          <div className="flex flex-col gap-1">
            <h2 className="text-3xl font-bold tracking-wide uppercase">
              {config.label}
            </h2>
            {showPrimaryBadge && (
              // "Primary Detection Engine" badge — mirrors legacy/frontend/index.html .primary-badge
              <span className="inline-flex items-center gap-1 text-xs font-semibold tracking-widest uppercase opacity-80 bg-black/20 px-2 py-0.5 rounded-full w-fit">
                🧠 Primary Detection Engine
              </span>
            )}
          </div>
        </div>
        
        {status === 'critical' && (
          <button 
            onClick={() => setIsMuted(!isMuted)}
            className="p-3 bg-black/20 rounded-full hover:bg-black/30 transition-colors"
            title="Toggle Spoken Warning"
          >
            <span className="text-2xl">{isMuted ? '🔇' : '🔊'}</span>
          </button>
        )}
      </div>
      
      {message && (
        <div className="mt-4 p-4 bg-black/20 rounded-lg">
          <p className="text-xl font-medium leading-relaxed">
            {message}
          </p>
        </div>
      )}
    </div>
  );
}

