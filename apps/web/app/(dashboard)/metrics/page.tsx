'use client';

import React, { useEffect, useState } from 'react';

interface Metrics {
  total_calls_analyzed: number;
  total_groq_tokens: number;
  total_tts_chars: number;
  cost_per_call_inr: number;
  total_cost_inr: number;
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    // In a real app, this would fetch from the actual API endpoint
    // Assuming backend runs on 8000
    fetch('http://localhost:8000/metrics')
      .then(res => res.json())
      .then(data => setMetrics(data))
      .catch(err => console.error("Failed to fetch metrics", err));
  }, []);

  if (!metrics) {
    return <div className="p-8 text-white">Loading metrics...</div>;
  }

  return (
    <div className="min-h-screen bg-black text-white p-8 font-mono">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="border-b border-gray-800 pb-4">
          <h1 className="text-3xl font-bold tracking-tight">Cost-Efficiency Dashboard</h1>
          <p className="text-gray-400 mt-2">Real-time breakdown of API usage and inference costs.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-inner">
            <h3 className="text-gray-400 text-sm tracking-wider uppercase mb-2">Total Calls</h3>
            <p className="text-4xl font-bold text-cyan-400">{metrics.total_calls_analyzed}</p>
          </div>
          
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-inner">
            <h3 className="text-gray-400 text-sm tracking-wider uppercase mb-2">Groq Tokens</h3>
            <p className="text-4xl font-bold text-purple-400">{metrics.total_groq_tokens.toLocaleString()}</p>
          </div>
          
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-inner">
            <h3 className="text-gray-400 text-sm tracking-wider uppercase mb-2">Cost Per Call</h3>
            <p className="text-4xl font-bold text-green-400">~₹{metrics.cost_per_call_inr.toFixed(2)}</p>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-inner">
           <h3 className="text-gray-400 text-sm tracking-wider uppercase mb-4 border-b border-gray-800 pb-2">Total Cost Summary</h3>
           <div className="flex justify-between items-center text-xl">
             <span>Estimated Spend:</span>
             <span className="font-bold text-green-400">₹{metrics.total_cost_inr.toFixed(2)} INR</span>
           </div>
           <p className="text-gray-500 text-sm mt-4 italic">Note: Web-search verification API costs are excluded from this calculation.</p>
        </div>
      </div>
    </div>
  );
}
