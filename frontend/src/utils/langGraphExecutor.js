/**
 * LangGraph 실행 유틸리티
 * Home.vue의 LangGraph 관련 함수들을 분리하여 관리
 */

import { handleSSEMessage } from './sseMessageHandler.js';

/**
 * LangGraph 실행 메인 함수
 * @param {string} inputText - 사용자 입력 텍스트
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function executeLanggraphFlow(inputText, context) {
  // 이미 실행 중인 경우 중복 실행 방지
  if (context.messages.isLoading.value || context.langgraph.isSearching.value) {
    console.log('이미 랭그래프가 실행 중입니다. 중복 실행 방지.');
    return;
  }

  console.log('🔄 LangGraph 4단계 분석 시작:', inputText);

  // 실행 상태 설정
  context.messages.isLoading.value = true;
  context.langgraph.isSearching.value = false;
  context.langgraph.isGeneratingAnswer.value = false;
  context.langgraph.isStreamingAnswer.value = false;
  context.langgraph.isDoneProcessed.value = false;
  context.langgraph.originalInput.value = inputText;

  // 랭그래프 UI 표시
  context.langgraph.showLanggraph.value = true;
  context.langgraph.currentStep.value = 0;

  // 스트리밍 상태 초기화
  context.langgraph.streamingAnswer.value = '';
  context.langgraph.finalAnswer.value = '';
  context.langgraph.analysisImageUrl.value = '';

  try {
    // 1단계: prepare_message API 호출하여 영구 message_id 발급
    const permanentMessageId = await prepareMessageForLangGraph(inputText, context);
    console.log('✅ 영구 메시지 ID 발급 완료:', permanentMessageId);

    // 2단계: 사용자 질문 메시지를 화면에 표시 (영구 ID 사용)
    if (context.$store.state.currentConversation) {
      const userMessage = {
        id: Date.now() + Math.random() * 1000,
        conversation_id: context.$store.state.currentConversation.id,
        role: 'user',
        question: inputText,
        ans: null,
        backend_id: permanentMessageId, // 영구 ID 설정
        created_at: new Date().toISOString()
      };
      context.$store.commit('addMessageToCurrentConversation', userMessage);
    }

    // 3단계: SSE 스트리밍으로 LangGraph 실행
    await executeLangGraphWithSSE(inputText, context, permanentMessageId);
  } catch (error) {
    console.error('❌ LangGraph 실행 오류:', error);
    await fallbackLanggraphFlow(inputText, error, context);
  }
}

/**
 * LangGraph 실행을 위한 영구 메시지 ID 발급
 * @param {string} inputText - 사용자 입력 텍스트
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 * @returns {number} 영구 메시지 ID
 */
async function prepareMessageForLangGraph(inputText, context) {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('인증 토큰이 없습니다.');
    }

    const conversationId = context.$store.state.currentConversation?.id;
    if (!conversationId) {
      throw new Error('현재 대화가 없습니다.');
    }

    const requestData = {
      question: inputText,
      q_mode: 'search', // LangGraph는 search 모드
      keyword: null,
      db_contents: null,
      image: null
    };

    console.log('📋 prepare_message API 호출:', requestData);

    const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages/prepare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`prepare_message API 호출 실패: ${response.status} ${errorText}`);
    }

    const result = await response.json();
    console.log('✅ prepare_message 응답:', result);

    if (result.userMessage && result.userMessage.id) {
      return result.userMessage.id;
    } else {
      throw new Error('영구 메시지 ID를 받지 못했습니다.');
    }
  } catch (error) {
    console.error('❌ prepare_message API 호출 오류:', error);
    throw error;
  }
}

/**
 * SSE 스트리밍으로 LangGraph 실행
 * @param {string} inputText - 사용자 입력 텍스트
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 * @param {number} permanentMessageId - 영구 메시지 ID
 */
