<!-- App.vue -->
<template>
  <div>
    <AudioRecorder @api-response="handleApiResponse" />
    <PdfViewer :apiResponse="apiResponse" />
  </div>
</template>

<script>
import PdfViewer from './components/PdfViewer.vue';
import AudioRecorder from './components/AudioRecorder.vue';

export default {
  components: {
    PdfViewer,
    AudioRecorder,
  },
  data() {
    return {
      apiResponse: {},
    };
  },
  methods: {
    handleApiResponse(response) {
      this.apiResponse = response;
    },
  },
};
</script>
