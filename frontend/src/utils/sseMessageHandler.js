/**
 * SSE 메시지 처리 유틸리티
 * Home.vue의 handleSSEMessage 함수를 분리하여 관리
 */

/**
 * SSE 메시지 처리 메인 함수
 * @param {Object} data - SSE 메시지 데이터
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */

export async function handleSSEMessage(data, context) {
  // 추가 질문은 별도 처리되므로 이 로직 제거
  // if (context.langgraph.isFollowupQuestion.value && (data.stage === 'A' || data.stage === 'B' || data.stage === 'C' || data.stage === 'D' || data.stage === 'E')) {
  //   console.log('🔒 추가 질문 중 - 랭그래프 영역 업데이트 방지:', data.stage);
  //   return;
  // }

  // DONE 메시지 처리 후 즉시 종료
  if (data.stage === 'DONE') {
    return await handleDoneMessage(data, context);
  }

  // 각 단계별 메시지 처리
  switch (data.stage) {
    case 'A':
      await handleStageA(data, context);
      break;
    case 'B':
      await handleStageB(data, context);
      break;
    case 'C':
      await handleStageC(data, context);
      break;
    case 'D':
      await handleStageD(data, context);
      break;
    case 'E':
      await handleStageE(data, context);
      break;
    case 'TEST':
      await handleTestMessage(data, context);
      break;
    case 'ERROR':
      await handleErrorMessage(data, context);
      break;
    default:
      // console.log('📡 알 수 없는 단계:', data.stage);
  }
}

/**
 * DONE 메시지 처리
 */
