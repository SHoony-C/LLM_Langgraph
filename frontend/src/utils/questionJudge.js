/**
 * 질문 유형 판별 및 분기 처리 유틸리티
 * 최초 질문과 추가 질문을 구분하여 적절한 API 엔드포인트로 라우팅
 */

/**
 * 질문이 최초 질문인지 추가 질문인지 판별
 * @param {string} question - 사용자 질문
 * @param {number|null} conversationId - 대화 ID (null이면 새 대화)
 * @param {Array} conversationHistory - 대화 히스토리 (선택사항)
 * @returns {Object} 판별 결과
 */
export function judgeQuestionType(question, conversationId, conversationHistory = []) {
    // console.log('[QUESTION_JUDGE] 질문 유형 판별 시작');
    // console.log('[QUESTION_JUDGE] - 질문:', question);
    // console.log('[QUESTION_JUDGE] - 대화 ID:', conversationId);
    // console.log('[QUESTION_JUDGE] - 히스토리 길이:', conversationHistory.length);

    // 1. conversationId가 null이거나 undefined면 새 대화 (최초 질문)
    if (!conversationId) {
        // console.log('[QUESTION_JUDGE] ✅ 새 대화 - 최초 질문으로 판별');
        return {
            isFirstQuestion: true,
            questionType: 'first',
            apiEndpoint: '/api/langgraph/stream',
            reason: '새 대화'
        };
    }

    // 2. 대화 히스토리가 비어있으면 최초 질문
    if (!conversationHistory || conversationHistory.length === 0) {
        console.log('[QUESTION_JUDGE] ✅ 빈 히스토리 - 최초 질문으로 판별');
        return {
            isFirstQuestion: true,
            questionType: 'first',
            apiEndpoint: '/api/langgraph/stream',
            reason: '빈 대화 히스토리'
        };
    }

    // 3. conversationId가 있고 대화 히스토리가 있으면 추가 질문
    // (LangGraph 정보 유무와 관계없이 기존 대화가 있으면 추가 질문)
    console.log('[QUESTION_JUDGE] ✅ 기존 대화 존재 - 추가 질문으로 판별');
    console.log('[QUESTION_JUDGE] - 대화 ID:', conversationId);
    console.log('[QUESTION_JUDGE] - 히스토리 메시지 수:', conversationHistory.length);
    
    return {
        isFirstQuestion: false,
        questionType: 'followup',
        apiEndpoint: '/api/normal_llm/langgraph/followup/stream',
        reason: '기존 대화의 추가 질문'
    };
}

/**
 * 질문을 적절한 API 엔드포인트로 전송
 * @param {string} question - 사용자 질문
 * @param {number|null} conversationId - 대화 ID
 * @param {Array} conversationHistory - 대화 히스토리
 * @param {Object} options - 추가 옵션
 * @returns {Promise} API 응답
 */