export async function executeLangGraphWithSSE(inputText, context, permanentMessageId) {
  // AbortController 생성 및 전역 저장
  const controller = new AbortController();
  window.sseController = controller;

  try {
    // 인증 토큰 가져오기
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('인증 토큰이 없습니다.');
    }

    // SSE 요청 데이터 구성
    const requestData = {
      question: inputText,
      conversation_id: context.$store.state.currentConversation?.id || null,
      message_id: permanentMessageId, // 영구 메시지 ID 포함
      generate_image: false,
      include_langgraph_context: false,
      langgraph_context: null
    };

    console.log('🚀 SSE 스트리밍 요청 시작:', requestData);

    // 랭그래프는 최초 질문만 처리 (추가 질문은 Home.vue에서 분기 처리)
    const endpoint = 'http://localhost:8000/api/langgraph/stream';
    
    console.log('🎯 랭그래프 엔드포인트:', endpoint);
    console.log('🎯 isFollowupQuestion:', context.langgraph.isFollowupQuestion.value);

    // SSE 요청 전송
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(requestData),
      signal: controller.signal
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // SSE 스트림 처리
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = '';
    let eventData = '';
    let done = false;

    while (!done) {
      const { done: streamDone, value } = await reader.read();
      done = streamDone;

      if (value) {
        buffer += decoder.decode(value, { stream: true });
      }

      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
        const rawLine = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);
        const line = rawLine.trimEnd();

        if (!line) {
          if (eventData) {
            const payload = eventData.trim();
            eventData = '';

            if (!payload) {
              continue;
            }

            if (payload === '[DONE]') {
              console.log('📡 SSE 스트림 종료');
              done = true;
              break;
            }

            try {
              const messageData = JSON.parse(payload);
              await handleSSEMessage(messageData, context);
            } catch (parseError) {
              console.warn('📡 SSE 메시지 파싱 오류:', parseError, '\n📄 원본 데이터:', payload);
            }
          }

          continue;
        }

        if (line.startsWith('data:')) {
          const dataPortion = line.slice(5).trimStart();
          if (eventData) {
            eventData += '\n';
          }
          eventData += dataPortion;
        }
      }

      if (done) {
        if (eventData) {
          const payload = eventData.trim();
          eventData = '';

          if (payload && payload !== '[DONE]') {
            try {
              const messageData = JSON.parse(payload);
              await handleSSEMessage(messageData, context);
            } catch (parseError) {
              console.warn('📡 SSE 메시지 파싱 오류 (스트림 종료 시):', parseError, '\n📄 원본 데이터:', payload);
            }
          }
        }

        if (buffer.trim() === '[DONE]') {
          console.log('📡 SSE 스트림 종료 (잔여 버퍼)');
        } else {
          console.log('📡 SSE 스트림 완료');
        }
      }
    }

  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('📡 SSE 스트림 중단됨');
    } else {
      console.error('❌ SSE 스트리밍 오류:', error);
      throw error;
    }
  } finally {
    // 실행 상태 해제
    context.messages.isLoading.value = false;
    context.langgraph.isSearching.value = false;
    context.langgraph.isGeneratingAnswer.value = false;
    context.langgraph.isStreamingAnswer.value = false;
    
    // 최초 질문 완료 후 추가 질문으로 플래그 변경
    context.langgraph.isFollowupQuestion.value = true;
    console.log('✅ 최초 질문 완료 (SSE) - isFollowupQuestion을 true로 설정');
  }
}

