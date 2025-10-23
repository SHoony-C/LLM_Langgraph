<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <textarea
        v-model="userInput" 
        class="chat-input" 
        placeholder="질문을 입력하세요..." 
        @keydown.enter.prevent="handleEnterKey"
        :disabled="isLoading || isStreaming"
        ref="inputField"
        rows="1"
        @input="handleInputChange"
      ></textarea>
      <button 
        class="send-btn" 
        :disabled="!userInput.trim() || isLoading || isStreaming" 
        @click="$emit('sendMessage')"
      >
        <span v-if="!isLoading">
          <svg class="send-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 2L11 13"></path>
            <path d="M22 2l-7 20-4-9-9-4 20-7z"></path>
          </svg>
        </span>
        <span v-else class="loading-spinner"></span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatInput',
  props: {
    isLoading: {
      type: Boolean,
      default: false
    },
    isStreaming: {
      type: Boolean,
      default: false
    }
  },
  emits: ['sendMessage', 'inputChange'],
  data() {
    return {
      userInput: ''
    };
  },
  methods: {
    handleEnterKey(event) {
      if (event.shiftKey && event.key === 'Enter') {
        return; // Shift+Enter는 줄바꿈으로 처리
      }
      this.$emit('sendMessage');
    },
    handleInputChange() {
      this.$emit('inputChange', this.userInput);
      this.adjustTextareaHeight();
    },
    adjustTextareaHeight() {
      const textarea = this.$refs.inputField;
      if (!textarea) return;
      
      try {
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 150);
        textarea.style.height = newHeight + 'px';
      } catch (error) {
        console.warn('Textarea height adjustment failed:', error);
      }
    },
    clearInput() {
      this.userInput = '';
      this.adjustTextareaHeight();
    },
    focusInput() {
      if (this.$refs.inputField && this.$refs.inputField.focus) {
        try {
          this.$refs.inputField.focus();
        } catch (error) {
          console.warn('Focus failed:', error);
        }
      }
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.adjustTextareaHeight();
    });
  }
};
</script>

<style scoped>
@import '../assets/styles/home.css';
</style>
