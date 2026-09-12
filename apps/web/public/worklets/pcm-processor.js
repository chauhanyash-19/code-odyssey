class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // 512 samples = 32ms at 16kHz
    this.bufferSize = 512;
    this.buffer = new Int16Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input.length > 0) {
      const channel = input[0];
      for (let i = 0; i < channel.length; i++) {
        // Convert Float32 [-1.0, 1.0] to Int16 [-32768, 32767]
        let s = Math.max(-1, Math.min(1, channel[i]));
        this.buffer[this.bufferIndex++] = s < 0 ? s * 0x8000 : s * 0x7FFF;

        if (this.bufferIndex >= this.bufferSize) {
          // Flush to main thread
          this.port.postMessage(this.buffer.buffer.slice(0));
          this.bufferIndex = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
