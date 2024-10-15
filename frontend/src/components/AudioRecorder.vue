<template>
  <div>
    <button @click="toggleRecording">
      {{ isRecording ? "Stop Recording" : "Start Recording" }}
    </button>
    <canvas ref="canvas" width="300" height="300"></canvas>
    <audio ref="audio" :src="audioUrl" @play="onPlaybackStart" @ended="onPlaybackEnd"></audio>
  </div>
</template>

<script>
export default {
  name: "AudioRecorder",
  data() {
    return {
      isRecording: false,
      isPlayingBack: false,
      mediaRecorder: null,
      audioChunks: [],
      audioUrl: null,
      audioContext: null,
      analyser: null,
      microphoneStream: null,
      animationFrameId: null,
      silenceTimeout: null,
      silenceThreshold: 0.05,
      playbackSource: null,
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
      this.isPlayingBack = false;
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
    async onRecordingStop() {
      const audioBlob = new Blob(this.audioChunks, { type: "audio/ogg; codecs=opus" });
      this.audioUrl = URL.createObjectURL(audioBlob);

      // Send the audioBlob to the Flask server
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.ogg");

      try {
        const response = await fetch("http://localhost:5000/upload", {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          console.log("Audio file uploaded successfully");
        } else {
          console.error("Failed to upload audio file");
        }
      } catch (error) {
        console.error("Error uploading audio file:", error);
      }

      // Set up playback (optional)
      if (!this.playbackSource) {
        this.playbackSource = this.audioContext.createMediaElementSource(this.$refs.audio);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;

        this.playbackSource.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);
      }

      setTimeout(() => {
        this.$refs.audio.play().catch((error) => {
          console.error("Playback failed:", error);
        });
      }, 100);
    },
    startVisualizing() {
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext("2d");
      const bufferLength = this.analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const draw = () => {
        this.analyser.getByteFrequencyData(dataArray);

        let sumSquares = 0.0;
        for (let i = 0; i < bufferLength; i++) {
          sumSquares += (dataArray[i] / 255) ** 2;
        }
        const rms = Math.sqrt(sumSquares / bufferLength);
        const radius = this.isRecording || this.isPlayingBack ? rms * 150 : 10;
        const color = this.isRecording
          ? "white"
          : this.isPlayingBack
          ? "rgba(173, 216, 230, 0.8)"
          : "rgba(255, 255, 255, 0.2)";

        ctx.fillStyle = "black";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.beginPath();
        ctx.arc(canvas.width / 2, canvas.height / 2, radius, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.closePath();

        if (this.isRecording && rms < this.silenceThreshold) {
          if (!this.silenceTimeout) {
            this.silenceTimeout = setTimeout(() => {
              this.stopRecording();
            }, 1000);
          }
        } else {
          clearTimeout(this.silenceTimeout);
          this.silenceTimeout = null;
        }

        this.animationFrameId = requestAnimationFrame(draw);
      };

      draw();
    },
    onPlaybackStart() {
      this.isPlayingBack = true;
    },
    onPlaybackEnd() {
      this.isPlayingBack = false;
      cancelAnimationFrame(this.animationFrameId);
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
