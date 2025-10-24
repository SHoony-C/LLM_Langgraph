/**
 * 대화 복원 유틸리티
 * Home.vue의 대화 복원 관련 함수들을 분리하여 관리
 */

/**
 * 대화에서 랭그래프 정보 복원
 * @param {Object} conversation - 대화 객체
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function restoreLanggraphFromConversation(conversation, context) {
  // 대화 복원 상태 설정
  context.langgraph.isRestoringConversation.value = true;
  context.langgraph.isNewConversation.value = false; // 기존 대화 복원

  // 랭그래프 완료 직후에는 복원 스킵 (상태 유지)
  if (context.langgraph.isLanggraphJustCompleted.value) {
    console.log('✅ 랭그래프 완료 직후 - 복원 스킵하여 상태 유지:', {
      showLanggraph: context.langgraph.showLanggraph.value,
      currentStep: context.langgraph.currentStep.value,
      hasAnswer: !!context.langgraph.finalAnswer.value
    });
    context.langgraph.isRestoringConversation.value = false;
    // 캐시 업데이트 안 함 - 상태를 완전히 그대로 유지
    return;
  }

  // 캐시 확인 - 동일한 대화에 대해 이미 복원했다면 스킵 (성능 최적화)
  // 단, 새 대화 생성 직후에는 캐시를 무시하여 다른 대화로 전환 시 복원 가능하도록 함
  if (context.langgraph.lastRestoredConversationId.value === conversation.id && 
      !context.isNewConversation) {
    console.log('📋 동일한 대화 이미 복원됨 - 스킵:', conversation.id);
    context.langgraph.isRestoringConversation.value = false;
    return;
  }

  console.log('🔄 대화에서 랭그래프 정보 복원 시작:', conversation.id);

  try {
    // 동일한 대화를 다시 복원하는 경우 (fetchConversations 후) - 상태 유지
    if (context.langgraph.lastRestoredConversationId.value === conversation.id && 
        context.langgraph.showLanggraph.value && 
        context.langgraph.finalAnswer.value) {
      console.log('✅ 동일한 대화 - 랭그래프 상태 유지 (초기화 스킵)');
      context.langgraph.isRestoringConversation.value = false;
      return;
    }
    
    // 랭그래프 상태 초기화 - showLanggraph는 false로 하지 않음
    // context.langgraph.resetLanggraph(); // 주석 처리 - 복원 시에는 초기화하지 않음
    
    // 필요한 속성만 초기화
    context.langgraph.currentStep.value = 0;
    context.langgraph.originalInput.value = '';
    context.langgraph.augmentedKeywords.value = [];
    context.langgraph.searchResults.value = [];
    context.langgraph.finalAnswer.value = '';
    context.langgraph.streamingAnswer.value = '';
    context.langgraph.analysisImageUrl.value = '';
    context.langgraph.isSearching.value = false;
    context.langgraph.isGeneratingAnswer.value = false;
    context.langgraph.isStreamingAnswer.value = false;
    context.langgraph.extractedKeywords.value = null;
    context.langgraph.extractedDbSearchTitle.value = null;

    // 대화의 메시지들에서 랭그래프 정보 찾기
    const messages = conversation.messages || [];
    
    // 메시지가 비어있으면 경고하고 랭그래프 숨기기
    if (messages.length === 0) {
      console.warn('⚠️ 대화 메시지가 비어있습니다. 대화 ID:', conversation.id);
      // console.log('📋 전체 메시지 목록:', []);
      // console.log('📭 LangGraph 정보 없음 - 일반 대화로 처리');
      
      // 랭그래프 영역 숨기기
      context.langgraph.showLanggraph.value = false;
      
      context.langgraph.lastRestoredConversationId.value = conversation.id;
      context.langgraph.isRestoringConversation.value = false;
      return;
    }
    
    let langgraphMessage = null;

    // LangGraph 정보가 있는 메시지 찾기 (user 메시지 중 q_mode가 'search'이거나 keyword/db_contents가 있는 메시지)
    for (const message of messages) {
      // user 메시지만 확인 (백엔드에서 keyword, db_contents는 user 메시지에만 포함됨)
      if (message.role === 'user' && (message.q_mode === 'search' || message.keyword || message.db_contents)) {
        langgraphMessage = message;
        break;
      }
    }
    
    // 디버깅: 모든 메시지의 q_mode 출력
    // console.log('📋 전체 메시지 목록:', messages.map(m => ({
    //   id: m.id,
    //   role: m.role,
    //   q_mode: m.q_mode,
    //   has_keyword: !!m.keyword,
    //   has_db_contents: !!m.db_contents,
    //   has_image: !!m.image
    // })));

    if (langgraphMessage) {
      console.log('✅ LangGraph 메시지 발견:', langgraphMessage.id);
      
      // 랭그래프 UI 표시
      context.langgraph.showLanggraph.value = true;
      context.langgraph.currentStep.value = 4; // 최종 단계로 설정
      context.langgraph.originalInput.value = langgraphMessage.question || '';

      // 키워드 정보 복원 (전체 상태 또는 키워드 배열)
      if (langgraphMessage.keyword) {
        try {
          const keywordData = typeof langgraphMessage.keyword === 'string' 
            ? JSON.parse(langgraphMessage.keyword) 
            : langgraphMessage.keyword;
          
          // 전체 langGraphState 객체인 경우
          if (keywordData && typeof keywordData === 'object' && !Array.isArray(keywordData)) {
            // 전체 상태 복원
            if (keywordData.originalInput) {
              context.langgraph.originalInput.value = keywordData.originalInput;
            }
            if (keywordData.augmentedKeywords) {
              context.langgraph.augmentedKeywords.value = keywordData.augmentedKeywords;
            }
            if (keywordData.searchResults) {
              context.langgraph.searchResults.value = keywordData.searchResults;
            }
            if (keywordData.finalAnswer) {
              context.langgraph.finalAnswer.value = keywordData.finalAnswer;
            }
            if (keywordData.analysisImageUrl) {
              context.langgraph.analysisImageUrl.value = keywordData.analysisImageUrl;
            }
            if (keywordData.extractedKeywords) {
              context.langgraph.extractedKeywords.value = keywordData.extractedKeywords;
            }
            if (keywordData.extractedDbSearchTitle) {
              context.langgraph.extractedDbSearchTitle.value = keywordData.extractedDbSearchTitle;
              context.langgraph.searchedDocuments.value = keywordData.extractedDbSearchTitle;
            }
            console.log('✅ 전체 상태 복원 완료 (langGraphState):', {
              originalInput: context.langgraph.originalInput.value,
              augmentedKeywords: context.langgraph.augmentedKeywords.value.length,
              searchResults: context.langgraph.searchResults.value.length,
              finalAnswer: context.langgraph.finalAnswer.value ? '있음' : '없음',
              analysisImageUrl: context.langgraph.analysisImageUrl.value ? '있음' : '없음'
            });
          } else if (Array.isArray(keywordData)) {
            // 키워드 배열인 경우
            context.langgraph.augmentedKeywords.value = keywordData.map((keyword, index) => ({
              id: `keyword-${index}`,
              text: keyword,
              category: 'augmented'
            }));
            context.langgraph.extractedKeywords.value = keywordData;
            console.log('✅ 키워드 복원 완료:', keywordData.length, '개');
          }
        } catch (error) {
          console.warn('키워드 파싱 실패:', error);
        }
      }

      // 검색 결과 정보 복원 (db_contents가 별도로 있는 경우)
      if (langgraphMessage.db_contents) {
        try {
          const dbContents = JSON.parse(langgraphMessage.db_contents);
          if (Array.isArray(dbContents)) {
            context.langgraph.searchResults.value = dbContents;
            context.langgraph.searchedDocuments.value = dbContents.map(doc => doc.document_name || '제목 없음');
            context.langgraph.extractedDbSearchTitle.value = context.langgraph.searchedDocuments.value;
            console.log('✅ 검색 결과 복원 완료:', dbContents.length, '건');
          }
        } catch (error) {
          console.warn('검색 결과 파싱 실패:', error);
        }
      }

      // 답변 정보 복원 (keyword에서 복원되지 않은 경우)
      if (langgraphMessage.ans && !context.langgraph.finalAnswer.value) {
        context.langgraph.finalAnswer.value = langgraphMessage.ans;
        console.log('✅ 답변 복원 완료');
      }

      // 이미지 URL 복원 (keyword에서 복원되지 않은 경우)
      if (langgraphMessage.image && !context.langgraph.analysisImageUrl.value) {
        context.langgraph.analysisImageUrl.value = langgraphMessage.image;
        console.log('✅ 분석 이미지 URL 복원 완료');
      }

      // console.log('✅ 랭그래프 정보 복원 완료');
    } else {
      console.log('📭 LangGraph 정보 없음 - 일반 대화로 처리');
    }

    // 복원된 대화 ID 캐시
    context.langgraph.lastRestoredConversationId.value = conversation.id;

  } catch (error) {
    console.error('❌ 랭그래프 정보 복원 실패:', error);
  } finally {
    context.langgraph.isRestoringConversation.value = false;
  }
}

/**
 * 관련 대화에서 LangGraph 정보 찾아서 복원
 * @param {number} conversationId - 대화 ID
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function findAndRestoreRelatedLangGraph(conversationId, context) {
  console.log('관련 대화 찾기 시작:', conversationId);

  try {
    const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/related`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log('관련 대화 검색 결과:', result);

    if (result.related_conversation) {
      console.log('✅ 관련 대화 발견:', result.related_conversation.id);
      
      // 관련 대화의 메시지들을 현재 대화에 추가
      const relatedMessages = result.related_conversation.messages || [];
      
      for (const message of relatedMessages) {
        context.$store.commit('addMessageToCurrentConversation', message);
      }

      // 랭그래프 정보 복원
      await restoreLanggraphFromConversation(result.related_conversation, context);
      
      console.log('✅ 관련 대화에서 랭그래프 정보 복원 완료');
    } else {
      console.log('📭 관련 대화 없음');
    }

  } catch (error) {
    console.error('❌ 관련 대화 찾기 실패:', error);
  }
}

/**
 * 새로고침 시 대화 복원 (URL 파라미터 기반)
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function restoreCurrentConversationOnRefresh(context) {
  try {
    // URL에서 conversation_id 파라미터 확인
    const urlParams = new URLSearchParams(window.location.search);
    const conversationId = urlParams.get('conversation_id');

    if (!conversationId) {
      console.log('URL에 conversation_id 파라미터 없음');
      return;
    }

    console.log('🔄 URL 파라미터로 대화 복원 시작:', conversationId);

    // 대화 정보 가져오기
    const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log('대화 정보 로드 완료:', result);

    // Vuex 스토어에 대화 설정
    context.$store.commit('setCurrentConversation', {
      id: parseInt(conversationId),
      messages: result.messages || []
    });

    // 랭그래프 정보 복원
    await restoreLanggraphFromConversation({
      id: parseInt(conversationId),
      messages: result.messages || []
    }, context);

    console.log('✅ URL 파라미터로 대화 복원 완료');

  } catch (error) {
    console.error('❌ URL 파라미터로 대화 복원 실패:', error);
  }
}

/**
 * 새로고침 시 현재 대화 복원
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export async function restoreCurrentConversation(context) {
  try {
    const currentConversation = context.$store.state.currentConversation;
    if (!currentConversation || !currentConversation.id) {
      console.log('복원할 대화가 없습니다.');
      return;
    }

    console.log('🔄 현재 대화 복원 시작:', currentConversation.id);

    // 대화 정보 다시 가져오기
    const response = await fetch(`http://localhost:8000/api/conversations/${currentConversation.id}/messages`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log('대화 정보 다시 로드 완료:', result);

    // Vuex 스토어에 대화 업데이트
    context.$store.commit('setCurrentConversation', {
      id: currentConversation.id,
      messages: result.messages || []
    });

    // 랭그래프 정보 복원
    await restoreLanggraphFromConversation({
      id: currentConversation.id,
      messages: result.messages || []
    }, context);

    console.log('✅ 현재 대화 복원 완료');

  } catch (error) {
    console.error('❌ 현재 대화 복원 실패:', error);
  }
}

/**
 * 현재 메시지에서 랭그래프 상태 복원 (피드백 후용)
 * @param {Object} context - Vue 컴포넌트 컨텍스트 (this)
 */