/**
 * 폴백 랭그래프 플로우 (오류 발생 시)
 * @param {string} inputText - 사용자 입력 텍스트
 * @param {Error} error - 발생한 오류
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function fallbackLanggraphFlow(inputText, error, context) {
  // 오류 정보를 저장하여 답변에 포함
  context.langgraph.langGraphError.value = error;

  // 오류 발생 시 간단한 메시지만 표시
  context.langgraph.currentStep.value = 1;
  context.messages.isLoading.value = false;
  context.langgraph.isSearching.value = false;

  const fallbackAnswer = `죄송합니다. 분석 중 오류가 발생했습니다: ${error.message}`;

  // 폴백 메시지 저장
  await saveFallbackMessage(inputText, fallbackAnswer, context);
  
  // 최초 질문 완료 후 추가 질문으로 플래그 변경 (폴백 케이스도 포함)
  context.langgraph.isFollowupQuestion.value = true;
  console.log('✅ 최초 질문 완료 (폴백) - isFollowupQuestion을 true로 설정');
}

/**
 * 폴백 메시지 저장
 * @param {string} question - 질문
 * @param {string} answer - 답변
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function saveFallbackMessage(question, answer, context) {
  try {
    if (!context.$store.state.currentConversation) {
      console.error('⚠️ 폴백 메시지 저장 실패: 현재 대화가 없습니다.');
      return;
    }

    const conversationId = context.$store.state.currentConversation.id;

    // 사용자 메시지 추가
    const userMessage = {
      id: Date.now() + Math.random(),
      conversation_id: conversationId,
      role: 'user',
      question: question,
      ans: null,
      created_at: new Date().toISOString()
    };

    context.$store.commit('addMessageToCurrentConversation', userMessage);

    // user 메시지의 ans 필드에 답변 저장
    userMessage.ans = answer;

    console.log('✅ 폴백 메시지 저장 완료');

  } catch (error) {
    console.error('❌ 폴백 메시지 저장 실패:', error);
  }
}

/**
 * LangGraph 결과 처리
 * @param {Object} result - LangGraph 실행 결과
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function processLangGraphResult(result, context) {
  // 각 단계별 결과를 순차적으로 처리
  if (result.keyword) {
    context.langgraph.currentStep.value = 2;
    context.langgraph.isSearching.value = true; // 키워드 생성 완료 후 검색 시작
    context.langgraph.augmentedKeywords.value = result.keyword.map((keyword, index) => ({
      id: `keyword-${index}`,
      text: keyword,
      category: 'augmented'
    }));
    context.langgraph.extractedKeywords.value = result.keyword;
    console.log('✅ 키워드 증강 완료:', context.langgraph.augmentedKeywords.value.length, '개');
  }

  if (result.candidates_total) {
    context.langgraph.currentStep.value = 3;
    context.langgraph.searchResults.value = result.candidates_total;
    context.langgraph.searchedDocuments.value = result.candidates_total.map(candidate => 
      candidate.res_payload?.document_name || '제목 없음'
    );
    context.langgraph.extractedDbSearchTitle.value = context.langgraph.searchedDocuments.value;
    console.log('✅ RAG 검색 완료:', context.langgraph.searchResults.value.length, '건');
  }

  if (result.response) {
    context.langgraph.currentStep.value = 4;
    context.langgraph.isSearching.value = false;
    context.langgraph.isGeneratingAnswer.value = true;
    
    if (result.response.answer) {
      context.langgraph.finalAnswer.value = result.response.answer;
      console.log('✅ 최종 답변 생성 완료');
    }
  }
}

/**
 * 직접 LangGraph 결과 처리 (API 응답에서)
 * @param {Object} apiResult - API 응답 결과
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function processDirectLangGraphResult(apiResult, context) {
  console.log('🔄 processDirectLangGraphResult 시작:', apiResult);

  // LangGraph 결과 처리
  if (apiResult.result) {
    await processLangGraphResult(apiResult.result, context);
  }

  // 최종 답변을 user 메시지의 ans 필드에 저장 (assistant 메시지 생성하지 않음)
  if (context.langgraph.finalAnswer.value && context.$store.state.currentConversation) {
    console.log('📝 [LANGGRAPH] 답변을 user 메시지의 ans 필드에 저장:', context.langgraph.finalAnswer.value.length, '자');
    
    // 현재 대화의 마지막 user 메시지를 찾아서 ans 필드 업데이트
    const currentConversation = context.$store.state.currentConversation;
    if (currentConversation && currentConversation.messages && currentConversation.messages.length > 0) {
      // 마지막 user 메시지 찾기
      const userMessages = currentConversation.messages.filter(msg => msg.role === 'user');
      if (userMessages.length > 0) {
        const lastUserMessage = userMessages[userMessages.length - 1];
        lastUserMessage.ans = context.langgraph.finalAnswer.value;
        console.log('✅ [LANGGRAPH] user 메시지 ans 필드 업데이트 완료:', lastUserMessage.id);
      }
    }

    // LangGraph 결과를 백엔드에 저장
    try {
      const saveResult = await context.saveLangGraphMessage({
        result: {
          response: {
            answer: context.langgraph.finalAnswer.value
          },
          keyword: context.langgraph.extractedKeywords.value,
          candidates_total: context.langgraph.extractedDbSearchTitle.value ? context.langgraph.extractedDbSearchTitle.value.map(title => ({ res_payload: { document_name: title } })) : []
        }
      });
      console.log('✅ LangGraph 메시지 저장 완료:', saveResult);
      
      // assistant 메시지를 사용하지 않으므로 backend_id 설정 제거됨
    } catch (error) {
      console.error('❌ LangGraph 메시지 저장 실패:', error);
    }
  }

  // 실행 상태 해제
  context.messages.isLoading.value = false;
  context.langgraph.isSearching.value = false;
  context.langgraph.isGeneratingAnswer.value = false;
  context.langgraph.isStreamingAnswer.value = false;
  
  // 최초 질문 완료 후 추가 질문으로 플래그 변경
  context.langgraph.isFollowupQuestion.value = true;
  console.log('✅ 최초 질문 완료 - isFollowupQuestion을 true로 설정');
}

// LangGraph 결과를 메시지로 저장 (기존 함수 - 폴백용)
async function saveLangGraphMessage(result, context) {
  try {
    if (!context.$store.state.currentConversation) {
      console.error('⚠️ LangGraph 메시지 저장 실패: 현재 대화가 없습니다.');
      return;
    }
    
    const conversationId = context.$store.state.currentConversation.id;
    const question = context.langgraph.originalInput.value || 'LangGraph 분석 요청';
    
    // SSE 결과 구조에 맞게 답변 추출
    let answer = '분석 결과가 없습니다.';
    if (result.result && result.result.response) {
      answer = result.result.response.answer || result.result.response.final_answer || '분석 결과가 없습니다.';
    } else if (result.response) {
      answer = result.response.answer || result.response.final_answer || '분석 결과가 없습니다.';
    } else if (context.langgraph.finalAnswer.value) {
      answer = context.langgraph.finalAnswer.value;
    }
    
    // 키워드와 문서 제목 데이터 준비
    let keywordData = context.langgraph.extractedKeywords.value;
    let dbSearchTitleData = context.langgraph.extractedDbSearchTitle.value;
    
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
      originalInput: context.langgraph.originalInput.value,
      augmentedKeywords: context.langgraph.augmentedKeywords.value,
      searchResults: context.langgraph.searchResults.value.slice(0, 5),
      finalAnswer: answer,
      analysisImageUrl: context.langgraph.analysisImageUrl.value, // 이미지 URL 저장 추가
      currentStep: context.langgraph.currentStep.value,
      extractedKeywords: keywordData,
      extractedDbSearchTitle: dbSearchTitleData
    };
    
    // 검색 결과를 db_contents로 변환
    const dbContentsData = context.langgraph.searchResults.value || [];
    
    console.log('🖼️ [FRONTEND IMAGE 전송] analysisImageUrl 값:', context.langgraph.analysisImageUrl.value);
    console.log('🖼️ [FRONTEND IMAGE 전송] analysisImageUrl 타입:', typeof context.langgraph.analysisImageUrl.value);
    console.log('🖼️ [FRONTEND IMAGE 전송] analysisImageUrl 길이:', context.langgraph.analysisImageUrl.value?.length);
    
    console.log('📤 [SAVE] 전송 데이터:', {
      question: question,
      q_mode: 'search',
      keyword: langGraphState,
      db_search_title: dbSearchTitleData,
      db_contents: dbContentsData,
      db_contents_length: dbContentsData.length,
      image: context.langgraph.analysisImageUrl.value
    });
    
    // 메시지 생성 API 호출
    const requestBody = { 
      question: question,
      q_mode: 'search',  // 첫 번째 질문은 q_mode를 'search'로 설정 (대화 제목 업데이트를 위해)
      assistant_response: answer,
      skip_llm: true,  // 첫 번째 질문은 LangGraph 답변만 사용, 별도 LLM 처리 안함
      keyword: JSON.stringify(langGraphState), // 전체 상태를 JSON으로 저장
      db_search_title: Array.isArray(dbSearchTitleData) ? JSON.stringify(dbSearchTitleData) : dbSearchTitleData,
      db_contents: JSON.stringify(dbContentsData), // 검색 결과 전체 정보 저장
      image: context.langgraph.analysisImageUrl.value,  // 이미지 URL 전송
      user_name: context.$store.state.user?.username || '사용자'
    };
    
    console.log('🖼️ [FRONTEND IMAGE 전송] 최종 requestBody.image 값:', requestBody.image);
    console.log('📤 [FRONTEND IMAGE 전송] 요청 본문 전체:', JSON.stringify(requestBody, null, 2));
    
    const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify(requestBody)
    });
    
    console.log('📥 [FRONTEND IMAGE 전송] 응답 상태:', response.status, response.statusText);
    
    if (response.ok) {
      await response.json();
      
      // 대화 제목 업데이트 (질문의 첫 50자로)
      if (context.$store.state.currentConversation) {
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
            // 스토어의 현재 대화 제목도 업데이트
            context.$store.commit('updateConversationTitle', {
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
      
      // 대화 목록 새로고침 제거 - UI refresh 방지
      console.log('✅ 대화 목록 새로고침 생략 (UI refresh 방지)');
      
    } else {
      console.error('❌ LangGraph 메시지 저장 실패:', response.status, response.statusText);
      const errorText = await response.text();
      console.error('❌ 오류 응답 내용:', errorText);
    }
  } catch (error) {
    console.error('LangGraph 메시지 저장 중 오류:', error);
  }
}

// LangGraph 결과를 백엔드에 저장하는 메서드
async function saveLangGraphMessageToBackend(question, answer, conversationId, context) {
  try {
    const token = localStorage.getItem('access_token');
    
    // LangGraph 결과 데이터 준비
    const messageData = {
      question: question,
      q_mode: 'search', // LangGraph 결과는 search 모드
      keyword: context.langgraph.extractedKeywords.value || null,
      db_search_title: context.langgraph.extractedDbSearchTitle.value ? JSON.stringify(context.langgraph.extractedDbSearchTitle.value) : null,
      db_contents: context.langgraph.searchResults.value ? JSON.stringify(context.langgraph.searchResults.value) : null,
      assistant_response: answer
    };
            
    const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(messageData)
    });
    
    if (!response.ok) {
      throw new Error(`메시지 저장 실패: ${response.status} ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('✅ LangGraph 메시지 저장 완료:', result);
    
    return result;
  } catch (error) {
    console.error('❌ LangGraph 메시지 저장 실패:', error);
    throw error;
  }
}

export default {
  executeLanggraphFlow,
  executeLangGraphWithSSE,
  fallbackLanggraphFlow,
  saveFallbackMessage,
  processLangGraphResult,
  processDirectLangGraphResult,
  saveLangGraphMessage,
  saveLangGraphMessageToBackend
};
