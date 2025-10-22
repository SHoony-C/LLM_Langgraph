<template>
  <div class="home">
        <div class="chat-container">
            <!-- 채팅 메시지 영역 -->
      <div class="chat-messages" ref="chatMessages">
        <!-- 랭그래프 구조 추가 -->
        <div class="rangraph-container" v-if="showRangraph">
          <div class="rangraph-header">
            <h2>🔬 AI 분석 - 랭그래프</h2>
          </div>
          
          <!-- 1단계: 키워드 증강 -->
          <div class="rangraph-step" :class="{ active: currentStep >= 1 }">
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
          <div class="rangraph-step" :class="{ active: currentStep >= 2 }">
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
                        @click="openSearchResultPopup(result)"
                      >
                        <div class="result-header">
                          <span class="result-number">#{{ index + 1 }}</span>
                          <span class="result-score">유사도: {{ result.score?.toFixed(4) || '0.0000' }}</span>
                        </div>
                        <div class="result-content">
                          <div class="result-title">{{ result.title || '제목 없음' }}</div>
                          <div class="result-summary">{{ result.summary || '요약 없음' }}</div>
                          <div class="result-text">{{ result.text || '내용 없음' }}</div>
                          <div v-if="result.image_url" class="result-image-indicator">
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
          <div class="rangraph-step" :class="{ active: currentStep >= 3 }">
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
          <div class="rangraph-step" :class="{ active: currentStep >= 4 }">
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
                    <img 
                      :src="analysisImageUrl" 
                      alt="랭그래프 4단계 분석 결과" 
                      class="analysis-result-image clickable-image" 
                      @error="handleImageError"
                      @click="openImageInNewTab(analysisImageUrl)"
                      title="클릭하면 새 탭에서 이미지를 볼 수 있습니다"
                    />
                    <div class="image-caption">
                      <strong>랭그래프 4단계 분석 결과</strong><br>
                      • RAG 검색 기반 분석 이미지<br>
                      • 클릭하면 새 탭에서 확대 보기
                    </div>
                    <!-- URL 표시 (검증용) -->
                    <div class="image-url-display">
                      <label>이미지 URL (검증용):</label>
                      <code class="url-text">{{ analysisImageUrl }}</code>
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
        <div class="rangraph-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
          </div>
          <div class="progress-text">{{ currentStep }}/4 단계 완료</div>
        </div>
        

        
        <!-- 랭그래프 히스토리 (추가 질문 모드용) -->
        <div v-if="rangraphHistory.length > 0" class="rangraph-history">
          <div class="history-header">
            <h3>📚 이전 분석 결과</h3>
            <p>추가 질문 모드에서 이전 분석 결과를 참고할 수 있습니다.</p>
          </div>
          <div class="history-items">
            <div 
              v-for="(history, index) in rangraphHistory" 
              :key="history.id"
              class="history-item"
            >
              <div class="history-header-item">
                <div class="history-number">#{{ index + 1 }}</div>
                <div class="history-info">
                  <div class="history-question">{{ history.originalInput }}</div>
                  <div class="history-timestamp">{{ new Date(history.timestamp).toLocaleString() }}</div>
                </div>
                <button 
                  class="history-delete-btn"
                  @click="deleteHistoryItem(history.id)"
                  title="이 항목 삭제"
                >
                  🗑️
                </button>
              </div>
              <div class="history-summary">
                <div class="summary-item">
                  <strong>키워드:</strong> {{ history.augmentedKeywords.length }}개
                </div>
                <div class="summary-item">
                  <strong>검색 결과:</strong> {{ history.searchResults.length }}건
                </div>
                <div class="summary-item">
                  <strong>답변:</strong> {{ history.finalAnswer ? '생성됨' : '없음' }}
                </div>
              </div>
            </div>
          </div>
        </div>
        </div>
        
                <!-- 기존 채팅 메시지들 -->
        <div v-if="!$store.state.currentConversation || !$store.state.currentConversation.messages || $store.state.currentConversation.messages.length === 0" class="empty-state">
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
        
        <div 
          :key="'conversation-' + ($store.state.currentConversation?.id || 'empty')" 
          class="messages-container"
          style="transform: translateZ(0)"
        >
          <div class="messages-wrapper">
            <div 
              v-for="message in currentMessages" 
              :key="`msg-${message.id}-${message.role}-${message.feedback}-${$store.state._feedbackUpdateTrigger}`" 
              :class="['message', message.role]"
            >
              <div class="message-content">
                <div class="message-text" v-if="message.role === 'user'">
                  {{ message.question || '' }}
                </div>
                <div class="message-text" v-else v-html="formatAnswer(message.ans || '')">
                </div>
              </div>
              
              <div v-if="message.role === 'assistant'" class="message-actions">
                <button 
                  class="action-btn thumbs-up" 
                  :class="{ active: getMessageFeedback(message.id) === 'positive' }"
                  @click="submitFeedback(message.id, 'positive')"
                  :title="`Message ID: ${message.id}, Current: ${getMessageFeedback(message.id) || 'none'}, Toggle to: ${getMessageFeedback(message.id) === 'positive' ? 'none' : 'positive'}`"
                >
                  <svg class="action-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                  </svg>
                </button>
                <button 
                  class="action-btn thumbs-down" 
                  :class="{ active: getMessageFeedback(message.id) === 'negative' }"
                  @click="submitFeedback(message.id, 'negative')"
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
              v-if="$store.state.isStreaming"
              key="streaming-message"
              class="message assistant streaming"
              :style="{
                minHeight: lastMessageHeight + 'px',
                opacity: streamingVisible ? 1 : 0
              }"
            >
              <div class="message-content" ref="streamingContent">
                <div class="message-text" ref="streamingText">{{ $store.state.streamingMessage }}<span class="cursor">|</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="chat-input-container">
        <div class="input-wrapper">
          <textarea
            v-model="userInput" 
            class="chat-input" 
            placeholder="질문을 입력하세요..." 
            @keydown.enter.prevent="sendChatMessage"
            :disabled="isLoading || $store.state.isStreaming"
            ref="inputField"
            rows="1"
          ></textarea>
          <button 
            class="send-btn" 
            :disabled="!userInput.trim() || isLoading || $store.state.isStreaming" 
            @click="sendChatMessage"
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
    </div>

    <!-- 검색 결과 상세 팝업 -->
    <SearchResultPopup 
      :show="showSearchResultPopup"
      :result="selectedSearchResult"
      @close="closeSearchResultPopup"
    />
  </div>
</template>

<script>
import { mapState } from 'vuex';
import SearchResultPopup from '@/components/SearchResultPopup.vue';

