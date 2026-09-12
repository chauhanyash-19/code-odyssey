'use client';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const startDemo = async () => {
    setLoading(true);
    try {
      // Create a session with the backend to get a valid JWT token
      const res = await fetch('http://localhost:8000/call/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ingestion_mode: 'browser_mic' })
      });
      const data = await res.json();
      
      if (data.call_id && data.token) {
        // Pass token in URL parameters or localStorage (URL for demo simplicity)
        router.push(`/call/${data.call_id}?token=${data.token}`);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to connect to backend. Is FastAPI running on port 8000?');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4 text-center">
      <h1 className="text-5xl font-bold mb-4 tracking-tighter">PhaseGuard <span className="text-blue-500">OS</span></h1>
      <p className="text-xl text-gray-400 mb-8 max-w-2xl">
        360° Multi-Modal Anti-Scam System. Deepfake detection, micro-tremor stress analysis, and live LLM fact-checking.
      </p>
      
      <button 
        onClick={startDemo} 
        disabled={loading}
        className="px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-xl font-bold text-xl transition-all shadow-[0_0_20px_rgba(37,99,235,0.4)] hover:shadow-[0_0_30px_rgba(37,99,235,0.6)] disabled:opacity-50"
      >
        {loading ? 'Initializing...' : 'Start Live Demo'}
      </button>
    </div>
  );
}
