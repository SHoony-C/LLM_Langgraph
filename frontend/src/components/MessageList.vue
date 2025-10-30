<template>
  <div class="messages-container" style="transform: translateZ(0)">
    <div class="messages-wrapper">
      <!-- 빈 상태 표시 (메시지가 없을 때) -->
      <div v-if="!currentMessages || currentMessages.length === 0" class="empty-state">
        <div class="empty-illustration">
          <svg class="empty-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="3" x2="9" y2="21"></line>
            <line x1="15" y1="3" x2="15" y2="21"></line>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="3" y1="15" x2="21" y2="15"></line>
          </svg>
        </div>
        <p>Start a new conversation</p>
      </div>
      
      <!-- 메시지들 -->
      <div 
        v-for="message in currentMessages" 
        :key="`msg-${message.id}-${message.role}-${message.feedback || 'none'}`" 
        class="message-group"
      >
        <!-- 질문 영역 -->
        <div v-if="message.role === 'user'" class="message user">
          <div class="message-content">
            <div class="message-text">{{ message.question || '' }}</div>
          </div>
        </div>
        
        <!-- 답변 영역 (질문 아래) - ans 필드가 있는 경우에만 표시 -->
        <div v-if="message.role === 'user' && message.ans" class="message assistant">
          <div class="message-content">
            <div class="message-text" v-html="formatAnswer(message.ans)"></div>
          </div>
          <!-- 답변 영역에만 피드백 버튼 표시 -->
          <div class="message-actions">
          <button 
            :key="`thumbs-up-${message.id}-${feedbackUpdateTrigger}`"
            class="action-btn thumbs-up" 
            :class="{ 
              active: messageFeedbackStates[message.id] === 'positive',
              disabled: isStreaming || isMessageStreaming(message.id)
            }"
            @click="!isStreaming && !isMessageStreaming(message.id) && $emit('submitFeedback', message.id, 'positive')"
            :disabled="isStreaming || isMessageStreaming(message.id)"
            :title="getFeedbackButtonTitle(message.id, 'positive')"
          >
            <svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
            </svg>
          </button>
          <button 
            :key="`thumbs-down-${message.id}-${feedbackUpdateTrigger}`"
            class="action-btn thumbs-down" 
            :class="{ 
              active: messageFeedbackStates[message.id] === 'negative',
              disabled: isStreaming || isMessageStreaming(message.id)
            }"
            @click="!isStreaming && !isMessageStreaming(message.id) && $emit('submitFeedback', message.id, 'negative')"
            :disabled="isStreaming || isMessageStreaming(message.id)"
            :title="getFeedbackButtonTitle(message.id, 'negative')"
          >
            <svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
            </svg>
          </button>
          </div>
        </div>
      </div>
      
      <!-- 스트리밍 중인 메시지 표시 (답변 영역) -->
      <div 
        v-if="isStreaming && streamingVisible "
        key="streaming-message"
        class="message assistant streaming"
        :style="{
          minHeight: lastMessageHeight + 'px',
          opacity: 1
        }"
      >
        <div class="message-content" ref="streamingContent">
          <div class="message-text" ref="streamingText">
            {{ streamingMessage }}<span class="cursor">|</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MessageList',
  props: {
    currentMessages: {
      type: Array,
      default: () => []
    },
    isStreaming: {
      type: Boolean,
      default: false
    },
    streamingMessage: {
      type: String,
      default: ''
    },
    streamingVisible: {
      type: Boolean,
      default: false
    },
    lastMessageHeight: {
      type: Number,
      default: 0
    },
  },
  emits: ['submitFeedback'],
  computed: {
    // 피드백 업데이트 트리거를 감지하여 강제 리렌더링
    feedbackUpdateTrigger() {
      return this.$store.state.feedbackUpdateTrigger || 0;
    },
    // 각 메시지의 피드백 상태를 computed로 관리
    messageFeedbackStates() {
      const states = {};
      this.currentMessages.forEach(message => {
        states[message.id] = message.feedback;
      });
      return states;
    }
  },
  watch: {
    isStreaming(newValue) {
      console.log('🔄 스트리밍 상태 변경:', newValue);
    },
    streamingVisible(newValue) {
      console.log('🔄 스트리밍 영역 표시 상태 변경:', newValue);
    },
    // 피드백 상태 변경을 감지하여 강제 업데이트
    feedbackUpdateTrigger() {
      console.log('🔄 피드백 트리거 변경 감지:', this.feedbackUpdateTrigger);
      // 강제 리렌더링을 위해 $forceUpdate 호출
      this.$forceUpdate();
    },
    // 메시지 배열 변경 감지
    messages: {
      handler() {
        console.log('🔄 메시지 배열 변경 감지');
        // 메시지가 변경되면 강제 업데이트
        this.$forceUpdate();
      },
      deep: true
    },
    // currentConversation 변경 감지
    '$store.state.currentConversation': {
      handler() {
        console.log('🔄 currentConversation 변경 감지');
        this.$forceUpdate();
      },
      deep: true
    }
  },
  methods: {
    formatAnswer(text) {
      if (!text) return '';
      
      let formattedText = text;
      
      // 1. 헤더 처리 (### 큰 헤더)
      formattedText = formattedText.replace(/^### (.*$)/gm, '<h3 class="markdown-h3">$1</h3>');
      formattedText = formattedText.replace(/^## (.*$)/gm, '<h2 class="markdown-h2">$1</h2>');
      formattedText = formattedText.replace(/^# (.*$)/gm, '<h1 class="markdown-h1">$1</h1>');
      
      // 2. **텍스트** 형태를 <strong>텍스트</strong>로 변환 (중간 헤더)
      formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong class="markdown-bold">$1</strong>');
      
      // 3. 표(테이블) 처리
      const tableRegex = /(\|[^\n]+\|\n)+/g;
      formattedText = formattedText.replace(tableRegex, (match) => {
        const lines = match.trim().split('\n');
        let tableHtml = '<table class="markdown-table">';
        
        lines.forEach((line, index) => {
          if (line.trim() && !line.match(/^\|[-\s|]+\|$/)) {
            const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell);
            if (cells.length > 0) {
              tableHtml += '<tr>';
              cells.forEach(cell => {
                if (index === 0) {
                  tableHtml += `<th class="markdown-th">${cell}</th>`;
                } else {
                  tableHtml += `<td class="markdown-td">${cell}</td>`;
                }
              });
              tableHtml += '</tr>';
            }
          }
        });
        
        tableHtml += '</table>';
        return tableHtml;
      });
      
      // 4. 리스트 처리
      formattedText = formattedText.replace(/^- (.*$)/gm, '<li class="markdown-li">$1</li>');
      formattedText = formattedText.replace(/(<li class="markdown-li">.*<\/li>)/s, '<ul class="markdown-ul">$1</ul>');
      
      // 5. 번호 리스트 처리
      formattedText = formattedText.replace(/^\d+\. (.*$)/gm, '<li class="markdown-oli">$1</li>');
      formattedText = formattedText.replace(/(<li class="markdown-oli">.*<\/li>)/s, '<ol class="markdown-ol">$1</ol>');
      
      // 6. 코드 블록 처리
      formattedText = formattedText.replace(/```([\s\S]*?)```/g, '<pre class="markdown-code"><code>$1</code></pre>');
      formattedText = formattedText.replace(/`([^`]+)`/g, '<code class="markdown-inline-code">$1</code>');
      
      // 7. 줄바꿈 처리
      formattedText = formattedText.replace(/\n\n/g, '</p><p class="markdown-p">');
      formattedText = formattedText.replace(/\n/g, '<br>');
      
      // 8. 단락 태그로 감싸기
      if (!formattedText.includes('<p class="markdown-p">')) {
        formattedText = `<p class="markdown-p">${formattedText}</p>`;
      } else {
        formattedText = `<p class="markdown-p">${formattedText}</p>`;
      }
      
      return formattedText;
    },
    getMessageFeedback(messageId) {
      const message = this.currentMessages.find(m => m.id === messageId);
      const feedback = message ? message.feedback : null;
      console.log('🔍 getMessageFeedback:', { 
        messageId, 
        feedback, 
        messageExists: !!message,
        trigger: this.feedbackUpdateTrigger 
      });
      return feedback;
    },
    isMessageStreaming(messageId) {
      // 메시지가 스트리밍 중인지 확인
      const message = this.currentMessages.find(m => m.id === messageId);
      if (!message) return false;
      
      // 중요: 질문과 답변이 하나의 row에 저장되는 구조
      // user 메시지의 ans 필드가 비어있고 현재 스트리밍 중일 때 스트리밍 중으로 간주
      const isIncomplete = !message.ans || message.ans.trim() === '';
      return isIncomplete && this.isStreaming && this.streamingVisible;
    },
    getFeedbackButtonTitle(messageId, feedbackType) {
      const currentFeedback = this.messageFeedbackStates[messageId];
      const isStreaming = this.isStreaming || this.isMessageStreaming(messageId);
      
      if (isStreaming) {
        return '답변이 완성되면 피드백을 남길 수 있습니다';
      }
      
      const toggleTo = currentFeedback === feedbackType ? 'none' : feedbackType;
      return `Message ID: ${messageId}, Current: ${currentFeedback || 'none'}, Toggle to: ${toggleTo}`;
    }
  }
};
</script>

<style scoped>
@import '../assets/styles/home.css';

/* 비활성화된 피드백 버튼 스타일 */
.action-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

.action-btn.disabled:hover {
  background-color: transparent;
  transform: none;
}
</style>
