<template>
  <div class="home">
        <div class="chat-container">
            <!-- 채팅 메시지 영역 -->
      <div class="chat-messages" ref="chatMessages">
        <!-- 랭그래프 컨테이너 -->
        <LanggraphContainer
          :show-langgraph="langgraph.showLanggraph.value"
          :current-step="langgraph.currentStep.value"
          :original-input="langgraph.originalInput.value"
          :augmented-keywords="langgraph.augmentedKeywords.value"
          :is-searching="langgraph.isSearching.value"
          :search-results="langgraph.searchResults.value"
          :searched-documents="langgraph.searchedDocuments.value"
          :has-search-completed="langgraph.hasSearchCompleted.value"
          :is-generating-answer="langgraph.isGeneratingAnswer.value"
          :final-answer="langgraph.finalAnswer.value"
          :streaming-answer="langgraph.streamingAnswer.value"
          :is-streaming-answer="langgraph.isStreamingAnswer.value"
          :analysis-image-url="langgraph.analysisImageUrl.value"
          :image-load-failed="langgraph.imageLoadFailed.value"
          :failed-image-url="langgraph.failedImageUrl.value"
          :last-image-url="langgraph.lastImageUrl.value"
          @open-search-result="openSearchResultPopup"
          @open-image-in-new-tab="openImageInNewTab"
        />
        
        <!-- 메시지 리스트 -->
        <div v-if="!$store.state.currentConversation" class="empty-state">
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
        
        <MessageList
          :current-messages="currentMessages"
          :is-streaming="$store.state.isStreaming"
          :streaming-message="$store.state.streamingMessage"
          :streaming-visible="sse.streamingVisible.value"
          :last-message-height="scroll.lastMessageHeight.value"
          @submit-feedback="submitFeedback"
        />
            </div>
            
      <!-- 채팅 입력 -->
      <ChatInput
        :is-loading="messages.isLoading.value"
        :is-streaming="$store.state.isStreaming"
        @send-message="sendChatMessage"
        @input-change="handleInputChange"
        ref="chatInput"
      />

    <!-- 검색 결과 상세 팝업 -->
    <SearchResultPopup 
      :show="showSearchResultPopup"
      :result="selectedSearchResult"
      @close="closeSearchResultPopup"
    />
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';
import SearchResultPopup from '@/components/SearchResultPopup.vue';
import LanggraphContainer from '@/components/LanggraphContainer.vue';
import MessageList from '@/components/MessageList.vue';
import ChatInput from '@/components/ChatInput.vue';
import { useLanggraph } from '@/composables/useLanggraph.js';
import { useMessages } from '@/composables/useMessages.js';
import { useSSE } from '@/composables/useSSE.js';
import { useScroll } from '@/composables/useScroll.js';
// judgeQuestionType은 더 이상 사용하지 않음 - isFollowupQuestion 플래그 사용
import { 
  executeLanggraphFlow
} from '@/utils/langGraphExecutor.js';
import { 
  executeAdditionalQuestionFlowWrapper
} from '@/utils/additionalQuestionHandler.js';
import {
  restoreLanggraphFromConversation,
  // restoreLanggraphFromCurrentMeages
} from '@/utils/conversationRestorer.js';
import {
  saveLangGraphMessage
} from '@/utils/messageStorage.js';

