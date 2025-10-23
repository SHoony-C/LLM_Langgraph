<template>
  <div class="langgraph-container" v-if="showLanggraph">
    <div class="langgraph-header">
      <h2>🔬 AI 분석 - 랭그래프</h2>
    </div>
    
    <!-- 1단계: 키워드 증강 -->
    <div class="langgraph-step" :class="{ active: currentStep >= 1 }">
      <div class="step-header">
        <div class="step-number">1</div>
        <h3>키워드 증강</h3>
        <div class="step-status" v-if="currentStep >= 1">
          <span class="status-icon">✓</span>
        </div>
      </div>
      <div class="step-content">
        <div class="input-section" :key="'input-' + (originalInput || 'empty')">
          <label class="section-label">입력된 내용:</label>
          <div class="original-input">
            <span v-if="originalInput">{{ originalInput }}</span>
            <span v-else class="placeholder-text">입력된 내용이 없습니다.</span>
          </div>
        </div>
        <div class="augmented-keywords" :key="'keywords-' + (augmentedKeywords.length || 0)">
          <label class="section-label">증강된 키워드:</label>
          <div class="keywords-list">
            <span 
              v-for="keyword in augmentedKeywords" 
              :key="keyword.id" 
              class="keyword-tag"
              :class="keyword.category"
            >
              {{ keyword.text }}
              <span class="keyword-category">{{ keyword.category }}</span>
            </span>
            <div v-if="!augmentedKeywords || augmentedKeywords.length === 0" class="no-keywords">
              <div class="loading-container">
                <div class="spinner"></div>
                <span>키워드를 증강 중입니다</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 2단계: DB 검색 -->
    <div class="langgraph-step" :class="{ active: currentStep >= 2 }">
      <div class="step-header">
        <div class="step-number">2</div>
        <h3>증강된 키워드로 DB 검색</h3>
        <div class="step-status" v-if="currentStep >= 2">
          <span class="status-icon">✓</span>
        </div>
      </div>
      <div class="step-content">
        <div class="search-status">
          <div v-if="currentStep >= 2 && isSearching" class="searching-indicator">
            <div class="spinner"></div>
            <span>데이터베이스 검색 중...</span>
          </div>
          <div v-else-if="currentStep >= 2 && ((typeof searchResults === 'number' && searchResults > 0) || (Array.isArray(searchResults) && searchResults.length > 0))" class="search-results">
            <label>검색 결과 ({{ typeof searchResults === 'number' ? searchResults : searchResults.length }}건):</label>
            <div class="results-list">
              <!-- 숫자인 경우 문서 제목만 표시 -->
              <template v-if="typeof searchResults === 'number' && searchedDocuments && searchedDocuments.length > 0">
                <div 
                  v-for="(docTitle, index) in searchedDocuments.slice(0, 5)" 
                  :key="index" 
                  class="result-item simple"
                >
                  <div class="result-header">
                    <span class="result-number">#{{ index + 1 }}</span>
                  </div>
                  <div class="result-content">
                    <div class="result-title">{{ docTitle }}</div>
                  </div>
                </div>
              </template>
              <!-- 배열인 경우 상세 정보 표시 -->
              <template v-else-if="Array.isArray(searchResults)">
                <div 
                  v-for="(result, index) in searchResults.slice(0, 5)" 
                  :key="index" 
                  class="result-item detailed clickable"
                  @click="$emit('openSearchResult', result)"
                >
                  <div class="result-header">
                    <span class="result-number">#{{ index + 1 }}</span>
                    <span class="result-score">유사도: {{ (result.res_score || result.score || 0).toFixed(4) }}</span>
                  </div>
                  <div class="result-content">
                    <div class="result-title">{{ result.res_payload?.document_name || result.title || '제목 없음' }}</div>
                    <div class="result-summary">{{ result.res_payload?.vector?.summary_result || result.summary || '요약 없음' }}</div>
                    <div class="result-text">{{ result.res_payload?.vector?.text || result.text || '내용 없음' }}</div>
                    <div v-if="result.res_payload?.vector?.image_url || result.image_url" class="result-image-indicator">
                      🖼️ 이미지 포함 (클릭하여 보기)
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
          <div v-else-if="currentStep >= 2 && hasSearchCompleted && !isSearching && (searchResults === 0 || (Array.isArray(searchResults) && searchResults.length === 0))" class="no-search-results">
            <div class="no-results-icon">🔍</div>
            <div class="no-results-message">
              <strong>검색 결과가 없습니다</strong>
              <p>데이터베이스에서 관련 정보를 찾을 수 없습니다.</p>
              <div class="improvement-suggestions">
                <strong>개선 제안:</strong>
                <ul>
                  <li>질문을 더 구체적으로 작성해주세요</li>
                  <li>관련 키워드를 추가해주세요</li>
                  <li>데이터베이스에 관련 문서가 있는지 확인해주세요</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 3단계: 답변 생성 -->
    <div class="langgraph-step" :class="{ active: currentStep >= 3 }">
      <div class="step-header">
        <div class="step-number">3</div>
        <h3>검색된 내용 기반 답변</h3>
        <div class="step-status" v-if="currentStep >= 3">
          <span class="status-icon">✓</span>
        </div>
      </div>
      <div class="step-content">
        <div class="answer-section">
          <div v-if="currentStep >= 3 && isGeneratingAnswer" class="generating-indicator">
            <div class="spinner"></div>
            <span>🤖 AI가 검색 결과를 분석하여 답변을 생성하고 있습니다...</span>
          </div>
          <div v-else-if="currentStep >= 3 && (finalAnswer || streamingAnswer)" class="final-answer">
            <label>최종 답변:</label>
            <div class="answer-content" v-html="formatAnswer(streamingAnswer || finalAnswer)"></div>
            <div v-if="isStreamingAnswer" class="streaming-indicator">
              <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span>답변 생성 중...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 4단계: 분석 결과 이미지 -->
    <div class="langgraph-step" :class="{ active: currentStep >= 4 }">
      <div class="step-header">
        <div class="step-number">4</div>
        <h3>분석 결과 이미지</h3>
        <div class="step-status" v-if="currentStep >= 4">
          <span class="status-icon">✓</span>
        </div>
      </div>
      <div class="step-content">
        <div class="image-section">
          <div v-if="currentStep >= 4 && analysisImageUrl" class="analysis-image">
            <label>분석 결과:</label>
            <div class="image-container">
              <!-- 이미지 오류 상태일 때만 오류 메시지 표시 -->
              <div v-if="imageLoadFailed" class="image-error-display">
                <div class="error-icon">⚠️</div>
                <div class="error-message">
                  <strong>이미지를 불러올 수 없습니다</strong>
                  <p>네트워크 연결을 확인하거나 서버 상태를 점검해주세요.</p>
                  <div class="error-url">
                    <label>이미지 URL:</label>
                    <code class="url-text">{{ failedImageUrl }}</code>
                  </div>
                </div>
              </div>
              <!-- 이미지가 정상이면 표시 (GET 요청 없음) -->
              <div v-else class="image-wrapper">
                <div class="image-placeholder">
                  <div class="placeholder-icon">🖼️</div>
                  <div class="placeholder-text">
                    <strong>분석 이미지 생성됨</strong>
                    <p>이미지 URL: {{ analysisImageUrl }}</p>
                    <button @click="$emit('openImageInNewTab', analysisImageUrl)" class="view-image-btn">
                      새 탭에서 이미지 보기
                    </button>
                  </div>
                </div>
              </div>
              <div class="image-caption">
                <strong>랭그래프 4단계 분석 결과</strong><br>
                • RAG 검색 기반 분석 이미지<br>
                • 클릭하면 새 탭에서 확대 보기
              </div>
            </div>
          </div>
          <div v-else-if="currentStep >= 4 && !analysisImageUrl" class="no-image-results">
            <div class="no-image-icon">🖼️</div>
            <div class="no-image-message">
              <strong>이미지 URL이 설정되지 않았습니다</strong>
              <p>RAG 검색 결과를 기반으로 한 이미지 URL이 생성되지 않았습니다.</p>
              <div class="image-info">
                <strong>디버깅 정보:</strong>
                <ul>
                  <li>현재 단계: {{ currentStep }}</li>
                  <li>최종 답변: {{ finalAnswer ? '있음' : '없음' }}</li>
                </ul>
                <div v-if="lastImageUrl" class="image-url-debug">
                  <strong>마지막 시도된 이미지 URL:</strong>
                  <code class="url-text">{{ lastImageUrl }}</code>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 진행 상태 표시 -->
    <div class="langgraph-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
      </div>
      <div class="progress-text">{{ currentStep }}/4 단계 완료</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LanggraphContainer',
  props: {
    showLanggraph: {
      type: Boolean,
      default: false
    },
    currentStep: {
      type: Number,
      default: 0
    },
    originalInput: {
      type: String,
      default: ''
    },
    augmentedKeywords: {
      type: Array,
      default: () => []
    },
    isSearching: {
      type: Boolean,
      default: false
    },
    searchResults: {
      type: [Array, Number],
      default: () => []
    },
    searchedDocuments: {
      type: Array,
      default: () => []
    },
    hasSearchCompleted: {
      type: Boolean,
      default: false
    },
    isGeneratingAnswer: {
      type: Boolean,
      default: false
    },
    finalAnswer: {
      type: String,
      default: ''
    },
    streamingAnswer: {
      type: String,
      default: ''
    },
    isStreamingAnswer: {
      type: Boolean,
      default: false
    },
    analysisImageUrl: {
      type: String,
      default: ''
    },
    imageLoadFailed: {
      type: Boolean,
      default: false
    },
    failedImageUrl: {
      type: String,
      default: ''
    },
    lastImageUrl: {
      type: String,
      default: ''
    }
  },
  emits: ['openSearchResult', 'openImageInNewTab'],
  computed: {
    progressPercentage() {
      return (this.currentStep / 4) * 100;
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
    }
  }
};
</script>

<style scoped>
@import '../assets/styles/home.css';
</style>
