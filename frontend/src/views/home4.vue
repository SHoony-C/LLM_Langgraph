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
        const response = await fetch(`https://report-collection/api/conversations/${conversationId}/messages`, {
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
          console.log('폴백 메시지 저장 완료:', messageData);
          
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
    copyToClipboard(text) {
      // 현대적인 Clipboard API 사용
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
          console.log('✅ 텍스트가 클립보드에 복사되었습니다.');
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
          console.log('✅ 폴백 방법으로 텍스트가 클립보드에 복사되었습니다.');
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
      console.log('🖼️ 이미지 로딩 실패로 인해 URL 초기화. 마지막 시도 URL:', this.lastImageUrl);
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
      console.log('🔄 로그인 후 새 대화창 초기화 시작...');
      this.newConversation();
      this.$store.commit('setLoginNewConversation', false); // 플래그 리셋
      console.log('✅ 로그인 후 새 대화창 초기화 완료');
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
          console.log('currentConversation 변경으로 인한 랭그래프 복원 시작');
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
    
    console.log('🧹 Home 컴포넌트 정리 완료');
  }
};
</script>

<style>
@import '../assets/styles/home.css';
</style> 