export default {
  name: 'HomePage',
  components: {
    SearchResultPopup,
    LanggraphContainer,
    MessageList,
    ChatInput
  },
  setup() {
    // Composables 사용
    const langgraph = useLanggraph();
    const messages = useMessages();
    const sse = useSSE();
    const scroll = useScroll();
    
    return {
      langgraph,
      messages,
      sse,
      scroll
    };
  },
  data() {
    return {
      showSearchResultPopup: false, // 검색 결과 팝업 표시 여부
      selectedSearchResult: null, // 선택된 검색 결과
      isNewConversation: false, // 새 대화 상태 플래그 (초기값: false, 새로고침 시 복원 가능)
      isPopupChanging: false, // popup 상태 변경 중 플래그 (scrollToBottom 방지)
    };
  },
  computed: {
    ...mapState([
      'conversations',
      'currentConversation',
      'isStreaming',
      'streamingMessage'
    ]),
    // 메시지 배열의 반응성을 보장하기 위한 computed 속성 (캐시 제거)
    currentMessages() {
      const currentConversation = this.$store.state.currentConversation;
      
      if (!currentConversation || !currentConversation.messages) {
        return [];
      }
      
      return currentConversation.messages;
    },
    // 랭그래프 진행률 계산
    progressPercentage() {
      return (this.langgraph.currentStep.value / 4) * 100;
    }
  },
  methods: {
    // LangGraph 메시지 저장 메서드
    async saveLangGraphMessage(result) {
      await saveLangGraphMessage(result, this);
    },

    // 랭그래프 컨테이너로 스크롤
    scrollToLanggraph() {
      this.scroll?.scrollToLanggraph();
    },

    // 메시지 전송
    async sendChatMessage() {
      if (!this.$refs.chatInput.userInput.trim() || this.messages.isLoading.value || this.$store.state.isStreaming) {
        return;
      }
      
      const messageText = this.$refs.chatInput.userInput.trim();
      this.$refs.chatInput.clearInput();
      
      // 질문 타입 판단
      const conversationId = this.$store.state.currentConversation?.id || null;
      // isFollowupQuestion 플래그 기반으로 처리
      try {
        if (this.langgraph.isFollowupQuestion.value) {
          // console.log('💬 추가 질문 - 일반 LLM 실행');
          // console.log('🔍 [DEBUG] 추가질문 실행 전 UI 상태:');
          // console.log('  - showLanggraph:', this.langgraph.showLanggraph.value);
          // console.log('  - currentStep:', this.langgraph.currentStep.value);
          // console.log('  - isFollowupQuestion:', this.langgraph.isFollowupQuestion.value);
          
          await executeAdditionalQuestionFlowWrapper(messageText, conversationId, this);
          
          // console.log('🔍 [DEBUG] 추가질문 실행 후 UI 상태:');
          // console.log('  - showLanggraph:', this.langgraph.showLanggraph.value);
          // console.log('  - currentStep:', this.langgraph.currentStep.value);
          // console.log('  - isFollowupQuestion:', this.langgraph.isFollowupQuestion.value);
        } else {
          // console.log('🔬 최초 질문 - LangGraph 실행');
          await executeLanggraphFlow(messageText, this);
        }
        
        // console.log('🔍 [DEBUG] $nextTick 호출 전 UI 상태:');
        // console.log('  - showLanggraph:', this.langgraph.showLanggraph.value);
        // console.log('  - currentStep:', this.langgraph.currentStep.value);
        
        this.$nextTick(() => {
          // console.log('  - showLanggraph:', this.langgraph.showLanggraph.value);
          // console.log('  - currentStep:', this.langgraph.currentStep.value);
          
          this.scroll?.scrollToBottom(this.$refs.chatMessages);
          this.scroll?.safeFocus(this.$refs.chatInput?.$refs?.inputField);
        });
          } catch (error) {
        console.error('Error sending message:', error);
        this.messages.isLoading.value = false;
        this.langgraph.isSearching.value = false;
      }
    },

    // 피드백 처리
    async submitFeedback(messageId, feedback) {
      const currentMessage = this.currentMessages.find(m => m.id === messageId);
      if (!currentMessage) {
        console.warn('⚠️ 피드백 처리 실패: 메시지를 찾을 수 없음', messageId);
        return;
      }
      
      console.log('👍 피드백 처리 시작:', { messageId, feedback, currentFeedback: currentMessage.feedback });
      
      try {
        await this.$store.dispatch('submitFeedback', { messageId, feedback });
        console.log('✅ 피드백 처리 완료');
      } catch (error) {
        console.error('❌ 피드백 처리 실패:', error);
      }
    },

    // 입력 변경 처리 (텍스트 영역 높이 조정)
    handleInputChange() {
      // ChatInput 컴포넌트의 텍스트 영역 높이 조정
      if (this.$refs.chatInput && this.$refs.chatInput.adjustTextareaHeight) {
        this.$refs.chatInput.adjustTextareaHeight();
      }
    },

    // 검색 결과 팝업 열기
    openSearchResultPopup(result) {
      this.isPopupChanging = true;  // 팝업 상태 변경 중 플래그 설정
      this.selectedSearchResult = result;
      this.showSearchResultPopup = true;
      // console.log('🔍 검색 결과 팝업 열기:', result.title);
      // 팝업 열기 완료 후 플래그 해제
      this.$nextTick(() => {
        setTimeout(() => {
          this.isPopupChanging = false;
        }, 100);
      });
    },

    // 검색 결과 팝업 닫기
    closeSearchResultPopup() {
      this.isPopupChanging = true;  // 팝업 상태 변경 중 플래그 설정
      this.showSearchResultPopup = false;
      this.selectedSearchResult = null;
      // 팝업 닫기 완료 후 플래그 해제
      this.$nextTick(() => {
        setTimeout(() => {
          this.isPopupChanging = false;
        }, 100);
      });
    },
    
    async newConversation() {
      // 중복 실행 방지
      if (this.isCreatingConversation) {
        console.log('[HOME] 새 대화 생성 중 - 중복 실행 방지');
        return;
      }
      
      this.isCreatingConversation = true;
      // console.log('🔄 새 대화 UI 초기화 시작...');
      
      // 새 대화 상태 설정 (실시간 기능 활성화) - 먼저 설정
      this.isNewConversation = true;
      this.isFirstQuestionInSession = true;
      this.isRestoringConversation = false;
      
      // 새 대화는 최초 질문이므로 isFollowupQuestion을 false로 설정
      this.langgraph.isFollowupQuestion.value = false;
      console.log('✅ 새 대화 생성 - isFollowupQuestion을 false로 설정');
      
      // 즉시 UI 상태만 초기화 (백엔드는 실제 메시지 전송 시 생성)
      this.userInput = '';
      this.langgraph.resetLanggraphState();
      this.finalAnswer = '';
      this.searchResults = [];
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      
      // 캐시 초기화
      this.lastRestoredConversationId = null;
      this.lastRestoredMessageCount = 0;
      
      // 랭그래프 캐시 초기화 (다른 대화로 전환 시 복원 가능하도록)
      this.langgraph.lastRestoredConversationId.value = null;
      
      // 즉시 DB에 새 대화 생성 (ChatGPT 방식)
      try {
        const newConversation = await this.$store.dispatch('createConversation');
        if (newConversation) {
          // 현재 대화로 설정하여 UI에 활성화
          this.$store.commit('setCurrentConversation', newConversation);
          console.log('✅ 새 대화 생성 완료:', newConversation.id);
        } else {
          console.error('❌ 새 대화 생성 실패');
          alert('새 대화 생성에 실패했습니다. 다시 시도해주세요.');
        }
      } catch (error) {
        console.error('❌ 새 대화 생성 오류:', error);
        alert('새 대화 생성 중 오류가 발생했습니다.');
      }
      
      // 플래그 해제
      this.isCreatingConversation = false;
      
      // console.log('✅ 새 대화 UI 초기화 완료');
      
      // 새 대화 생성 완료 후 플래그 리셋 (watcher 실행 후에 리셋)
      setTimeout(() => {
        this.isNewConversation = false;
        this.scroll?.scrollToBottom(this.$refs.chatMessages);
        this.scroll?.safeFocus(this.$refs.chatInput?.$refs?.inputField);
      }, 100); // watcher가 실행된 후에 리셋
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
    
    // 스크롤 위치 안정화를 위한 메서드
    preserveScrollPosition() {
      const scrollEl = this.$refs.chatMessages;
      if (scrollEl) {
        this.lastScrollPosition = scrollEl.scrollTop;
      }
    },
  },
  beforeUnmount() {
    // WebSocket 사용하지 않음
  },
  mounted() {
    this.$nextTick(() => {
      this.scroll?.safeFocus(this.$refs.chatInput?.$refs?.inputField);
      this.scroll?.adjustTextareaHeight(this.$refs.chatInput?.$refs?.inputField); // 초기 높이 설정
// 텍스트 선택은 CSS에서 처리됨
    });
    
    // 로그인 후 새 대화창 상태 확인
    if (this.$store.state.loginNewConversation) {
      // console.log('🔄 로그인 후 새 대화창 초기화 시작...');
      this.newConversation();
      this.$store.commit('setLoginNewConversation', false); // 플래그 리셋
      // console.log('✅ 로그인 후 새 대화창 초기화 완료');
    } 
    // watcher에서 자동으로 복원하므로 mounted에서는 처리하지 않음
    // (중복 API 호출 방지)
  },
  updated() {
    // popup 상태 변경 중에는 스크롤하지 않음
    if (this.isPopupChanging) {
      return;
    }
    // DOM 업데이트 완료 후 스크롤 조정 (통합된 쓰로틀링 사용)
    this.scroll?.scrollToBottom(this.$refs.chatMessages);
  },
  watch: {
    // 팝업 상태 변경 시 스크롤 방지
    showSearchResultPopup() {
      // 팝업 열기/닫기 시 스크롤 실행하지 않음
    },

    // ChatInput의 userInput 변경 감지 (ChatInput 컴포넌트 내부에서 처리됨)
    // 스트리밍 메시지가 업데이트될 때마다 스크롤을 아래로 이동 (최적화된 쓰로틀링)
    '$store.state.streamingMessage'() {
      // 스크롤 실행 주기 완화 - 0.5초마다만 실행
      if (this.scroll && !this.scroll.scrollThrottled.value) {
        this.scroll.scrollThrottled.value = true;
        this.scroll.scrollToBottom(this.$refs.chatMessages);
        setTimeout(() => {
          if (this.scroll) {
            this.scroll.scrollThrottled.value = false;
          }
        }, 500);
      }
    },
    // 현재 대화가 변경될 때 스크롤을 맨 아래로 이동하고 랭그래프 복원 (캐시 제거)
    '$store.state.currentConversation'(newConversation) {
      // 랭그래프 완료 직후에는 아무것도 하지 않음 (상태 유지)
      if (this.langgraph.isLanggraphJustCompleted.value) {
        console.log('✅ 랭그래프 완료 직후 - watcher 완전 스킵하여 상태 유지');
        return; // 스크롤도 하지 않음
      }
      
      // 기존 대화 선택 시 실시간 기능 비활성화
      if (this.$store.state.conversationRestored) {
        this.isNewConversation = false;
        this.isFirstQuestionInSession = false;
        this.$store.commit('setConversationRestored', false); // 플래그 리셋
      }
      
      // 새 대화 생성 중이면 복원하지 않음
      if (this.isNewConversation) {
        // console.log('📝 새 대화 생성 중 - 랭그래프 복원 스킵');
        this.$nextTick(() => {
          this.scroll?.scrollToBottom(this.$refs.chatMessages);
        });
        return;
      }
      
      // 스크롤과 랭그래프 복원을 비동기로 처리하여 UI 블로킹 방지
      this.$nextTick(() => {
        this.scroll?.scrollToBottom(this.$refs.chatMessages);
        
        // 랭그래프 복원 로직 (비동기) - 새 대화가 아닌 경우에만 복원
        if (newConversation) {
          // 메시지가 있는 경우 바로 복원
          if (newConversation.messages && newConversation.messages.length > 0) {
            console.log('🔄 기존 대화 선택 - 랭그래프 복원 시작 (메시지 있음)');
            // 비동기 처리로 UI 블로킹 방지
            setTimeout(async () => {
              await restoreLanggraphFromConversation(newConversation, this);
              // 복원 후 UI 강제 업데이트
              this.$forceUpdate();
              this.$nextTick(() => {
                this.scroll?.scrollToBottom(this.$refs.chatMessages);
              });
            }, 0);
          } else {
            // 메시지가 없는 경우 (새로고침 등) API로 가져와서 복원
            console.log('🔄 메시지 없음 - API로 메시지 가져오기:', newConversation.id);
            setTimeout(async () => {
              try {
                const response = await fetch(`http://localhost:8000/api/conversations/${newConversation.id}/messages`, {
                  method: 'GET',
                  headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                  },
                  credentials: 'include'
                });
                
                if (response.ok) {
                  const data = await response.json();
                  console.log('✅ 메시지 가져오기 성공:', data.messages?.length || 0, '개');
                  
                  // 메시지를 포함한 대화 객체 생성
                  const conversationWithMessages = {
                    ...newConversation,
                    messages: data.messages || []
                  };
                  
                  // store 업데이트 (watcher 재실행 방지를 위해 조용히 업데이트)
                  this.$store.state.currentConversation.messages = data.messages || [];
                  
                  // 랭그래프 복원
                  await restoreLanggraphFromConversation(conversationWithMessages, this);
                  
                  // UI 업데이트
                  this.$forceUpdate();
                  this.$nextTick(() => {
                    this.scroll?.scrollToBottom(this.$refs.chatMessages);
                  });
                } else {
                  console.error('❌ 메시지 가져오기 실패:', response.status);
                }
              } catch (error) {
                console.error('❌ 메시지 가져오기 오류:', error);
              }
            }, 0);
          }
        }
      });
    },
    // shouldScrollToBottom 상태가 true로 변경될 때 스크롤을 맨 아래로 이동 (최적화)
    '$store.state.shouldScrollToBottom'(newValue) {
      if (newValue) {
        this.scroll?.scrollToBottom(this.$refs.chatMessages); // 통합된 쓰로틀링 사용
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
                this.scroll?.scrollToBottom(this.$refs.chatMessages); // 통합된 쓰로틀링 사용
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
        this.scroll?.scrollToBottom(this.$refs.chatMessages); // 통합된 쓰로틀링 사용
      }
    },
    // 새 대화 생성 트리거 감시
    '$store.state._newConversationTrigger'(newVal, oldVal) {
      // 값이 실제로 변경되었을 때만 실행 (중복 실행 방지)
      if (newVal && newVal !== oldVal) {
        console.log('[HOME] 새 대화 트리거 감지:', newVal);
      // 새 대화 생성 시 랭그래프 상태 초기화
      this.langgraph.resetLanggraphState();
        // 새 대화 생성
        this.newConversation();
      }
    },
    // currentMessages 변경 감지하여 빈 메시지일 때 랭그래프 숨기기
    currentMessages(newMessages) {
      if (!newMessages || newMessages.length === 0) {
        this.langgraph.showLanggraph.value = false;
      }
    }
  },
  
  beforeDestroy() {
    // 메모리 누수 방지를 위한 정리 작업
    if (this.scrollTimeout) {
      clearTimeout(this.scrollTimeout);
      this.scrollTimeout = null;
    }
    
    // WebSocket 사용하지 않음
    
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
