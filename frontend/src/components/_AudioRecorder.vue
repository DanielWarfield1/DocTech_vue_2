<template>
  <div>
    <button @click="toggleRecording">
      {{ isRecording ? "Stop Recording" : "Start Recording" }}
    </button>
    <canvas ref="canvas" width="300" height="300"></canvas>
    <audio ref="audio" controls v-if="audioUrl" :src="audioUrl"></audio>
  </div>
</template>

<script>
export default {
  name: "AudioRecorder",
  data() {
    return {
      isRecording: false,
      mediaRecorder: null,
      audioChunks: [],
      audioUrl: null,
      audioContext: null,
      analyser: null,
      microphoneStream: null,
      animationFrameId: null,
      silenceTimeout: null,
      silenceThreshold: 0.1, // Threshold for detecting silence
    };
  },
  methods: {
    async toggleRecording() {
      if (this.isRecording) {
        this.stopRecording();
      } else {
        await this.startRecording();
      }
    },
    async startRecording() {
      this.isRecording = true;
      this.audioChunks = [];
      this.audioUrl = null;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.microphoneStream = stream;

      this.mediaRecorder = new MediaRecorder(stream);
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) this.audioChunks.push(event.data);
      };
      this.mediaRecorder.onstop = this.onRecordingStop;
      this.mediaRecorder.start();

      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = this.audioContext.createMediaStreamSource(stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);

      this.startVisualizing();
    },
    stopRecording() {
      this.isRecording = false;
      this.mediaRecorder.stop();
      this.microphoneStream.getTracks().forEach((track) => track.stop());
      cancelAnimationFrame(this.animationFrameId);
    },
    onRecordingStop() {
      const audioBlob = new Blob(this.audioChunks, { type: "audio/ogg; codecs=opus" });
      this.audioUrl = URL.createObjectURL(audioBlob);
    },
    startVisualizing() {
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext("2d");
      const bufferLength = this.analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const draw = () => {
        this.analyser.getByteFrequencyData(dataArray);

        // Calculate RMS volume level
        let sumSquares = 0.0;
        for (let i = 0; i < bufferLength; i++) {
          sumSquares += (dataArray[i] / 255) ** 2;
        }
        const rms = Math.sqrt(sumSquares / bufferLength);
        const radius = rms * 150; // Scale radius by RMS level

        // Clear canvas and draw the circle
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.beginPath();
        ctx.arc(canvas.width / 2, canvas.height / 2, radius, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(0, 150, 255, 0.5)";
        ctx.fill();
        ctx.closePath();

        // Check for silence (low RMS)
        if (rms < this.silenceThreshold && this.isRecording) {
          if (!this.silenceTimeout) {
            this.silenceTimeout = setTimeout(() => {
              this.stopRecording();
            }, 1000); // Stops recording if low volume for 1 second
          }
        } else {
          clearTimeout(this.silenceTimeout);
          this.silenceTimeout = null;
        }

        this.animationFrameId = requestAnimationFrame(draw);
      };

      draw();
    },
  },
  beforeUnmount() {
    cancelAnimationFrame(this.animationFrameId);
    if (this.silenceTimeout) clearTimeout(this.silenceTimeout);
    if (this.audioContext) this.audioContext.close();
    if (this.microphoneStream) {
      this.microphoneStream.getTracks().forEach((track) => track.stop());
    }
  },
};
</script>

<style scoped>
canvas {
  border: 1px solid #ddd;
}
</style>