export async function sendQuestionToAppropriateEndpoint(question, conversationId, conversationHistory = [], options = {}) {
    console.log('[QUESTION_ROUTER] 질문 라우팅 시작');
    
    // 질문 유형 판별
    const judgment = judgeQuestionType(question, conversationId, conversationHistory);
    
    console.log('[QUESTION_ROUTER] 판별 결과:', judgment);
    
    // API 요청 데이터 구성
    const requestData = {
        question: question,
        conversation_id: conversationId,
        generate_image: options.generateImage || false,
        include_langgraph_context: !judgment.isFirstQuestion, // 추가 질문일 때만 컨텍스트 포함
        langgraph_context: !judgment.isFirstQuestion ? {
            documents: conversationHistory
                .filter(msg => msg.langgraph_result?.documents)
                .flatMap(msg => msg.langgraph_result.documents)
                .slice(0, 5) // 최대 5개 문서만
        } : null
    };

    console.log('[QUESTION_ROUTER] 요청 데이터:', requestData);
    console.log('[QUESTION_ROUTER] API 엔드포인트:', judgment.apiEndpoint);

    try {
        // 적절한 엔드포인트로 요청 전송
        const response = await fetch(judgment.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        console.log('[QUESTION_ROUTER] ✅ API 요청 성공');
        
        return {
            response: response,
            judgment: judgment,
            requestData: requestData
        };

    } catch (error) {
        console.error('[QUESTION_ROUTER] ❌ API 요청 실패:', error);
        throw error;
    }
}

/**
 * 대화 히스토리에서 LangGraph 정보 추출
 * @param {Array} conversationHistory - 대화 히스토리
 * @returns {Object} LangGraph 컨텍스트
 */
export function extractLangGraphContext(conversationHistory) {
    console.log('[CONTEXT_EXTRACTOR] LangGraph 컨텍스트 추출 시작');
    
    const context = {
        documents: [],
        keywords: [],
        hasSearchResults: false
    };

    if (!conversationHistory || conversationHistory.length === 0) {
        console.log('[CONTEXT_EXTRACTOR] 빈 히스토리');
        return context;
    }

    // LangGraph 정보가 있는 메시지 찾기
    for (const msg of conversationHistory) {
        if (msg.langgraph_result?.documents) {
            context.documents.push(...msg.langgraph_result.documents);
            context.hasSearchResults = true;
        }
        
        if (msg.keyword) {
            try {
                const keywords = typeof msg.keyword === 'string' 
                    ? JSON.parse(msg.keyword) 
                    : msg.keyword;
                if (Array.isArray(keywords)) {
                    context.keywords.push(...keywords);
                }
            } catch (e) {
                console.warn('[CONTEXT_EXTRACTOR] 키워드 파싱 실패:', e);
            }
        }
    }

    // 중복 제거 및 제한
    context.documents = context.documents.slice(0, 5);
    context.keywords = [...new Set(context.keywords)].slice(0, 10);

    console.log('[CONTEXT_EXTRACTOR] 추출된 컨텍스트:', {
        documentsCount: context.documents.length,
        keywordsCount: context.keywords.length,
        hasSearchResults: context.hasSearchResults
    });

    return context;
}

/**
 * 질문 유형에 따른 UI 상태 업데이트
 * @param {Object} judgment - 판별 결과
 * @param {Function} updateUI - UI 업데이트 함수
 */
export function updateUIForQuestionType(judgment, updateUI) {
    console.log('[UI_UPDATER] UI 업데이트 시작:', judgment);
    
    if (judgment.isFirstQuestion) {
        // 최초 질문 UI
        updateUI({
            showLangGraphProgress: true,
            showSearchResults: true,
            questionType: 'first',
            statusMessage: 'RAG 검색 및 분석을 진행합니다...'
        });
    } else {
        // 추가 질문 UI
        updateUI({
            showLangGraphProgress: false,
            showSearchResults: false,
            questionType: 'followup',
            statusMessage: '이전 대화 맥락을 고려하여 답변합니다...'
        });
    }
}

/**
 * 에러 처리 및 폴백 로직
 * @param {Error} error - 발생한 에러
 * @param {Object} judgment - 원래 판별 결과
 * @returns {Object} 폴백 처리 결과
 */
export function handleQuestionError(error, judgment) {
    console.error('[ERROR_HANDLER] 질문 처리 오류:', error);
    
    // LangGraph 실패 시 일반 LLM으로 폴백
    if (judgment.isFirstQuestion && error.message.includes('langgraph')) {
        console.log('[ERROR_HANDLER] LangGraph 실패 - 일반 LLM으로 폴백');
        return {
            ...judgment,
            isFirstQuestion: false,
            questionType: 'fallback',
            apiEndpoint: '/api/chat/stream',
            reason: 'LangGraph 실패로 인한 폴백'
        };
    }
    
    // 일반적인 에러 처리
    return {
        error: error.message,
        fallback: true,
        apiEndpoint: '/api/chat/stream'
    };
}

export default {
    judgeQuestionType,
    sendQuestionToAppropriateEndpoint,
    extractLangGraphContext,
    updateUIForQuestionType,
    handleQuestionError
};