export function restoreLanggraphFromCurrentMessages(context) {
  try {
    const currentConversation = context.$store.state.currentConversation;
    if (!currentConversation || !currentConversation.messages) {
      return;
    }

    console.log('🔄 현재 메시지에서 랭그래프 상태 복원 시작');

    // LangGraph 정보가 있는 메시지 찾기
    const messages = currentConversation.messages;
    
    // 메시지가 비어있으면 랭그래프 숨기기
    if (messages.length === 0) {
      console.warn('⚠️ 현재 대화 메시지가 비어있습니다.');
      context.langgraph.showLanggraph.value = false;
      return;
    }
    let langgraphMessage = null;

    for (const message of messages) {
      if (message.q_mode === 'search' || message.keyword || message.db_contents) {
        langgraphMessage = message;
        break;
      }
    }

    if (langgraphMessage) {
      console.log('✅ LangGraph 메시지 발견, 상태 복원:', langgraphMessage.id);
      
      // 랭그래프 UI 표시
      context.langgraph.showLanggraph.value = true;
      context.langgraph.currentStep.value = 4;
      context.langgraph.originalInput.value = langgraphMessage.question || '';

      // 키워드 복원 (전체 상태 또는 키워드 배열)
      if (langgraphMessage.keyword) {
        try {
          const keywordData = typeof langgraphMessage.keyword === 'string' 
            ? JSON.parse(langgraphMessage.keyword) 
            : langgraphMessage.keyword;
          
          // 전체 langGraphState 객체인 경우
          if (keywordData && typeof keywordData === 'object' && !Array.isArray(keywordData)) {
            // 전체 상태 복원
            if (keywordData.originalInput) {
              context.langgraph.originalInput.value = keywordData.originalInput;
            }
            if (keywordData.augmentedKeywords) {
              context.langgraph.augmentedKeywords.value = keywordData.augmentedKeywords;
            }
            if (keywordData.searchResults) {
              context.langgraph.searchResults.value = keywordData.searchResults;
            }
            if (keywordData.finalAnswer) {
              context.langgraph.finalAnswer.value = keywordData.finalAnswer;
            }
            if (keywordData.analysisImageUrl) {
              context.langgraph.analysisImageUrl.value = keywordData.analysisImageUrl;
            }
            if (keywordData.extractedKeywords) {
              context.langgraph.extractedKeywords.value = keywordData.extractedKeywords;
            }
            if (keywordData.extractedDbSearchTitle) {
              context.langgraph.extractedDbSearchTitle.value = keywordData.extractedDbSearchTitle;
              context.langgraph.searchedDocuments.value = keywordData.extractedDbSearchTitle;
            }
          } else if (Array.isArray(keywordData)) {
            // 키워드 배열인 경우
            context.langgraph.augmentedKeywords.value = keywordData.map((keyword, index) => ({
              id: `keyword-${index}`,
              text: keyword,
              category: 'augmented'
            }));
            context.langgraph.extractedKeywords.value = keywordData;
          }
        } catch (error) {
          console.warn('키워드 파싱 실패:', error);
        }
      }

      // 검색 결과 복원 (db_contents가 별도로 있는 경우)
      if (langgraphMessage.db_contents) {
        try {
          const dbContents = JSON.parse(langgraphMessage.db_contents);
          if (Array.isArray(dbContents)) {
            context.langgraph.searchResults.value = dbContents;
            context.langgraph.searchedDocuments.value = dbContents.map(doc => doc.document_name || '제목 없음');
            context.langgraph.extractedDbSearchTitle.value = context.langgraph.searchedDocuments.value;
          }
        } catch (error) {
          console.warn('검색 결과 파싱 실패:', error);
        }
      }

      // 답변 복원 (keyword에서 복원되지 않은 경우)
      if (langgraphMessage.ans && !context.langgraph.finalAnswer.value) {
        context.langgraph.finalAnswer.value = langgraphMessage.ans;
      }

      // 이미지 URL 복원 (keyword에서 복원되지 않은 경우)
      if (langgraphMessage.image && !context.langgraph.analysisImageUrl.value) {
        context.langgraph.analysisImageUrl.value = langgraphMessage.image;
      }

      console.log('✅ 랭그래프 상태 복원 완료');
    }

  } catch (error) {
    console.error('❌ 랭그래프 상태 복원 실패:', error);
  }
}

