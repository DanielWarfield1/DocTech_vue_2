<!-- AudioRecorder.vue -->
<template>
  <div>
    <button @click="toggleRecording">
      {{ isRecording ? "Stop Recording" : "Start Recording" }}
    </button>
    <canvas ref="canvas" width="300" height="300"></canvas>
    <audio ref="audio" :src="audioResponseUrl" type="audio/mpeg" controls></audio>
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
      audioResponseUrl: null,
      plan: null,
      microphoneStream: null,
      animationFrameId: null,
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
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.microphoneStream = stream;
      this.mediaRecorder = new MediaRecorder(stream);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) this.audioChunks.push(event.data);
      };

      this.mediaRecorder.onstop = this.onRecordingStop;
      this.mediaRecorder.start();

      this.setupVisualization();
    },
    stopRecording() {
      this.isRecording = false;
      this.mediaRecorder.stop();
      this.microphoneStream.getTracks().forEach((track) => track.stop());
      cancelAnimationFrame(this.animationFrameId);
    },
    async onRecordingStop() {
      const audioBlob = new Blob(this.audioChunks, { type: "audio/ogg; codecs=opus" });
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.ogg");

      try {
        const response = await fetch("http://localhost:5000/decide_and_respond", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();

        this.audioResponseUrl = data.audio_url;
        console.log("Audio Response URL:", this.audioResponseUrl);
        this.plan = data.plan;

        // Ensure the audio source is loaded, then play it
        this.$nextTick(() => {
          this.$refs.audio.load();  // Load the new audio source
          this.$refs.audio.play().catch(error => {
            console.error("Error playing audio:", error);
          });
        });

        // Execute the plan in parallel with the audio playback
        this.executePlan();
      } catch (error) {
        console.error("Error handling audio file:", error);
      }
    },
    executePlan() {
      if (this.plan) {
        fetch("http://localhost:5000/execute_plan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.plan),
        })
        .then(response => response.json())
        .then(data => {
          this.$emit("api-response", data);  // Emit the response for any parent components
        })
        .catch(error => console.error("Error executing plan:", error));
      }
    },
    setupVisualization() {
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext("2d");
      const draw = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        this.animationFrameId = requestAnimationFrame(draw);
      };
      draw();
    },
  },
  beforeUnmount() {
    cancelAnimationFrame(this.animationFrameId);
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
