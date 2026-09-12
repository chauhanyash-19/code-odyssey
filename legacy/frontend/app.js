// PhaseGuard Frontend Logic

const API_BASE = 'http://localhost:8000';
let ws = null;
let currentCallId = null;
let currentToken = null;

// DOM Elements
const els = {
    statusIndicator: document.querySelector('.status-indicator'),
    statusText: document.querySelector('.status-text'),
    btnSimulate: document.getElementById('btn-simulate'),
    btnDeploy: document.getElementById('btn-deploy-scambaiter'),
    btnDossier: document.getElementById('btn-generate-dossier'),
    callIdDisplay: document.getElementById('call-id-display'),
    
    // DSP Panel
    pdiValue: document.getElementById('pdi-value'),
    pdiFill: document.getElementById('pdi-fill'),
    pdiLabel: document.getElementById('pdi-label'),
    tremorValue: document.getElementById('tremor-value'),
    tremorFill: document.getElementById('tremor-fill'),
    tremorLabel: document.getElementById('tremor-label'),
    ensembleLabel: document.getElementById('ensemble-label'),
    
    // FactCheck Panel
    transcriptBox: document.getElementById('transcript-box'),
    verdictBanner: document.getElementById('verdict-banner'),
    factcheckSpinner: document.getElementById('factcheck-spinner'),
    finalVerdictOverlay: document.getElementById('final-verdict-overlay')
};

// Canvas Visualizer
const canvas = document.getElementById('audio-visualizer');
const ctx = canvas.getContext('2d');
let animationId;
let isVisualizing = false;

function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

function drawWaveform() {
    if (!isVisualizing) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    
    // Draw a generic cool looking animated wave for demo purposes
    // In a real app, this would be hooked up to the WebAudio API AnalyserNode
    const time = Date.now() / 1000;
    ctx.strokeStyle = els.finalVerdictOverlay.innerText === 'CRITICAL' 
        ? 'rgba(255, 51, 102, 0.8)' 
        : 'rgba(0, 255, 136, 0.8)';
    ctx.lineWidth = 2;

    for (let i = 0; i < canvas.width; i++) {
        const amplitude = 30 + Math.sin(time * 2 + i * 0.05) * 15;
        const y = canvas.height / 2 + Math.sin(i * 0.02 + time * 5) * amplitude * Math.sin(i * 0.01);
        ctx.lineTo(i, y);
    }
    
    ctx.stroke();
    animationId = requestAnimationFrame(drawWaveform);
}

// State Updates
function updateConnection(state, text) {
    els.statusIndicator.className = `status-indicator ${state}`;
    els.statusText.innerText = text;
}

function updateColor(val, threshold, element, isHigherWorse = true) {
    const isBad = isHigherWorse ? val >= threshold : val <= threshold;
    element.className = `fill ${isBad ? 'bg-critical' : 'bg-safe'}`;
    return isBad;
}

// WebSocket Handlers
function connectWebSocket(callId, token) {
    const wsUrl = `ws://localhost:8000/ws/call/${callId}?token=${token}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        updateConnection('connected', 'Live Analysis Active');
        isVisualizing = true;
        drawWaveform();
        // Clear placeholder
        els.transcriptBox.innerHTML = '';
        els.btnDossier.classList.remove('hidden');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'pdi_update') {
            els.pdiValue.innerText = data.pdi_score.toFixed(4);
            els.pdiFill.style.width = `${Math.min(data.pdi_score * 100, 100)}%`;
            updateColor(data.pdi_score, 0.6, els.pdiFill);
            els.pdiLabel.innerText = data.is_synthetic ? 'SYNTHETIC' : 'HUMAN';
            els.pdiLabel.className = `gauge-label ${data.is_synthetic ? 'color-critical' : 'color-safe'}`;
        }
        
        else if (data.type === 'tremor_update') {
            els.tremorValue.innerText = data.tremor_energy.toFixed(4);
            // Cap visual at 0.5 for fill bar
            els.tremorFill.style.width = `${Math.min((data.tremor_energy / 0.5) * 100, 100)}%`;
            updateColor(data.tremor_energy, 0.15, els.tremorFill, false); // Lower is worse (less human)
            els.tremorLabel.innerText = data.has_tremor ? 'HUMAN TREMOR' : 'FLAT';
        }
        
        else if (data.type === 'ensemble_update') {
            els.ensembleLabel.innerText = data.label;
            els.ensembleLabel.className = `value ${
                data.label === 'CRITICAL' ? 'bg-critical' : 
                data.label === 'SAFE' ? 'bg-safe' : 'bg-warning'
            }`;
        }
        
        else if (data.type === 'factcheck_update') {
            if (data.status === 'VERIFYING') {
                els.factcheckSpinner.classList.remove('hidden');
                return;
            }
            els.factcheckSpinner.classList.add('hidden');
            
            // Add transcript chunk (simulated from message for demo)
            const p = document.createElement('p');
            p.innerText = `> ${data.message}`;
            els.transcriptBox.appendChild(p);
            els.transcriptBox.scrollTop = els.transcriptBox.scrollHeight;
            
            // Update Banner
            els.verdictBanner.innerText = data.message;
            els.verdictBanner.className = `verdict-banner ${data.status.toLowerCase()}`;
            
            // Update Overlay
            els.finalVerdictOverlay.innerText = data.status;
            els.finalVerdictOverlay.style.opacity = '0.8';
            els.finalVerdictOverlay.style.color = data.status === 'CRITICAL' ? 'var(--accent-critical)' : 
                                                  data.status === 'SAFE' ? 'var(--accent-safe)' : 'var(--accent-warning)';
            
            if (data.status === 'CRITICAL') {
                els.btnDeploy.classList.remove('hidden');
            }
        }
    };

    ws.onerror = (err) => {
        console.error('WS Error', err);
        updateConnection('error', 'Connection Error');
    };

    ws.onclose = () => {
        updateConnection('disconnected', 'Stream Ended');
        isVisualizing = false;
    };
}

// Buttons
els.btnSimulate.addEventListener('click', async () => {
    try {
        els.btnSimulate.disabled = true;
        els.btnSimulate.innerText = 'Initializing...';
        
        const res = await fetch(`${API_BASE}/call/init`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ingestion_mode: 'browser_mic' })
        });
        const data = await res.json();
        
        currentCallId = data.call_id;
        currentToken = data.token;
        els.callIdDisplay.innerText = currentCallId;
        
        els.btnSimulate.innerText = 'Simulating...';
        
        // Connect WS
        connectWebSocket(currentCallId, currentToken);
        
    } catch (err) {
        console.error(err);
        alert('Failed to initialize call. Is backend running?');
        els.btnSimulate.disabled = false;
        els.btnSimulate.innerText = 'Simulate Call';
    }
});

els.btnDeploy.addEventListener('click', async () => {
    if (!currentCallId) return;
    try {
        await fetch(`${API_BASE}/call/${currentCallId}/scambait`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        els.btnDeploy.innerText = 'Scambaiter Active';
        els.btnDeploy.disabled = true;
        els.btnDeploy.classList.remove('warning');
        els.btnDeploy.classList.add('primary');
    } catch (err) {
        console.error(err);
    }
});

els.btnDossier.addEventListener('click', async () => {
    if (!currentCallId) return;
    window.open(`${API_BASE}/call/${currentCallId}/dossier?token=${currentToken}`, '_blank');
});