export default {
  name: 'HomePage',
  components: {
    SearchResultPopup
  },
  data() {
    return {
      userInput: '',
      isLoading: false,
      scrollThrottled: false,
      scrollTimeout: null, // 스크롤 디바운스용
      lastMessageHeight: 0, // 마지막 메시지 높이 저장
      lastScrollPosition: 0, // 마지막 스크롤 위치 저장
      observer: null, // 메시지 크기 변화 감지를 위한 observer
      streamingVisible: false, // 스트리밍 메시지 표시 여부
      showRangraph: false, // 랭그래프 표시 여부
      currentStep: 0, // 랭그래프 진행 단계
      originalInput: '', // 입력된 텍스트
      augmentedKeywords: [], // 증강된 키워드
      isSearching: false, // 데이터베이스 검색 중 여부
      searchResults: [], // 검색 결과
      searchedDocuments: [], // 검색된 문서 제목들
      hasSearchCompleted: false, // 검색이 완료되었는지 여부
      isGeneratingAnswer: false, // 답변 생성 중 여부
      showSearchResultPopup: false, // 검색 결과 팝업 표시 여부
      selectedSearchResult: null, // 선택된 검색 결과
      isDoneProcessed: false, // DONE 메시지 처리 완료 여부
      finalAnswer: '', // 최종 답변
      streamingAnswer: '', // 실시간 스트리밍 답변
      isStreamingAnswer: false, // 답변 스트리밍 중 여부
      analysisImageUrl: '', // 랭그래프 4단계 분석 결과 이미지 URL
      lastImageUrl: '', // 마지막으로 시도된 이미지 URL (디버깅용)
      langGraphError: null, // LangGraph API 오류 정보
              extractedKeywords: null, // 추출된 키워드 정보
      extractedDbSearchTitle: null, // 추출된 문서 검색 타이틀
      rangraphHistory: [], // 랭그래프 히스토리 (추가 질문 모드용)
      isFirstQuestionInSession: true, // 현재 세션에서 첫 번째 질문 여부
      
      // 성능 최적화를 위한 캐시 변수들
      cachedMessages: null,
      cachedConversationId: null,
      cachedMessagesLength: 0,
      lastRestoredConversationId: null,
      lastRestoredMessageCount: 0,
      scrollPending: false,
      
      // 실시간 기능 보존을 위한 상태 변수들
      isNewConversation: true, // 새 대화 여부 (실시간 기능 활성화용)
      isRestoringConversation: false // 대화 복원 중 여부
      
    };
  },
  computed: {
    ...mapState([
      'conversations',
      'currentConversation',
      'isStreaming',
      'streamingMessage'
    ]),
    // 메시지 배열의 반응성을 보장하기 위한 computed 속성 (메모이제이션 최적화)
    currentMessages() {
      const currentConversation = this.$store.state.currentConversation;
      
      if (!currentConversation || !currentConversation.messages) {
        return [];
      }
      
      // 메시지 배열 참조가 변경되지 않았다면 기존 배열 반환 (성능 최적화)
      if (this.cachedMessages && 
          this.cachedConversationId === currentConversation.id &&
          this.cachedMessagesLength === currentConversation.messages.length) {
        return this.cachedMessages;
      }
      
      // 캐시 업데이트는 watch에서 처리하도록 변경
      return currentConversation.messages;
    },
    // 개별 메시지의 피드백 상태를 확인하는 메소드
    getMessageFeedback() {
      return (messageId) => {
        const message = this.currentMessages.find(m => m.id === messageId);
        const feedback = message ? message.feedback : null;
        return feedback;
      };
    },
    // 랭그래프 진행률 계산
    progressPercentage() {
      return (this.currentStep / 4) * 100;
    }

  },
  methods: {
    getFullImageUrl(url) {
      if (!url) return '';

      // "/appdata/RC/images/" → "https://10.172.107.182/imageview/"
      return url.replace(/^\/appdata\/RC\/images\//, 'https://10.172.107.182/imageview/');
    },

    // 검색 결과 팝업 열기
    openSearchResultPopup(result) {
      this.selectedSearchResult = result;
      this.showSearchResultPopup = true;
      // console.log('🔍 검색 결과 팝업 열기:', result.title);
    },

    // 검색 결과 팝업 닫기
    closeSearchResultPopup() {
      this.showSearchResultPopup = false;
      this.selectedSearchResult = null;
    },

    // conversation에서 랭그래프 정보 복원 (성능 최적화 + 실시간 기능 보존)
    async restoreRangraphFromConversation(conversation) {
      // 대화 복원 상태 설정
      this.isRestoringConversation = true;
      this.isNewConversation = false; // 기존 대화 복원
      
      // 캐시 확인 - 동일한 대화에 대해 이미 복원했다면 스킵 (성능 최적화)
      if (this.lastRestoredConversationId === conversation?.id && 
          this.lastRestoredMessageCount === conversation?.messages?.length) {
        // console.log('동일한 대화에 대해 이미 복원됨 - 스킵');
        this.isRestoringConversation = false;
        return;
      }
      
      // console.log('restoreRangraphFromConversation 호출됨:', {
        conversation: conversation,
        hasMessages: !!conversation?.messages,
        messageCount: conversation?.messages?.length || 0
      });
      
      if (!conversation || !conversation.messages) {
        // console.log('대화 또는 메시지가 없어 랭그래프 복원 불가');
        // 새 대화이므로 첫 번째 질문 상태로 초기화
        this.isFirstQuestionInSession = true;
        this.lastRestoredConversationId = null;
        this.lastRestoredMessageCount = 0;
        return;
      }
      
      // 비동기 처리로 UI 블로킹 방지
      await this.$nextTick();
      
      // console.log('랭그래프 복원 시작:', {
        conversationId: conversation.id,
        messageCount: conversation.messages.length
      });
      
      // 성능 최적화: search 메시지만 먼저 필터링 (가장 빠른 조건)
      const searchMessages = conversation.messages.filter(msg => msg.q_mode === 'search');
      
      // search 메시지가 없으면 첫 번째 사용자 메시지에서 LangGraph 정보 찾기 (최적화)
      let firstQuestionMessage = null;
      if (searchMessages.length === 0) {
        // 사용자 메시지만 필터링하여 검색 범위 축소
        const userMessages = conversation.messages.filter(msg => msg.role === 'user');
        
        for (const msg of userMessages) {
          // 간단한 조건부터 먼저 확인 (성능 최적화)
          if (msg.keyword || msg.db_search_title) {
            // JSON 파싱은 필요한 경우에만 수행
            if (msg.keyword && msg.keyword.startsWith('{')) {
              try {
                const keywordData = JSON.parse(msg.keyword);
                if (keywordData && typeof keywordData === 'object' && keywordData.originalInput) {
                  firstQuestionMessage = msg;
                  // console.log('JSON 형태의 LangGraph 상태가 있는 메시지 발견');
                  break;
                }
              } catch (e) {
                // JSON 파싱 실패 시 일반 키워드로 간주
              }
            }
            
            firstQuestionMessage = msg;
            // console.log('일반 LangGraph 정보가 있는 메시지 발견');
            break;
          }
        }
      }
      
      // LangGraph 복원할 메시지 결정
      const messageToRestore = searchMessages.length > 0 ? searchMessages[0] : firstQuestionMessage;
      
      if (messageToRestore) {
        // LangGraph 정보가 있는 메시지로 복원
        const firstSearchMessage = messageToRestore;
        
        // console.log('첫 번째 검색 메시지 복원:', firstSearchMessage.id);
        
        // 이미 첫 번째 질문이 완료된 대화이므로 상태 변경
        this.isFirstQuestionInSession = false;
        
        // 현재 표시된 LangGraph가 같은 대화의 것인지 확인
        if (this.showRangraph && this.currentStep >= 4 && this.originalInput === firstSearchMessage.question) {
          // console.log('동일한 대화의 LangGraph가 이미 표시 중이므로 복원 생략');
          // 캐시 정보 업데이트
          this.lastRestoredConversationId = conversation.id;
          this.lastRestoredMessageCount = conversation.messages.length;
          this.isRestoringConversation = false;
          return;
        }
        
        // 랭그래프 상태 설정 (대화 복원 시에는 즉시 완료 상태)
        this.showRangraph = true;
        this.currentStep = 4; // 완료된 상태로 복원 (실시간 애니메이션 없음)
        this.originalInput = firstSearchMessage.question;
        this.finalAnswer = firstSearchMessage.ans;
        this.extractedKeywords = firstSearchMessage.keyword;
        this.extractedDbSearchTitle = firstSearchMessage.db_search_title;
        
        // LangGraph 전체 상태 복원 (비동기 처리)
        if (firstSearchMessage.keyword) {
          try {
            // keyword 필드에 저장된 LangGraph 상태 파싱
            const langGraphState = JSON.parse(firstSearchMessage.keyword);
            
            // LangGraph 상태가 올바른 형태인지 확인
            if (langGraphState && typeof langGraphState === 'object' && langGraphState.originalInput) {
              // console.log('완전한 LangGraph 상태 복원 시작:', langGraphState);
              
              // 모든 LangGraph 상태 복원
              this.originalInput = langGraphState.originalInput;
              this.augmentedKeywords = langGraphState.augmentedKeywords || [];
              this.searchResults = langGraphState.searchResults || [];
              this.finalAnswer = langGraphState.finalAnswer || firstSearchMessage.ans;
              this.analysisImageUrl = langGraphState.analysisImageUrl || firstSearchMessage.image || ''; // 이미지 URL 복원 (메시지에서도 가져오기)
              this.extractedKeywords = langGraphState.extractedKeywords;
              this.extractedDbSearchTitle = langGraphState.extractedDbSearchTitle;
              
              // console.log('✅ 완전한 LangGraph 상태 복원 완료');
            } else {
              // 이전 형태의 키워드 데이터인 경우 (하위 호환성)
              // console.log('이전 형태의 키워드 데이터 복원');
              if (Array.isArray(langGraphState)) {
                this.augmentedKeywords = langGraphState.map((keyword, index) => ({
                  id: index + 1,
                  text: keyword,
                  category: '키워드'
                }));
              } else {
                this.augmentedKeywords = [{
                  id: 1,
                  text: firstSearchMessage.keyword,
                  category: '키워드'
                }];
              }
            }
          } catch (e) {
            // keyword가 단순 문자열인 경우 (하위 호환성)
            // console.log('단순 문자열 키워드 복원:', firstSearchMessage.keyword);
            this.augmentedKeywords = [{
              id: 1,
              text: firstSearchMessage.keyword,
              category: '키워드'
            }];
          }
        }
        
        // 검색 결과가 LangGraph 상태에서 복원되지 않은 경우에만 db_search_title에서 복원
        if (!this.searchResults || this.searchResults.length === 0) {
          if (firstSearchMessage.db_search_title) {
            try {
              // db_search_title이 JSON 배열인 경우 파싱
              const titleData = JSON.parse(firstSearchMessage.db_search_title);
              if (Array.isArray(titleData)) {
                this.searchResults = titleData.map((title, index) => ({
                  id: `restored-${index}`,
                  res_id: `restored-${index}`,
                  res_score: 0.8, // 기본 점수
                  res_payload: {
                    document_name: title,
                    ppt_summary: '이전 세션에서 검색된 문서입니다.',
                    ppt_content: '이전 세션에서 검색된 내용입니다.'
                  }
                }));
              } else {
                // 단일 문자열인 경우
                this.searchResults = [{
                  id: 'restored',
                  res_id: 'restored',
                  res_score: 0.8,
                  res_payload: {
                    document_name: firstSearchMessage.db_search_title,
                    ppt_summary: '이전 세션에서 검색된 문서입니다.',
                    ppt_content: '이전 세션에서 검색된 내용입니다.'
                  }
                }];
              }
            } catch (e) {
              // 파싱 실패 시 단일 문자열로 처리
              this.searchResults = [{
                id: 'restored',
                res_id: 'restored',
                res_score: 0.8,
                res_payload: {
                  document_name: firstSearchMessage.db_search_title,
                  ppt_summary: '이전 세션에서 검색된 문서입니다.',
                  ppt_content: '이전 세션에서 검색된 내용입니다.'
                }
              }];
            }
          }
        }
        
        // 이미지 URL이 아직 설정되지 않은 경우 메시지에서 직접 복원
        if (!this.analysisImageUrl && firstSearchMessage.image) {
          this.analysisImageUrl = firstSearchMessage.image;
          // console.log('메시지에서 직접 이미지 URL 복원:', this.analysisImageUrl);
        }
        
        // 랭그래프 단계별 상태 복원
        this.isSearching = false;
        this.isGeneratingAnswer = false;
        
        // console.log('랭그래프 복원 완료:', {
          showRangraph: this.showRangraph,
          currentStep: this.currentStep,
          originalInput: this.originalInput,
          augmentedKeywords: this.augmentedKeywords,
          searchResults: this.searchResults,
          finalAnswer: this.finalAnswer,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle
        });
        
        // 화면 업데이트 강제 실행
        this.$nextTick(() => {
          this.$forceUpdate();
        });
        
      } else {
        // console.log('LangGraph 정보가 있는 메시지가 없어 랭그래프 복원 불가');
        // console.log('대화에 메시지는 있지만 LangGraph 관련 정보(keyword, db_search_title)가 없음');
        
        // 모든 메시지가 q_mode: 'add'인지 확인 (추가 질문만 있는 대화)
        const allAddMessages = conversation.messages.every(msg => msg.q_mode === 'add');
        
        if (allAddMessages && conversation.messages.length > 0) {
          // console.log('🔍 추가 질문만 있는 대화입니다. 관련 대화에서 LangGraph 정보를 찾아보겠습니다.');
          
          // 관련 대화 찾기 시도
          try {
            await this.findAndRestoreRelatedLangGraph(conversation.id);
          } catch (error) {
            console.error('관련 대화 찾기 실패:', error);
            // console.log('💡 관련 대화를 찾을 수 없어 일반 채팅 모드로 동작합니다.');
            
            // 추가 질문 전용 대화이므로 LangGraph 비활성화
            this.isFirstQuestionInSession = false; // 추가 질문 모드 유지
            this.showRangraph = false;
            this.currentStep = 0;
            this.resetRangraph();
          }
        } else {
          // 일반적인 경우: 첫 번째 질문 상태로 설정
          this.isFirstQuestionInSession = true;
          
          // 랭그래프 숨김
          this.showRangraph = false;
          this.currentStep = 0;
          this.resetRangraph();
        }
        
        // 캐시 정보 업데이트
        this.lastRestoredConversationId = conversation.id;
        this.lastRestoredMessageCount = conversation.messages.length;
      }
      
      // 대화 복원 완료
      this.isRestoringConversation = false;
    },
    
    // 관련 대화에서 LangGraph 정보 찾아서 복원
    async findAndRestoreRelatedLangGraph(conversationId) {
      // console.log('관련 대화 찾기 시작:', conversationId);
      
      try {
        const response = await fetch(`/api/conversations/${conversationId}/related`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.$store.state.token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        // console.log('관련 대화 API 응답:', data);
        
        if (data.related_conversation) {
          // console.log('✅ 관련 대화를 찾았습니다:', data.related_conversation.id);
          
          // 관련 대화의 LangGraph 정보로 복원
          await this.restoreRangraphFromConversation(data.related_conversation);
          
          // 추가 질문 모드로 설정 (LangGraph는 표시하되 추가 질문 가능)
          this.isFirstQuestionInSession = false;
          
          // console.log('🎯 관련 대화에서 LangGraph 복원 완료');
        } else {
          // console.log('❌ 관련 대화를 찾을 수 없습니다:', data.message);
          
          // 관련 대화가 없으므로 일반 채팅 모드
          this.isFirstQuestionInSession = false;
          this.showRangraph = false;
          this.currentStep = 0;
          this.resetRangraph();
        }
      } catch (error) {
        console.error('관련 대화 찾기 API 호출 실패:', error);
        throw error;
      }
    },
    
    getConversationIcon(iconType) {
      const iconMap = {
        "image": "🖼️",
        "code": "💻",
        "document": "📄",
        "math": "🧮",
        "general": "💬",
        "graph": "📊",
        "analysis": "📈",
        "data": "🔢",
        "dashboard": "📱",
        "ai": "🤖",
        "search": "🔍",
        "translation": "🔤",
        "audio": "🔊",
        "video": "🎬",
        "design": "🎨",
        "map": "🗺️",
        "science": "🔬",
        "finance": "💰",
        "health": "⚕️",
        "news": "📰",
        "weather": "☁️",
        "calendar": "📅",
        "task": "✅"
      };
      
      return iconMap[iconType] || "💬";
    },
    
    // 랭그래프 상태 초기화 (새 대화 생성 시)
    resetRangraphState() {
      this.resetRangraph();
      this.isFirstQuestionInSession = true; // 새 대화에서는 첫 번째 질문 상태로 초기화
      // console.log('새 대화 생성으로 인한 랭그래프 상태 초기화 완료 - 첫 번째 질문 상태: true');
    },
    
    // 랭그래프 초기화
    resetRangraph() {
      this.showRangraph = false;
      this.currentStep = 0;
      this.originalInput = '';
      this.augmentedKeywords = [];
      this.searchResults = [];
      this.finalAnswer = '';
      this.analysisImageUrl = ''; // 이미지 URL 초기화 추가
      this.lastImageUrl = ''; // 마지막 이미지 URL 초기화 추가
      this.langGraphError = null;
      this.isSearching = false;
      this.isGeneratingAnswer = false;
      this.isGeneratingImage = false;
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      this.extractedResIds = [];
      this.topDocument = null;
      },
    
    // 랭그래프를 히스토리에 저장
    saveRangraphToHistory() {
      if (this.showRangraph && this.currentStep >= 4) {
        const rangraphData = {
          id: Date.now(),
          originalInput: this.originalInput,
          augmentedKeywords: [...this.augmentedKeywords],
          searchResults: [...this.searchResults],
          finalAnswer: this.finalAnswer,
          analysisImageUrl: this.analysisImageUrl, // 이미지 URL 히스토리 저장 추가
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle,
          timestamp: new Date().toISOString()
        };
        
        this.rangraphHistory.push(rangraphData);
      }
    },
    
    async newConversation() {
      // console.log('🔄 새 대화 UI 초기화 시작...');
      
      // 새 대화 상태 설정 (실시간 기능 활성화)
      this.isNewConversation = true;
      this.isFirstQuestionInSession = true;
      this.isRestoringConversation = false;
      
      // 즉시 UI 상태만 초기화 (백엔드는 실제 메시지 전송 시 생성)
      this.userInput = '';
      this.resetRangraphState();
      this.rangraphHistory = [];
      this.finalAnswer = '';
      this.searchResults = [];
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      
      // 캐시 초기화
      this.lastRestoredConversationId = null;
      this.lastRestoredMessageCount = 0;
      
      // 현재 대화를 null로 설정하여 새 대화 상태로 만듦
      this.$store.commit('setCurrentConversation', null);
      
      // 실제로 새 대화를 생성하여 사이드바에 표시
      try {
        // console.log('🆕 새 대화 생성 중...');
        const newConversation = await this.$store.dispatch('createConversation');
        if (newConversation) {
          // console.log('✅ 새 대화 생성 완료:', newConversation.id);
          // console.log('📋 사이드바에 새 대화 탭 표시됨');
        } else {
          console.warn('⚠️ 새 대화 생성 실패 - UI 상태만 초기화됨');
        }
      } catch (error) {
        console.error('❌ 새 대화 생성 오류:', error);
        // 오류가 발생해도 UI 상태는 새 대화로 유지
      }
      
      // console.log('✅ 새 대화 UI 초기화 완료');
      // console.log('🔍 새 대화 상태:', {
        isNewConversation: this.isNewConversation,
        isFirstQuestionInSession: this.isFirstQuestionInSession,
        isRestoringConversation: this.isRestoringConversation,
        currentConversation: this.$store.state.currentConversation?.id || 'null'
      });
      
      // DOM 업데이트
      this.$nextTick(() => {
        this.scrollToBottom();
        this.safeFocus();
      });
    },
    async sendChatMessage(event) {
      if (event && event.shiftKey && event.key === 'Enter') {
        return; // Shift+Enter는 줄바꿈으로 처리
      }
      
      // 이미 실행 중이거나 스트리밍 중인 경우 중복 실행 방지
      if (!this.userInput.trim() || this.isLoading || this.isSearching || this.$store.state.isStreaming) {
        // console.log('메시지 전송 차단:', {
          hasInput: !!this.userInput.trim(),
          isLoading: this.isLoading,
          isSearching: this.isSearching,
          isStreaming: this.$store.state.isStreaming
        });
        return;
      }
      
      // Store the input text before clearing it
      const messageText = this.userInput.trim();
      
      // Clear input immediately
      this.userInput = '';
      this.adjustTextareaHeight(); // 높이 재조정
      
      // 실행 상태 설정 (executeRangraphFlow에서 관리됨)
      // this.isLoading = true; // 이 줄 제거
      
      try {
        // 세션 기반 첫 번째 질문 판별
        const shouldRunRangraph = this.isFirstQuestionInSession;
        
        // console.log('📋 대화 상태 확인:', {
          hasCurrentConversation: !!this.$store.state.currentConversation,
          currentConversationId: this.$store.state.currentConversation?.id,
          isFirstQuestionInSession: this.isFirstQuestionInSession,
          shouldRunRangraph
        });
        
        // 첫 번째 질문이면 새 대화 생성, 추가 질문이면 기존 대화 유지
        if (shouldRunRangraph) {
          // 첫 번째 질문: 새 대화 생성 (필요시)
          if (!this.$store.state.currentConversation) {
            // console.log('🆕 첫 번째 질문 - 새 대화 생성');
            await this.$store.dispatch('createConversation');
          }
        } else {
          // 추가 질문: 기존 대화 유지 (없으면 오류)
          if (!this.$store.state.currentConversation) {
            console.error('⚠️ 추가 질문인데 현재 대화가 없습니다. 첫 번째 질문으로 처리합니다.');
            this.isFirstQuestionInSession = true;
            await this.$store.dispatch('createConversation');
          } else {
            // console.log('✅ 추가 질문 - 기존 대화 유지:', this.$store.state.currentConversation.id);
          }
        }
        
        const currentConversation = this.$store.state.currentConversation;
        const conversationId = currentConversation.id;
        
        // console.log('📋 최종 질문 타입 판단:', {
          currentConversationId: conversationId,
          isFirstQuestionInSession: this.isFirstQuestionInSession,
          shouldRunRangraph: shouldRunRangraph ? '🔬 랭그래프' : '💬 추가질문',
          messageText: messageText.substring(0, 50) + '...'
        });
        
        if (shouldRunRangraph) {
          // 첫 번째 질문: LangGraph만 실행 (별도 LLM 처리 없음)
          // console.log('🔄 첫 번째 질문 - LangGraph만 실행 (별도 LLM 처리 없음)');
          // console.log('🔍 실행 전 상태:', {
            isNewConversation: this.isNewConversation,
            isFirstQuestionInSession: this.isFirstQuestionInSession,
            isRestoringConversation: this.isRestoringConversation
          });
          
          // LangGraph 실행 - 결과를 그대로 최종 답변으로 사용
          await this.executeRangraphFlow(messageText);
          
          // console.log('🔍 LangGraph 실행 완료 - 별도 LLM 처리 없이 완료');
          // console.log('🔍 실행 후 상태:', {
            isNewConversation: this.isNewConversation,
            isFirstQuestionInSession: this.isFirstQuestionInSession,
            isRestoringConversation: this.isRestoringConversation
          });
        } else {
          // 이후 질문: 컨텍스트 재사용하여 추가 LLM 처리
          // console.log('💬 추가 질문 - 컨텍스트 재사용하여 LLM 처리');
          await this.executeFollowupQuestion(messageText, conversationId);
        }
        
        this.$nextTick(() => {
          this.scrollToBottom();
          this.safeFocus();
        });
      } catch (error) {
        console.error('Error sending message:', error);
        // 오류 발생 시 실행 상태 해제
        this.isLoading = false;
        this.isSearching = false;
      }
      // finally 블록 제거 - executeRangraphFlow에서 상태 관리
    },
   
    // 추가 질문 처리 메서드 (실시간 스트리밍 응답)
    async executeFollowupQuestion(inputText, conversationId) {
      try {
        this.isLoading = true;
        
        // console.log('[FOLLOWUP] 추가 질문 실시간 스트리밍 시작');
        // console.log('[FOLLOWUP] LangGraph UI 상태 유지:', {
          showRangraph: this.showRangraph,
          currentStep: this.currentStep,
          finalAnswer: this.finalAnswer ? '있음' : '없음'
        });
        
        // LangGraph UI 상태 백업 (추가 질문 중에도 유지)
        const langGraphBackup = {
          showRangraph: this.showRangraph,
          currentStep: this.currentStep,
          originalInput: this.originalInput,
          augmentedKeywords: [...(this.augmentedKeywords || [])],
          searchResults: [...(this.searchResults || [])],
          finalAnswer: this.finalAnswer,
          analysisImageUrl: this.analysisImageUrl // 이미지 URL 백업 추가
        };
        
        // 먼저 사용자 질문을 즉시 화면에 표시
        const userMessage = {
          id: Date.now(),
          conversation_id: conversationId,
          role: 'user',
          question: inputText,
          ans: null,
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 사용자 메시지 즉시 추가
        this.$store.commit('addMessageToCurrentConversation', userMessage);
        
        // 스트리밍 메시지 완전 초기화 (이전 답변 제거)
        // console.log('[FOLLOWUP] 스트리밍 초기화 시작');
        this.$store.commit('updateStreamingMessage', '');
        this.$store.commit('setIsStreaming', false);
        
        // DOM 업데이트 대기
        await this.$nextTick();
        
        // 스트리밍 상태 확인 및 시작
        // console.log('[FOLLOWUP] 스트리밍 시작 - isStreaming:', this.$store.state.isStreaming);
        this.$store.commit('setIsStreaming', true);
        this.$store.commit('updateStreamingMessage', '');
        
        // 스트리밍 UI 강제 표시
        this.streamingVisible = true;
        
        // DOM 업데이트 강제 실행
        await this.$nextTick();
        this.$forceUpdate();
        
        // 스트리밍 상태 재확인
        // console.log('[FOLLOWUP] 스트리밍 상태 설정 완료 - isStreaming:', this.$store.state.isStreaming);
        // console.log('[FOLLOWUP] 스트리밍 UI 표시:', this.streamingVisible);
        // console.log('[FOLLOWUP] 스트리밍 메시지:', this.$store.state.streamingMessage);
        
        // LangGraph UI 상태 즉시 복원 (스트리밍 중에도 보이도록)
        this.showRangraph = langGraphBackup.showRangraph;
        this.currentStep = langGraphBackup.currentStep;
        this.originalInput = langGraphBackup.originalInput;
        this.augmentedKeywords = langGraphBackup.augmentedKeywords;
        this.searchResults = langGraphBackup.searchResults;
        this.finalAnswer = langGraphBackup.finalAnswer;
        this.analysisImageUrl = langGraphBackup.analysisImageUrl; // 이미지 URL 복원 추가
        
        // 강제 UI 업데이트
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('[FOLLOWUP] LangGraph UI 복원 완료');
        });
        
        // 추가 질문 스트리밍 API 호출
        const response = await fetch('http://localhost:8000/api/llm/langgraph/followup/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: inputText,
            conversation_id: conversationId,
            // 두 번째 질문부터는 LangGraph 컨텍스트 포함
            langgraph_context: {
              original_question: this.originalInput,
              keywords: this.extractedKeywords,
              search_results: this.searchResults.slice(0, 3), // 상위 3개 검색 결과만
              previous_answer: this.finalAnswer,
              documents: this.extractedDbSearchTitle
            },
            include_langgraph_context: true  // LangGraph 컨텍스트 포함 플래그
          })
        });
        
        if (!response.ok) {
          throw new Error(`추가 질문 스트리밍 API 호출 실패 (${response.status}: ${response.statusText})`);
        }
        
        // 스트리밍 응답 처리
        // console.log('📡 추가 질문 스트리밍 응답 처리 시작...');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedMessage = '';
        
        let streamingActive = true;
        let chunkCount = 0;
        while (streamingActive) {
          const { value, done } = await reader.read();
          if (done) {
            // console.log('📡 추가 질문 스트리밍 완료 - done=true');
            streamingActive = false;
            break;
          }
          
          chunkCount++;
          const chunk = decoder.decode(value);
          // console.log(`📡 추가 질문 청크 ${chunkCount} 수신:`, chunk);
          const lines = chunk.split('\n\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const content = line.substring(6);
              
              if (content === '[DONE]') {
                // console.log('📡 추가 질문 [DONE] 신호 수신 - 스트리밍 종료');
                streamingActive = false;
                break;
              }
              
              try {
                // JSON 형태의 데이터인지 확인
                const jsonData = JSON.parse(content);
                if (jsonData.content) {
                  // console.log('📡 추가 질문 JSON 데이터 처리:', jsonData.content);
                  accumulatedMessage += jsonData.content;
                  // 스트리밍 상태 확인 후 업데이트
                  // console.log('📡 스트리밍 상태 확인 - isStreaming:', this.$store.state.isStreaming);
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                  // console.log('📡 스트리밍 메시지 업데이트됨:', accumulatedMessage.length, '문자');
                } else if (jsonData.text) {
                  // console.log('📡 추가 질문 JSON 데이터 처리 (text):', jsonData.text);
                  accumulatedMessage += jsonData.text;
                  // 스트리밍 상태 확인 후 업데이트
                  // console.log('📡 스트리밍 상태 확인 - isStreaming:', this.$store.state.isStreaming);
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                  // console.log('📡 스트리밍 메시지 업데이트됨:', accumulatedMessage.length, '문자');
                }
              } catch (e) {
                // JSON이 아닌 일반 텍스트인 경우
                // console.log('📡 추가 질문 텍스트 데이터 처리:', content);
                accumulatedMessage += content;
                // 안전한 스트리밍 메시지 업데이트
                this.$store.commit('updateStreamingMessage', accumulatedMessage);
              }
            }
          }
        }
        
        // console.log(`📡 추가 질문 스트리밍 최종 완료 - 총 ${chunkCount}개 청크 처리`);
        // console.log(`📡 추가 질문 누적된 메시지: "${accumulatedMessage}"`);
        
        // 스트리밍된 메시지를 assistant 메시지로 현재 대화에 추가
        const assistantMessage = {
          id: Date.now() + 1,
          conversation_id: conversationId,
          role: 'assistant',
          question: inputText,
          ans: accumulatedMessage || '답변을 생성할 수 없습니다.',
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 assistant 메시지 추가
        this.$store.commit('addMessageToCurrentConversation', assistantMessage);
        
        // 스트리밍 완료
        this.$store.commit('setIsStreaming', false);
        
        // 백엔드에 메시지 저장 (q_mode: 'add')
        // console.log('💾 추가 질문 메시지 저장 시작 - q_mode: add');
        await this.saveAdditionalQuestionMessage(inputText, accumulatedMessage || '답변을 생성할 수 없습니다.');
        
        // LangGraph UI 상태 최종 복원 (저장 후에도 유지)
        this.showRangraph = langGraphBackup.showRangraph;
        this.currentStep = langGraphBackup.currentStep;
        this.originalInput = langGraphBackup.originalInput;
        this.augmentedKeywords = langGraphBackup.augmentedKeywords;
        this.searchResults = langGraphBackup.searchResults;
        this.finalAnswer = langGraphBackup.finalAnswer;
        this.analysisImageUrl = langGraphBackup.analysisImageUrl; // 이미지 URL 복원 추가
        
        // console.log('[FOLLOWUP] 최종 LangGraph UI 상태 복원 완료');
        this.$nextTick(() => {
          this.$forceUpdate();
        });
        
      } catch (error) {
        console.error('[FOLLOWUP] 추가 질문 처리 오류:', error);
        
        // 오류 메시지를 assistant 메시지로 추가
        const errorMessage = {
          id: Date.now() + 2,
          conversation_id: conversationId,
          role: 'assistant',
          question: inputText,
          ans: `⚠️ **오류 발생**: ${error.message}`,
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 오류 메시지 추가
        this.$store.commit('addMessageToCurrentConversation', errorMessage);
        
        // 스트리밍 중단
        this.$store.commit('setIsStreaming', false);
        
        // 폴백으로 기존 방식 시도
        await this.executeSimpleLLMFlow(inputText);
      } finally {
        this.isLoading = false;
      }
    },
    
    // 추가 질문 메시지 저장
    async saveFollowupMessage(question, result, conversationId) {
      try {
        // console.log('[FOLLOWUP] 메시지 저장 시작');
        
        const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: question,
            q_mode: 'add',  // 추가 질문 모드
            assistant_response: result.result?.answer || '답변을 생성할 수 없습니다.',
            keyword: result.tags || '',
            db_search_title: result.db_search_title || '',
            skip_llm: true  // LLM 재호출 방지
          })
        });
        
        if (response.ok) {
          const messageData = await response.json();
          // console.log('[FOLLOWUP] 메시지 저장 완료:', messageData);
          
          // LangGraph UI 유지를 위해 현재 상태 백업
          const currentLangGraphState = {
            showRangraph: this.showRangraph,
            currentStep: this.currentStep,
            originalInput: this.originalInput,
            augmentedKeywords: [...this.augmentedKeywords],
            searchResults: [...this.searchResults],
            finalAnswer: this.finalAnswer,
          };
          
          // 대화 목록 새로고침 (조건부 - 새 대화인 경우에만)
          if (!this.$store.state.currentConversation) {
            await this.$store.dispatch('fetchConversations');
          }
          
          // LangGraph 상태 복원
          this.showRangraph = currentLangGraphState.showRangraph;
          this.currentStep = currentLangGraphState.currentStep;
          this.originalInput = currentLangGraphState.originalInput;
          this.augmentedKeywords = currentLangGraphState.augmentedKeywords;
          this.searchResults = currentLangGraphState.searchResults;
          this.finalAnswer = currentLangGraphState.finalAnswer;
          
          // console.log('[FOLLOWUP] LangGraph UI 상태 복원 완료');
        } else {
          console.error('[FOLLOWUP] 메시지 저장 실패:', response.status, response.statusText);
        }
        
      } catch (error) {
        console.error('[FOLLOWUP] 메시지 저장 중 오류:', error);
      }
    },
    
    // 심플한 LLM 답변 플로우 (첫 번째 이후 질문용) - 스트리밍 지원
    async executeSimpleLLMFlow(inputText) {
      try {
        // console.log('💬 일반 LLM 스트리밍 답변 실행 시작:', inputText);
        
        // LangGraph UI 상태 백업 (폴백 시에도 유지)
        const langGraphBackup = {
          showRangraph: this.showRangraph,
          currentStep: this.currentStep,
          originalInput: this.originalInput,
          augmentedKeywords: [...(this.augmentedKeywords || [])],
          searchResults: [...(this.searchResults || [])],
          finalAnswer: this.finalAnswer,
        };
        
        // 먼저 사용자 질문을 즉시 화면에 표시
        const userMessage = {
          id: Date.now(),
          conversation_id: this.$store.state.currentConversation?.id,
          role: 'user',
          question: inputText,
          ans: null,
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 사용자 메시지 추가
        this.$store.commit('addMessageToCurrentConversation', userMessage);
        
        // 스트리밍 메시지 완전 초기화 (이전 답변 제거)
        this.$store.commit('updateStreamingMessage', '');
        this.$store.commit('setIsStreaming', false); // 먼저 false로 설정
        
        // DOM 업데이트 후 스트리밍 시작
        await this.$nextTick();
        
        // 스트리밍 시작 (깨끗한 상태에서)
        this.$store.commit('setIsStreaming', true);
        this.$store.commit('updateStreamingMessage', '');
        
        // 스트리밍 UI 강제 표시
        this.streamingVisible = true;
        
        // console.log('[SIMPLE_LLM] 스트리밍 메시지 초기화 완료');
        // console.log('[SIMPLE_LLM] 스트리밍 UI 표시:', this.streamingVisible);
        
        // 스트리밍 LLM API 호출
        const response = await fetch('http://localhost:8000/api/llm/chat/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({
            question: inputText,
            conversation_id: this.$store.state.currentConversation?.id
          })
        });
        
        if (!response.ok) {
          throw new Error(`LLM 스트리밍 API 호출 실패 (${response.status}: ${response.statusText})`);
        }
        
        // 스트리밍 응답 처리
        // console.log('📡 executeSimpleLLMFlow 스트리밍 응답 처리 시작...');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedMessage = '';
        
        let streamingActive = true;
        let chunkCount = 0;
        while (streamingActive) {
          const { value, done } = await reader.read();
          if (done) {
            // console.log('📡 executeSimpleLLMFlow 스트리밍 완료 - done=true');
            streamingActive = false;
            break;
          }
          
          chunkCount++;
          const chunk = decoder.decode(value);
          // console.log(`📡 executeSimpleLLMFlow 청크 ${chunkCount} 수신:`, chunk);
          const lines = chunk.split('\n\n');
          // console.log(`📡 executeSimpleLLMFlow 청크 ${chunkCount}에서 ${lines.length}개 라인 분리`);
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const content = line.substring(6);
              // console.log(`📡 executeSimpleLLMFlow 데이터 라인 처리: "${content}"`);
              
              if (content === '[DONE]') {
                // console.log('📡 executeSimpleLLMFlow [DONE] 신호 수신 - 스트리밍 종료');
                streamingActive = false;
                break;
              }
              
              try {
                // JSON 형태의 데이터인지 확인
                const jsonData = JSON.parse(content);
                if (jsonData.content) {
                  // console.log('📡 executeSimpleLLMFlow JSON 데이터 처리:', jsonData.content);
                  accumulatedMessage += jsonData.content;
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                } else if (jsonData.text) {
                  // console.log('📡 executeSimpleLLMFlow JSON 데이터 처리 (text):', jsonData.text);
                  accumulatedMessage += jsonData.text;
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                }
              } catch (e) {
                // JSON이 아닌 일반 텍스트인 경우
                // console.log('📡 executeSimpleLLMFlow 텍스트 데이터 처리:', content);
                accumulatedMessage += content;
                this.$store.commit('updateStreamingMessage', accumulatedMessage);
              }
            } else if (line.trim()) {
              // console.log(`📡 executeSimpleLLMFlow 비-데이터 라인 무시: "${line}"`);
            }
          }
        }
        
        // console.log(`📡 executeSimpleLLMFlow 스트리밍 최종 완료 - 총 ${chunkCount}개 청크 처리`);
        // console.log(`📡 executeSimpleLLMFlow 누적된 메시지 길이: ${accumulatedMessage.length}자`);
        // console.log(`📡 executeSimpleLLMFlow 누적된 메시지 내용: "${accumulatedMessage}"`);
        
        // console.log('✅ 일반 LLM 스트리밍 답변 생성 완료');
        
        // 스트리밍된 메시지를 assistant 메시지로 현재 대화에 추가
        const assistantMessage = {
          id: Date.now() + 1,
          conversation_id: this.$store.state.currentConversation?.id,
          role: 'assistant',
          question: inputText,
          ans: accumulatedMessage || '답변을 생성할 수 없습니다.',
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 assistant 메시지 추가 (화면에 유지)
        this.$store.commit('addMessageToCurrentConversation', assistantMessage);
        
        // 스트리밍 완료 (스트리밍 UI 숨김)
        this.$store.commit('setIsStreaming', false);
        
        // 백엔드에 메시지 저장 (q_mode: 'add')
        // console.log('💾 추가 질문 메시지 저장 시작 - q_mode: add');
        await this.saveAdditionalQuestionMessage(inputText, accumulatedMessage || '답변을 생성할 수 없습니다.');
        
        // LangGraph UI 상태 복원 (폴백 시에도 유지)
        this.showRangraph = langGraphBackup.showRangraph;
        this.currentStep = langGraphBackup.currentStep;
        this.originalInput = langGraphBackup.originalInput;
        this.augmentedKeywords = langGraphBackup.augmentedKeywords;
        this.searchResults = langGraphBackup.searchResults;
        this.finalAnswer = langGraphBackup.finalAnswer;
        
        // console.log('💾 일반 LLM 답변 저장 및 표시 완료 - LangGraph UI 상태 복원');
        this.$nextTick(() => {
          this.$forceUpdate();
        });
        
      } catch (error) {
        console.error('심플 LLM 스트리밍 답변 실행 오류:', error);
        
        // 오류 메시지를 assistant 메시지로 추가
        const errorMessage = {
          id: Date.now() + 3,
          conversation_id: this.$store.state.currentConversation?.id,
          role: 'assistant',
          question: inputText,
          ans: `⚠️ **오류 발생**: ${error.message}`,
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 오류 메시지 추가
        this.$store.commit('addMessageToCurrentConversation', errorMessage);
        
        // 스트리밍 중단
        this.$store.commit('setIsStreaming', false);
        
        // 백엔드에 오류 메시지도 저장
        await this.saveAdditionalQuestionMessage(inputText, `⚠️ **오류 발생**: ${error.message}`);
      }
    },
    
    // 추가 질문 플로우 실행 (두 번째 질문부터) - 스트리밍 지원
    async executeAdditionalQuestionFlow(inputText) {
      try {
        // 기존 랭그래프를 히스토리에 저장
        if (this.showRangraph && this.currentStep >= 4) {
          this.saveRangraphToHistory();
        }
        
        // console.log('💬 추가 질문 스트리밍 답변 실행 시작:', inputText);
        
        // 먼저 사용자 질문을 즉시 화면에 표시
        const userMessage = {
          id: Date.now(),
          conversation_id: this.$store.state.currentConversation?.id,
          role: 'user',
          question: inputText,
          ans: null,
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 사용자 메시지 추가
        this.$store.commit('addMessageToCurrentConversation', userMessage);
        
        // 스트리밍 메시지 완전 초기화 (이전 답변 제거)
        this.$store.commit('updateStreamingMessage', '');
        this.$store.commit('setIsStreaming', false); // 먼저 false로 설정
        
        // DOM 업데이트 후 스트리밍 시작
        await this.$nextTick();
        
        // 스트리밍 시작 (깨끗한 상태에서)
        this.$store.commit('setIsStreaming', true);
        this.$store.commit('updateStreamingMessage', '');
        
        // 스트리밍 UI 강제 표시
        this.streamingVisible = true;
        
        // console.log('[ADDITIONAL] 스트리밍 메시지 초기화 완료');
        // console.log('[ADDITIONAL] 스트리밍 UI 표시:', this.streamingVisible);
        
        // 스트리밍 LLM API 호출하여 추가 질문에 답변
        const response = await fetch('http://localhost:8000/api/llm/chat/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({
            question: inputText,
            conversation_id: this.$store.state.currentConversation?.id
          })
        });
        
        if (!response.ok) {
          throw new Error(`LLM 스트리밍 API 호출 실패 (${response.status}: ${response.statusText})`);
        }
        
        // 스트리밍 응답 처리
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedMessage = '';
        
        let streamingActive = true;
        while (streamingActive) {
          const { value, done } = await reader.read();
          if (done) {
            streamingActive = false;
            break;
          }
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const content = line.substring(6);
              
              if (content === '[DONE]') {
                streamingActive = false;
                break;
              }
              
              try {
                // JSON 형태의 데이터인지 확인
                const jsonData = JSON.parse(content);
                if (jsonData.content) {
                  accumulatedMessage += jsonData.content;
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                } else if (jsonData.text) {
                  accumulatedMessage += jsonData.text;
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                }
              } catch (e) {
                // JSON이 아닌 일반 텍스트인 경우
                accumulatedMessage += content;
                this.$store.commit('updateStreamingMessage', accumulatedMessage);
              }
            }
          }
        }
        
        // console.log('✅ 추가 질문 스트리밍 답변 생성 완료');
        
        // 스트리밍된 메시지를 assistant 메시지로 현재 대화에 추가
        const assistantMessage = {
          id: Date.now() + 2,
          conversation_id: this.$store.state.currentConversation?.id,
          role: 'assistant',
          question: inputText,
          ans: accumulatedMessage || '답변을 생성할 수 없습니다.',
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 assistant 메시지 추가 (화면에 유지)
        this.$store.commit('addMessageToCurrentConversation', assistantMessage);
        
        // 스트리밍 완료 (스트리밍 UI 숨김)
        this.$store.commit('setIsStreaming', false);
        
        // 백엔드에 메시지 저장 (q_mode: 'add')
        // console.log('💾 추가 질문 메시지 저장 시작 - q_mode: add');
        await this.saveAdditionalQuestionMessage(inputText, accumulatedMessage || '답변을 생성할 수 없습니다.');
        
        // finalAnswer는 설정하지 않음 (currentMessages에서 표시하므로)
        
      } catch (error) {
        console.error('추가 질문 스트리밍 실행 오류:', error);
        
        // 오류 메시지를 assistant 메시지로 추가
        const errorMessage = {
          id: Date.now() + 4,
          conversation_id: this.$store.state.currentConversation?.id,
          role: 'assistant',
          question: inputText,
          ans: `⚠️ **오류 발생**: ${error.message}`,
          created_at: new Date().toISOString()
        };
        
        // 현재 대화에 오류 메시지 추가
        this.$store.commit('addMessageToCurrentConversation', errorMessage);
        
        // 스트리밍 중단
        this.$store.commit('setIsStreaming', false);
        
        // 백엔드에 오류 메시지도 저장
        await this.saveAdditionalQuestionMessage(inputText, `⚠️ **오류 발생**: ${error.message}`);
      }
    },
    
    // 추가 질문 메시지 저장 (q_mode: 'add')
    async saveAdditionalQuestionMessage(question, answer) {
      try {
        // 저장 상태 업데이트
        this.isSavingMessage = true;
        this.saveStatus = '';
        
        if (!this.$store.state.currentConversation) {
          await this.$store.dispatch('createConversation');
        }
        
        const conversationId = this.$store.state.currentConversation.id;
        
        // 메시지 생성 API 호출 (q_mode: 'add')
        const requestBody = { 
          question: question,
          q_mode: 'add',  // 추가 질문 모드
          assistant_response: answer,
          keyword: null,  // 추가 질문에는 키워드 없음
          db_search_title: null,  // 추가 질문에는 문서 타이틀 없음
          image: this.analysisImageUrl,  // 기존 이미지 URL 유지 (추가 질문에서도)
          user_name: this.$store.state.user?.username || '사용자'  // username 사용
        };
        
        // console.log('📤 추가 질문 메시지 저장 API 요청 데이터:', requestBody);
        
        const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify(requestBody)
        });
        
        if (response.ok) {
          const messageData = await response.json();
          // console.log('추가 질문 메시지 저장 완료:', messageData);
          
          // 저장 성공 로그만 남기고 사용자 메시지는 제거
          // console.log('✅ 추가 질문 메시지가 성공적으로 저장되었습니다.');
          this.saveStatus = '';
          
          // 대화 목록 새로고침 제거 - 이미 화면에 메시지가 표시되어 있으므로
          // await this.$store.dispatch('fetchConversations');
          
          // LangGraph UI 상태는 executeFollowupQuestion에서 관리하므로 여기서는 건드리지 않음
          // console.log('✅ 추가 질문 저장 완료 - LangGraph UI 상태 유지');
        } else if (response.status === 401) {
          // 인증 실패 시 토큰 갱신 시도
          console.error('❌ 인증 실패 (401). 토큰 갱신 시도...');
          this.saveStatus = '⚠️ 인증이 만료되었습니다. 토큰을 갱신 중...';
          
          try {
            // 토큰 갱신 시도
            await this.refreshToken();
            // console.log('🔄 토큰 갱신 완료, 저장 재시도...');
            
            // 토큰 갱신 후 저장 재시도
            this.$nextTick(() => {
              this.saveAdditionalQuestionMessage(question, answer);
            });
          } catch (refreshError) {
            console.error('❌ 토큰 갱신 실패:', refreshError);
            this.saveStatus = '⚠️ 인증이 만료되었습니다. 자동으로 SSO 로그인으로 이동합니다...';
            
            // 자동 SSO 로그인으로 리다이렉트
            setTimeout(() => {
              try {
                window.location.replace('http://localhost:8000/api/auth/auth_sh');
              } catch (error) {
                window.location.href = 'http://localhost:8000/api/auth/auth_sh';
              }
            }, 1500);
          }
        } else {
          console.error('❌ 추가 질문 메시지 저장 실패:', response.status, response.statusText);
          
          // 오류 응답 내용 확인
          let errorMessage = `${response.status} ${response.statusText}`;
          try {
            const errorData = await response.json();
            console.error('📄 API 오류 응답 (JSON):', errorData);
            if (errorData.detail) {
              errorMessage = errorData.detail;
            }
          } catch (e) {
            console.error('📄 API 오류 응답 JSON 파싱 실패:', e);
            // JSON 파싱 실패 시 텍스트로 읽기 시도
            try {
              const errorText = await response.text();
              console.error('📄 API 오류 응답 (텍스트):', errorText);
              if (errorText) {
                errorMessage = errorText;
              }
            } catch (e2) {
              console.error('📄 API 오류 응답 읽기 완전 실패:', e2);
            }
          }
          
          this.saveStatus = `⚠️ 메시지 저장 실패: ${errorMessage}`;
          console.error('💾 저장 실패 상태 설정:', this.saveStatus);
          
          // 저장 실패 시 재시도 로직 (최적화)
          // console.log('🔄 추가 질문 메시지 저장 재시도...');
          this.$nextTick(() => {
            this.saveAdditionalQuestionMessage(question, answer);
          });
        }
      } catch (error) {
        console.error('추가 질문 메시지 저장 중 오류:', error);
        this.saveStatus = `⚠️ 메시지 저장 오류: ${error.message}`;
        
        // 오류 발생 시 재시도 로직 (최적화)
        // console.log('🔄 추가 질문 메시지 저장 재시도...');
        this.$nextTick(() => {
          this.saveAdditionalQuestionMessage(question, answer);
        });
      } finally {
        this.isSavingMessage = false;
      }
    },
    
    // 랭그래프 플로우 실행 (실시간 기능 보존)
    async executeRangraphFlow(inputText) {
      // 이미 실행 중인 경우 중복 실행 방지
      if (this.isLoading || this.isSearching) {
        // console.log('이미 랭그래프가 실행 중입니다. 중복 실행 방지.');
        return;
      }
      
      // console.log('🚀 executeRangraphFlow 시작:', inputText);
      // console.log('🔍 실시간 기능 상태:', {
        isNewConversation: this.isNewConversation,
        isFirstQuestionInSession: this.isFirstQuestionInSession,
        isRestoringConversation: this.isRestoringConversation
      });
      
      // 새 대화가 아닌 경우 기존 랭그래프를 히스토리에 저장
      if (this.showRangraph && this.currentStep >= 4) {
        this.saveRangraphToHistory();
      }
      
      // 먼저 사용자 질문을 즉시 화면에 표시
      const userMessage = {
        id: Date.now(),
        conversation_id: this.$store.state.currentConversation?.id,
        role: 'user',
        question: inputText,
        ans: null,
        created_at: new Date().toISOString()
      };
      
      // 현재 대화에 사용자 메시지 즉시 추가
      this.$store.commit('addMessageToCurrentConversation', userMessage);
      
      // 실행 상태 설정
      this.isLoading = true;
      this.isSearching = true;
      
      // 새로운 랭그래프 시작
      this.showRangraph = true;
      this.currentStep = 0;
      this.augmentedKeywords = [];
      this.searchResults = [];
      this.searchedDocuments = [];
      this.hasSearchCompleted = false; // 검색 완료 상태 초기화
      this.showSearchResultPopup = false; // 팝업 상태 초기화
      this.selectedSearchResult = null; // 선택된 검색 결과 초기화
      this.isDoneProcessed = false; // DONE 처리 완료 상태 초기화
      this.finalAnswer = '';
      this.analysisImageUrl = ''; // 이미지 URL 초기화 추가
      this.lastImageUrl = ''; // 마지막 이미지 URL 초기화 추가
      this.langGraphError = null;
      this.originalInput = inputText;
      
      // 추출된 데이터 초기화
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      
      try {
        
        // console.log('🔍 SSE 연결 조건 확인:', {
          isNewConversation: this.isNewConversation,
          isFirstQuestionInSession: this.isFirstQuestionInSession,
          isRestoringConversation: this.isRestoringConversation,
          currentConversation: this.$store.state.currentConversation?.id || 'null',
          shouldConnect: this.isFirstQuestionInSession && !this.isRestoringConversation
        });
        
        // 첫 번째 질문이고 복원 중이 아닌 경우 SSE 스트리밍 사용
        if (this.isFirstQuestionInSession && !this.isRestoringConversation) {
          // console.log('🎯 첫 번째 질문 감지 - SSE 스트리밍 활성화');
          try {
            await this.executeLangGraphWithSSE(inputText);
            return; // SSE 처리 완료 후 종료
          } catch (sseError) {
            // AbortError는 정상적인 종료이므로 폴백하지 않음
            if (sseError.name === 'AbortError') {
              // console.log('✅ SSE 연결이 정상적으로 종료됨 (AbortError)');
              return; // 정상 종료
            }
            console.warn('⚠️ SSE 스트리밍 실패, 기본 API로 폴백:', sseError);
            // 다른 오류의 경우에만 폴백으로 기본 API 사용
          }
        } else {
          // console.log('🔄 추가 질문 또는 복원 상태 - 기본 API 사용');
        }
        
        // 기본 LangGraph API 호출 (폴백용)
        const response = await fetch('http://localhost:8000/api/llm/langgraph', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: inputText
          })
        });
        
        if (!response.ok) {
          throw new Error(`LangGraph API 호출 실패 (${response.status}: ${response.statusText})`);
        }
        
        const result = await response.json();
        // console.log('LangGraph API 응답:', result);
        
        // 직접 결과 처리
        this.processDirectLangGraphResult(result);
        
      } catch (error) {
        console.error('LangGraph 실행 오류:', error);
        // 오류 발생 시 기본 플로우로 폴백 (오류 정보 포함)
        await this.fallbackRangraphFlow(inputText, error);
      } finally {
        this.isLoading = false;
        this.isSearching = false;
      }
    },
    
    // WebSocket 연결 설정
    // SSE 스트리밍으로 LangGraph 실행
    async executeLangGraphWithSSE(inputText) {
      // // console.log('🚀 SSE 스트리밍 시작:', inputText);
      
      // AbortController 생성 및 전역 저장
      const controller = new AbortController();
      window.sseController = controller;
      // // console.log('🔌 SSE AbortController 생성');
      
      try {
        const response = await fetch('http://localhost:8000/api/llm/langgraph/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: inputText
          }),
          signal: controller.signal // AbortController 신호 추가
        });
        
        if (!response.ok) {
          throw new Error(`SSE 요청 실패: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // console.log('✅ SSE 스트림 시작');
        
        let streamActive = true;
        while (streamActive) {
          const { done, value } = await reader.read();
          
          if (done) {
            // console.log('🏁 SSE 스트림 완료');
            streamActive = false;
            break;
          }
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6); // 'data: ' 제거
              
              if (data === '[DONE]') {
                // console.log('🏁 SSE 스트리밍 완료');
                return;
              }
              
              if (data.trim()) {
                try {
                  const parsedData = JSON.parse(data);
                  
                  // 하트비트 메시지 무시
                  if (parsedData.heartbeat) {
                    continue;
                  }
                  
                  // 에러 처리
                  if (parsedData.error) {
                    console.error('❌ SSE 에러:', parsedData.error);
                    throw new Error(parsedData.error);
                  }
                  
                  // console.log('📡 SSE 데이터 처리:', parsedData);
                  this.handleSSEMessage(parsedData);
                  
                } catch (parseError) {
                  console.error('❌ SSE 메시지 파싱 오류:', parseError, 'Data:', data);
                }
              }
            }
          }
        }
        
      } catch (error) {
        // AbortError는 정상적인 종료이므로 에러가 아님
        if (error.name === 'AbortError') {
          // console.log('✅ SSE 스트리밍 정상 종료 (AbortError)');
          return; // 정상 종료
        }
        console.error('❌ SSE 스트리밍 오류:', error);
        throw error;
      }
    },
    
    // SSE 메시지 처리
    handleSSEMessage(data) {
      // console.log('📡 SSE 메시지 수신:', data);
      // console.log('📡 메시지 단계:', data.stage);
      // console.log('📡 메시지 상태:', data.status);
      // console.log('📡 메시지 결과:', data.result);
      // console.log('📡 현재 단계:', this.currentStep);

      // DONE 메시지 처리 후 즉시 종료
      if (data.stage === 'DONE') {
        if (this.isDoneProcessed) {
          // console.log('🔒 DONE 메시지 이미 처리됨 - 중복 처리 방지');
          return;
        }
        
        // console.log('🏁 DONE 메시지 수신 - 최종 UI 업데이트');
        this.isDoneProcessed = true; // DONE 처리 완료 플래그 설정
        
        // 모든 로딩 상태 완료
        this.isLoading = false;
        this.isSearching = false;
        this.isGeneratingAnswer = false;
        this.isStreamingAnswer = false;
        
        // 최종 단계로 설정
        this.currentStep = 4; // UI 4단계: 분석 결과 이미지 표시
        
        // 분석 결과 이미지 처리 (DONE 메시지에서만)
        if (data.result && data.result.analysis_image_url) {
          this.analysisImageUrl = data.result.analysis_image_url;
          // console.log('🖼️ DONE에서 분석 이미지 URL 설정:', this.analysisImageUrl);
        }
        
        // 최종 답변이 없으면 스트리밍된 답변 사용
        if (!this.finalAnswer && this.streamingAnswer) {
          this.finalAnswer = this.streamingAnswer;
          // console.log('🎯 DONE에서 최종 답변 설정:', this.finalAnswer);
        }
        
        // 랭그래프 종료 후 질문 영역 다음에 최종 답변을 채팅 메시지로 추가
        // console.log('🔍 [DONE] 최종 답변 확인:', {
          finalAnswer: this.finalAnswer ? this.finalAnswer.substring(0, 100) + '...' : null,
          streamingAnswer: this.streamingAnswer ? this.streamingAnswer.substring(0, 100) + '...' : null,
          finalAnswerLength: this.finalAnswer?.length || 0,
          streamingAnswerLength: this.streamingAnswer?.length || 0,
          currentConversation: this.$store.state.currentConversation?.id,
          hasCurrentConversation: !!this.$store.state.currentConversation
        });
        
        const answerToAdd = this.finalAnswer || this.streamingAnswer;
        // console.log('🎯 [DONE] 추가할 답변:', {
          answerToAdd: answerToAdd ? answerToAdd.substring(0, 100) + '...' : null,
          answerLength: answerToAdd?.length || 0,
          hasAnswer: !!answerToAdd
        });
        
        if (answerToAdd && this.$store.state.currentConversation) {
          const assistantMessage = {
            id: Date.now() + Math.random(), // 고유 ID 생성
            conversation_id: this.$store.state.currentConversation.id,
            role: 'assistant',
            question: null,
            ans: answerToAdd,
            created_at: new Date().toISOString()
          };
          
          // console.log('💬 [DONE] 채팅 메시지 추가 시도:', {
            id: assistantMessage.id,
            conversation_id: assistantMessage.conversation_id,
            role: assistantMessage.role,
            answerPreview: assistantMessage.ans.substring(0, 100) + '...',
            answerLength: assistantMessage.ans.length
          });
          
          // Vuex 스토어 상태 확인
          // console.log('📊 [DONE] Vuex 스토어 상태:', {
            currentMessages: this.$store.state.currentConversation?.messages?.length || 0,
            currentConversation: this.$store.state.currentConversation?.id
          });
          
          this.$store.commit('addMessageToCurrentConversation', assistantMessage);
          
          // console.log('✅ [DONE] 채팅 메시지 추가 완료');
          // console.log('📊 [DONE] 추가 후 메시지 수:', this.$store.state.currentConversation?.messages?.length || 0);
          
          // 스크롤을 맨 아래로 이동
          this.$nextTick(() => {
            // console.log('📜 [DONE] 스크롤 이동 시작');
            this.scrollToBottom();
            // console.log('📜 [DONE] 스크롤 이동 완료');
          });
        } else {
          // console.log('❌ [DONE] 채팅 메시지 추가 실패:', {
            hasAnswer: !!answerToAdd,
            answerLength: answerToAdd?.length || 0,
            hasConversation: !!this.$store.state.currentConversation,
            conversationId: this.$store.state.currentConversation?.id || 'null'
          });
        }
        
        // UI 강제 업데이트
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ DONE 메시지 처리 완료 - 모든 UI 업데이트 완료');
        });
        
        // console.log('🔒 DONE 처리 완료 - 이후 모든 업데이트 종료');
        
        // SSE 연결 종료 신호 발송
        if (window.sseController) {
          // console.log('🔌 SSE 연결 종료 시도');
          window.sseController.abort();
          window.sseController = null;
          // console.log('✅ SSE 연결 종료 완료');
        }
        
        return; // 여기서 처리 종료
      }
      
      // 단계별 처리
      if (data.stage === 'A' && data.status === 'started') {
        // console.log('🔄 A단계: 초기화 시작');
        this.currentStep = 0; // 아직 UI 단계 시작 전
        this.isSearching = true;
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 1단계 시작 UI 업데이트 완료');
        });
      } else if (data.stage === 'A' && data.status === 'completed') {
        // console.log('🔄 A단계: 초기화 완료');
        this.currentStep = 0; // 아직 UI 단계 시작 전
        this.originalInput = data.result.question || data.result.message;
        this.isSearching = false;
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 1단계 완료 UI 업데이트 완료');
        });
      } else if (data.stage === 'B' && data.status === 'started') {
        // console.log('🔄 B단계: 키워드 증강 시작 → UI 1단계 활성화');
        this.currentStep = 1; // UI 1단계: 키워드 증강
        this.isSearching = true;
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 2단계 시작 UI 업데이트 완료');
        });
      } else if (data.stage === 'B' && data.status === 'completed') {
        // console.log('🔄 B단계: 키워드 생성 완료 → UI 1단계 완료');
        this.currentStep = 1; // UI 1단계: 키워드 증강 완료
        // isSearching 상태는 변경하지 않음 - 다음 단계(검색)를 위해 유지
        
        const keywords = data.result.keywords || [];
        this.augmentedKeywords = keywords.map((keyword, index) => ({
          id: index + 1,
          text: keyword,
          category: this.categorizeKeyword(keyword, index)
        }));
        
        // console.log('🔑 생성된 키워드:', this.augmentedKeywords);
        // console.log('🔑 키워드 개수:', this.augmentedKeywords.length);
        
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 2단계 UI 업데이트 완료');
        });
      } else if (data.stage === 'C' && data.status === 'started') {
        // console.log('🔄 C단계: RAG 검색 시작 → UI 2단계 활성화');
        this.currentStep = 2; // UI 2단계: DB 검색
        this.isSearching = true;
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 3단계 시작 UI 업데이트 완료');
        });
      } else if (data.stage === 'C' && data.status === 'completed') {
        // console.log('🔄 C단계: RAG 검색 완료 → UI 2단계 완료 (로딩 유지)');
        this.currentStep = 2; // UI 2단계: DB 검색 완료
        // isSearching은 D단계 완료까지 유지 (계속 로딩)
        this.hasSearchCompleted = true; // 검색 완료 상태 설정
        
        const docCount = data.result.documents_count || data.result.top_documents || 0;
        
        // 상세 검색 결과가 있으면 배열로, 없으면 숫자로 저장
        if (data.result.search_results && data.result.search_results.length > 0) {
          this.searchResults = data.result.search_results; // 상세 결과 배열
          // console.log('📄 상세 검색 결과:', this.searchResults);
        } else {
          this.searchResults = docCount;  // 검색 결과 수만 저장
          // 검색된 문서 제목들 저장 (기존 방식)
          if (data.result.document_titles && data.result.document_titles.length > 0) {
            this.searchedDocuments = data.result.document_titles;
            // console.log('📄 검색된 문서 제목들:', this.searchedDocuments);
          }
        }
        
        // console.log('📄 검색된 문서 수:', docCount);
        
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 3단계 완료 UI 업데이트 완료');
        });
      } else if (data.stage === 'D' && data.status === 'started') {
        // console.log('🔄 D단계: 문서 재순위 시작 → UI 2단계 유지');
        // currentStep은 2 유지 (DB 검색 단계에서 처리)
        this.isSearching = true;
        this.streamingAnswer = ''; // 스트리밍 답변 초기화
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ D단계 시작 UI 업데이트 완료');
        });
      } else if (data.stage === 'D' && data.status === 'streaming') {
        // console.log('🔄 D단계: 답변 스트리밍 중 → UI 3단계');
        this.currentStep = 3; // UI 3단계: 검색된 내용 기반 답변
        this.isGeneratingAnswer = false;
        this.isStreamingAnswer = true;
        this.isSearching = false; // 검색 완료, 답변 생성 시작
        
        // 실시간 스트리밍 답변 업데이트 (토큰별 누적)
        if (data.result.content) {
          this.streamingAnswer += data.result.content; // 토큰별로 누적
          // // console.log('📝 D단계 스트리밍 토큰 추가:', data.result.content);
          // // console.log('📝 현재 누적 답변 길이:', this.streamingAnswer.length);
        } else if (data.result.accumulated_answer) {
          this.streamingAnswer = data.result.accumulated_answer;
        }
        
        this.$nextTick(() => {
          this.$forceUpdate();
          // // console.log('✅ D단계 실시간 답변 스트리밍 업데이트 완료');
        });
      } else if (data.stage === 'D' && data.status === 'completed') {
        // console.log('🔄 D단계: 문서 재순위 및 답변 완료 → UI 3단계');
        this.currentStep = 3; // UI 3단계: 검색된 내용 기반 답변 완료
        this.isSearching = false;
        this.isStreamingAnswer = false;
        this.isGeneratingAnswer = false;
        this.isLoading = false; // 전체 로딩 상태 완료
        
        // 최종 답변 설정 (스트리밍된 답변이 있으면 그것을 사용)
        this.finalAnswer = this.streamingAnswer || data.result.answer;
        // console.log('🎯 D단계 최종 답변 설정:', this.finalAnswer);
        
        // D단계에서는 채팅 메시지 추가하지 않음 (DONE에서 처리)
        
        const docCount = data.result.documents_count || 0;
        // console.log('📄 재순위된 문서 수:', docCount);
        
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ D단계 완료 UI 업데이트 완료');
        });
      } else if (data.stage === 'E' && (data.status === 'started' || data.status === 'streaming' || data.status === 'completed')) {
        // console.log('🔄 E단계 무시 (D단계에서 이미 처리됨):', data.status);
        // D단계에서 이미 모든 처리가 완료되었으므로 E단계는 무시
        
        // 이미지 URL 처리 (강화된 디버깅)
        // console.log('🔍 4단계 데이터 전체 확인:', data.result);
        // console.log('🔍 analysis_image_url 필드 확인:', data.result.analysis_image_url);
        // console.log('🔍 data.result 타입:', typeof data.result);
        // console.log('🔍 data.result 키들:', Object.keys(data.result || {}));
        
        // 여러 경로에서 이미지 URL 찾기
        let imageUrl = null;
        if (data.result.analysis_image_url) {
          imageUrl = data.result.analysis_image_url;
          // console.log('🖼️ D단계에서 이미지 URL 발견:', imageUrl);
        }
        
        if (imageUrl) {
          this.analysisImageUrl = imageUrl;
          this.lastImageUrl = imageUrl; // 디버깅용 저장
          // console.log('🖼️ 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
          this.$forceUpdate(); // 강제 UI 업데이트
        } else {
          // console.log('⚠️ D단계에서 analysis_image_url을 찾을 수 없습니다');
          // console.log('⚠️ 사용 가능한 필드들:', Object.keys(data.result || {}));
        }
        
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ D단계 UI 업데이트 완료');
        });
      }
    },
    
    handleWebSocketMessage(data) {
      // console.log('📡 WebSocket 메시지 수신:', data);
      // console.log('📡 메시지 노드:', data.node);
      // console.log('📡 메시지 상태:', data.status);
      // console.log('📡 메시지 데이터:', data.data);
      // console.log('📡 현재 단계:', this.currentStep);
      // console.log('📡 현재 키워드 개수:', this.augmentedKeywords?.length || 0);
      
      if (data.node === 'node_init' && data.status === 'completed') {
        // console.log('🔄 1단계: 초기화 완료');
        this.currentStep = 1;
        this.originalInput = data.data.result;
        this.isSearching = false;
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 1단계 UI 업데이트 완료');
        });
      } else if (data.node === 'node_rc_keyword' && data.status === 'completed') {
        // console.log('🔄 2단계: 키워드 증강 시작');
        // console.log('🔑 키워드 노드 완료 - 전체 데이터:', data);
        // console.log('🔑 키워드 노드 완료 - result 데이터:', data.data?.result);
        // console.log('🔑 키워드 노드 완료 - result 타입:', typeof data.data?.result);
        // console.log('🔑 키워드 노드 완료 - result 길이:', data.data?.result?.length);
        
        if (data.data && data.data.result && Array.isArray(data.data.result)) {
          this.currentStep = 2;
          this.isSearching = true; // 키워드 생성 완료 후 검색 시작
          this.augmentedKeywords = data.data.result.map((keyword, index) => ({
            id: index + 1,
            text: keyword,
            category: this.categorizeKeyword(keyword, index)
          }));
          
          // 키워드 추출하여 저장
          this.extractedKeywords = data.data.result;
          // console.log('🔑 extractedKeywords 설정됨:', this.extractedKeywords);
          // console.log('🔑 augmentedKeywords 설정됨:', this.augmentedKeywords);
          
          // 강제 리렌더링
          this.$nextTick(() => {
            this.$forceUpdate();
            // console.log('✅ 2단계 UI 업데이트 완료 - 키워드 표시됨');
          });
        } else {
          console.error('🔑 키워드 데이터 형식 오류:', data);
        }
      } else if (data.node === 'node_rc_rag' && data.status === 'completed') {
        // console.log('🔄 3단계: DB 검색 완료');
        // console.log('📊 RAG 노드 완료 - 데이터:', data.data.result);
        this.currentStep = 3; // 3단계로 이동 (답변 생성)
        this.isSearching = false; // 검색 완료
        this.isGeneratingAnswer = true; // 답변 생성 시작
        
        // 검색 결과를 올바른 구조로 저장
        this.searchResults = data.data.result;
        // console.log('💾 검색 결과 저장:', this.searchResults);
        
        // 검색된 문서 제목 추출하여 저장
        if (data.data.result && data.data.result.length > 0) {
          this.extractedDbSearchTitle = data.data.result.map(item => 
            item.res_payload?.document_name || '제목 없음'
          );
          // console.log('📄 추출된 문서 제목:', this.extractedDbSearchTitle);
        } else {
          this.extractedDbSearchTitle = '검색 결과 없음';
        }
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 3단계 UI 업데이트 완료 - 검색 결과 표시됨');
        });
      } else if (data.node === 'node_rc_rerank' && data.status === 'completed') {
        // 재순위 결과 처리
      } else if ((data.node === 'node_rc_answer' || data.node === 'node_rc_plain_answer') && data.status === 'completed') {
        // console.log('🔄 4단계: 최종 답변 생성 완료');
        this.isGeneratingAnswer = false; // 답변 생성 완료
        // console.log(`📝 ${data.node} 노드 완료 - 데이터:`, data.data.result);
        this.currentStep = 4;
        this.finalAnswer = data.data.result.answer || data.data.result;
        // console.log('🎯 finalAnswer 설정됨:', this.finalAnswer);
        
        // LangGraph 실행 결과에서 필요한 데이터 추출
        // console.log('🔍 node_rc_answer 완료 - 전체 데이터:', data.data.result);
        
        if (data.data.result) {
          // 키워드 증강 목록 저장
          if (data.data.result.keyword) {
            this.extractedKeywords = data.data.result.keyword;
            // console.log('🔑 추출된 키워드:', this.extractedKeywords);
          } else {
            // console.log('⚠️ 키워드 데이터가 없습니다');
          }
          
          // 검색된 문서 제목들 저장
          if (data.data.result.db_search_title) {
            this.extractedDbSearchTitle = data.data.result.db_search_title;
            // console.log('📄 추출된 문서 제목:', this.extractedDbSearchTitle);
          } else {
            // console.log('⚠️ 문서 제목 데이터가 없습니다');
          }
          
          // 이미지 URL 처리 (강화된 검색)
          // console.log('🔍 WebSocket 4단계 데이터 전체 확인:', data.data.result);
          // console.log('🔍 WebSocket analysis_image_url 필드 확인:', data.data.result.analysis_image_url);
          
          let imageUrl = null;
          
          // 여러 경로에서 이미지 URL 찾기
          if (data.data.result.analysis_image_url) {
            imageUrl = data.data.result.analysis_image_url;
            // console.log('🖼️ WebSocket - data.data.result에서 이미지 URL 발견:', imageUrl);
          } else if (data.data.result.response && data.data.result.response.analysis_image_url) {
            imageUrl = data.data.result.response.analysis_image_url;
            // console.log('🖼️ WebSocket - data.data.result.response에서 이미지 URL 발견:', imageUrl);
          }
          
          if (imageUrl) {
            this.analysisImageUrl = imageUrl;
            this.lastImageUrl = imageUrl; // 디버깅용 저장
            // console.log('🖼️ WebSocket 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
          } else {
            // console.log('⚠️ WebSocket 분석 이미지 URL 데이터가 없습니다');
            // console.log('⚠️ 사용 가능한 필드들:', Object.keys(data.data.result || {}));
            if (data.data.result.response) {
              // console.log('⚠️ response 필드들:', Object.keys(data.data.result.response || {}));
            }
          }
          
          // q_mode 확인
          if (data.data.result.q_mode) {
            // console.log('🔍 q_mode:', data.data.result.q_mode);
          } else {
            // console.log('⚠️ q_mode 데이터가 없습니다');
          }
        } else {
          // console.log('❌ data.data.result가 없습니다');
        }
        
        // LangGraph 완료 후 결과 저장 (즉시 실행)
        // console.log('LangGraph 완료, 저장 함수 호출 시작...');
        // console.log('저장할 데이터 확인:');
        // console.log('  - 질문:', this.originalInput);
        // console.log('  - 답변:', this.finalAnswer);
        // console.log('  - 키워드:', this.extractedKeywords);
        // console.log('  - 문서제목:', this.extractedDbSearchTitle);
        
        // 첫 번째 질문 완료 후 상태 변경 (실시간 처리 완료 시점)
        this.isFirstQuestionInSession = false;
        this.isNewConversation = false;
        // console.log('🎯 첫 번째 질문 실시간 처리 완료 - 상태 변경');
        
        // 저장 함수 즉시 호출 (지연 제거)
        // console.log('🔄 저장 함수 즉시 호출...');
        // console.log('🔄 saveLangGraphMessageFromWebSocket 함수 호출 시작');
        
        // 함수 호출 전 상태 확인
        // console.log('📊 저장 함수 호출 전 상태:');
        // console.log('  - isSavingMessage:', this.isSavingMessage);
        // console.log('  - saveStatus:', this.saveStatus);
        // console.log('  - currentConversation:', this.$store.state.currentConversation);
        
        // 저장 함수 호출 (await 사용하여 완료까지 대기)
        this.saveLangGraphMessageFromWebSocket().then(() => {
          // console.log('✅ LangGraph 저장 완료');
        }).catch((error) => {
          console.error('❌ LangGraph 저장 실패:', error);
        });
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
          // console.log('✅ 4단계 UI 업데이트 완료 - 최종 답변 표시됨');
        });
      } else if (data.node === 'node_rc_plain_answer' && data.status === 'streaming') {
        // LLM Streaming 응답 처리
        // console.log('LLM Streaming 응답:', data.data);
        
        // 스트리밍 시작 시 답변 생성 상태로 설정
        if (!this.isGeneratingAnswer) {
          this.isGeneratingAnswer = true;
          this.currentStep = 3; // 3단계로 설정
        }
        
        if (data.data && data.data.content) {
          // 스트리밍 응답을 누적
          if (!this.finalAnswer) {
            this.finalAnswer = '';
          }
          this.finalAnswer += data.data.content;
          
          // 실시간으로 UI 업데이트
          this.$nextTick(() => {
            this.$forceUpdate();
          });
        }
      }
    },
    

    
    // 직접 LangGraph 결과 처리 (API 응답에서 - 실시간 기능 고려)
    async processDirectLangGraphResult(apiResult) {
      // console.log('🔄 processDirectLangGraphResult 시작:', apiResult);
      // console.log('🔍 실시간 기능 상태:', {
        isNewConversation: this.isNewConversation,
        isFirstQuestionInSession: this.isFirstQuestionInSession,
        isRestoringConversation: this.isRestoringConversation
      });
      
      // 데이터 구조 상세 로깅
      // console.log('🔍 apiResult.result 구조:', apiResult.result);
      if (apiResult.result && apiResult.result.response) {
        // console.log('🔍 apiResult.result.response:', apiResult.result.response);
        // console.log('🔍 res_id:', apiResult.result.response.res_id);
        // console.log('🔍 db_search_title:', apiResult.result.response.db_search_title);
      }
      // console.log('🔍 candidates_total:', apiResult.result.candidates_total);
      
      try {
        const result = apiResult.result;
        
        // 실시간 기능이 비활성화된 경우 (추가 질문 또는 복원) 즉시 완료 상태로 설정
        if (!this.isFirstQuestionInSession || this.isRestoringConversation) {
          // console.log('🚀 실시간 기능 비활성화 - 즉시 완료 상태로 설정');
          // console.log('🔍 비활성화 이유:', {
            isFirstQuestionInSession: this.isFirstQuestionInSession,
            isRestoringConversation: this.isRestoringConversation
          });
          
          this.currentStep = 4; // 완료 상태
          this.isSearching = false;
          this.isLoading = false;
          
          // 결과 데이터 직접 설정
          if (result && result.response) {
            // console.log('🔍 직접 처리 - result.response 전체 확인:', result.response);
            // console.log('🔍 직접 처리 - analysis_image_url 필드 확인:', result.response.analysis_image_url);
            
            this.finalAnswer = result.response.answer || '답변을 생성할 수 없습니다.';
            this.extractedKeywords = result.response.keyword || null;
            this.extractedDbSearchTitle = result.response.db_search_title || null;
            
            // 이미지 URL 처리 (강화된 검색)
            let imageUrl = null;
            if (result.response.analysis_image_url) {
              imageUrl = result.response.analysis_image_url;
              // console.log('🖼️ 직접 처리 - result.response에서 이미지 URL 발견:', imageUrl);
            } else if (result.analysis_image_url) {
              imageUrl = result.analysis_image_url;
              // console.log('🖼️ 직접 처리 - result에서 이미지 URL 발견:', imageUrl);
            }
            
            if (imageUrl) {
              this.analysisImageUrl = imageUrl;
              this.lastImageUrl = imageUrl; // 디버깅용 저장
              // console.log('🖼️ 직접 처리 - 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
            } else {
              // console.log('⚠️ 직접 처리 - analysis_image_url이 없습니다');
              // console.log('⚠️ result.response 필드들:', Object.keys(result.response || {}));
              // console.log('⚠️ result 필드들:', Object.keys(result || {}));
            }
          }
          
          // console.log('✅ 즉시 완료 처리됨');
          return;
        }
        
        // console.log('🎬 첫 번째 질문 - 실시간 단계별 처리 시작');
        
        // 1단계: 초기화 완료
        this.currentStep = 1;
        this.isSearching = false;
        // console.log('✅ 1단계: 초기화 완료');
        this.$nextTick(() => this.$forceUpdate());
        await new Promise(resolve => setTimeout(resolve, 500)); // 0.5초 지연
        
        // 2단계: 키워드 증강 결과 표시
        if (result && (result.keyword || apiResult.tags)) {
          this.currentStep = 2;
          this.isSearching = true;
          const keywords = result.keyword || (apiResult.tags ? apiResult.tags.split(', ') : []);
          this.augmentedKeywords = Array.isArray(keywords) ? keywords.map((keyword, index) => ({
            id: index + 1,
            text: String(keyword).trim(),
            category: '키워드'
          })) : [];
          this.extractedKeywords = keywords;
          // console.log('✅ 2단계: 키워드 설정 완료:', this.augmentedKeywords);
          this.$nextTick(() => this.$forceUpdate());
          await new Promise(resolve => setTimeout(resolve, 500)); // 0.5초 지연
        }
        
        // 3단계: 검색 결과 표시
        if (result && (result.candidates_total || (result.response && result.response.res_id))) {
          this.currentStep = 3;
          this.isSearching = false;
          this.isGeneratingAnswer = true;
          
          // 검색 결과 데이터 추출 (두 가지 구조 지원)
          let searchData = [];
          let dbSearchTitles = [];
          
          if (result.candidates_total) {
            // 기존 구조 (candidates_total 배열)
            searchData = result.candidates_total || [];
            dbSearchTitles = searchData.map(item => 
              item?.res_payload?.document_name || item?.title || '제목 없음'
            );
          } else if (result.response && result.response.res_id) {
            // 새로운 구조 (response 객체 내부)
            const resIds = result.response.res_id || [];
            const titles = result.response.db_search_title || [];
            
            // res_id와 title을 조합하여 검색 결과 생성
            searchData = resIds.map((id, index) => ({
              res_id: id,
              res_score: 1.0 - (index * 0.1), // 임시 점수
              res_payload: {
                document_name: titles[index] || '제목 없음',
                ppt_summary: '검색 결과',
                ppt_content: '검색된 문서 내용'
              },
              res_relevance: 1.0 - (index * 0.1)
            }));
            
            dbSearchTitles = titles;
          }
          
          this.searchResults = Array.isArray(searchData) ? searchData.slice(0, 5) : []; // 상위 5개만 표시
          this.extractedDbSearchTitle = dbSearchTitles;
          
          // console.log('✅ 3단계: 검색 결과 설정 완료:', this.searchResults);
          // console.log('📄 문서 제목 설정 완료:', this.extractedDbSearchTitle);
          this.$nextTick(() => this.$forceUpdate());
          await new Promise(resolve => setTimeout(resolve, 500)); // 0.5초 지연
        }
        
        // 4단계: 최종 답변 표시 (LangGraph 결과를 그대로 사용)
        if (result && result.response && (result.response.answer || result.response.final_answer)) {
          this.currentStep = 4;
          this.isGeneratingAnswer = false;
          
          // LangGraph의 답변을 그대로 최종 답변으로 사용 (별도 LLM 처리 없음)
          const langGraphAnswer = result.response.answer || result.response.final_answer;
          this.finalAnswer = langGraphAnswer;
          
          // console.log('🎯 LangGraph 답변을 그대로 사용:', langGraphAnswer.substring(0, 100) + '...');
          
          // 백엔드 응답에서 추가 데이터 추출
          if (result.response && result.response.keyword) {
            this.extractedKeywords = result.response.keyword;
          }
          if (result.response && result.response.db_search_title) {
            this.extractedDbSearchTitle = result.response.db_search_title;
          }
          // 이미지 URL 처리 (강화된 검색)
          let imageUrl = null;
          
          // 여러 경로에서 이미지 URL 찾기
          if (result.response && result.response.analysis_image_url) {
            imageUrl = result.response.analysis_image_url;
            // console.log('🖼️ processDirectLangGraphResult - result.response에서 이미지 URL 발견:', imageUrl);
          } else if (result.analysis_image_url) {
            imageUrl = result.analysis_image_url;
            // console.log('🖼️ processDirectLangGraphResult - result에서 이미지 URL 발견:', imageUrl);
          }
          
          if (imageUrl) {
            this.analysisImageUrl = imageUrl;
            this.lastImageUrl = imageUrl; // 디버깅용 저장
            // console.log('🖼️ processDirectLangGraphResult - 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
          } else {
            // console.log('⚠️ processDirectLangGraphResult - 이미지 URL을 찾을 수 없습니다');
            // console.log('⚠️ result 구조:', result);
            // console.log('⚠️ result.response 구조:', result.response);
          }
          
          // console.log('✅ 4단계: LangGraph 최종 답변 설정 완료 (별도 LLM 처리 없음)');
          this.$nextTick(() => this.$forceUpdate());
          
          // 첫 번째 질문 완료 후 상태 변경
          this.isFirstQuestionInSession = false;
          // console.log('🔄 첫 번째 질문 완료 - 상태 변경됨');
          
          // 답변이 완료되면 저장
          await this.saveLangGraphMessage(apiResult);
        }
        
        // 최종 상태 정리
        this.isLoading = false;
        this.isSearching = false;
        this.isGeneratingAnswer = false;
        
        // console.log('🎯 processDirectLangGraphResult 완료 - 모든 단계 처리됨');
        
      } catch (error) {
        console.error('❌ processDirectLangGraphResult 오류:', error);
        // 오류 발생 시에도 상태 정리
        this.isLoading = false;
        this.isSearching = false;
        this.isGeneratingAnswer = false;
      }
    },
    
    // LangGraph 결과 처리
    async processLangGraphResult(result) {
      // 각 단계별 결과를 순차적으로 처리
      if (result.keyword) {
        this.currentStep = 2;
        this.isSearching = true; // 키워드 생성 완료 후 검색 시작
        this.augmentedKeywords = result.keyword.map((keyword, index) => ({
          id: index + 1,
          text: keyword,
          category: '키워드'
        }));
        await this.$nextTick();
      }
      
      if (result.candidates_total) {
        this.currentStep = 3;
        this.isSearching = false; // 검색 완료
        this.searchResults = result.candidates_total.map((item) => ({
          id: item.res_id,
          title: item.res_payload.title,
          snippet: item.res_payload.content,
          source: '검색 결과',
          date: new Date().toISOString().split('T')[0]
        }));
        await this.$nextTick();
      }
      
      if (result.response && result.response.answer) {
        this.currentStep = 4;
        this.finalAnswer = result.response.answer;
        await this.$nextTick();
      }
      
      
      // 분석 결과 이미지 URL 처리
      if (result.response && result.response.analysis_image_url) {
        this.analysisImageUrl = result.response.analysis_image_url;
        // console.log('🖼️ processLangGraphResult - 분석 이미지 URL 설정:', this.analysisImageUrl);
      }
      
      // WebSocket을 통해 실시간으로 진행되므로 여기서는 저장하지 않음
      // LangGraph 완료 시 handleWebSocketMessage에서 저장됨
    },
    
    // 히스토리 항목 삭제
    deleteHistoryItem(historyId) {
      const index = this.rangraphHistory.findIndex(item => item.id === historyId);
      if (index !== -1) {
        this.rangraphHistory.splice(index, 1);
      }
    },
    
    // 토큰 갱신 메서드
    async refreshToken() {
      try {
        // console.log('🔄 토큰 갱신 시작...');
        
        // 현재 토큰으로 갱신 시도
        const response = await fetch('http://localhost:8000/api/auth/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          // console.log('✅ 토큰 갱신 성공');
          
          // 새 토큰을 스토어에 저장
          this.$store.commit('setToken', data.access_token);
          
          return true;
        } else {
          console.error('❌ 토큰 갱신 실패:', response.status);
          throw new Error('토큰 갱신 실패');
        }
      } catch (error) {
        console.error('❌ 토큰 갱신 중 오류:', error);
        throw error;
      }
    },
    
    // WebSocket에서 LangGraph 완료 후 결과 저장
    async saveLangGraphMessageFromWebSocket() {
      try {
        // console.log('🔄 saveLangGraphMessageFromWebSocket 함수 시작');
        
        // 중복 저장 방지 - 이미 저장 중이면 리턴
        if (this.isSavingMessage) {
          // console.log('⚠️ 이미 저장 중입니다. 중복 호출 방지.');
          return;
        }
        
        // 저장 상태 업데이트
        this.isSavingMessage = true;
        this.saveStatus = '';
        
        if (!this.$store.state.currentConversation) {
          // console.log('📝 새 대화 생성 중...');
          await this.$store.dispatch('createConversation');
        }
        
        const conversationId = this.$store.state.currentConversation.id;
        const question = this.originalInput || 'LangGraph 분석 요청';
        const answer = this.finalAnswer || '분석 결과가 없습니다.';
        
        // console.log('📊 WebSocket에서 LangGraph 완료 후 저장할 데이터:', {
          conversationId: conversationId,
          question: question,
          answer: answer,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle,
          currentStep: this.currentStep
        });
        
        // LangGraph 전체 상태를 JSON으로 저장 (복원을 위해)
        const langGraphState = {
          originalInput: this.originalInput,
          augmentedKeywords: this.augmentedKeywords,
          searchResults: this.searchResults.slice(0, 5), // 상위 5개만 저장
          finalAnswer: this.finalAnswer,
          analysisImageUrl: this.analysisImageUrl, // 이미지 URL 저장 추가
          currentStep: this.currentStep,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle
        };
        
        // 키워드 필드에 전체 LangGraph 상태 저장
        const keywordData = JSON.stringify(langGraphState);
        
        // 문서 제목 데이터 처리
        let dbSearchTitleData = this.extractedDbSearchTitle;
        if (Array.isArray(dbSearchTitleData)) {
          dbSearchTitleData = JSON.stringify(dbSearchTitleData);
        }
        
        const user_name = this.$store.state.user?.username || '사용자';
        // console.log('사용자 정보 확인:', {
          user: this.$store.state.user,
          username: this.$store.state.user?.username,
          loginid: this.$store.state.user?.loginid,
          selected_user_name: user_name
        });
        
        const requestBody = { 
          question: question,
          ans: answer,  // ans 필드로 전송
          role: "user",
          q_mode: 'search',  // LangGraph 실행은 항상 검색 모드
          assistant_response: answer,  // 백엔드 호환성을 위해 유지
          keyword: keywordData,
          db_search_title: dbSearchTitleData,
          image: this.analysisImageUrl,  // 이미지 URL 전송
          user_name: user_name,  // username 사용
          skip_llm: true  // LLM 재호출 방지 플래그
        };
        
        // console.log('📤 백엔드로 전송할 요청 데이터:', requestBody);
        // console.log('🌐 API 엔드포인트:', `http://localhost:8000/api/conversations/${conversationId}/messages`);
        // console.log('🔑 인증 토큰:', this.$store.state.token ? '설정됨' : '설정되지 않음');
        // console.log('📊 현재 상태 데이터:');
        // console.log('  - extractedKeywords:', this.extractedKeywords);
        // console.log('  - extractedDbSearchTitle:', this.extractedDbSearchTitle);
        // console.log('  - originalInput:', this.originalInput);
        // console.log('  - finalAnswer:', this.finalAnswer);
        
        // 메시지 생성 API 호출
        // console.log('📡 API 호출 시작...');
        const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify(requestBody)
        });
        
        // console.log('📡 API 응답 상태:', response.status, response.statusText);
        // console.log('📡 API 응답 헤더:', Object.fromEntries(response.headers.entries()));
        
        if (response.ok) {
          const messageData = await response.json();
          // console.log('✅ WebSocket LangGraph 메시지 저장 완료:', messageData);
          
          // 저장된 메시지 ID 확인
          if (messageData.userMessage && messageData.userMessage.id) {
            // console.log('📊 저장된 메시지 ID:', messageData.userMessage.id);
            // console.log('📊 저장된 메시지 데이터:', {
              question: messageData.userMessage.question,
              ans: messageData.userMessage.ans?.substring(0, 100) + '...',
              q_mode: messageData.userMessage.q_mode,
              keyword: messageData.userMessage.keyword ? '저장됨' : '없음',
              db_search_title: messageData.userMessage.db_search_title ? '저장됨' : '없음'
            });
          }
          
          // 저장 성공 로그만 남기고 사용자 메시지는 제거
          // console.log('✅ LangGraph 분석 결과가 성공적으로 저장되었습니다.');
          this.saveStatus = '';
          
          // 대화 목록 새로고침 (조건부 - 새 대화인 경우에만)
          if (!this.$store.state.currentConversation) {
            // console.log('🔄 대화 목록 새로고침 중...');
            await this.$store.dispatch('fetchConversations');
            // console.log('✅ 대화 목록 새로고침 완료');
          }
          
          // 화면에 즉시 반영되도록 강제 업데이트
          this.$nextTick(() => {
            this.$forceUpdate();
            // console.log('🔄 화면 강제 업데이트 완료');
          });
        } else if (response.status === 401) {
          // 인증 실패 시 토큰 갱신 시도
          console.error('❌ 인증 실패 (401). 토큰 갱신 시도...');
          this.saveStatus = '⚠️ 인증이 만료되었습니다. 토큰을 갱신 중...';
          
          try {
            // 토큰 갱신 시도
            await this.refreshToken();
            // console.log('🔄 토큰 갱신 완료, 저장 재시도...');
            
            // 토큰 갱신 후 저장 재시도
            setTimeout(() => {
              this.saveLangGraphMessageFromWebSocket();
            }, 1000);
          } catch (refreshError) {
            console.error('❌ 토큰 갱신 실패:', refreshError);
            this.saveStatus = '⚠️ 인증이 만료되었습니다. 자동으로 SSO 로그인으로 이동합니다...';
            
            // 자동 SSO 로그인으로 리다이렉트
            setTimeout(() => {
              try {
                window.location.replace('http://localhost:8000/api/auth/auth_sh');
              } catch (error) {
                window.location.href = 'http://localhost:8000/api/auth/auth_sh';
              }
            }, 1500);
          }
        } else {
          console.error('❌ WebSocket LangGraph 메시지 저장 실패:', response.status, response.statusText);
          
          // 오류 응답 내용 확인
          let errorMessage = `${response.status} ${response.statusText}`;
          try {
            const errorData = await response.json();
            console.error('📄 API 오류 응답 (JSON):', errorData);
            if (errorData.detail) {
              errorMessage = errorData.detail;
            }
          } catch (e) {
            console.error('📄 API 오류 응답 JSON 파싱 실패:', e);
            // JSON 파싱 실패 시 텍스트로 읽기 시도
            try {
              const errorText = await response.text();
              console.error('📄 API 오류 응답 (텍스트):', errorText);
              if (errorText) {
                errorMessage = errorText;
              }
            } catch (e2) {
              console.error('📄 API 오류 응답 읽기 완전 실패:', e2);
            }
          }
          
          this.saveStatus = `⚠️ 메시지 저장 실패: ${errorMessage}`;
          console.error('💾 저장 실패 상태 설정:', this.saveStatus);
          
          // 저장 실패 시 재시도 로직 제거 - 중복 저장 방지
          // console.log('❌ LangGraph 메시지 저장 실패. 재시도하지 않음.');
        }
      } catch (error) {
        console.error('❌ WebSocket LangGraph 메시지 저장 중 오류:', error);
        console.error('❌ 오류 스택:', error.stack);
        console.error('❌ 저장 시도한 데이터:', {
          conversationId: this.$store.state.currentConversation?.id,
          question: this.originalInput,
          answer: this.finalAnswer?.substring(0, 100) + '...',
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle
        });
        this.saveStatus = `⚠️ 메시지 저장 오류: ${error.message}`;
        
        // 오류 발생 시 재시도 로직 제거 - 중복 저장 방지
        // console.log('❌ LangGraph 메시지 저장 오류. 재시도하지 않음.');
      } finally {
        this.isSavingMessage = false;
        // console.log('🔄 저장 프로세스 완료, isSavingMessage 초기화');
      }
    },
    
    // LangGraph 결과를 메시지로 저장 (기존 함수 - 폴백용)
    async saveLangGraphMessage(result) {
      try {
        if (!this.$store.state.currentConversation) {
          await this.$store.dispatch('createConversation');
        }
        
        const conversationId = this.$store.state.currentConversation.id;
        const question = this.originalInput || 'LangGraph 분석 요청';
        
        // SSE 결과 구조에 맞게 답변 추출
        let answer = '분석 결과가 없습니다.';
        if (result.result && result.result.response) {
          answer = result.result.response.answer || result.result.response.final_answer || '분석 결과가 없습니다.';
        } else if (result.response) {
          answer = result.response.answer || result.response.final_answer || '분석 결과가 없습니다.';
        } else if (this.finalAnswer) {
          answer = this.finalAnswer;
        }
        
        // console.log('saveLangGraphMessage에서 저장할 데이터:', {
          question: question,
          answer: answer,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle,
          resultStructure: result
        });
        
        // 키워드와 문서 제목 데이터 준비
        let keywordData = this.extractedKeywords;
        let dbSearchTitleData = this.extractedDbSearchTitle;
        
        // SSE 결과에서 키워드 추출
        if (!keywordData && result.result && result.result.keyword) {
          keywordData = result.result.keyword;
        }
        
        // SSE 결과에서 문서 제목 추출
        if (!dbSearchTitleData && result.result && result.result.candidates_total) {
          dbSearchTitleData = result.result.candidates_total.map(item => 
            item?.res_payload?.document_name || '제목 없음'
          );
        }
        
        // LangGraph 전체 상태를 JSON으로 저장 (복원을 위해)
        const langGraphState = {
          originalInput: this.originalInput,
          augmentedKeywords: this.augmentedKeywords,
          searchResults: this.searchResults.slice(0, 5),
          finalAnswer: answer,
          analysisImageUrl: this.analysisImageUrl, // 이미지 URL 저장 추가
          currentStep: this.currentStep,
          extractedKeywords: keywordData,
          extractedDbSearchTitle: dbSearchTitleData
        };
        
        // console.log('💾 저장할 LangGraph 상태:', langGraphState);
        
        // 메시지 생성 API 호출
        const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: question,
            q_mode: 'search',  // LangGraph 실행은 항상 검색 모드
            assistant_response: answer,
            skip_llm: true,  // 첫 번째 질문은 LangGraph 답변만 사용, 별도 LLM 처리 안함
            keyword: JSON.stringify(langGraphState), // 전체 상태를 JSON으로 저장
            db_search_title: Array.isArray(dbSearchTitleData) ? JSON.stringify(dbSearchTitleData) : dbSearchTitleData,
            image: this.analysisImageUrl,  // 이미지 URL 전송
            user_name: this.$store.state.user?.username || '사용자'
          })
        });
        
        if (response.ok) {
          const messageData = await response.json();
          // console.log('✅ LangGraph 메시지 저장 완료:', messageData);
          
          // 대화 제목 업데이트 (질문의 첫 50자로)
          if (this.$store.state.currentConversation) {
            const conversationTitle = question.length > 50 ? question.substring(0, 50) + '...' : question;
            
            try {
              const titleUpdateResponse = await fetch(`http://localhost:8000/api/conversations/${conversationId}`, {
                method: 'PUT',
                headers: { 
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({ 
                  title: conversationTitle
                })
              });
              
              if (titleUpdateResponse.ok) {
                // console.log('✅ 대화 제목 업데이트 완료:', conversationTitle);
                // 스토어의 현재 대화 제목도 업데이트
                this.$store.commit('updateConversationTitle', {
                  conversationId: conversationId,
                  title: conversationTitle
                });
              } else {
                console.warn('⚠️ 대화 제목 업데이트 실패:', titleUpdateResponse.status);
              }
            } catch (titleError) {
              console.warn('⚠️ 대화 제목 업데이트 중 오류:', titleError);
            }
          }
          
          // 대화 목록 새로고침
          await this.$store.dispatch('fetchConversations');
          
        } else {
          console.error('❌ LangGraph 메시지 저장 실패:', response.status, response.statusText);
          const errorText = await response.text();
          console.error('❌ 오류 응답 내용:', errorText);
        }
      } catch (error) {
        console.error('LangGraph 메시지 저장 중 오류:', error);
      }
    },
    
    // 폴백 랭그래프 플로우 (오류 발생 시)
    async fallbackRangraphFlow(inputText, error = null) {
      // 오류 정보를 저장하여 답변에 포함
      this.langGraphError = error;
      
      // 오류 발생 시 간단한 메시지만 표시
      this.currentStep = 1;
      this.isSearching = false; // 오류 시 검색 상태 해제
      this.augmentedKeywords = [];
      this.searchResults = [];
      this.finalAnswer = '';
      
      // 오류 메시지 표시
      this.finalAnswer = `⚠️ **시스템 오류**: 
LangGraph API 연결에 실패했습니다.

**오류 정보**:
• API 오류: ${error?.message || 'LangGraph API 호출 실패'}
• API 엔드포인트: /api/llm/langgraph → 404 Not Found

**해결 방안**:
• LangGraph 서버가 실행 중인지 확인하세요
• API 엔드포인트가 올바른지 확인하세요
• WebSocket 서버가 8000번 포트에서 실행 중인지 확인하세요
입력하신 "${inputText}"에 대한 분석을 위해서는 LangGraph 서버가 정상적으로 실행되어야 합니다.`;
      
      // 오류 메시지도 저장
      await this.saveFallbackMessage(inputText, this.finalAnswer);
    },
    
    // 폴백 메시지 저장
    async saveFallbackMessage(question, answer) {
      try {
        if (!this.$store.state.currentConversation) {
          await this.$store.dispatch('createConversation');
        }
        
        const conversationId = this.$store.state.currentConversation.id;
        
        // 메시지 생성 API 호출
        const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: question,
            q_mode: null,  // 오류 메시지는 검색 모드가 아님
            assistant_response: answer,
            keyword: '오류, 시스템 오류',
            db_search_title: 'LangGraph 연결 실패',
            user_name: this.$store.state.user?.username || '사용자'  // username 사용
          })
        });
        
        if (response.ok) {
          const messageData = await response.json();
          // console.log('폴백 메시지 저장 완료:', messageData);
          
          // 대화 목록 새로고침 (조건부 - 새 대화인 경우에만)
          if (!this.$store.state.currentConversation) {
            await this.$store.dispatch('fetchConversations');
          }
        } else {
          console.error('폴백 메시지 저장 실패:', response.status, response.statusText);
        }
      } catch (error) {
        console.error('폴백 메시지 저장 중 오류:', error);
      }
    },
    
    // 랭그래프 컨테이너로 스크롤
    scrollToRangraph() {
      this.$nextTick(() => {
        const rangraphContainer = document.querySelector('.rangraph-container');
        if (rangraphContainer) {
          // 랭그래프 컨테이너가 보이도록 스크롤
          rangraphContainer.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
          });
          
          // 랭그래프 컨테이너 내부는 맨 위로 스크롤
          rangraphContainer.scrollTop = 0;
        }
      });
    },
    
    // 랭그래프 컨테이너를 최하단으로 스크롤
    scrollToRangraphBottom() {
      this.$nextTick(() => {
        const rangraphContainer = document.querySelector('.rangraph-container');
        if (rangraphContainer) {
          // 랭그래프 컨테이너를 최하단으로 스크롤
          rangraphContainer.scrollTop = rangraphContainer.scrollHeight;
          
          // 추가로 전체 채팅 영역도 랭그래프 하단으로 스크롤
          if (this.$refs.chatMessages) {
            const chatContainer = this.$refs.chatMessages;
            chatContainer.scrollTop = chatContainer.scrollHeight;
          }
        }
      });
    },
    
    // 안전한 focus 메서드
    safeFocus() {
      if (this.$refs.inputField && this.$refs.inputField.focus) {
        try {
          this.$refs.inputField.focus();
        } catch (error) {
          console.warn('Focus failed:', error);
        }
      }
    },
    
    // 마크다운을 HTML로 변환하여 포맷팅 처리
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
      // | 개선 항목 | 핵심 내용 | 형태의 표를 HTML 테이블로 변환
      const tableRegex = /(\|[^\n]+\|\n)+/g;
      formattedText = formattedText.replace(tableRegex, (match) => {
        const lines = match.trim().split('\n');
        let tableHtml = '<table class="markdown-table">';
        
        lines.forEach((line, index) => {
          if (line.trim() && !line.match(/^\|[-\s|]+\|$/)) { // 구분선 제외
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
      // - 항목 형태를 <ul><li> 형태로 변환
      formattedText = formattedText.replace(/^- (.*$)/gm, '<li class="markdown-li">$1</li>');
      formattedText = formattedText.replace(/(<li class="markdown-li">.*<\/li>)/s, '<ul class="markdown-ul">$1</ul>');
      
      // 5. 번호 리스트 처리
      // 1. 항목 형태를 <ol><li> 형태로 변환
      formattedText = formattedText.replace(/^\d+\. (.*$)/gm, '<li class="markdown-oli">$1</li>');
      formattedText = formattedText.replace(/(<li class="markdown-oli">.*<\/li>)/s, '<ol class="markdown-ol">$1</ol>');
      
      // 6. 코드 블록 처리
      formattedText = formattedText.replace(/```([\s\S]*?)```/g, '<pre class="markdown-code"><code>$1</code></pre>');
      formattedText = formattedText.replace(/`([^`]+)`/g, '<code class="markdown-inline-code">$1</code>');
      
      // 7. 줄바꿈 처리 (마지막에 처리)
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
    
    adjustTextareaHeight() {
      const textarea = this.$refs.inputField;
      if (!textarea) return;
      
      try {
        // 높이 초기화
        textarea.style.height = 'auto';
        
        // 스크롤 높이에 맞게 높이 조정 (최대 150px까지)
        const newHeight = Math.min(textarea.scrollHeight, 150);
        textarea.style.height = newHeight + 'px';
      } catch (error) {
        console.warn('Textarea height adjustment failed:', error);
      }
    },
    async submitFeedback(messageId, feedback) {
      // 현재 메시지 상태 확인
      const currentMessage = this.currentMessages.find(m => m.id === messageId);
      if (!currentMessage) return;
      
      // Store action 호출
      await this.$store.dispatch('submitFeedback', { messageId, feedback });
    },
    // 스크롤 최적화 - 통합된 쓰로틀링 적용
    scrollToBottom() {
      // 이미 스크롤 요청이 대기 중이면 스킵
      if (this.scrollPending) {
        return;
      }
      
      this.scrollPending = true;
      
      // requestAnimationFrame을 사용한 최적화된 스크롤
      requestAnimationFrame(() => {
        if (this.$refs.chatMessages) {
          const scrollEl = this.$refs.chatMessages;
          scrollEl.scrollTop = scrollEl.scrollHeight;
        }
        this.scrollPending = false;
      });
    },
    // 키워드 분류 함수
    categorizeKeyword(keyword, index) {
      const keywordLower = keyword.toLowerCase();
      
      // 첫 번째 키워드는 항상 '원본'
      if (index === 0) {
        return '원본';
      }
      
      // 키워드 내용에 따른 분류
      if (keywordLower.includes('분석') || keywordLower.includes('analysis') || keywordLower.includes('데이터')) {
        return '분석';
      } else if (keywordLower.includes('개선') || keywordLower.includes('향상') || keywordLower.includes('최적화')) {
        return '개선';
      } else if (keywordLower.includes('전략') || keywordLower.includes('계획') || keywordLower.includes('방안')) {
        return '전략';
      } else if (keywordLower.includes('성과') || keywordLower.includes('결과') || keywordLower.includes('효과')) {
        return '성과';
      } else if (keywordLower.includes('관리') || keywordLower.includes('운영') || keywordLower.includes('시스템')) {
        return '관리';
      } else if (keywordLower.includes('기술') || keywordLower.includes('개발') || keywordLower.includes('솔루션')) {
        return '기술';
      } else if (keywordLower.includes('비즈니스') || keywordLower.includes('사업') || keywordLower.includes('경영')) {
        return '비즈니스';
      } else if (keywordLower.includes('프로세스') || keywordLower.includes('절차') || keywordLower.includes('워크플로우')) {
        return '프로세스';
      } else {
        // 인덱스에 따른 순환 분류
        const categories = ['핵심', '관련', '확장', '부가'];
        return categories[(index - 1) % categories.length];
      }
    },
    
    // 이미지를 새 탭에서 열기
    openImageInNewTab(imageUrl) {
      if (!imageUrl) {
        console.warn('이미지 URL이 없습니다');
        return;
      }
      
      try {
        // 새 탭에서 이미지 열기
        const newTab = window.open(imageUrl, '_blank', 'noopener,noreferrer');
        if (!newTab) {
          // 팝업이 차단된 경우 사용자에게 알림
          alert('팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.');
        } else {
          // console.log('이미지를 새 탭에서 열었습니다:', imageUrl);
        }
      } catch (error) {
        console.error('이미지 열기 실패:', error);
        // 대체 방법: 현재 탭에서 이미지로 이동
        try {
          window.location.href = imageUrl;
        } catch (fallbackError) {
          console.error('대체 방법도 실패:', fallbackError);
        }
      }
    },
    
    copyToClipboard(text) {
      // 현대적인 Clipboard API 사용
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
          // console.log('✅ 텍스트가 클립보드에 복사되었습니다.');
        }).catch((err) => {
          console.error('❌ 클립보드 복사 실패:', err);
          this.fallbackCopyToClipboard(text);
        });
      } else {
        // 폴백 방법 사용
        this.fallbackCopyToClipboard(text);
      }
    },
    
    // 폴백 복사 방법
    fallbackCopyToClipboard(text) {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        textArea.style.opacity = '0';
        textArea.setAttribute('readonly', '');
        document.body.appendChild(textArea);
        
        textArea.focus();
        textArea.select();
        textArea.setSelectionRange(0, 99999); // 모바일 지원
        
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        
        if (successful) {
          // console.log('✅ 폴백 방법으로 텍스트가 클립보드에 복사되었습니다.');
        } else {
          console.error('❌ 폴백 복사 방법도 실패했습니다.');
        }
      } catch (err) {
        console.error('❌ 폴백 복사 중 오류:', err);
      }
    },
    
    // 최적화된 애니메이션 메서드들
    beforeMessageEnter(el) {
      el.style.opacity = 0;
    },
    enterMessage(el, done) {
      el.style.opacity = 1;
      done();
    },
    leaveMessage(el, done) {
      el.style.opacity = 0;
      done();
    },
    
    // 이미지 로딩 에러 핸들링
    handleImageError(event) {
      console.warn('🖼️ 이미지 로딩 실패:', this.analysisImageUrl);
      // 실패한 URL을 lastImageUrl에 저장하고 analysisImageUrl을 초기화
      this.lastImageUrl = this.analysisImageUrl;
      this.analysisImageUrl = '';
      event.target.style.display = 'none';
      // console.log('🖼️ 이미지 로딩 실패로 인해 URL 초기화. 마지막 시도 URL:', this.lastImageUrl);
    },
    
    // 스크롤 위치 안정화를 위한 메서드
    preserveScrollPosition() {
      const scrollEl = this.$refs.chatMessages;
      if (scrollEl) {
        this.lastScrollPosition = scrollEl.scrollTop;
      }
    },
    restoreScrollPosition() {
      const scrollEl = this.$refs.chatMessages;
      if (scrollEl) {
        scrollEl.scrollTop = this.lastScrollPosition;
      }
    }
  },
  beforeUnmount() {
    // WebSocket 연결 해제
            if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) {
          try {
            this.websocket.close();
          } catch (error) {
            console.error('WebSocket 연결 해제 중 오류:', error);
          } finally {
            this.websocket = null;
          }
        }
  },
  mounted() {
    this.$nextTick(() => {
      this.safeFocus();
      this.adjustTextareaHeight(); // 초기 높이 설정
// 텍스트 선택은 CSS에서 처리됨
    });
    
    // 로그인 후 새 대화창 상태 확인
    if (this.$store.state.loginNewConversation) {
      // console.log('🔄 로그인 후 새 대화창 초기화 시작...');
      this.newConversation();
      this.$store.commit('setLoginNewConversation', false); // 플래그 리셋
      // console.log('✅ 로그인 후 새 대화창 초기화 완료');
    }
  },
  updated() {
    // DOM 업데이트 완료 후 스크롤 조정 (통합된 쓰로틀링 사용)
    this.scrollToBottom();
  },
  watch: {

    // 입력 텍스트가 변경될 때마다 textarea 높이 조정
    userInput() {
      this.$nextTick(() => {
        if (this.$refs.inputField) {
          this.adjustTextareaHeight();
        }
      });
    },
    // 스트리밍 메시지가 업데이트될 때마다 스크롤을 아래로 이동 (최적화된 쓰로틀링)
    '$store.state.streamingMessage'() {
      this.scrollToBottom(); // 통합된 쓰로틀링 사용
    },
    // 현재 대화가 변경될 때 스크롤을 맨 아래로 이동하고 랭그래프 복원 (최적화)
    '$store.state.currentConversation'(newConversation) {
      // 메시지 캐시 업데이트
      if (newConversation && newConversation.messages) {
        this.cachedConversationId = newConversation.id;
        this.cachedMessagesLength = newConversation.messages.length;
        this.cachedMessages = newConversation.messages;
      } else {
        this.cachedMessages = null;
        this.cachedConversationId = null;
        this.cachedMessagesLength = 0;
      }
      
      // 기존 대화 선택 시 실시간 기능 비활성화
      if (this.$store.state.conversationRestored) {
        this.isNewConversation = false;
        this.isFirstQuestionInSession = false;
        this.$store.commit('setConversationRestored', false); // 플래그 리셋
      }
      
      // 스크롤과 랭그래프 복원을 비동기로 처리하여 UI 블로킹 방지
      this.$nextTick(() => {
        this.scrollToBottom();
        
        // 랭그래프 복원 로직 (비동기)
        if (newConversation && newConversation.messages) {
          // console.log('currentConversation 변경으로 인한 랭그래프 복원 시작');
          // 비동기 처리로 UI 블로킹 방지
          setTimeout(() => {
            this.restoreRangraphFromConversation(newConversation);
          }, 0);
        }
      });
    },
    // shouldScrollToBottom 상태가 true로 변경될 때 스크롤을 맨 아래로 이동 (최적화)
    '$store.state.shouldScrollToBottom'(newValue) {
      if (newValue) {
        this.scrollToBottom(); // 통합된 쓰로틀링 사용
        this.$store.commit('setShouldScrollToBottom', false);
      }
    },
    // 스트리밍 상태 변경 워처 (최적화된 ResizeObserver)
    '$store.state.isStreaming'(newValue) {
      if (newValue) {
        // 스트리밍 시작 시
        this.$nextTick(() => {
          this.streamingVisible = true;
          
          if (this.$refs.streamingText) {
            // 최적화된 ResizeObserver - 쓰로틀링 통합
            if (!this.observer) {
              this.observer = new ResizeObserver(() => {
                this.scrollToBottom(); // 통합된 쓰로틀링 사용
              });
            }
            this.observer.observe(this.$refs.streamingText);
          }
        });
      } else {
        // 스트리밍 종료 시
        this.streamingVisible = false;
        
        // observer 정리
        if (this.observer) {
          this.observer.disconnect();
          this.observer = null;
        }
        
        // 스트리밍 완료 후 스크롤 조정
        this.scrollToBottom(); // 통합된 쓰로틀링 사용
      }
    },
    // 피드백 업데이트 트리거 감시
    '$store.state._feedbackUpdateTrigger'() {
      // 피드백 변경 시 자연스러운 반응성 보장 (강제 업데이트 제거)
    },
    // 새 대화 생성 트리거 감시
    '$store.state._newConversationTrigger'() {
      // 새 대화 생성 시 랭그래프 상태 초기화
      this.resetRangraphState();
    }

  },
  beforeDestroy() {
    // 메모리 누수 방지를 위한 정리 작업
    if (this.scrollTimeout) {
      clearTimeout(this.scrollTimeout);
      this.scrollTimeout = null;
    }
    
    // WebSocket 연결 정리
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
    
    // Observer 정리
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    
    // console.log('🧹 Home 컴포넌트 정리 완료');
  }
};
</script>

<style>
@import '../assets/styles/home.css';
</style> 
