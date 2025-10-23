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
        :key="`msg-${message.id}-${message.role}-${message.feedback}-${feedbackUpdateTrigger}`" 
        :class="['message', message.role]"
      >
        <div class="message-content">
          <div class="message-text" v-if="message.role === 'user'">
            {{ message.question || '' }}
          </div>
          <div class="message-text" v-else>
            <div v-html="formatAnswer(message.ans || '')"></div>
          </div>
        </div>
        
        <div v-if="message.role === 'assistant'" class="message-actions">
          <button 
            class="action-btn thumbs-up" 
            :class="{ active: getMessageFeedback(message.id) === 'positive' }"
            @click="$emit('submitFeedback', message.id, 'positive')"
            :title="`Message ID: ${message.id}, Current: ${getMessageFeedback(message.id) || 'none'}, Toggle to: ${getMessageFeedback(message.id) === 'positive' ? 'none' : 'positive'}`"
          >
            <svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
            </svg>
          </button>
          <button 
            class="action-btn thumbs-down" 
            :class="{ active: getMessageFeedback(message.id) === 'negative' }"
            @click="$emit('submitFeedback', message.id, 'negative')"
            :title="`Message ID: ${message.id}, Current: ${getMessageFeedback(message.id) || 'none'}, Toggle to: ${getMessageFeedback(message.id) === 'negative' ? 'none' : 'negative'}`"
          >
            <svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
            </svg>
          </button>
        </div>
      </div>
      
      <!-- 스트리밍 중인 메시지 표시 -->
      <div 
        v-if="isStreaming"
        key="streaming-message"
        class="message assistant streaming"
        :style="{
          minHeight: lastMessageHeight + 'px',
          opacity: streamingVisible ? 1 : 0
        }"
      >
        <div class="message-content" ref="streamingContent">
          <div class="message-text" ref="streamingText">{{ streamingMessage }}<span class="cursor">|</span></div>
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
    feedbackUpdateTrigger: {
      type: Number,
      default: 0
    }
  },
  emits: ['submitFeedback'],
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
      return message ? message.feedback : null;
    }
  }
};
</script>

<style scoped>
@import '../assets/styles/home.css';
</style>
