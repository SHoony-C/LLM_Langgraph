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
                        <div class="result-title">{{ result.res_payload?.document_name || '제목 없음' }}</div>
                        <div class="result-summary">{{ result.res_payload?.vector?.summary_result  || '요약 없음' }}</div>
                        <div class="result-text">{{ result.res_payload?.vector?.text || '내용 없음' }}</div>
                        <div v-if="result.res_payload?.vector?.image_url" class="result-image">
                          <img
                            v-if="result.res_payload?.vector?.image_url"
                            :src="getFullImageUrl(result.res_payload.vector.image_url)"
                            alt="검색 결과 이미지"
                            class="preview-image"
                          />
                        </div>
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
                <div v-if="currentStep >= 4 && analysisImageUrl" class="analysis-image">
                  <label>분석 결과:</label>
                  <div class="image-container">
                    <img :src="analysisImageUrl" alt="랭그래프 4단계 분석 결과" class="analysis-result-image" @error="handleImageError" />
                    <div class="image-caption">
                      <strong>랭그래프 4단계 분석 결과</strong><br>
                      • RAG 검색 기반 분석 이미지
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
                <div class="message-text">
                  {{ message.role === 'user' ? (message.question || '') : (message.ans || '') }}
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
      isGeneratingAnswer: false, // 답변 생성 중 여부
      finalAnswer: '', // 최종 답변
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

    // conversation에서 랭그래프 정보 복원 (성능 최적화 + 실시간 기능 보존)
    async restoreRangraphFromConversation(conversation) {
      // 대화 복원 상태 설정
      this.isRestoringConversation = true;
      this.isNewConversation = false; // 기존 대화 복원
      
      // 캐시 확인 - 동일한 대화에 대해 이미 복원했다면 스킵 (성능 최적화)
      if (this.lastRestoredConversationId === conversation?.id && 
          this.lastRestoredMessageCount === conversation?.messages?.length) {
        console.log('동일한 대화에 대해 이미 복원됨 - 스킵');
        this.isRestoringConversation = false;
        return;
      }
      
      console.log('restoreRangraphFromConversation 호출됨:', {
        conversation: conversation,
        hasMessages: !!conversation?.messages,
        messageCount: conversation?.messages?.length || 0
      });
      
      if (!conversation || !conversation.messages) {
        console.log('대화 또는 메시지가 없어 랭그래프 복원 불가');
        // 새 대화이므로 첫 번째 질문 상태로 초기화
        this.isFirstQuestionInSession = true;
        this.lastRestoredConversationId = null;
        this.lastRestoredMessageCount = 0;
        return;
      }
      
      // 비동기 처리로 UI 블로킹 방지
      await this.$nextTick();
      
      console.log('랭그래프 복원 시작:', {
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
                  console.log('JSON 형태의 LangGraph 상태가 있는 메시지 발견');
                  break;
                }
              } catch (e) {
                // JSON 파싱 실패 시 일반 키워드로 간주
              }
            }
            
            firstQuestionMessage = msg;
            console.log('일반 LangGraph 정보가 있는 메시지 발견');
            break;
          }
        }
      }
      
      // LangGraph 복원할 메시지 결정
      const messageToRestore = searchMessages.length > 0 ? searchMessages[0] : firstQuestionMessage;
      
      if (messageToRestore) {
        // LangGraph 정보가 있는 메시지로 복원
        const firstSearchMessage = messageToRestore;
        
        console.log('첫 번째 검색 메시지 복원:', firstSearchMessage.id);
        
        // 이미 첫 번째 질문이 완료된 대화이므로 상태 변경
        this.isFirstQuestionInSession = false;
        
        // 현재 표시된 LangGraph가 같은 대화의 것인지 확인
        if (this.showRangraph && this.currentStep >= 4 && this.originalInput === firstSearchMessage.question) {
          console.log('동일한 대화의 LangGraph가 이미 표시 중이므로 복원 생략');
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
              console.log('완전한 LangGraph 상태 복원 시작:', langGraphState);
              
              // 모든 LangGraph 상태 복원
              this.originalInput = langGraphState.originalInput;
              this.augmentedKeywords = langGraphState.augmentedKeywords || [];
              this.searchResults = langGraphState.searchResults || [];
              this.finalAnswer = langGraphState.finalAnswer || firstSearchMessage.ans;
              this.analysisImageUrl = langGraphState.analysisImageUrl || firstSearchMessage.image || ''; // 이미지 URL 복원 (메시지에서도 가져오기)
              this.extractedKeywords = langGraphState.extractedKeywords;
              this.extractedDbSearchTitle = langGraphState.extractedDbSearchTitle;
              
              console.log('✅ 완전한 LangGraph 상태 복원 완료');
            } else {
              // 이전 형태의 키워드 데이터인 경우 (하위 호환성)
              console.log('이전 형태의 키워드 데이터 복원');
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
            console.log('단순 문자열 키워드 복원:', firstSearchMessage.keyword);
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
          console.log('메시지에서 직접 이미지 URL 복원:', this.analysisImageUrl);
        }
        
        // 랭그래프 단계별 상태 복원
        this.isSearching = false;
        this.isGeneratingAnswer = false;
        
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
        console.log('LangGraph 정보가 있는 메시지가 없어 랭그래프 복원 불가');
        console.log('대화에 메시지는 있지만 LangGraph 관련 정보(keyword, db_search_title)가 없음');
        
        // 모든 메시지가 q_mode: 'add'인지 확인 (추가 질문만 있는 대화)
        const allAddMessages = conversation.messages.every(msg => msg.q_mode === 'add');
        
        if (allAddMessages && conversation.messages.length > 0) {
          console.log('🔍 추가 질문만 있는 대화입니다. 관련 대화에서 LangGraph 정보를 찾아보겠습니다.');
          
          // 관련 대화 찾기 시도
          try {
            await this.findAndRestoreRelatedLangGraph(conversation.id);
          } catch (error) {
            console.error('관련 대화 찾기 실패:', error);
            console.log('💡 관련 대화를 찾을 수 없어 일반 채팅 모드로 동작합니다.');
            
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
      console.log('관련 대화 찾기 시작:', conversationId);
      
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
        console.log('관련 대화 API 응답:', data);
        
        if (data.related_conversation) {
          console.log('✅ 관련 대화를 찾았습니다:', data.related_conversation.id);
          
          // 관련 대화의 LangGraph 정보로 복원
          await this.restoreRangraphFromConversation(data.related_conversation);
          
          // 추가 질문 모드로 설정 (LangGraph는 표시하되 추가 질문 가능)
          this.isFirstQuestionInSession = false;
          
          console.log('🎯 관련 대화에서 LangGraph 복원 완료');
        } else {
          console.log('❌ 관련 대화를 찾을 수 없습니다:', data.message);
          
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
      console.log('새 대화 생성으로 인한 랭그래프 상태 초기화 완료 - 첫 번째 질문 상태: true');
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
      console.log('🔄 새 대화 UI 초기화 시작...');
      
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
        console.log('🆕 새 대화 생성 중...');
        const newConversation = await this.$store.dispatch('createConversation');
        if (newConversation) {
          console.log('✅ 새 대화 생성 완료:', newConversation.id);
          console.log('📋 사이드바에 새 대화 탭 표시됨');
        } else {
          console.warn('⚠️ 새 대화 생성 실패 - UI 상태만 초기화됨');
        }
      } catch (error) {
        console.error('❌ 새 대화 생성 오류:', error);
        // 오류가 발생해도 UI 상태는 새 대화로 유지
      }
      
      console.log('✅ 새 대화 UI 초기화 완료');
      console.log('🔍 새 대화 상태:', {
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
        // 세션 기반 첫 번째 질문 판별
        const shouldRunRangraph = this.isFirstQuestionInSession;
        
        console.log('📋 대화 상태 확인:', {
          hasCurrentConversation: !!this.$store.state.currentConversation,
          currentConversationId: this.$store.state.currentConversation?.id,
          isFirstQuestionInSession: this.isFirstQuestionInSession,
          shouldRunRangraph
        });
        
        // 첫 번째 질문이면 새 대화 생성, 추가 질문이면 기존 대화 유지
        if (shouldRunRangraph) {
          // 첫 번째 질문: 새 대화 생성 (필요시)
          if (!this.$store.state.currentConversation) {
            console.log('🆕 첫 번째 질문 - 새 대화 생성');
            await this.$store.dispatch('createConversation');
          }
        } else {
          // 추가 질문: 기존 대화 유지 (없으면 오류)
          if (!this.$store.state.currentConversation) {
            console.error('⚠️ 추가 질문인데 현재 대화가 없습니다. 첫 번째 질문으로 처리합니다.');
            this.isFirstQuestionInSession = true;
            await this.$store.dispatch('createConversation');
          } else {
            console.log('✅ 추가 질문 - 기존 대화 유지:', this.$store.state.currentConversation.id);
          }
        }
        
        const currentConversation = this.$store.state.currentConversation;
        const conversationId = currentConversation.id;
        
        console.log('📋 최종 질문 타입 판단:', {
          currentConversationId: conversationId,
          isFirstQuestionInSession: this.isFirstQuestionInSession,
          shouldRunRangraph: shouldRunRangraph ? '🔬 랭그래프' : '💬 추가질문',
          messageText: messageText.substring(0, 50) + '...'
        });
        
        if (shouldRunRangraph) {
          // 첫 번째 질문: LangGraph만 실행 (별도 LLM 처리 없음)
          console.log('🔄 첫 번째 질문 - LangGraph만 실행 (별도 LLM 처리 없음)');
          console.log('🔍 실행 전 상태:', {
            isNewConversation: this.isNewConversation,
            isFirstQuestionInSession: this.isFirstQuestionInSession,
            isRestoringConversation: this.isRestoringConversation
          });
          
          // LangGraph 실행 - 결과를 그대로 최종 답변으로 사용
          await this.executeRangraphFlow(messageText);
          
          console.log('🔍 LangGraph 실행 완료 - 별도 LLM 처리 없이 완료');
          console.log('🔍 실행 후 상태:', {
            isNewConversation: this.isNewConversation,
            isFirstQuestionInSession: this.isFirstQuestionInSession,
            isRestoringConversation: this.isRestoringConversation
          });
        } else {
          // 이후 질문: 컨텍스트 재사용하여 추가 LLM 처리
          console.log('💬 추가 질문 - 컨텍스트 재사용하여 LLM 처리');
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
    

    
