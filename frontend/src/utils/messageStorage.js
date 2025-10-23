/**
 * LangGraph 메시지 저장 유틸리티
 */

/**
 * LangGraph 결과를 백엔드에 저장
 * @param {Object} result - LangGraph 실행 결과
 * @param {Object} context - Vue 컴포넌트 컨텍스트
 */
export async function saveLangGraphMessage(result, context) {
  try {
    if (!context.$store.state.currentConversation) {
      console.error('⚠️ LangGraph 메시지 저장 실패: 현재 대화가 없습니다.');
      return;
    }
    
    const conversationId = context.$store.state.currentConversation.id;
    const question = context.langgraph.originalInput.value || 'LangGraph 분석 요청';
    
    // console.log('💾 [SAVE] originalInput:', context.langgraph.originalInput.value);
    // console.log('💾 [SAVE] 저장할 질문:', question);
    
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
    
    // 이미지 URL 추출 (여러 소스에서 시도)
    let imageUrl = context.langgraph.analysisImageUrl.value;
    if (!imageUrl && result.result && result.result.response && result.result.response.analysis_image_url) {
      imageUrl = result.result.response.analysis_image_url;
    } else if (!imageUrl && result.result && result.result.analysis_image_url) {
      imageUrl = result.result.analysis_image_url;
    }
    
    // LangGraph 전체 상태를 JSON으로 저장 (복원을 위해)
    const langGraphState = {
      originalInput: context.langgraph.originalInput.value,
      augmentedKeywords: context.langgraph.augmentedKeywords.value,
      searchResults: context.langgraph.searchResults.value.slice(0, 5),
      finalAnswer: answer,
      analysisImageUrl: imageUrl,  // 추출된 이미지 URL 사용
      currentStep: context.langgraph.currentStep.value,
      extractedKeywords: keywordData,
      extractedDbSearchTitle: dbSearchTitleData
    };
    
    // db_contents 생성 (llm_bu.py 참고)
    const db_contents_list = [];
    const searchResults = context.langgraph.searchResults.value || [];
    
    if (searchResults && searchResults.length > 0) {
      for (let idx = 0; idx < Math.min(5, searchResults.length); idx++) {
        const candidate = searchResults[idx];
        const payload = candidate.res_payload || {};
        const vector_data = payload.vector || {};
        
        // image_url 처리 - Qdrant 구조에 맞게
        let image_url_value = '';
        if (payload.image_url) {
          const img_url = payload.image_url;
          if (Array.isArray(img_url) && img_url.length > 0) {
            image_url_value = img_url[0];
          } else if (typeof img_url === 'string') {
            image_url_value = img_url;
          }
        } else if (vector_data.image_url) {
          const img_url = vector_data.image_url;
          if (Array.isArray(img_url) && img_url.length > 0) {
            image_url_value = img_url[0];
          } else if (typeof img_url === 'string') {
            image_url_value = img_url;
          }
        }
        
        const db_content = {
          rank: idx + 1,
          document_name: payload.document_name || candidate.title || '',
          score: candidate.res_score || candidate.score || 0,
          combined_score: candidate.combined_score || candidate.res_score || candidate.score || 0,
          relevance_score: candidate.res_relevance || 0,
          text: vector_data.text || '',
          summary_purpose: vector_data.summary_purpose || '',
          summary_result: vector_data.summary_result || candidate.summary || '',
          summary_fb: vector_data.summary_fb || '',
          image_url: image_url_value,
          res_id: candidate.res_id || ''
        };
        db_contents_list.push(db_content);
      }
    }
    
    const db_contents_json = JSON.stringify(db_contents_list);
    
    console.log('📤 [SAVE] 전송 데이터:', {
      question: question,
      q_mode: 'search',
      keyword: langGraphState,
      db_search_title: dbSearchTitleData,
      db_contents: db_contents_list,
      db_contents_length: db_contents_list.length,
      image: imageUrl  // 추출된 이미지 URL 사용
    });
    
    // 메시지 생성 API 호출
    const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify({ 
        question: question,
        q_mode: 'search',
        assistant_response: answer,
        skip_llm: true,
        keyword: JSON.stringify(langGraphState),
        db_search_title: Array.isArray(dbSearchTitleData) ? JSON.stringify(dbSearchTitleData) : dbSearchTitleData,
        db_contents: db_contents_json,  // db_contents 추가
        image: imageUrl,  // 추출된 이미지 URL 사용
        user_name: context.$store.state.user?.username || '사용자'
      })
    });
    
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
      
      // 대화 목록 새로고침
      await context.$store.dispatch('fetchConversations');
      
    } else {
      console.error('❌ LangGraph 메시지 저장 실패:', response.status, response.statusText);
      const errorText = await response.text();
      console.error('❌ 오류 응답 내용:', errorText);
    }
  } catch (error) {
    console.error('LangGraph 메시지 저장 중 오류:', error);
  }
}

export default {
  saveLangGraphMessage
};

