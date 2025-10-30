/**
 * 추가 질문 처리 유틸리티
 * Home.vue의 추가 질문 관련 함수들을 분리하여 관리
 * 
 * 중요: 이 시스템에서는 질문과 답변이 하나의 Message row에 저장됩니다.
 * - question 필드: 사용자 질문
 * - ans 필드: AI 답변
 * - role: 'user' (질문과 답변이 모두 user 메시지에 포함)
 * - 별도의 assistant 메시지는 생성하지 않음
 */

/**
 * 추가 질문 실행 메인 함수
 * @param {string} inputText - 사용자 입력 텍스트
 * @param {number|null} conversationId - 대화 ID
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function executeAdditionalQuestionFlow(inputText, conversationId, context) {
  try {
    // conversationId가 제공되지 않은 경우 currentConversation에서 가져오기
    if (!conversationId) {
      if (!context.$store.state.currentConversation) {
        console.error('⚠️ 추가 질문 실행 실패: 현재 대화가 없습니다.');
        return;
      }
      conversationId = context.$store.state.currentConversation.id;
    }

    console.log('💬 추가 질문 스트리밍 답변 실행 시작:', inputText);

    // 인증 토큰 가져오기
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('인증 토큰이 없습니다.');
    }

    // 1. 먼저 영구 message_id 발급

    const prepareResponse = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages/prepare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        question: inputText,
        q_mode: 'add',
        conversation_id: conversationId
      })
    });

    if (!prepareResponse.ok) {
      throw new Error(`Prepare message failed: ${prepareResponse.status}`);
    }

    const preparedData = await prepareResponse.json();
    console.log('✅ 추가 질문 영구 메시지 ID 발급 완료:', preparedData);

    // 2. 백엔드에서 생성된 메시지를 프론트엔드에 추가 (UI 표시용)
    // 중요: 질문과 답변이 하나의 row에 저장되는 구조
    // - question: 사용자 질문 (즉시 저장)
    // - ans: AI 답변 (스트리밍 완료 후 업데이트)
    // - UI에서는 user 메시지에 질문과 답변을 모두 표시
    const userMessage = {
      id: `${preparedData.userMessage.id}-user`,
      conversation_id: conversationId,
      role: 'user',
      question: inputText,  // 사용자 질문
      ans: '',  // AI 답변 (아직 없음, 스트리밍 완료 후 업데이트됨)
      created_at: new Date().toISOString(),
      backend_id: preparedData.userMessage.id
    };

    // 현재 대화에 메시지 추가 (UI 표시용)
    context.$store.commit('addMessageToCurrentConversation', userMessage);

    // 스트리밍 메시지 초기화
    context.$store.commit('updateStreamingMessage', '');
    context.$store.commit('setIsStreaming', false);


    // DOM 업데이트 대기
    await context.$nextTick();

    // 스트리밍 상태 시작 (메시지가 실제로 시작될 때만)
    context.$store.commit('setIsStreaming', true);
    context.$store.commit('updateStreamingMessage', '');
    context.sse.streamingVisible.value = true; // 스트리밍 영역을 미리 확보
    console.log('👀 추가 질문 스트리밍 영역 표시 시작');

    // DOM 업데이트 대기
    await context.$nextTick();

    // token은 이미 위에서 선언됨

    // LangGraph 컨텍스트는 수집하지 않음 (추가 질문은 일반 LLM만 사용)
    // 요청 데이터 구성
    const requestData = {
      question: inputText,
      conversation_id: conversationId,
      message_id: preparedData.userMessage.id, // 영구 메시지 ID 포함
      generate_image: false,
      include_langgraph_context: false,
      langgraph_context: null,
      q_mode: 'add'  // 추가질문 모드 설정
    };

    console.log('📤 추가 질문 요청 데이터:', requestData);
    console.log('📤 추가 질문 요청 상세:');
    console.log('  - question:', inputText);
    console.log('  - conversation_id:', conversationId);
    console.log('  - q_mode:', 'add');
    console.log('  - generate_image:', false);
    
    // 현재 대화의 메시지 히스토리 확인
    const currentConversation = context.$store.state.currentConversation;
    if (currentConversation && currentConversation.messages) {
      console.log('📋 현재 대화 메시지 히스토리:');
      console.log('  - 총 메시지 수:', currentConversation.messages.length);
      currentConversation.messages.forEach((msg, index) => {
        console.log(`  - 메시지 ${index + 1}:`, {
          id: msg.id,
          role: msg.role,
          question: msg.question ? msg.question.substring(0, 100) + '...' : '없음',
          ans: msg.ans ? msg.ans.substring(0, 100) + '...' : '없음',
          created_at: msg.created_at
        });
      });
    } else {
      console.log('⚠️ 현재 대화 또는 메시지가 없습니다');
    }

    // 스트림 요청 전송
    const response = await fetch('http://localhost:8000/api/normal_llm/followup/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    let assistantResponse = '';
    const contentType = response.headers.get('content-type') || '';
    const isEventStream = contentType.includes('text/event-stream');
    console.log('📡 추가 질문 스트림 콘텐츠 타입:', contentType || '알 수 없음');

    if (isEventStream) {
      // 이벤트 스트림 처리 (SSE)
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let streamClosed = false;

      const processBuffer = () => {
        let boundaryIndex = buffer.indexOf('\n\n');

        while (boundaryIndex !== -1) {
          const rawEvent = buffer.slice(0, boundaryIndex);
          buffer = buffer.slice(boundaryIndex + 2);

          const dataLines = rawEvent
            .split('\n')
            .filter(line => line.startsWith('data: '));

          if (dataLines.length === 0) {
            boundaryIndex = buffer.indexOf('\n\n');
            continue;
          }

          const dataPayload = dataLines
            .map(line => line.slice(6))
            .join('\n');

          if (dataPayload === '[DONE]') {
            console.log('📡 추가 질문 스트리밍 종료 신호 수신');
            streamClosed = true;
            return;
          }

          try {
            const messageData = JSON.parse(dataPayload);

            if (messageData.content) {
              assistantResponse += messageData.content;
              context.$store.commit('updateStreamingMessage', assistantResponse);

              if (assistantResponse.length > 0 && !context.sse.streamingVisible.value) {
                context.sse.streamingVisible.value = true;
                console.log('👀 추가 질문 스트리밍 영역 활성화 (데이터 수신)');
              }
            }
          } catch (parseError) {
            console.warn('📡 추가 질문 스트리밍 데이터 파싱 오류:', parseError, '\n📄 원본 데이터:', dataPayload);
          }

          boundaryIndex = buffer.indexOf('\n\n');
        }
      };

      while (!streamClosed) {
        const { done: streamDone, value } = await reader.read();

        if (value) {
          buffer += decoder.decode(value, { stream: !streamDone });
          processBuffer();
        }

        if (streamDone) {
          buffer += decoder.decode(new Uint8Array(), { stream: false });
          processBuffer();
          console.log('📡 추가 질문 이벤트 스트리밍 완료');
          break;
        }
      }
    } else {
      // 일반 텍스트 스트리밍 처리
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done: streamDone, value } = await reader.read();

        if (value) {
          const chunkText = decoder.decode(value, { stream: !streamDone });
          if (chunkText) {
            assistantResponse += chunkText;
            context.$store.commit('updateStreamingMessage', assistantResponse);

            if (assistantResponse.length > 0 && !context.sse.streamingVisible.value) {
              context.sse.streamingVisible.value = true;
              console.log('👀 추가 질문 스트리밍 영역 활성화 (텍스트 데이터)');
            }
          }
        }

        if (streamDone) {
          console.log('📡 추가 질문 텍스트 스트리밍 완료');
          break;
        }
      }
    }

    // 스트리밍 완료 후 처리
    if (assistantResponse) {
      // console.log('✅ 추가 질문 스트리밍 완료');
      // console.log('🔍 [DEBUG] 스트리밍 완료 시점 - UI 상태 체크:');
      // console.log('  - showLanggraph:', context.langgraph.showLanggraph.value);
      // console.log('  - currentStep:', context.langgraph.currentStep.value);
      // console.log('  - isFollowupQuestion:', context.langgraph.isFollowupQuestion.value);
      
      // 스트리밍 상태 해제
      context.$store.commit('setIsStreaming', false);
      context.$store.commit('updateStreamingMessage', '');
      context.sse.streamingVisible.value = false;
      
      // console.log('🔍 [DEBUG] 스트리밍 상태 해제 후:');
      // console.log('  - isStreaming:', context.$store.state.isStreaming);
      // console.log('  - streamingMessage:', context.$store.state.streamingMessage);
      // console.log('  - streamingVisible:', context.sse.streamingVisible.value);
      
      // DOM 업데이트 대기
      await context.$nextTick();
      
      // 3. 스트리밍 완료 시 메시지 내용 업데이트 (UI 업데이트용)
      // 중요: user 메시지의 ans 필드에 AI 답변을 업데이트
      try {
        const completeResponse = await fetch(`http://localhost:8000/api/messages/${preparedData.userMessage.id}/complete`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            assistant_response: assistantResponse,  // user 메시지의 ans 필드에 저장됨
            image_url: null
          })
        });

        if (completeResponse.ok) {
          // console.log('✅ 추가 질문 메시지 완료 처리 성공');
          // console.log('📊 메시지 완료 처리 상세:');
          // console.log('  - user_message_id:', preparedData.userMessage.id);
          // console.log('  - response_length:', assistantResponse.length);
          // console.log('  - conversation_id:', conversationId);
          
          // console.log('🔍 [DEBUG] updateMessageAnswer 호출 전 UI 상태:');
          // console.log('  - showLanggraph:', context.langgraph.showLanggraph.value);
          // console.log('  - currentStep:', context.langgraph.currentStep.value);
          // console.log('  - isFollowupQuestion:', context.langgraph.isFollowupQuestion.value);
          
          // user 메시지의 ans 필드에 답변 저장 (Vue 반응성 시스템 사용)
          context.$store.commit('updateMessageAnswer', {
            messageId: preparedData.userMessage.id,
            answer: assistantResponse
          });
          
          // console.log('🔍 [DEBUG] updateMessageAnswer 호출 후 UI 상태:');
          // console.log('  - showLanggraph:', context.langgraph.showLanggraph.value);
          // console.log('  - currentStep:', context.langgraph.currentStep.value);
          // console.log('  - isFollowupQuestion:', context.langgraph.isFollowupQuestion.value);
          
          // console.log('✅ [ADDITIONAL] user 메시지 ans 필드 업데이트 완료:', preparedData.userMessage.id);
          // console.log('✅ 프론트엔드 assistant 메시지 추가 완료');
        } else {
          console.warn('⚠️ 추가 질문 메시지 완료 처리 실패:', completeResponse.status);
        }
      } catch (completeError) {
        console.warn('⚠️ 추가 질문 메시지 완료 처리 오류:', completeError);
      }
    } else {
      // 답변이 없는 경우에만 스트리밍 상태 해제
      context.$store.commit('setIsStreaming', false);
      context.$store.commit('updateStreamingMessage', '');
      context.sse.streamingVisible.value = false;
    }

    console.log('✅ 추가 질문 처리 완료');

  } catch (error) {
    console.error('❌ 추가 질문 처리 오류:', error);
    
    // 에러 메시지를 사용자에게 표시
    const errorMessage = `죄송합니다. 추가 질문 처리 중 오류가 발생했습니다: ${error.message}`;
    
    if (context.$store.state.currentConversation) {
      const errorUserMessage = {
        id: Date.now() + Math.random(),
        conversation_id: context.$store.state.currentConversation.id,
        role: 'user',
        question: inputText,
        ans: errorMessage,  // 에러 메시지를 ans 필드에 저장
        created_at: new Date().toISOString()
      };
      
      context.$store.commit('addMessageToCurrentConversation', errorUserMessage);
    }
    
    // 스트리밍 상태 해제
    context.$store.commit('setIsStreaming', false);
    context.$store.commit('updateStreamingMessage', '');
    context.sse.streamingVisible.value = false;
  }
}

// saveAndReplaceAdditionalQuestionMessage 함수는 더 이상 사용하지 않으므로 제거됨

/**
 * LangGraph 컨텍스트 수집 (Judge 함수 사용)
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 * @returns {Object|null} LangGraph 컨텍스트
 */