async function handleDoneMessage(data, context) {
  if (context.langgraph.isDoneProcessed.value) {
    // console.log('🔒 DONE 메시지 이미 처리됨 - 중복 처리 방지');
    return;
  }
  
  // console.log('🏁 DONE 메시지 수신 - 최종 UI 업데이트');
  context.langgraph.isDoneProcessed.value = true; // DONE 처리 완료 플래그 설정
  
  // 모든 로딩 상태 완료
  context.messages.isLoading.value = false;
  context.langgraph.isSearching.value = false;
  context.langgraph.isGeneratingAnswer.value = false;
  context.langgraph.isStreamingAnswer.value = false;
  
  // 최종 단계로 설정
  context.langgraph.currentStep.value = 4; // UI 4단계: 분석 결과 이미지 표시
  
  // 분석 결과 이미지 처리 (DONE 메시지에서만)
  console.log('🖼️ [SSE DONE] data.result 구조:', Object.keys(data.result || {}));
  console.log('🖼️ [SSE DONE] data.result.response 존재:', !!data.result?.response);
  
  if (data.result && data.result.response) {
    console.log('🖼️ [SSE DONE] data.result.response 구조:', Object.keys(data.result.response || {}));
    console.log('🖼️ [SSE DONE] data.result.response.analysis_image_url 값:', data.result.response.analysis_image_url);
  }
  
  if (data.result && data.result.analysis_image_url) {
    context.langgraph.analysisImageUrl.value = data.result.analysis_image_url;
    console.log('✅ [SSE DONE] 분석 이미지 URL 설정 (직접):', context.langgraph.analysisImageUrl.value);
  } else if (data.result && data.result.response && data.result.response.analysis_image_url) {
    context.langgraph.analysisImageUrl.value = data.result.response.analysis_image_url;
    console.log('✅ [SSE DONE] 분석 이미지 URL 설정 (response 내부):', context.langgraph.analysisImageUrl.value);
  } else {
    console.warn('⚠️ [SSE DONE] analysis_image_url을 찾을 수 없음');
  }
  
    // 최종 답변이 없으면 스트리밍된 답변 사용
    if (!context.langgraph.finalAnswer.value && context.langgraph.streamingAnswer.value) {
      context.langgraph.finalAnswer.value = context.langgraph.streamingAnswer.value;
      // console.log('🎯 DONE에서 최종 답변 설정:', context.langgraph.finalAnswer.value);
    }
    
  // 랭그래프 완료 플래그 먼저 설정 (복원 방지)
  context.langgraph.isLanggraphJustCompleted.value = true;
  
  // 최초 질문 완료 후 추가 질문으로 플래그 변경
  context.langgraph.isFollowupQuestion.value = true;
  console.log('✅ 최초 질문 완료 - isFollowupQuestion을 true로 설정');
    
    // 랭그래프 종료 후 최종 답변을 user 메시지의 ans 필드에 저장 (assistant 메시지 생성하지 않음)
    const answerToAdd = context.langgraph.finalAnswer.value || context.langgraph.streamingAnswer.value;
    
    console.log('📝 [DONE] 답변을 user 메시지의 ans 필드에 저장 시작:', {
      hasAnswer: !!answerToAdd,
      answerLength: answerToAdd ? answerToAdd.length : 0,
      hasConversation: !!context.$store.state.currentConversation,
      conversationId: context.$store.state.currentConversation?.id,
      currentMessageCount: context.$store.state.currentConversation?.messages?.length
    });
    
    if (answerToAdd && context.$store.state.currentConversation) {
      console.log('✅ [DONE] 조건 충족 - user 메시지 ans 필드 업데이트 진행');
      
      // 현재 대화의 마지막 user 메시지를 찾아서 ans 필드 업데이트
      const currentConversation = context.$store.state.currentConversation;
      if (currentConversation && currentConversation.messages && currentConversation.messages.length > 0) {
        // 마지막 user 메시지 찾기
        const userMessages = currentConversation.messages.filter(msg => msg.role === 'user');
        if (userMessages.length > 0) {
          const lastUserMessage = userMessages[userMessages.length - 1];
          lastUserMessage.ans = answerToAdd;
          console.log('✅ [DONE] user 메시지 ans 필드 업데이트 완료:', lastUserMessage.id);
        }
      }
    
    // LangGraph 결과를 백엔드에 저장
    try {
      console.log('🖼️ [DONE] saveLangGraphMessage 호출 전 analysisImageUrl:', context.langgraph.analysisImageUrl.value);
      
      const messageData = {
        result: {
          response: {
            answer: answerToAdd,
            analysis_image_url: context.langgraph.analysisImageUrl.value  // 이미지 URL 추가
          },
          keyword: context.langgraph.extractedKeywords.value,
          candidates_total: context.langgraph.extractedDbSearchTitle.value ? context.langgraph.extractedDbSearchTitle.value.map(title => ({ res_payload: { document_name: title } })) : []
        }
      };
      
      // console.log('🖼️ [DONE] saveLangGraphMessage 호출 데이터:', JSON.stringify(messageData, null, 2));
      
      const saveResult = await context.saveLangGraphMessage(messageData);
      console.log('✅ [DONE] LangGraph 메시지 저장 완료:', saveResult);
      
      // assistant 메시지를 사용하지 않으므로 backend_id 설정 제거됨
      
      // 대화 목록 새로고침 제거 - UI refresh 방지
      console.log('✅ [DONE] 대화 목록 새로고침 생략 (UI refresh 방지)');
    } catch (error) {
      console.error('❌ [DONE] LangGraph 메시지 저장 실패:', error);
    }
  } else {
    console.warn('⚠️ [DONE] 답변 메시지 추가 조건 미충족:', {
      answerToAdd: answerToAdd?.substring(0, 50),
      currentConversation: context.$store.state.currentConversation?.id
    });
  }
  
  // 랭그래프 상태 유지 - showLanggraph를 false로 변경하지 않음
  console.log('✅ [DONE] 랭그래프 UI 유지:', {
    showLanggraph: context.langgraph.showLanggraph.value,
    currentStep: context.langgraph.currentStep.value,
    hasAnswer: !!context.langgraph.finalAnswer.value
  });
  
  // 랭그래프 컨테이너로 스크롤
  context.scrollToLanggraph();
  
  // 5초 후 플래그 해제 (UI refresh 방지)
  setTimeout(() => {
    context.langgraph.isLanggraphJustCompleted.value = false;
    console.log('✅ [DONE] 랭그래프 완료 플래그 해제');
  }, 5000);
}

/**
 * A단계 (초기화) 메시지 처리
 */
async function handleStageA(data, context) {
  if (data.status === 'started') {
    context.langgraph.currentStep.value = 1;
    // originalInput은 executeLanggraphFlow에서 이미 설정되어 있으므로 유지
    if (!context.langgraph.originalInput.value && data.result && data.result.question) {
      context.langgraph.originalInput.value = data.result.question;
    }
    console.log('🔄 A단계 시작 - 원본 입력:', context.langgraph.originalInput.value);
  } else if (data.status === 'completed') {
    // console.log('✅ A단계 완료');
  }
}

/**
 * B단계 (키워드 증강) 메시지 처리
 */
