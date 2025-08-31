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
                <div v-else-if="currentStep >= 2 && searchResults && searchResults.length > 0" class="search-results">
                  <label>검색 결과 (상위 5건):</label>
                  <div class="results-list">
                    <div 
                      v-for="(result, index) in searchResults.slice(0, 5)" 
                      :key="result.res_id || index" 
                      class="result-item"
                    >
                      <div class="result-header">
                        <span class="result-number">#{{ index + 1 }}</span>
                        <span class="result-score">유사도: {{ result.res_score?.toFixed(4) || '0.0000' }}</span>
                      </div>
                      <div class="result-content">
                        <div class="result-title">{{ result.res_payload?.ppt_title || '제목 없음' }}</div>
                        <div class="result-summary">{{ result.res_payload?.ppt_summary || '요약 없음' }}</div>
                        <div class="result-text">{{ result.res_payload?.ppt_content || '내용 없음' }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else-if="currentStep >= 2 && !isSearching && searchResults && searchResults.length === 0" class="no-search-results">
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
                <div v-else-if="currentStep >= 3 && finalAnswer" class="final-answer">
                  <label>최종 답변:</label>
                  <div class="answer-content" v-html="formatAnswer(finalAnswer)"></div>
                  

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
                <div v-if="currentStep >= 4 && isGeneratingImage" class="generating-image-indicator">
                  <div class="spinner"></div>
                  <span>이미지 생성 중...</span>
                </div>
                <div v-else-if="currentStep >= 4 && analysisImage" class="analysis-image">
                  <label>분석 결과:</label>
                  <div class="image-container">
                    <img :src="analysisImage" alt="분석 결과" class="analysis-result-image" />
                    <div class="image-caption">
                      <strong>분석 결과</strong><br>
                      • AI 생성 이미지
                    </div>
                  </div>
                </div>
                <div v-else-if="currentStep >= 4 && !isGeneratingImage && !analysisImage" class="no-image-results">
                  <div class="no-image-icon">🖼️</div>
                  <div class="no-image-message">
                    <strong>이미지 생성이 완료되지 않았습니다</strong>
                    <p>현재 단계에서는 이미지 생성이 지원되지 않거나 필요하지 않습니다.</p>
                    <div class="image-info">
                      <strong>이미지 생성 정보:</strong>
                      <ul>
                        <li>텍스트 기반 분석 결과만 제공됩니다</li>
                        <li>이미지가 필요한 경우 별도로 요청해주세요</li>
                        <li>DALL-E API 키가 설정되어 있어야 합니다</li>
                      </ul>
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
                <div class="message-text">
                  {{ message.role === 'user' ? (message.question || '') : (message.ans || '') }}
                </div>
                
                <div v-if="message.role === 'assistant' && message.image" class="message-image">
                  <img :src="message.image" alt="AI generated image" />
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
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  name: 'HomePage',
  data() {
    return {
      userInput: '',
      isLoading: false,
      scrollThrottled: false,
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
      isGeneratingAnswer: false, // 답변 생성 중 여부
      finalAnswer: '', // 최종 답변
      isGeneratingImage: false, // 이미지 생성 중 여부
      analysisImage: '', // 분석 결과 이미지
      websocket: null, // WebSocket 인스턴스
      langGraphError: null, // LangGraph API 오류 정보
              extractedKeywords: null, // 추출된 키워드 정보
      extractedDbSearchTitle: null, // 추출된 문서 검색 타이틀
      rangraphHistory: [], // 랭그래프 히스토리 (추가 질문 모드용)
      
    };
  },
  computed: {
    ...mapState([
      'conversations',
      'currentConversation',
      'isStreaming',
      'streamingMessage'
    ]),
    // 메시지 배열의 반응성을 보장하기 위한 computed 속성
    currentMessages() {
      const currentConversation = this.$store.state.currentConversation;
      
      if (!currentConversation || !currentConversation.messages) {
        return [];
      }
      
      const messages = [...currentConversation.messages]; // 새 배열 생성으로 반응성 보장
      
      return messages;
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
    // conversation에서 랭그래프 정보 복원
    async restoreRangraphFromConversation(conversation) {
      console.log('restoreRangraphFromConversation 호출됨:', {
        conversation: conversation,
        hasMessages: !!conversation?.messages,
        messageCount: conversation?.messages?.length || 0
      });
      
      if (!conversation || !conversation.messages) {
        console.log('대화 또는 메시지가 없어 랭그래프 복원 불가');
        return;
      }
      
      console.log('랭그래프 복원 시작:', {
        conversationId: conversation.id,
        messageCount: conversation.messages.length,
        messages: conversation.messages.map(m => ({ 
          id: m.id, 
          q_mode: m.q_mode, 
          role: m.role,
          question: m.question,
          keyword: m.keyword,
          db_search_title: m.db_search_title,
          ans: m.ans
        }))
      });
      
      // q_mode가 'search'인 메시지를 찾아서 랭그래프 복원
      const searchMessages = conversation.messages.filter(msg => msg.q_mode === 'search');
      
      console.log('검색 메시지 필터링 결과:', {
        totalMessages: conversation.messages.length,
        searchMessagesCount: searchMessages.length,
        searchMessages: searchMessages.map(m => ({
          id: m.id,
          q_mode: m.q_mode,
          question: m.question,
          keyword: m.keyword,
          db_search_title: m.db_search_title
        }))
      });
      
      if (searchMessages.length > 0) {
        // 가장 최근의 검색 메시지를 기준으로 랭그래프 복원
        const latestSearchMessage = searchMessages[searchMessages.length - 1];
        
        console.log('가장 최근 검색 메시지:', latestSearchMessage);
        
        // 랭그래프 상태 설정
        this.showRangraph = true;
        this.currentStep = 4; // 완료된 상태로 복원
        this.originalInput = latestSearchMessage.question;
        this.finalAnswer = latestSearchMessage.ans;
        this.extractedKeywords = latestSearchMessage.keyword;
        this.extractedDbSearchTitle = latestSearchMessage.db_search_title;
        
        // 키워드 복원
        if (latestSearchMessage.keyword) {
          try {
            // keyword가 JSON 형태로 저장되어 있다면 파싱
            const keywordData = JSON.parse(latestSearchMessage.keyword);
            if (Array.isArray(keywordData)) {
              this.augmentedKeywords = keywordData.map((keyword, index) => ({
                id: index + 1,
                text: keyword,
                category: '키워드'
              }));
            } else {
              // 배열이 아닌 경우 단일 키워드로 처리
              this.augmentedKeywords = [{
                id: 1,
                text: latestSearchMessage.keyword,
                category: '키워드'
              }];
            }
          } catch (e) {
            // keyword가 단순 문자열인 경우
            this.augmentedKeywords = [{
              id: 1,
              text: latestSearchMessage.keyword,
              category: '키워드'
            }];
          }
        }
        
        // 검색 결과 복원 (db_search_title에서)
        if (latestSearchMessage.db_search_title) {
          try {
            // db_search_title이 JSON 배열인 경우 파싱
            const titleData = JSON.parse(latestSearchMessage.db_search_title);
            if (Array.isArray(titleData)) {
              this.searchResults = titleData.map((title, index) => ({
                id: `restored-${index}`,
                res_id: `restored-${index}`,
                res_score: 0.8, // 기본 점수
                res_payload: {
                  ppt_title: title,
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
                  ppt_title: latestSearchMessage.db_search_title,
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
                ppt_title: latestSearchMessage.db_search_title,
                ppt_summary: '이전 세션에서 검색된 문서입니다.',
                ppt_content: '이전 세션에서 검색된 내용입니다.'
              }
            }];
          }
        }
        
        // 랭그래프 단계별 상태 복원
        this.isSearching = false;
        this.isGeneratingAnswer = false;
        this.isGeneratingImage = false;
        
        console.log('랭그래프 복원 완료:', {
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
        console.log('검색 메시지가 없어 랭그래프 복원 불가');
        // 검색 메시지가 없으면 랭그래프 숨김
        this.showRangraph = false;
        this.currentStep = 0;
        this.resetRangraph();
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
      console.log('새 대화 생성으로 인한 랭그래프 상태 초기화 완료');
    },
    
    // 랭그래프 초기화
    resetRangraph() {
      this.showRangraph = false;
      this.currentStep = 0;
      this.originalInput = '';
      this.augmentedKeywords = [];
      this.searchResults = [];
      this.finalAnswer = '';
      this.analysisImage = '';
      this.langGraphError = null;
      this.isSearching = false;
      this.isGeneratingAnswer = false;
      this.isGeneratingImage = false;
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      this.extractedResIds = [];
      this.topDocument = null;
      
      // WebSocket 연결도 해제
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
    
    // 랭그래프를 히스토리에 저장
    saveRangraphToHistory() {
      if (this.showRangraph && this.currentStep >= 4) {
        const rangraphData = {
          id: Date.now(),
          originalInput: this.originalInput,
          augmentedKeywords: [...this.augmentedKeywords],
          searchResults: [...this.searchResults],
          finalAnswer: this.finalAnswer,
          analysisImage: this.analysisImage,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle,
          timestamp: new Date().toISOString()
        };
        
        this.rangraphHistory.push(rangraphData);
      }
    },
    
    async newConversation() {
      console.log('🔄 새 대화 UI 초기화 시작...');
      
      // 즉시 UI 상태만 초기화 (백엔드는 실제 메시지 전송 시 생성)
      this.userInput = '';
      this.resetRangraphState();
      this.rangraphHistory = [];
      this.finalAnswer = '';
      this.searchResults = [];
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      
      // 현재 대화를 null로 설정하여 새 대화 상태로 만듦
      this.$store.commit('setCurrentConversation', null);
      
      console.log('✅ 새 대화 UI 초기화 완료 (실제 대화는 첫 메시지 전송 시 생성)');
      
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
        console.log('메시지 전송 차단:', {
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
        // 첫 번째 질문인지 확인 (단순화된 로직)
        const currentConversation = this.$store.state.currentConversation;
        const hasMessages = currentConversation && currentConversation.messages && currentConversation.messages.length > 0;
        
        // 간단한 분기: 메시지가 없으면 첫 번째 질문 (랭그래프), 있으면 추가 질문 (일반 LLM)
        const shouldRunRangraph = !hasMessages;
        
        console.log('📋 질문 타입 판단:', {
          currentConversationId: currentConversation?.id,
          hasMessages,
          messageCount: currentConversation?.messages?.length || 0,
          shouldRunRangraph: shouldRunRangraph ? '🔬 랭그래프' : '💬 일반 LLM',
          messageText: messageText.substring(0, 50) + '...'
        });
        
        if (shouldRunRangraph) {
          // 첫 번째 질문: 오로지 랭그래프만 실행
          console.log('🔄 첫 번째 질문 - 랭그래프 실행');
          await this.executeRangraphFlow(messageText);
        } else {
          // 이후 질문 또는 이미 처리된 질문: 일반 LLM 답변만 실행
          console.log('💬 이후 질문 또는 이미 처리된 질문 - LLM 답변 실행');
          await this.executeSimpleLLMFlow(messageText);
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
    

    
    // 심플한 LLM 답변 플로우 (첫 번째 이후 질문용) - 스트리밍 지원
    async executeSimpleLLMFlow(inputText) {
      try {
        console.log('💬 일반 LLM 스트리밍 답변 실행 시작:', inputText);
        
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
        
        // 스트리밍 시작
        this.$store.commit('setIsStreaming', true);
        this.$store.commit('setStreamingMessage', '');
        
        // 스트리밍 LLM API 호출
        const response = await fetch('http://localhost:8001/api/llm/chat/stream', {
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
        console.log('📡 executeSimpleLLMFlow 스트리밍 응답 처리 시작...');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedMessage = '';
        
        let streamingActive = true;
        let chunkCount = 0;
        while (streamingActive) {
          const { value, done } = await reader.read();
          if (done) {
            console.log('📡 executeSimpleLLMFlow 스트리밍 완료 - done=true');
            streamingActive = false;
            break;
          }
          
          chunkCount++;
          const chunk = decoder.decode(value);
          console.log(`📡 executeSimpleLLMFlow 청크 ${chunkCount} 수신:`, chunk);
          const lines = chunk.split('\n\n');
          console.log(`📡 executeSimpleLLMFlow 청크 ${chunkCount}에서 ${lines.length}개 라인 분리`);
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const content = line.substring(6);
              console.log(`📡 executeSimpleLLMFlow 데이터 라인 처리: "${content}"`);
              
              if (content === '[DONE]') {
                console.log('📡 executeSimpleLLMFlow [DONE] 신호 수신 - 스트리밍 종료');
                streamingActive = false;
                break;
              }
              
              try {
                // JSON 형태의 데이터인지 확인
                const jsonData = JSON.parse(content);
                if (jsonData.text) {
                  console.log('📡 executeSimpleLLMFlow JSON 데이터 처리:', jsonData.text);
                  accumulatedMessage += jsonData.text;
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                }
              } catch (e) {
                // JSON이 아닌 일반 텍스트인 경우
                console.log('📡 executeSimpleLLMFlow 텍스트 데이터 처리:', content);
                accumulatedMessage += content;
                this.$store.commit('updateStreamingMessage', accumulatedMessage);
              }
            } else if (line.trim()) {
              console.log(`📡 executeSimpleLLMFlow 비-데이터 라인 무시: "${line}"`);
            }
          }
        }
        
        console.log(`📡 executeSimpleLLMFlow 스트리밍 최종 완료 - 총 ${chunkCount}개 청크 처리`);
        console.log(`📡 executeSimpleLLMFlow 누적된 메시지 길이: ${accumulatedMessage.length}자`);
        console.log(`📡 executeSimpleLLMFlow 누적된 메시지 내용: "${accumulatedMessage}"`);
        
        console.log('✅ 일반 LLM 스트리밍 답변 생성 완료');
        
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
        console.log('💾 추가 질문 메시지 저장 시작 - q_mode: add');
        await this.saveAdditionalQuestionMessage(inputText, accumulatedMessage || '답변을 생성할 수 없습니다.');
        
        // finalAnswer는 설정하지 않음 (currentMessages에서 표시하므로)
        
        console.log('💾 일반 LLM 답변 저장 및 표시 완료');
        
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
        
        console.log('💬 추가 질문 스트리밍 답변 실행 시작:', inputText);
        
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
        
        // 스트리밍 시작
        this.$store.commit('setIsStreaming', true);
        this.$store.commit('setStreamingMessage', '');
        
        // 스트리밍 LLM API 호출하여 추가 질문에 답변
        const response = await fetch('http://localhost:8001/api/llm/chat/stream', {
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
                if (jsonData.text) {
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
        
        console.log('✅ 추가 질문 스트리밍 답변 생성 완료');
        
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
        console.log('💾 추가 질문 메시지 저장 시작 - q_mode: add');
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
          user_name: this.$store.state.user?.username || '사용자'  // username 사용
        };
        
        console.log('📤 추가 질문 메시지 저장 API 요청 데이터:', requestBody);
        
        const response = await fetch(`http://localhost:8001/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify(requestBody)
        });
        
        if (response.ok) {
          const messageData = await response.json();
          console.log('추가 질문 메시지 저장 완료:', messageData);
          
          // 저장 성공 로그만 남기고 사용자 메시지는 제거
          console.log('✅ 추가 질문 메시지가 성공적으로 저장되었습니다.');
          this.saveStatus = '';
          
          // 대화 목록 새로고침 제거 - 이미 화면에 메시지가 표시되어 있으므로
          // await this.$store.dispatch('fetchConversations');
          
          // 화면에 즉시 반영되도록 강제 업데이트도 제거
          // this.$nextTick(() => {
          //   this.$forceUpdate();
          // });
        } else if (response.status === 401) {
          // 인증 실패 시 토큰 갱신 시도
          console.error('❌ 인증 실패 (401). 토큰 갱신 시도...');
          this.saveStatus = '⚠️ 인증이 만료되었습니다. 토큰을 갱신 중...';
          
          try {
            // 토큰 갱신 시도
            await this.refreshToken();
            console.log('🔄 토큰 갱신 완료, 저장 재시도...');
            
            // 토큰 갱신 후 저장 재시도
            setTimeout(() => {
              this.saveAdditionalQuestionMessage(question, answer);
            }, 1000);
          } catch (refreshError) {
            console.error('❌ 토큰 갱신 실패:', refreshError);
            this.saveStatus = '⚠️ 인증이 만료되었습니다. 다시 로그인해주세요.';
            
            // 로그인 페이지로 리다이렉트
            setTimeout(() => {
              this.$router.push('/login');
            }, 2000);
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
          
          // 저장 실패 시 재시도 로직 추가
          console.log('🔄 2초 후 추가 질문 메시지 저장 재시도 예약...');
          setTimeout(() => {
            console.log('🔄 추가 질문 메시지 저장 재시도 시작...');
            this.saveAdditionalQuestionMessage(question, answer);
          }, 2000);
        }
      } catch (error) {
        console.error('추가 질문 메시지 저장 중 오류:', error);
        this.saveStatus = `⚠️ 메시지 저장 오류: ${error.message}`;
        
        // 오류 발생 시 재시도 로직 추가
        setTimeout(() => {
          console.log('🔄 추가 질문 메시지 저장 재시도...');
          this.saveAdditionalQuestionMessage(question, answer);
        }, 3000);
      } finally {
        this.isSavingMessage = false;
      }
    },
    
    // 랭그래프 플로우 실행
    async executeRangraphFlow(inputText) {
      // 이미 실행 중인 경우 중복 실행 방지
      if (this.isLoading || this.isSearching) {
        console.log('이미 랭그래프가 실행 중입니다. 중복 실행 방지.');
        return;
      }
      
      // 새 대화가 아닌 경우 기존 랭그래프를 히스토리에 저장
      if (this.showRangraph && this.currentStep >= 4) {
        this.saveRangraphToHistory();
      }
      
      // 실행 상태 설정
      this.isLoading = true;
      this.isSearching = true;
      
      // 새로운 랭그래프 시작
      this.showRangraph = true;
      this.currentStep = 0;
      this.augmentedKeywords = [];
      this.searchResults = [];
      this.finalAnswer = '';
      this.analysisImage = '';
      this.langGraphError = null;
      this.originalInput = inputText;
      
      // 추출된 데이터 초기화
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      
      try {
        console.log('LangGraph 실행 시작 - WebSocket 연결 시도...');
        // WebSocket 연결 설정
        await this.setupWebSocket();
        console.log('WebSocket 연결 완료 - LangGraph API 호출 시작...');
        
        // WebSocket 연결 확인
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
          console.error('WebSocket 연결 실패');
          throw new Error('WebSocket 연결을 할 수 없습니다.');
        }
        
        // LangGraph API 호출 (랭그래프 전용)
        const response = await fetch('http://localhost:8001/api/llm/langgraph', {
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
        console.log('LangGraph API 응답:', result);
        
        // WebSocket을 통해 실시간 진행 상황을 받으므로 여기서는 저장하지 않음
        // 각 노드 완료 시 WebSocket 메시지로 처리됨
        
      } catch (error) {
        console.error('LangGraph 실행 오류:', error);
        // 오류 발생 시 기본 플로우로 폴백 (오류 정보 포함)
        await this.fallbackRangraphFlow(inputText, error);
      } finally {
        // 실행 상태 해제 (WebSocket 메시지로 완료 상태가 관리됨)
        this.isLoading = false;
        this.isSearching = false;
      }
    },
    
    // WebSocket 연결 설정
    async setupWebSocket() {
      return new Promise((resolve, reject) => {
        try {
          console.log('WebSocket 연결 시도 중...');
          
          // 기존 WebSocket이 있으면 닫기
          if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) {
            try {
              this.websocket.close();
            } catch (error) {
              console.error('기존 WebSocket 연결 해제 중 오류:', error);
            }
          }
          
          // WebSocket 객체 생성 전에 null로 초기화
          this.websocket = null;
          
          try {
            this.websocket = new WebSocket('ws://localhost:8001/ws/node_end');
          } catch (wsError) {
            console.error('WebSocket 생성 실패:', wsError);
            reject(new Error('WebSocket 연결을 생성할 수 없습니다.'));
            return;
          }
          
          this.websocket.onopen = () => {
            console.log('WebSocket 연결 성공 - localhost:8001/ws/node_end');
            if (this.websocket) {
              console.log('WebSocket 상태:', this.websocket.readyState);
              console.log('WebSocket URL:', this.websocket.url);
              console.log('WebSocket 프로토콜:', this.websocket.protocol);
            }
          
          // 연결 테스트 메시지 전송
          try {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
              this.websocket.send(JSON.stringify({
                type: 'test',
                message: 'WebSocket 연결 테스트'
              }));
              console.log('WebSocket 테스트 메시지 전송됨');
            }
          } catch (error) {
            console.error('WebSocket 테스트 메시지 전송 실패:', error);
          }
          
          resolve(); // 연결 성공 시 Promise 해결
        };
          
          this.websocket.onmessage = (event) => {
            console.log('WebSocket 메시지 수신됨:', event.data);
            try {
              const data = JSON.parse(event.data);
              this.handleWebSocketMessage(data);
            } catch (error) {
              console.error('WebSocket 메시지 파싱 오류:', error);
            }
          };
          
          this.websocket.onerror = (error) => {
            console.error('WebSocket 오류:', error);
            reject(error); // 오류 시 Promise 거부
          };
          
          this.websocket.onclose = (event) => {
            console.log('WebSocket 연결 종료:', event.code, event.reason);
            if (this.websocket) {
              console.log('WebSocket 상태:', this.websocket.readyState);
            }
            this.websocket = null;
          };
          
          // 연결 타임아웃 설정
          setTimeout(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.CONNECTING) {
              console.error('WebSocket 연결 타임아웃');
              this.websocket.close();
              reject(new Error('WebSocket 연결 타임아웃'));
            }
          }, 5000);
          
        } catch (error) {
          console.error('WebSocket 연결 실패:', error);
          reject(error);
        }
      });
    },
    
    // WebSocket 메시지 처리
    handleWebSocketMessage(data) {
      console.log('📡 WebSocket 메시지 수신:', data);
      console.log('📡 메시지 노드:', data.node);
      console.log('📡 메시지 상태:', data.status);
      console.log('📡 메시지 데이터:', data.data);
      console.log('📡 현재 단계:', this.currentStep);
      console.log('📡 현재 키워드 개수:', this.augmentedKeywords?.length || 0);
      
      if (data.node === 'node_init' && data.status === 'completed') {
        this.currentStep = 1;
        this.originalInput = data.data.result;
        this.isSearching = false;
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
        });
      } else if (data.node === 'node_rc_keyword' && data.status === 'completed') {
        console.log('🔑 키워드 노드 완료 - 전체 데이터:', data);
        console.log('🔑 키워드 노드 완료 - result 데이터:', data.data?.result);
        console.log('🔑 키워드 노드 완료 - result 타입:', typeof data.data?.result);
        console.log('🔑 키워드 노드 완료 - result 길이:', data.data?.result?.length);
        
        if (data.data && data.data.result && Array.isArray(data.data.result)) {
        this.currentStep = 2;
        this.isSearching = true; // 키워드 생성 완료 후 검색 시작
        this.augmentedKeywords = data.data.result.map((keyword, index) => ({
          id: index + 1,
          text: keyword,
          category: '키워드'
        }));
        
        // 키워드 추출하여 저장
        this.extractedKeywords = data.data.result;
          console.log('🔑 extractedKeywords 설정됨:', this.extractedKeywords);
          console.log('🔑 augmentedKeywords 설정됨:', this.augmentedKeywords);
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
        });
        } else {
          console.error('🔑 키워드 데이터 형식 오류:', data);
        }
      } else if (data.node === 'node_rc_rag' && data.status === 'completed') {
        console.log('RAG 노드 완료 - 데이터:', data.data.result);
        this.currentStep = 3; // 3단계로 이동 (답변 생성)
        this.isSearching = false; // 검색 완료
        this.isGeneratingAnswer = true; // 답변 생성 시작
        
        // 검색 결과를 올바른 구조로 저장
        this.searchResults = data.data.result;
        console.log('💾 검색 결과 저장:', this.searchResults);
        
        // 검색된 문서 제목 추출하여 저장
        if (data.data.result && data.data.result.length > 0) {
          this.extractedDbSearchTitle = data.data.result.map(item => 
            item.res_payload?.ppt_title || '제목 없음'
          );
          console.log('📄 추출된 문서 제목:', this.extractedDbSearchTitle);
        } else {
          this.extractedDbSearchTitle = '검색 결과 없음';
        }
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
        });
      } else if (data.node === 'node_rc_rerank' && data.status === 'completed') {
        // 재순위 결과 처리
      } else if (data.node === 'node_rc_answer' && data.status === 'completed') {
        console.log('답변 노드 완료 - 데이터:', data.data.result);
        this.currentStep = 4;
        this.isGeneratingAnswer = false; // 답변 생성 완료
        this.finalAnswer = data.data.result.answer;
        console.log('finalAnswer 설정됨:', this.finalAnswer);
        
        // LangGraph 실행 결과에서 필요한 데이터 추출
        if (data.data.result) {
          // 키워드 증강 목록 저장
          if (data.data.result.keyword) {
            this.extractedKeywords = data.data.result.keyword;
            console.log('🔑 추출된 키워드:', this.extractedKeywords);
          }
          
          // 검색된 문서 제목들 저장
          if (data.data.result.db_search_title) {
            this.extractedDbSearchTitle = data.data.result.db_search_title;
            console.log('📄 추출된 문서 제목:', this.extractedDbSearchTitle);
          }
        }
        
        // 이미지가 있으면 표시
        if (data.data.result.image_url) {
          this.analysisImage = data.data.result.image_url;
        }
        
        // LangGraph 완료 후 결과 저장 (즉시 실행)
        console.log('LangGraph 완료, 저장 함수 호출 시작...');
        // 중복 호출 방지 - 이미 아래에서 호출됨
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
        });
      } else if ((data.node === 'node_rc_answer' || data.node === 'node_rc_plain_answer') && data.status === 'completed') {
        this.isGeneratingAnswer = false; // 답변 생성 완료
        console.log(`${data.node} 노드 완료 - 데이터:`, data.data.result);
        this.currentStep = 4;
        this.finalAnswer = data.data.result.answer || data.data.result;
        console.log('finalAnswer 설정됨:', this.finalAnswer);
        
        // LangGraph 실행 결과에서 필요한 데이터 추출
        console.log('🔍 node_rc_answer 완료 - 전체 데이터:', data.data.result);
        
        if (data.data.result) {
          // 키워드 증강 목록 저장
          if (data.data.result.keyword) {
            this.extractedKeywords = data.data.result.keyword;
            console.log('🔑 추출된 키워드:', this.extractedKeywords);
          } else {
            console.log('⚠️ 키워드 데이터가 없습니다');
          }
          
          // 검색된 문서 제목들 저장
          if (data.data.result.db_search_title) {
            this.extractedDbSearchTitle = data.data.result.db_search_title;
            console.log('📄 추출된 문서 제목:', this.extractedDbSearchTitle);
          } else {
            console.log('⚠️ 문서 제목 데이터가 없습니다');
          }
          
          // q_mode 확인
          if (data.data.result.q_mode) {
            console.log('🔍 q_mode:', data.data.result.q_mode);
          } else {
            console.log('⚠️ q_mode 데이터가 없습니다');
          }
        } else {
          console.log('❌ data.data.result가 없습니다');
        }
        
        // LangGraph 완료 후 결과 저장 (즉시 실행)
        console.log('LangGraph 완료, 저장 함수 호출 시작...');
        console.log('저장할 데이터 확인:');
        console.log('  - 질문:', this.originalInput);
        console.log('  - 답변:', this.finalAnswer);
        console.log('  - 키워드:', this.extractedKeywords);
        console.log('  - 문서제목:', this.extractedDbSearchTitle);
        
        // 저장 함수 즉시 호출 (지연 제거)
        console.log('🔄 저장 함수 즉시 호출...');
        console.log('🔄 saveLangGraphMessageFromWebSocket 함수 호출 시작');
        
        // 함수 호출 전 상태 확인
        console.log('📊 저장 함수 호출 전 상태:');
        console.log('  - isSavingMessage:', this.isSavingMessage);
        console.log('  - saveStatus:', this.saveStatus);
        console.log('  - currentConversation:', this.$store.state.currentConversation);
        
        this.saveLangGraphMessageFromWebSocket();
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
        });
      } else if (data.node === 'node_rc_plain_answer' && data.status === 'streaming') {
        // LLM Streaming 응답 처리
        console.log('LLM Streaming 응답:', data.data);
        
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
        await new Promise(resolve => setTimeout(resolve, 1000));
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
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      
      if (result.response && result.response.answer) {
        this.currentStep = 4;
        this.finalAnswer = result.response.answer;
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      
      // 이미지 생성 (선택적) - LangGraph에서 제공하는 이미지가 있으면 표시
      if (result.response && result.response.image_url) {
        this.analysisImage = result.response.image_url;
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
        console.log('🔄 토큰 갱신 시작...');
        
        // 현재 토큰으로 갱신 시도
        const response = await fetch('http://localhost:8001/api/auth/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('✅ 토큰 갱신 성공');
          
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
        console.log('🔄 saveLangGraphMessageFromWebSocket 함수 시작');
        
        // 중복 저장 방지 - 이미 저장 중이면 리턴
        if (this.isSavingMessage) {
          console.log('⚠️ 이미 저장 중입니다. 중복 호출 방지.');
          return;
        }
        
        // 저장 상태 업데이트
        this.isSavingMessage = true;
        this.saveStatus = '';
        
        if (!this.$store.state.currentConversation) {
          console.log('📝 새 대화 생성 중...');
          await this.$store.dispatch('createConversation');
        }
        
        const conversationId = this.$store.state.currentConversation.id;
        const question = this.originalInput || 'LangGraph 분석 요청';
        const answer = this.finalAnswer || '분석 결과가 없습니다.';
        
        console.log('📊 WebSocket에서 LangGraph 완료 후 저장할 데이터:', {
          conversationId: conversationId,
          question: question,
          answer: answer,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle,
          currentStep: this.currentStep
        });
        
        // 키워드 데이터 처리 (리스트인 경우 JSON 문자열로 변환)
        let keywordData = this.extractedKeywords;
        if (Array.isArray(keywordData)) {
          keywordData = JSON.stringify(keywordData);
        }
        
        // 문서 제목 데이터 처리 (리스트인 경우 JSON 문자열로 변환)
        let dbSearchTitleData = this.extractedDbSearchTitle;
        if (Array.isArray(dbSearchTitleData)) {
          dbSearchTitleData = JSON.stringify(dbSearchTitleData);
        }
        
        const user_name = this.$store.state.user?.username || '사용자';
        console.log('사용자 정보 확인:', {
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
          user_name: user_name,  // username 사용
          skip_llm: true  // LLM 재호출 방지 플래그
        };
        
        console.log('📤 백엔드로 전송할 요청 데이터:', requestBody);
        console.log('🌐 API 엔드포인트:', `http://localhost:8001/api/conversations/${conversationId}/messages`);
        console.log('🔑 인증 토큰:', this.$store.state.token ? '설정됨' : '설정되지 않음');
        
        console.log('📤 백엔드로 전송할 요청 데이터:', requestBody);
        console.log('🌐 API 엔드포인트:', `http://localhost:8001/api/conversations/${conversationId}/messages`);
        console.log('🔑 인증 토큰:', this.$store.state.token ? '설정됨' : '설정되지 않음');
        
        console.log('📤 백엔드로 전송할 요청 데이터:', requestBody);
        console.log('🌐 API 엔드포인트:', `http://localhost:8001/api/conversations/${conversationId}/messages`);
        console.log('🔑 인증 토큰:', this.$store.state.token ? '설정됨' : '설정되지 않음');
        console.log('📊 현재 상태 데이터:');
        console.log('  - extractedKeywords:', this.extractedKeywords);
        console.log('  - extractedDbSearchTitle:', this.extractedDbSearchTitle);
        console.log('  - originalInput:', this.originalInput);
        console.log('  - finalAnswer:', this.finalAnswer);
        
        // 메시지 생성 API 호출
        console.log('📡 API 호출 시작...');
        const response = await fetch(`http://localhost:8001/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify(requestBody)
        });
        
        console.log('📡 API 응답 상태:', response.status, response.statusText);
        console.log('📡 API 응답 헤더:', Object.fromEntries(response.headers.entries()));
        
        if (response.ok) {
          const messageData = await response.json();
          console.log('✅ WebSocket LangGraph 메시지 저장 완료:', messageData);
          
          // 저장 성공 로그만 남기고 사용자 메시지는 제거
          console.log('✅ LangGraph 분석 결과가 성공적으로 저장되었습니다.');
          this.saveStatus = '';
          
          // 대화 목록 새로고침
          console.log('🔄 대화 목록 새로고침 중...');
          await this.$store.dispatch('fetchConversations');
          console.log('✅ 대화 목록 새로고침 완료');
          
          // 화면에 즉시 반영되도록 강제 업데이트
          this.$nextTick(() => {
            this.$forceUpdate();
            console.log('🔄 화면 강제 업데이트 완료');
          });
        } else if (response.status === 401) {
          // 인증 실패 시 토큰 갱신 시도
          console.error('❌ 인증 실패 (401). 토큰 갱신 시도...');
          this.saveStatus = '⚠️ 인증이 만료되었습니다. 토큰을 갱신 중...';
          
          try {
            // 토큰 갱신 시도
            await this.refreshToken();
            console.log('🔄 토큰 갱신 완료, 저장 재시도...');
            
            // 토큰 갱신 후 저장 재시도
            setTimeout(() => {
              this.saveLangGraphMessageFromWebSocket();
            }, 1000);
          } catch (refreshError) {
            console.error('❌ 토큰 갱신 실패:', refreshError);
            this.saveStatus = '⚠️ 인증이 만료되었습니다. 다시 로그인해주세요.';
            
            // 로그인 페이지로 리다이렉트
            setTimeout(() => {
              this.$router.push('/login');
            }, 2000);
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
          console.log('❌ LangGraph 메시지 저장 실패. 재시도하지 않음.');
        }
      } catch (error) {
        console.error('WebSocket LangGraph 메시지 저장 중 오류:', error);
        this.saveStatus = `⚠️ 메시지 저장 오류: ${error.message}`;
        
        // 오류 발생 시 재시도 로직 제거 - 중복 저장 방지
        console.log('❌ LangGraph 메시지 저장 오류. 재시도하지 않음.');
      } finally {
        this.isSavingMessage = false;
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
        const answer = result.response?.answer || '분석 결과가 없습니다.';
        
        console.log('saveLangGraphMessage에서 저장할 데이터:', {
          question: question,
          answer: answer,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle
        });
        
        // 메시지 생성 API 호출
        const response = await fetch(`http://localhost:8001/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: question,
            q_mode: 'search',  // LangGraph 실행은 항상 검색 모드
            assistant_response: answer,
            keyword: this.extractedKeywords,
            db_search_title: this.extractedDbSearchTitle,
            user_name: this.$store.state.user?.username || '사용자'  // username 사용
          })
        });
        
        if (response.ok) {
          const messageData = await response.json();
          console.log('LangGraph 메시지 저장 완료:', messageData);
          
          // 대화 목록 새로고침
          await this.$store.dispatch('fetchConversations');
        } else {
          console.error('LangGraph 메시지 저장 실패:', response.status, response.statusText);
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
      this.analysisImage = '';
      
      // 오류 메시지 표시
      this.finalAnswer = `⚠️ **시스템 오류**: 
LangGraph API 연결에 실패했습니다.

**오류 정보**:
• API 오류: ${error?.message || 'LangGraph API 호출 실패'}
• API 엔드포인트: /api/llm/langgraph → 404 Not Found
• WebSocket 연결: ws://localhost:8001/ws/node_end → 연결 실패

**해결 방안**:
• LangGraph 서버가 실행 중인지 확인하세요
• API 엔드포인트가 올바른지 확인하세요
• WebSocket 서버가 8001번 포트에서 실행 중인지 확인하세요

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
        const response = await fetch(`http://localhost:8001/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: question,
            q_mode: 'search',  // 오류 메시지도 검색 모드로 저장
            assistant_response: answer,
            keyword: '오류, 시스템 오류',
            db_search_title: 'LangGraph 연결 실패',
            user_name: this.$store.state.user?.username || '사용자'  // username 사용
          })
        });
        
        if (response.ok) {
          const messageData = await response.json();
          console.log('폴백 메시지 저장 완료:', messageData);
          
          // 대화 목록 새로고침
          await this.$store.dispatch('fetchConversations');
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
    
    // 마크다운을 HTML로 변환하여 볼드 처리
    formatAnswer(text) {
      if (!text) return '';
      
      // **텍스트** 형태를 <strong>텍스트</strong>로 변환
      let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      
      // 줄바꿈을 <br> 태그로 변환
      formattedText = formattedText.replace(/\n/g, '<br>');
      
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
    scrollToBottom() {
      if (this.$refs.chatMessages) {
        const scrollEl = this.$refs.chatMessages;
        
        // 부드러운 스크롤링을 위해 requestAnimationFrame 사용
        requestAnimationFrame(() => {
        scrollEl.scrollTop = scrollEl.scrollHeight;
        });
      }
    },
    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        // Text copied to clipboard
      }).catch(() => {
        // Error copying text
      });
    },
    // 새로운 애니메이션 메서드들
    beforeMessageEnter(el) {
      // 시작 위치를 현재 위치로 설정하고 투명도만 조절
      el.style.opacity = 0;
      el.style.position = 'relative';
      el.style.top = '0';
      el.style.left = '0';
      el.style.transform = 'translateY(0)';
    },
    enterMessage(el, done) {
      // 애니메이션 시작 전 높이 기록 (점프 방지용)
      const height = el.offsetHeight;
      
      // 높이 보존을 위한 스타일 설정
      el.style.minHeight = `${height}px`;
      el.style.transform = 'translateY(0)';
      
      // 투명도만 변경하고 바로 완료 (애니메이션 없음) 
      el.style.opacity = 1;
      done();
    },
    leaveMessage(el, done) {
      // 나가는 요소의 높이를 기록해 놓음 (점프 방지용)
      const height = el.offsetHeight;
      this.lastMessageHeight = Math.max(height, this.lastMessageHeight);
      
      // 즉시 제거 (애니메이션 없음)
      el.style.opacity = 0;
      done();
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
    },
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
    });
  },
  updated() {
    // 스크롤을 바로 조정하지 않고 DOM 업데이트 완료 후 조정
    this.$nextTick(() => {
      this.scrollToBottom();
    });
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
    // 스트리밍 메시지가 업데이트될 때마다 스크롤을 아래로 이동
    '$store.state.streamingMessage'() {
      if (!this.scrollThrottled) {
        this.scrollThrottled = true;
        requestAnimationFrame(() => {
        this.scrollToBottom();
          setTimeout(() => {
            this.scrollThrottled = false;
          }, 100);
      });
      }
    },
    // 현재 대화가 변경될 때 스크롤을 맨 아래로 이동하고 랭그래프 복원
    '$store.state.currentConversation'() {
      this.$nextTick(() => {
        this.scrollToBottom();
        
        setTimeout(() => {
          this.scrollToBottom();
        }, 300);
      });
      
      // 랭그래프 복원 로직 추가
      const currentConversation = this.$store.state.currentConversation;
      if (currentConversation && currentConversation.messages) {
        console.log('currentConversation 변경으로 인한 랭그래프 복원 시작');
        this.restoreRangraphFromConversation(currentConversation);
      }
    },
    // shouldScrollToBottom 상태가 true로 변경될 때 스크롤을 맨 아래로 이동
    '$store.state.shouldScrollToBottom'(newValue) {
      if (newValue) {
        this.$nextTick(() => {
          this.scrollToBottom();
          this.$store.commit('setShouldScrollToBottom', false);
        });
      }
    },
    // Add a new watcher to observe the streaming element's size
    '$store.state.isStreaming'(newValue) {
      if (newValue) {
        // 스트리밍 시작 시 타이머 설정
        this.$nextTick(() => {
          // 잠시 후 스트리밍 메시지 표시 (깜빡임 방지)
          setTimeout(() => {
            this.streamingVisible = true;
          }, 50);
          
          if (this.$refs.streamingText) {
            // Observer setup to track streaming message size changes
            const resizeObserver = new ResizeObserver(() => {
              this.scrollToBottom();
            });
            
            resizeObserver.observe(this.$refs.streamingText);
            this.observer = resizeObserver;
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
        this.$nextTick(() => {
          this.scrollToBottom();
          
          // 약간의 지연 후 한번 더 스크롤 조정
          setTimeout(() => {
            this.scrollToBottom();
          }, 100);
        });
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
    },

  }
};
</script>

<style>
@import '../assets/styles/home.css';
</style> 
