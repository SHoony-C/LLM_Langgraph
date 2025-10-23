/**
 * 추가 질문 처리 유틸리티
 * Home.vue의 추가 질문 관련 함수들을 분리하여 관리
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

    // 먼저 사용자 질문을 즉시 화면에 표시
    const userMessage = {
      id: Date.now() + Math.random() * 1000, // 고유한 ID 보장
      conversation_id: conversationId,
      role: 'user',
      question: inputText,
      ans: null,
      created_at: new Date().toISOString()
    };

    // 현재 대화에 사용자 메시지 추가
    context.$store.commit('addMessageToCurrentConversation', userMessage);

    // 스트리밍 메시지 초기화
    context.$store.commit('updateStreamingMessage', '');
    context.$store.commit('setIsStreaming', false);

    // DOM 업데이트 대기
    await context.$nextTick();

    // 스트리밍 상태 시작
    context.$store.commit('setIsStreaming', true);
    context.$store.commit('updateStreamingMessage', '');
    context.streamingVisible = true;

    // DOM 업데이트 강제 실행
    await context.$nextTick();
    context.$forceUpdate();

    // 인증 토큰 가져오기
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('인증 토큰이 없습니다.');
    }

    // LangGraph 컨텍스트는 수집하지 않음 (추가 질문은 일반 LLM만 사용)
    // 요청 데이터 구성
    const requestData = {
      question: inputText,
      conversation_id: conversationId,
      generate_image: false,
      include_langgraph_context: false,
      langgraph_context: null
    };

    console.log('📤 추가 질문 요청 데이터:', requestData);

    // SSE 요청 전송
    const response = await fetch('http://localhost:8000/api/normal_llm/langgraph/followup/stream', {
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

    // SSE 스트림 처리
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantResponse = '';

    let done = false;
    while (!done) {
      const { done: streamDone, value } = await reader.read();
      done = streamDone;
      
      if (done) {
        console.log('📡 추가 질문 SSE 스트림 완료');
        break;
      }

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          if (data === '[DONE]') {
            console.log('📡 추가 질문 SSE 스트림 종료');
            break;
          }

          try {
            const messageData = JSON.parse(data);
            
            if (messageData.content) {
              assistantResponse += messageData.content;
              context.$store.commit('updateStreamingMessage', assistantResponse);
            }
          } catch (parseError) {
            console.warn('📡 추가 질문 SSE 메시지 파싱 오류:', parseError);
          }
        }
      }
    }

    // 스트리밍 완료 후 최종 답변 저장
    if (assistantResponse) {
      await saveAdditionalQuestionMessage(inputText, assistantResponse, conversationId, context);
    }

    // 스트리밍 상태 해제
    context.$store.commit('setIsStreaming', false);
    context.$store.commit('updateStreamingMessage', '');
    context.streamingVisible = false;

    console.log('✅ 추가 질문 처리 완료');

  } catch (error) {
    console.error('❌ 추가 질문 처리 오류:', error);
    
    // 에러 메시지를 사용자에게 표시
    const errorMessage = `죄송합니다. 추가 질문 처리 중 오류가 발생했습니다: ${error.message}`;
    
    if (context.$store.state.currentConversation) {
      const assistantMessage = {
        id: Date.now() + Math.random(),
        conversation_id: context.$store.state.currentConversation.id,
        role: 'assistant',
        question: null,
        ans: errorMessage,
        created_at: new Date().toISOString()
      };
      
      context.$store.commit('addMessageToCurrentConversation', assistantMessage);
    }
    
    // 스트리밍 상태 해제
    context.$store.commit('setIsStreaming', false);
    context.$store.commit('updateStreamingMessage', '');
    context.streamingVisible = false;
  }
}

/**
 * 추가 질문 메시지 저장
 * @param {string} question - 질문
 * @param {string} answer - 답변
 * @param {number|null} conversationId - 대화 ID
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function saveAdditionalQuestionMessage(question, answer, conversationId, context) {
  try {
    // 저장 상태 업데이트
    context.isSavingMessage = true;
    context.saveStatus = '';

    if (!conversationId) {
      if (!context.$store.state.currentConversation) {
        console.error('⚠️ 추가 질문 메시지 저장 실패: 현재 대화가 없습니다.');
        return;
      }
      conversationId = context.$store.state.currentConversation.id;
    }

    console.log('💾 추가 질문 메시지 저장 시작:', {
      question: question.substring(0, 50) + '...',
      answerLength: answer.length,
      conversationId: conversationId
    });

    // 인증 토큰 가져오기
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('인증 토큰이 없습니다.');
    }

    // 요청 데이터 구성
    const requestData = {
      question: question,
      assistant_response: answer,
      q_mode: 'add', // 추가 질문 모드
      image_url: null
    };

    // 백엔드에 메시지 저장 요청
    const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages/stream`, {
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

    const result = await response.json();
    console.log('✅ 추가 질문 메시지 저장 완료:', result);

    // 어시스턴트 메시지를 Vuex 스토어에 추가
    if (result.assistantMessage) {
      context.$store.commit('addMessageToCurrentConversation', result.assistantMessage);
    }

    context.saveStatus = 'success';

  } catch (error) {
    console.error('❌ 추가 질문 메시지 저장 실패:', error);
    context.saveStatus = 'error';
    
    // 에러 메시지를 사용자에게 표시
    const errorMessage = `메시지 저장 중 오류가 발생했습니다: ${error.message}`;
    
    if (context.$store.state.currentConversation) {
      const assistantMessage = {
        id: Date.now() + Math.random(),
        conversation_id: context.$store.state.currentConversation.id,
        role: 'assistant',
        question: null,
        ans: errorMessage,
        created_at: new Date().toISOString()
      };
      
      context.$store.commit('addMessageToCurrentConversation', assistantMessage);
    }
  } finally {
    context.isSavingMessage = false;
  }
}

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
  saveAdditionalQuestionMessage,
  getLanggraphContextForAdditionalQuestion,
  executeAdditionalQuestionFlowWrapper
};