async function handleStageB(data, context) {
  if (data.status === 'started') {
    context.langgraph.currentStep.value = 2;
    // console.log('🔄 B단계 시작 - 키워드 증강');
  } else if (data.status === 'completed') {
    if (data.result && data.result.keywords) {
      context.langgraph.augmentedKeywords.value = data.result.keywords.map((keyword, index) => ({
        id: `keyword-${index}`,
        text: keyword,
        category: context.langgraph.categorizeKeyword(keyword, index)
      }));
      context.langgraph.extractedKeywords.value = data.result.keywords;
      // console.log('✅ B단계 완료 - 키워드 증강:', context.langgraph.augmentedKeywords.value.length, '개');
    }
  }
}

/**
 * C단계 (RAG 검색) 메시지 처리
 */
async function handleStageC(data, context) {
  if (data.status === 'started') {
    context.langgraph.currentStep.value = 3;
    context.langgraph.isSearching.value = true;
    // console.log('🔄 C단계 시작 - RAG 검색');
  } else if (data.status === 'completed') {
    context.langgraph.isSearching.value = false;
    if (data.result && data.result.search_results) {
      context.langgraph.searchResults.value = data.result.search_results;
      context.langgraph.searchedDocuments.value = data.result.document_titles || [];
      context.langgraph.extractedDbSearchTitle.value = data.result.document_titles || [];
      // console.log('✅ C단계 완료 - 검색 결과:', context.langgraph.searchResults.value.length, '건');
    }
  }
}

/**
 * D단계 (문서 재순위) 메시지 처리
 */
async function handleStageD(data, context) {
  if (data.status === 'started') {
    // console.log('🔄 D단계 시작 - 문서 재순위');
  } else if (data.status === 'completed') {
    // console.log('✅ D단계 완료 - 문서 재순위');
  } else if (data.status === 'streaming') {
    // 스트리밍 답변 처리
    if (data.result && data.result.content) {
      context.langgraph.streamingAnswer.value = (context.langgraph.streamingAnswer.value || '') + data.result.content;
      context.langgraph.isStreamingAnswer.value = true;
      context.langgraph.isGeneratingAnswer.value = true;
      context.langgraph.currentStep.value = 4;
      
      // 스트리밍 답변을 실시간으로 표시
      context.$store.commit('updateStreamingMessage', context.langgraph.streamingAnswer.value);
    }
  }
}

/**
 * E단계 (답변 생성) 메시지 처리
 */
async function handleStageE(data, context) {
  if (data.status === 'started') {
    context.langgraph.isGeneratingAnswer.value = true;
    context.langgraph.currentStep.value = 4;
    // console.log('🔄 E단계 시작 - 답변 생성');
  } else if (data.status === 'completed') {
    context.langgraph.isGeneratingAnswer.value = false;
    context.langgraph.isStreamingAnswer.value = false;
    
    if (data.result && data.result.answer) {
      context.langgraph.finalAnswer.value = data.result.answer;
      // console.log('✅ E단계 완료 - 최종 답변 생성');
    }
  } else if (data.status === 'streaming') {
    // 스트리밍 답변 처리
    if (data.result && data.result.content) {
      context.langgraph.streamingAnswer.value = (context.langgraph.streamingAnswer.value || '') + data.result.content;
      context.langgraph.isStreamingAnswer.value = true;
      context.langgraph.isGeneratingAnswer.value = true;
      
      // 스트리밍 답변을 실시간으로 표시
      context.$store.commit('updateStreamingMessage', context.langgraph.streamingAnswer.value);
    }
  }
}

/**
 * 테스트 메시지 처리
 */
async function handleTestMessage(/* data, context */) {
  // console.log('🧪 테스트 메시지 수신:', data.result);
}

/**
 * 에러 메시지 처리
 */
async function handleErrorMessage(data, context) {
  console.error('❌ SSE 에러 메시지:', data.error);
  context.messages.isLoading.value = false;
  context.langgraph.isSearching.value = false;
  context.langgraph.isGeneratingAnswer.value = false;
  context.langgraph.isStreamingAnswer.value = false;
  
  // 에러 메시지를 사용자에게 표시
  if (context.$store.state.currentConversation) {
    const errorMessage = {
      id: Date.now() + Math.random(),
      conversation_id: context.$store.state.currentConversation.id,
      role: 'assistant',
      question: null,
      ans: `오류가 발생했습니다: ${data.error}`,
      created_at: new Date().toISOString()
    };
    
    context.$store.commit('addMessageToCurrentConversation', errorMessage);
  }
}

export default {
  handleSSEMessage
};