export function getLanggraphContextForAdditionalQuestion(context) {
  try {
    const currentConversation = context.$store.state.currentConversation;
    if (!currentConversation || !currentConversation.messages) {
      return null;
    }

    // Judge 함수를 사용하여 LangGraph 컨텍스트 추출
    const { extractLangGraphContext } = require('./questionJudge.js');
    const langgraphContext = extractLangGraphContext(currentConversation.messages);

    if (langgraphContext.hasSearchResults) {
      return {
        documents: langgraphContext.documents || [],
        documents_count: langgraphContext.documents.length || 0,
        sources: [],
        question: '',
        answer: '',
        // 추가 컨텍스트 정보
        context_type: 'langgraph_search',
        search_query: '',
        retrieved_docs: langgraphContext.documents || [],
        keywords: langgraphContext.keywords || []
      };
    }

    return null;
  } catch (error) {
    console.warn('랭그래프 컨텍스트 수집 실패:', error);
    return null;
  }
}

// ===== 💬 추가 질문 처리 함수 (분리된 함수 사용) =====
export async function executeAdditionalQuestionFlowWrapper(inputText, conversationId = null, context) {
  return await executeAdditionalQuestionFlow(inputText, conversationId, context);
}

export default {
  executeAdditionalQuestionFlow,
  getLanggraphContextForAdditionalQuestion,
  executeAdditionalQuestionFlowWrapper
};