// 메시지에서 랭그래프 상태 복원
function restoreLanggraphFromMessages(messages, context) {
  try {
    // 랭그래프 결과가 있는 메시지 찾기
    const langgraphMessage = messages.find(msg => 
      msg.role === 'assistant' && 
      msg.langgraph_result && 
      msg.q_mode === 'search'
    );
    
    if (langgraphMessage && langgraphMessage.langgraph_result) {
      const result = langgraphMessage.langgraph_result;
      
      // 랭그래프 UI 상태 복원
      context.langgraph.showLanggraph.value = true;
      context.langgraph.currentStep.value = 4; // 최종 단계
      context.langgraph.originalInput.value = result.question || '';
      context.langgraph.finalAnswer.value = result.answer || '';
      
      // 검색 결과 복원
      if (result.documents && Array.isArray(result.documents)) {
        context.langgraph.searchResults.value = result.documents.map(doc => ({
          title: doc.title || '제목 없음',
          content: doc.content || '',
          source: doc.source || '',
          score: doc.score || 0
        }));
      }
      
      // 키워드 복원
      if (result.keyword) {
        context.langgraph.extractedKeywords.value = result.keyword;
      }
      
      console.log('✅ 랭그래프 상태 복원 완료:', {
        step: context.langgraph.currentStep.value,
        searchResults: context.langgraph.searchResults.value.length,
        hasKeywords: !!context.langgraph.extractedKeywords.value
      });
    } else {
      console.log('복원할 랭그래프 상태가 없습니다.');
    }
  } catch (error) {
    console.error('랭그래프 상태 복원 오류:', error);
  }
}

export default {
  restoreLanggraphFromConversation,
  findAndRestoreRelatedLangGraph,
  restoreCurrentConversationOnRefresh,
  restoreCurrentConversation,
  restoreLanggraphFromCurrentMessages,
  restoreLanggraphFromMessages
};
