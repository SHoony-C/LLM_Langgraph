   
    // 추가 질문 처리 메서드 (실시간 스트리밍 응답)
    async executeFollowupQuestion(inputText, conversationId) {
      try {
        this.isLoading = true;
        
        console.log('[FOLLOWUP] 추가 질문 실시간 스트리밍 시작');
        console.log('[FOLLOWUP] LangGraph UI 상태 유지:', {
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
        console.log('[FOLLOWUP] 스트리밍 초기화 시작');
        this.$store.commit('updateStreamingMessage', '');
        this.$store.commit('setIsStreaming', false);
        
        // DOM 업데이트 대기
        await this.$nextTick();
        
        // 스트리밍 상태 확인 및 시작
        console.log('[FOLLOWUP] 스트리밍 시작 - isStreaming:', this.$store.state.isStreaming);
        this.$store.commit('setIsStreaming', true);
        this.$store.commit('updateStreamingMessage', '');
        
        // 스트리밍 UI 강제 표시
        this.streamingVisible = true;
        
        // DOM 업데이트 강제 실행
        await this.$nextTick();
        this.$forceUpdate();
        
        // 스트리밍 상태 재확인
        console.log('[FOLLOWUP] 스트리밍 상태 설정 완료 - isStreaming:', this.$store.state.isStreaming);
        console.log('[FOLLOWUP] 스트리밍 UI 표시:', this.streamingVisible);
        console.log('[FOLLOWUP] 스트리밍 메시지:', this.$store.state.streamingMessage);
        
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
          console.log('[FOLLOWUP] LangGraph UI 복원 완료');
        });
        
        // 추가 질문 스트리밍 API 호출
        const response = await fetch('https://report-collection/api/llm/langgraph/followup/stream', {
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
        console.log('📡 추가 질문 스트리밍 응답 처리 시작...');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedMessage = '';
        
        let streamingActive = true;
        let chunkCount = 0;
        while (streamingActive) {
          const { value, done } = await reader.read();
          if (done) {
            console.log('📡 추가 질문 스트리밍 완료 - done=true');
            streamingActive = false;
            break;
          }
          
          chunkCount++;
          const chunk = decoder.decode(value);
          console.log(`📡 추가 질문 청크 ${chunkCount} 수신:`, chunk);
          const lines = chunk.split('\n\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const content = line.substring(6);
              
              if (content === '[DONE]') {
                console.log('📡 추가 질문 [DONE] 신호 수신 - 스트리밍 종료');
                streamingActive = false;
                break;
              }
              
              try {
                // JSON 형태의 데이터인지 확인
                const jsonData = JSON.parse(content);
                if (jsonData.content) {
                  console.log('📡 추가 질문 JSON 데이터 처리:', jsonData.content);
                  accumulatedMessage += jsonData.content;
                  // 스트리밍 상태 확인 후 업데이트
                  console.log('📡 스트리밍 상태 확인 - isStreaming:', this.$store.state.isStreaming);
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                  console.log('📡 스트리밍 메시지 업데이트됨:', accumulatedMessage.length, '문자');
                } else if (jsonData.text) {
                  console.log('📡 추가 질문 JSON 데이터 처리 (text):', jsonData.text);
                  accumulatedMessage += jsonData.text;
                  // 스트리밍 상태 확인 후 업데이트
                  console.log('📡 스트리밍 상태 확인 - isStreaming:', this.$store.state.isStreaming);
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                  console.log('📡 스트리밍 메시지 업데이트됨:', accumulatedMessage.length, '문자');
                }
              } catch (e) {
                // JSON이 아닌 일반 텍스트인 경우
                console.log('📡 추가 질문 텍스트 데이터 처리:', content);
                accumulatedMessage += content;
                // 안전한 스트리밍 메시지 업데이트
                this.$store.commit('updateStreamingMessage', accumulatedMessage);
              }
            }
          }
        }
        
        console.log(`📡 추가 질문 스트리밍 최종 완료 - 총 ${chunkCount}개 청크 처리`);
        console.log(`📡 추가 질문 누적된 메시지: "${accumulatedMessage}"`);
        
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
        console.log('💾 추가 질문 메시지 저장 시작 - q_mode: add');
        await this.saveAdditionalQuestionMessage(inputText, accumulatedMessage || '답변을 생성할 수 없습니다.');
        
        // LangGraph UI 상태 최종 복원 (저장 후에도 유지)
        this.showRangraph = langGraphBackup.showRangraph;
        this.currentStep = langGraphBackup.currentStep;
        this.originalInput = langGraphBackup.originalInput;
        this.augmentedKeywords = langGraphBackup.augmentedKeywords;
        this.searchResults = langGraphBackup.searchResults;
        this.finalAnswer = langGraphBackup.finalAnswer;
        this.analysisImageUrl = langGraphBackup.analysisImageUrl; // 이미지 URL 복원 추가
        
        console.log('[FOLLOWUP] 최종 LangGraph UI 상태 복원 완료');
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
        console.log('[FOLLOWUP] 메시지 저장 시작');
        
        const response = await fetch(`https://report-collection/api/conversations/${conversationId}/messages`, {
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
          console.log('[FOLLOWUP] 메시지 저장 완료:', messageData);
          
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
          
          console.log('[FOLLOWUP] LangGraph UI 상태 복원 완료');
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
        console.log('💬 일반 LLM 스트리밍 답변 실행 시작:', inputText);
        
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
        
        console.log('[SIMPLE_LLM] 스트리밍 메시지 초기화 완료');
        console.log('[SIMPLE_LLM] 스트리밍 UI 표시:', this.streamingVisible);
        
        // 스트리밍 LLM API 호출
        const response = await fetch('https://report-collection/api/llm/chat/stream', {
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
                if (jsonData.content) {
                  console.log('📡 executeSimpleLLMFlow JSON 데이터 처리:', jsonData.content);
                  accumulatedMessage += jsonData.content;
                  this.$store.commit('updateStreamingMessage', accumulatedMessage);
                } else if (jsonData.text) {
                  console.log('📡 executeSimpleLLMFlow JSON 데이터 처리 (text):', jsonData.text);
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
        
        // LangGraph UI 상태 복원 (폴백 시에도 유지)
        this.showRangraph = langGraphBackup.showRangraph;
        this.currentStep = langGraphBackup.currentStep;
        this.originalInput = langGraphBackup.originalInput;
        this.augmentedKeywords = langGraphBackup.augmentedKeywords;
        this.searchResults = langGraphBackup.searchResults;
        this.finalAnswer = langGraphBackup.finalAnswer;
        
        console.log('💾 일반 LLM 답변 저장 및 표시 완료 - LangGraph UI 상태 복원');
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
        
        console.log('[ADDITIONAL] 스트리밍 메시지 초기화 완료');
        console.log('[ADDITIONAL] 스트리밍 UI 표시:', this.streamingVisible);
        
        // 스트리밍 LLM API 호출하여 추가 질문에 답변
        const response = await fetch('https://report-collection/api/llm/chat/stream', {
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
          image: this.analysisImageUrl,  // 기존 이미지 URL 유지 (추가 질문에서도)
          user_name: this.$store.state.user?.username || '사용자'  // username 사용
        };
        
        console.log('📤 추가 질문 메시지 저장 API 요청 데이터:', requestBody);
        
        const response = await fetch(`https://report-collection/api/conversations/${conversationId}/messages`, {
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
          
          // LangGraph UI 상태는 executeFollowupQuestion에서 관리하므로 여기서는 건드리지 않음
          console.log('✅ 추가 질문 저장 완료 - LangGraph UI 상태 유지');
        } else if (response.status === 401) {
          // 인증 실패 시 토큰 갱신 시도
          console.error('❌ 인증 실패 (401). 토큰 갱신 시도...');
          this.saveStatus = '⚠️ 인증이 만료되었습니다. 토큰을 갱신 중...';
          
          try {
            // 토큰 갱신 시도
            await this.refreshToken();
            console.log('🔄 토큰 갱신 완료, 저장 재시도...');
            
            // 토큰 갱신 후 저장 재시도
            this.$nextTick(() => {
              this.saveAdditionalQuestionMessage(question, answer);
            });
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
          
          // 저장 실패 시 재시도 로직 (최적화)
          console.log('🔄 추가 질문 메시지 저장 재시도...');
          this.$nextTick(() => {
            this.saveAdditionalQuestionMessage(question, answer);
          });
        }
      } catch (error) {
        console.error('추가 질문 메시지 저장 중 오류:', error);
        this.saveStatus = `⚠️ 메시지 저장 오류: ${error.message}`;
        
        // 오류 발생 시 재시도 로직 (최적화)
        console.log('🔄 추가 질문 메시지 저장 재시도...');
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
        console.log('이미 랭그래프가 실행 중입니다. 중복 실행 방지.');
        return;
      }
      
      console.log('🚀 executeRangraphFlow 시작:', inputText);
      console.log('🔍 실시간 기능 상태:', {
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
      this.finalAnswer = '';
      this.analysisImageUrl = ''; // 이미지 URL 초기화 추가
      this.lastImageUrl = ''; // 마지막 이미지 URL 초기화 추가
      this.langGraphError = null;
      this.originalInput = inputText;
      
      // 추출된 데이터 초기화
      this.extractedKeywords = null;
      this.extractedDbSearchTitle = null;
      
      try {
        
        console.log('🔍 SSE 연결 조건 확인:', {
          isNewConversation: this.isNewConversation,
          isFirstQuestionInSession: this.isFirstQuestionInSession,
          isRestoringConversation: this.isRestoringConversation,
          currentConversation: this.$store.state.currentConversation?.id || 'null',
          shouldConnect: this.isFirstQuestionInSession && !this.isRestoringConversation
        });
        
        // 첫 번째 질문이고 복원 중이 아닌 경우 SSE 스트리밍 사용
        if (this.isFirstQuestionInSession && !this.isRestoringConversation) {
          console.log('🎯 첫 번째 질문 감지 - SSE 스트리밍 활성화');
          try {
            await this.executeLangGraphWithSSE(inputText);
            return; // SSE 처리 완료 후 종료
          } catch (sseError) {
            console.warn('⚠️ SSE 스트리밍 실패, 기본 API로 폴백:', sseError);
            // 폴백으로 기본 API 사용
          }
        } else {
          console.log('🔄 추가 질문 또는 복원 상태 - 기본 API 사용');
        }
        
        // 기본 LangGraph API 호출 (폴백용)
        const response = await fetch('https://report-collection/api/llm/langgraph', {
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
      console.log('🚀 SSE 스트리밍 시작:', inputText);
      
      try {
        const response = await fetch('https://report-collection/api/llm/langgraph/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: inputText
          })
        });
        
        if (!response.ok) {
          throw new Error(`SSE 요청 실패: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        console.log('✅ SSE 스트림 시작');
        
        let streamActive = true;
        while (streamActive) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log('🏁 SSE 스트림 완료');
            streamActive = false;
            break;
          }
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6); // 'data: ' 제거
              
              if (data === '[DONE]') {
                console.log('🏁 SSE 스트리밍 완료');
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
                  
                  console.log('📡 SSE 데이터 처리:', parsedData);
                  this.handleSSEMessage(parsedData);
                  
                } catch (parseError) {
                  console.error('❌ SSE 메시지 파싱 오류:', parseError, 'Data:', data);
                }
              }
            }
          }
        }
        
      } catch (error) {
        console.error('❌ SSE 스트리밍 오류:', error);
        throw error;
      }
    },
    
