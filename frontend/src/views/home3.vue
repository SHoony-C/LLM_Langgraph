    // SSE 메시지 처리
    handleSSEMessage(data) {
      console.log('📡 SSE 메시지 수신:', data);
      console.log('📡 메시지 단계:', data.stage);
      console.log('📡 메시지 상태:', data.status);
      console.log('📡 메시지 결과:', data.result);
      console.log('📡 현재 단계:', this.currentStep);
      
      // 단계별 처리
      if (data.stage === 'A' && data.status === 'completed') {
        console.log('🔄 1단계: 입력 정리 완료');
        this.currentStep = 1;
        this.originalInput = data.result.question || data.result.message;
        this.isSearching = false;
        this.$nextTick(() => {
          this.$forceUpdate();
          console.log('✅ 1단계 UI 업데이트 완료');
        });
      } else if (data.stage === 'B' && data.status === 'completed') {
        console.log('🔄 2단계: 키워드 생성 완료');
        this.currentStep = 2;
        this.isSearching = true;
        
        const keywords = data.result.keywords || [];
        this.augmentedKeywords = keywords.map((keyword, index) => ({
          id: index + 1,
          text: keyword,
          category: '키워드'
        }));
        
        console.log('🔑 생성된 키워드:', this.augmentedKeywords);
        this.$nextTick(() => {
          this.$forceUpdate();
          console.log('✅ 2단계 UI 업데이트 완료');
        });
      } else if (data.stage === 'C' && data.status === 'completed') {
        console.log('🔄 3단계: RAG 검색/재순위 완료');
        this.currentStep = 3;
        this.isSearching = true;
        
        const docCount = data.result.documents_count || data.result.top_documents || 0;
        console.log('📄 검색된 문서 수:', docCount);
        
        this.$nextTick(() => {
          this.$forceUpdate();
          console.log('✅ 3단계 UI 업데이트 완료');
        });
      } else if (data.stage === 'D' && data.status === 'completed') {
        console.log('🔄 4단계: 최종 답변 생성 완료');
        this.currentStep = 4;
        this.isSearching = false;
        
        console.log('🎯 최종 답변 미리보기:', data.result.answer);
        
        // 이미지 URL 처리 (강화된 디버깅)
        console.log('🔍 4단계 데이터 전체 확인:', data.result);
        console.log('🔍 analysis_image_url 필드 확인:', data.result.analysis_image_url);
        console.log('🔍 data.result 타입:', typeof data.result);
        console.log('🔍 data.result 키들:', Object.keys(data.result || {}));
        
        // 여러 경로에서 이미지 URL 찾기
        let imageUrl = null;
        if (data.result.analysis_image_url) {
          imageUrl = data.result.analysis_image_url;
          console.log('🖼️ D단계에서 이미지 URL 발견:', imageUrl);
        }
        
        if (imageUrl) {
          this.analysisImageUrl = imageUrl;
          this.lastImageUrl = imageUrl; // 디버깅용 저장
          console.log('🖼️ 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
          this.$forceUpdate(); // 강제 UI 업데이트
        } else {
          console.log('⚠️ D단계에서 analysis_image_url을 찾을 수 없습니다');
          console.log('⚠️ 사용 가능한 필드들:', Object.keys(data.result || {}));
        }
        
        this.$nextTick(() => {
          this.$forceUpdate();
          console.log('✅ 4단계 UI 업데이트 완료');
        });
      } else if (data.stage === 'DONE') {
        console.log('🏁 LangGraph 실행 완료');
        // SSE 결과를 기존 API 형식으로 변환
        const apiResult = {
          status: "success",
          result: data.result,
          tags: data.keyword ? data.keyword.join(', ') : (data.result.keyword ? data.result.keyword.join(', ') : null),
          db_search_title: data.candidates_total ? `${data.candidates_total.length}건` : null,
          message: "LangGraph 실행 완료 (SSE)"
        };
        this.processDirectLangGraphResult(apiResult);
      }
    },
    
    handleWebSocketMessage(data) {
      console.log('📡 WebSocket 메시지 수신:', data);
      console.log('📡 메시지 노드:', data.node);
      console.log('📡 메시지 상태:', data.status);
      console.log('📡 메시지 데이터:', data.data);
      console.log('📡 현재 단계:', this.currentStep);
      console.log('📡 현재 키워드 개수:', this.augmentedKeywords?.length || 0);
      
      if (data.node === 'node_init' && data.status === 'completed') {
        console.log('🔄 1단계: 초기화 완료');
        this.currentStep = 1;
        this.originalInput = data.data.result;
        this.isSearching = false;
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
          console.log('✅ 1단계 UI 업데이트 완료');
        });
      } else if (data.node === 'node_rc_keyword' && data.status === 'completed') {
        console.log('🔄 2단계: 키워드 증강 시작');
        console.log('🔑 키워드 노드 완료 - 전체 데이터:', data);
        console.log('🔑 키워드 노드 완료 - result 데이터:', data.data?.result);
        console.log('🔑 키워드 노드 완료 - result 타입:', typeof data.data?.result);
        console.log('🔑 키워드 노드 완료 - result 길이:', data.data?.result?.length);
        
        if (data.data && data.data.result && Array.isArray(data.data.result)) {
          this.currentStep = 2;
          this.isSearching = true; // 키워드 생성 완료 후 검색 시작
          this.augmentedKeywords = data.data.result.map((keyword, index) => ({
            id: index + 1,
            text: keyword,
            category: '키워드'
          }));
          
          // 키워드 추출하여 저장
          this.extractedKeywords = data.data.result;
          console.log('🔑 extractedKeywords 설정됨:', this.extractedKeywords);
          console.log('🔑 augmentedKeywords 설정됨:', this.augmentedKeywords);
          
          // 강제 리렌더링
          this.$nextTick(() => {
            this.$forceUpdate();
            console.log('✅ 2단계 UI 업데이트 완료 - 키워드 표시됨');
          });
        } else {
          console.error('🔑 키워드 데이터 형식 오류:', data);
        }
      } else if (data.node === 'node_rc_rag' && data.status === 'completed') {
        console.log('🔄 3단계: DB 검색 완료');
        console.log('📊 RAG 노드 완료 - 데이터:', data.data.result);
        this.currentStep = 3; // 3단계로 이동 (답변 생성)
        this.isSearching = false; // 검색 완료
        this.isGeneratingAnswer = true; // 답변 생성 시작
        
        // 검색 결과를 올바른 구조로 저장
        this.searchResults = data.data.result;
        console.log('💾 검색 결과 저장:', this.searchResults);
        
        // 검색된 문서 제목 추출하여 저장
        if (data.data.result && data.data.result.length > 0) {
          this.extractedDbSearchTitle = data.data.result.map(item => 
            item.res_payload?.document_name || '제목 없음'
          );
          console.log('📄 추출된 문서 제목:', this.extractedDbSearchTitle);
        } else {
          this.extractedDbSearchTitle = '검색 결과 없음';
        }
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
          console.log('✅ 3단계 UI 업데이트 완료 - 검색 결과 표시됨');
        });
      } else if (data.node === 'node_rc_rerank' && data.status === 'completed') {
        // 재순위 결과 처리
      } else if ((data.node === 'node_rc_answer' || data.node === 'node_rc_plain_answer') && data.status === 'completed') {
        console.log('🔄 4단계: 최종 답변 생성 완료');
        this.isGeneratingAnswer = false; // 답변 생성 완료
        console.log(`📝 ${data.node} 노드 완료 - 데이터:`, data.data.result);
        this.currentStep = 4;
        this.finalAnswer = data.data.result.answer || data.data.result;
        console.log('🎯 finalAnswer 설정됨:', this.finalAnswer);
        
        // LangGraph 실행 결과에서 필요한 데이터 추출
        console.log('🔍 node_rc_answer 완료 - 전체 데이터:', data.data.result);
        
        if (data.data.result) {
          // 키워드 증강 목록 저장
          if (data.data.result.keyword) {
            this.extractedKeywords = data.data.result.keyword;
            console.log('🔑 추출된 키워드:', this.extractedKeywords);
          } else {
            console.log('⚠️ 키워드 데이터가 없습니다');
          }
          
          // 검색된 문서 제목들 저장
          if (data.data.result.db_search_title) {
            this.extractedDbSearchTitle = data.data.result.db_search_title;
            console.log('📄 추출된 문서 제목:', this.extractedDbSearchTitle);
          } else {
            console.log('⚠️ 문서 제목 데이터가 없습니다');
          }
          
          // 이미지 URL 처리 (강화된 검색)
          console.log('🔍 WebSocket 4단계 데이터 전체 확인:', data.data.result);
          console.log('🔍 WebSocket analysis_image_url 필드 확인:', data.data.result.analysis_image_url);
          
          let imageUrl = null;
          
          // 여러 경로에서 이미지 URL 찾기
          if (data.data.result.analysis_image_url) {
            imageUrl = data.data.result.analysis_image_url;
            console.log('🖼️ WebSocket - data.data.result에서 이미지 URL 발견:', imageUrl);
          } else if (data.data.result.response && data.data.result.response.analysis_image_url) {
            imageUrl = data.data.result.response.analysis_image_url;
            console.log('🖼️ WebSocket - data.data.result.response에서 이미지 URL 발견:', imageUrl);
          }
          
          if (imageUrl) {
            this.analysisImageUrl = imageUrl;
            this.lastImageUrl = imageUrl; // 디버깅용 저장
            console.log('🖼️ WebSocket 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
          } else {
            console.log('⚠️ WebSocket 분석 이미지 URL 데이터가 없습니다');
            console.log('⚠️ 사용 가능한 필드들:', Object.keys(data.data.result || {}));
            if (data.data.result.response) {
              console.log('⚠️ response 필드들:', Object.keys(data.data.result.response || {}));
            }
          }
          
          // q_mode 확인
          if (data.data.result.q_mode) {
            console.log('🔍 q_mode:', data.data.result.q_mode);
          } else {
            console.log('⚠️ q_mode 데이터가 없습니다');
          }
        } else {
          console.log('❌ data.data.result가 없습니다');
        }
        
        // LangGraph 완료 후 결과 저장 (즉시 실행)
        console.log('LangGraph 완료, 저장 함수 호출 시작...');
        console.log('저장할 데이터 확인:');
        console.log('  - 질문:', this.originalInput);
        console.log('  - 답변:', this.finalAnswer);
        console.log('  - 키워드:', this.extractedKeywords);
        console.log('  - 문서제목:', this.extractedDbSearchTitle);
        
        // 첫 번째 질문 완료 후 상태 변경 (실시간 처리 완료 시점)
        this.isFirstQuestionInSession = false;
        this.isNewConversation = false;
        console.log('🎯 첫 번째 질문 실시간 처리 완료 - 상태 변경');
        
        // 저장 함수 즉시 호출 (지연 제거)
        console.log('🔄 저장 함수 즉시 호출...');
        console.log('🔄 saveLangGraphMessageFromWebSocket 함수 호출 시작');
        
        // 함수 호출 전 상태 확인
        console.log('📊 저장 함수 호출 전 상태:');
        console.log('  - isSavingMessage:', this.isSavingMessage);
        console.log('  - saveStatus:', this.saveStatus);
        console.log('  - currentConversation:', this.$store.state.currentConversation);
        
        // 저장 함수 호출 (await 사용하여 완료까지 대기)
        this.saveLangGraphMessageFromWebSocket().then(() => {
          console.log('✅ LangGraph 저장 완료');
        }).catch((error) => {
          console.error('❌ LangGraph 저장 실패:', error);
        });
        
        // 강제 리렌더링
        this.$nextTick(() => {
          this.$forceUpdate();
          console.log('✅ 4단계 UI 업데이트 완료 - 최종 답변 표시됨');
        });
      } else if (data.node === 'node_rc_plain_answer' && data.status === 'streaming') {
        // LLM Streaming 응답 처리
        console.log('LLM Streaming 응답:', data.data);
        
        // 스트리밍 시작 시 답변 생성 상태로 설정
        if (!this.isGeneratingAnswer) {
          this.isGeneratingAnswer = true;
          this.currentStep = 3; // 3단계로 설정
        }
        
        if (data.data && data.data.content) {
          // 스트리밍 응답을 누적
          if (!this.finalAnswer) {
            this.finalAnswer = '';
          }
          this.finalAnswer += data.data.content;
          
          // 실시간으로 UI 업데이트
          this.$nextTick(() => {
            this.$forceUpdate();
          });
        }
      }
    },
    

    
    // 직접 LangGraph 결과 처리 (API 응답에서 - 실시간 기능 고려)
    async processDirectLangGraphResult(apiResult) {
      console.log('🔄 processDirectLangGraphResult 시작:', apiResult);
      console.log('🔍 실시간 기능 상태:', {
        isNewConversation: this.isNewConversation,
        isFirstQuestionInSession: this.isFirstQuestionInSession,
        isRestoringConversation: this.isRestoringConversation
      });
      
      // 데이터 구조 상세 로깅
      console.log('🔍 apiResult.result 구조:', apiResult.result);
      if (apiResult.result && apiResult.result.response) {
        console.log('🔍 apiResult.result.response:', apiResult.result.response);
        console.log('🔍 res_id:', apiResult.result.response.res_id);
        console.log('🔍 db_search_title:', apiResult.result.response.db_search_title);
      }
      console.log('🔍 candidates_total:', apiResult.result.candidates_total);
      
      try {
        const result = apiResult.result;
        
        // 실시간 기능이 비활성화된 경우 (추가 질문 또는 복원) 즉시 완료 상태로 설정
        if (!this.isFirstQuestionInSession || this.isRestoringConversation) {
          console.log('🚀 실시간 기능 비활성화 - 즉시 완료 상태로 설정');
          console.log('🔍 비활성화 이유:', {
            isFirstQuestionInSession: this.isFirstQuestionInSession,
            isRestoringConversation: this.isRestoringConversation
          });
          
          this.currentStep = 4; // 완료 상태
          this.isSearching = false;
          this.isLoading = false;
          
          // 결과 데이터 직접 설정
          if (result && result.response) {
            console.log('🔍 직접 처리 - result.response 전체 확인:', result.response);
            console.log('🔍 직접 처리 - analysis_image_url 필드 확인:', result.response.analysis_image_url);
            
            this.finalAnswer = result.response.answer || '답변을 생성할 수 없습니다.';
            this.extractedKeywords = result.response.keyword || null;
            this.extractedDbSearchTitle = result.response.db_search_title || null;
            
            // 이미지 URL 처리 (강화된 검색)
            let imageUrl = null;
            if (result.response.analysis_image_url) {
              imageUrl = result.response.analysis_image_url;
              console.log('🖼️ 직접 처리 - result.response에서 이미지 URL 발견:', imageUrl);
            } else if (result.analysis_image_url) {
              imageUrl = result.analysis_image_url;
              console.log('🖼️ 직접 처리 - result에서 이미지 URL 발견:', imageUrl);
            }
            
            if (imageUrl) {
              this.analysisImageUrl = imageUrl;
              this.lastImageUrl = imageUrl; // 디버깅용 저장
              console.log('🖼️ 직접 처리 - 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
            } else {
              console.log('⚠️ 직접 처리 - analysis_image_url이 없습니다');
              console.log('⚠️ result.response 필드들:', Object.keys(result.response || {}));
              console.log('⚠️ result 필드들:', Object.keys(result || {}));
            }
          }
          
          console.log('✅ 즉시 완료 처리됨');
          return;
        }
        
        console.log('🎬 첫 번째 질문 - 실시간 단계별 처리 시작');
        
        // 1단계: 초기화 완료
        this.currentStep = 1;
        this.isSearching = false;
        console.log('✅ 1단계: 초기화 완료');
        this.$nextTick(() => this.$forceUpdate());
        await new Promise(resolve => setTimeout(resolve, 500)); // 0.5초 지연
        
        // 2단계: 키워드 증강 결과 표시
        if (result && (result.keyword || apiResult.tags)) {
          this.currentStep = 2;
          this.isSearching = true;
          const keywords = result.keyword || (apiResult.tags ? apiResult.tags.split(', ') : []);
          this.augmentedKeywords = Array.isArray(keywords) ? keywords.map((keyword, index) => ({
            id: index + 1,
            text: String(keyword).trim(),
            category: '키워드'
          })) : [];
          this.extractedKeywords = keywords;
          console.log('✅ 2단계: 키워드 설정 완료:', this.augmentedKeywords);
          this.$nextTick(() => this.$forceUpdate());
          await new Promise(resolve => setTimeout(resolve, 500)); // 0.5초 지연
        }
        
        // 3단계: 검색 결과 표시
        if (result && (result.candidates_total || (result.response && result.response.res_id))) {
          this.currentStep = 3;
          this.isSearching = false;
          this.isGeneratingAnswer = true;
          
          // 검색 결과 데이터 추출 (두 가지 구조 지원)
          let searchData = [];
          let dbSearchTitles = [];
          
          if (result.candidates_total) {
            // 기존 구조 (candidates_total 배열)
            searchData = result.candidates_total || [];
            dbSearchTitles = searchData.map(item => 
              item?.res_payload?.document_name || item?.title || '제목 없음'
            );
          } else if (result.response && result.response.res_id) {
            // 새로운 구조 (response 객체 내부)
            const resIds = result.response.res_id || [];
            const titles = result.response.db_search_title || [];
            
            // res_id와 title을 조합하여 검색 결과 생성
            searchData = resIds.map((id, index) => ({
              res_id: id,
              res_score: 1.0 - (index * 0.1), // 임시 점수
              res_payload: {
                document_name: titles[index] || '제목 없음',
                ppt_summary: '검색 결과',
                ppt_content: '검색된 문서 내용'
              },
              res_relevance: 1.0 - (index * 0.1)
            }));
            
            dbSearchTitles = titles;
          }
          
          this.searchResults = Array.isArray(searchData) ? searchData.slice(0, 5) : []; // 상위 5개만 표시
          this.extractedDbSearchTitle = dbSearchTitles;
          
          console.log('✅ 3단계: 검색 결과 설정 완료:', this.searchResults);
          console.log('📄 문서 제목 설정 완료:', this.extractedDbSearchTitle);
          this.$nextTick(() => this.$forceUpdate());
          await new Promise(resolve => setTimeout(resolve, 500)); // 0.5초 지연
        }
        
        // 4단계: 최종 답변 표시 (LangGraph 결과를 그대로 사용)
        if (result && result.response && (result.response.answer || result.response.final_answer)) {
          this.currentStep = 4;
          this.isGeneratingAnswer = false;
          
          // LangGraph의 답변을 그대로 최종 답변으로 사용 (별도 LLM 처리 없음)
          const langGraphAnswer = result.response.answer || result.response.final_answer;
          this.finalAnswer = langGraphAnswer;
          
          console.log('🎯 LangGraph 답변을 그대로 사용:', langGraphAnswer.substring(0, 100) + '...');
          
          // 백엔드 응답에서 추가 데이터 추출
          if (result.response && result.response.keyword) {
            this.extractedKeywords = result.response.keyword;
          }
          if (result.response && result.response.db_search_title) {
            this.extractedDbSearchTitle = result.response.db_search_title;
          }
          // 이미지 URL 처리 (강화된 검색)
          let imageUrl = null;
          
          // 여러 경로에서 이미지 URL 찾기
          if (result.response && result.response.analysis_image_url) {
            imageUrl = result.response.analysis_image_url;
            console.log('🖼️ processDirectLangGraphResult - result.response에서 이미지 URL 발견:', imageUrl);
          } else if (result.analysis_image_url) {
            imageUrl = result.analysis_image_url;
            console.log('🖼️ processDirectLangGraphResult - result에서 이미지 URL 발견:', imageUrl);
          }
          
          if (imageUrl) {
            this.analysisImageUrl = imageUrl;
            this.lastImageUrl = imageUrl; // 디버깅용 저장
            console.log('🖼️ processDirectLangGraphResult - 분석 이미지 URL 설정 완료:', this.analysisImageUrl);
          } else {
            console.log('⚠️ processDirectLangGraphResult - 이미지 URL을 찾을 수 없습니다');
            console.log('⚠️ result 구조:', result);
            console.log('⚠️ result.response 구조:', result.response);
          }
          
          console.log('✅ 4단계: LangGraph 최종 답변 설정 완료 (별도 LLM 처리 없음)');
          this.$nextTick(() => this.$forceUpdate());
          
          // 첫 번째 질문 완료 후 상태 변경
          this.isFirstQuestionInSession = false;
          console.log('🔄 첫 번째 질문 완료 - 상태 변경됨');
          
          // 답변이 완료되면 저장
          await this.saveLangGraphMessage(apiResult);
        }
        
        // 최종 상태 정리
        this.isLoading = false;
        this.isSearching = false;
        this.isGeneratingAnswer = false;
        
        console.log('🎯 processDirectLangGraphResult 완료 - 모든 단계 처리됨');
        
      } catch (error) {
        console.error('❌ processDirectLangGraphResult 오류:', error);
        // 오류 발생 시에도 상태 정리
        this.isLoading = false;
        this.isSearching = false;
        this.isGeneratingAnswer = false;
      }
    },
    
    // LangGraph 결과 처리
    async processLangGraphResult(result) {
      // 각 단계별 결과를 순차적으로 처리
      if (result.keyword) {
        this.currentStep = 2;
        this.isSearching = true; // 키워드 생성 완료 후 검색 시작
        this.augmentedKeywords = result.keyword.map((keyword, index) => ({
          id: index + 1,
          text: keyword,
          category: '키워드'
        }));
        await this.$nextTick();
      }
      
      if (result.candidates_total) {
        this.currentStep = 3;
        this.isSearching = false; // 검색 완료
        this.searchResults = result.candidates_total.map((item) => ({
          id: item.res_id,
          title: item.res_payload.title,
          snippet: item.res_payload.content,
          source: '검색 결과',
          date: new Date().toISOString().split('T')[0]
        }));
        await this.$nextTick();
      }
      
      if (result.response && result.response.answer) {
        this.currentStep = 4;
        this.finalAnswer = result.response.answer;
        await this.$nextTick();
      }
      
      
      // 분석 결과 이미지 URL 처리
      if (result.response && result.response.analysis_image_url) {
        this.analysisImageUrl = result.response.analysis_image_url;
        console.log('🖼️ processLangGraphResult - 분석 이미지 URL 설정:', this.analysisImageUrl);
      }
      
      // WebSocket을 통해 실시간으로 진행되므로 여기서는 저장하지 않음
      // LangGraph 완료 시 handleWebSocketMessage에서 저장됨
    },
    
    // 히스토리 항목 삭제
    deleteHistoryItem(historyId) {
      const index = this.rangraphHistory.findIndex(item => item.id === historyId);
      if (index !== -1) {
        this.rangraphHistory.splice(index, 1);
      }
    },
    
    // 토큰 갱신 메서드
    async refreshToken() {
      try {
        console.log('🔄 토큰 갱신 시작...');
        
        // 현재 토큰으로 갱신 시도
        const response = await fetch('https://report-collection/api/auth/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('✅ 토큰 갱신 성공');
          
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
    
    // WebSocket에서 LangGraph 완료 후 결과 저장
    async saveLangGraphMessageFromWebSocket() {
      try {
        console.log('🔄 saveLangGraphMessageFromWebSocket 함수 시작');
        
        // 중복 저장 방지 - 이미 저장 중이면 리턴
        if (this.isSavingMessage) {
          console.log('⚠️ 이미 저장 중입니다. 중복 호출 방지.');
          return;
        }
        
        // 저장 상태 업데이트
        this.isSavingMessage = true;
        this.saveStatus = '';
        
        if (!this.$store.state.currentConversation) {
          console.log('📝 새 대화 생성 중...');
          await this.$store.dispatch('createConversation');
        }
        
        const conversationId = this.$store.state.currentConversation.id;
        const question = this.originalInput || 'LangGraph 분석 요청';
        const answer = this.finalAnswer || '분석 결과가 없습니다.';
        
        console.log('📊 WebSocket에서 LangGraph 완료 후 저장할 데이터:', {
          conversationId: conversationId,
          question: question,
          answer: answer,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle,
          currentStep: this.currentStep
        });
        
        // LangGraph 전체 상태를 JSON으로 저장 (복원을 위해)
        const langGraphState = {
          originalInput: this.originalInput,
          augmentedKeywords: this.augmentedKeywords,
          searchResults: this.searchResults.slice(0, 5), // 상위 5개만 저장
          finalAnswer: this.finalAnswer,
          analysisImageUrl: this.analysisImageUrl, // 이미지 URL 저장 추가
          currentStep: this.currentStep,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle
        };
        
        // 키워드 필드에 전체 LangGraph 상태 저장
        const keywordData = JSON.stringify(langGraphState);
        
        // 문서 제목 데이터 처리
        let dbSearchTitleData = this.extractedDbSearchTitle;
        if (Array.isArray(dbSearchTitleData)) {
          dbSearchTitleData = JSON.stringify(dbSearchTitleData);
        }
        
        const user_name = this.$store.state.user?.username || '사용자';
        console.log('사용자 정보 확인:', {
          user: this.$store.state.user,
          username: this.$store.state.user?.username,
          loginid: this.$store.state.user?.loginid,
          selected_user_name: user_name
        });
        
        const requestBody = { 
          question: question,
          ans: answer,  // ans 필드로 전송
          role: "user",
          q_mode: 'search',  // LangGraph 실행은 항상 검색 모드
          assistant_response: answer,  // 백엔드 호환성을 위해 유지
          keyword: keywordData,
          db_search_title: dbSearchTitleData,
          image: this.analysisImageUrl,  // 이미지 URL 전송
          user_name: user_name,  // username 사용
          skip_llm: true  // LLM 재호출 방지 플래그
        };
        
        console.log('📤 백엔드로 전송할 요청 데이터:', requestBody);
        console.log('🌐 API 엔드포인트:', `https://report-collection/api/conversations/${conversationId}/messages`);
        console.log('🔑 인증 토큰:', this.$store.state.token ? '설정됨' : '설정되지 않음');
        console.log('📊 현재 상태 데이터:');
        console.log('  - extractedKeywords:', this.extractedKeywords);
        console.log('  - extractedDbSearchTitle:', this.extractedDbSearchTitle);
        console.log('  - originalInput:', this.originalInput);
        console.log('  - finalAnswer:', this.finalAnswer);
        
        // 메시지 생성 API 호출
        console.log('📡 API 호출 시작...');
        const response = await fetch(`https://report-collection/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify(requestBody)
        });
        
        console.log('📡 API 응답 상태:', response.status, response.statusText);
        console.log('📡 API 응답 헤더:', Object.fromEntries(response.headers.entries()));
        
        if (response.ok) {
          const messageData = await response.json();
          console.log('✅ WebSocket LangGraph 메시지 저장 완료:', messageData);
          
          // 저장된 메시지 ID 확인
          if (messageData.userMessage && messageData.userMessage.id) {
            console.log('📊 저장된 메시지 ID:', messageData.userMessage.id);
            console.log('📊 저장된 메시지 데이터:', {
              question: messageData.userMessage.question,
              ans: messageData.userMessage.ans?.substring(0, 100) + '...',
              q_mode: messageData.userMessage.q_mode,
              keyword: messageData.userMessage.keyword ? '저장됨' : '없음',
              db_search_title: messageData.userMessage.db_search_title ? '저장됨' : '없음'
            });
          }
          
          // 저장 성공 로그만 남기고 사용자 메시지는 제거
          console.log('✅ LangGraph 분석 결과가 성공적으로 저장되었습니다.');
          this.saveStatus = '';
          
          // 대화 목록 새로고침 (조건부 - 새 대화인 경우에만)
          if (!this.$store.state.currentConversation) {
            console.log('🔄 대화 목록 새로고침 중...');
            await this.$store.dispatch('fetchConversations');
            console.log('✅ 대화 목록 새로고침 완료');
          }
          
          // 화면에 즉시 반영되도록 강제 업데이트
          this.$nextTick(() => {
            this.$forceUpdate();
            console.log('🔄 화면 강제 업데이트 완료');
          });
        } else if (response.status === 401) {
          // 인증 실패 시 토큰 갱신 시도
          console.error('❌ 인증 실패 (401). 토큰 갱신 시도...');
          this.saveStatus = '⚠️ 인증이 만료되었습니다. 토큰을 갱신 중...';
          
          try {
            // 토큰 갱신 시도
            await this.refreshToken();
            console.log('🔄 토큰 갱신 완료, 저장 재시도...');
            
            // 토큰 갱신 후 저장 재시도
            setTimeout(() => {
              this.saveLangGraphMessageFromWebSocket();
            }, 1000);
          } catch (refreshError) {
            console.error('❌ 토큰 갱신 실패:', refreshError);
            this.saveStatus = '⚠️ 인증이 만료되었습니다. 다시 로그인해주세요.';
            
            // 로그인 페이지로 리다이렉트
            setTimeout(() => {
              this.$router.push('/login');
            }, 2000);
          }
        } else {
          console.error('❌ WebSocket LangGraph 메시지 저장 실패:', response.status, response.statusText);
          
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
          
          // 저장 실패 시 재시도 로직 제거 - 중복 저장 방지
          console.log('❌ LangGraph 메시지 저장 실패. 재시도하지 않음.');
        }
      } catch (error) {
        console.error('❌ WebSocket LangGraph 메시지 저장 중 오류:', error);
        console.error('❌ 오류 스택:', error.stack);
        console.error('❌ 저장 시도한 데이터:', {
          conversationId: this.$store.state.currentConversation?.id,
          question: this.originalInput,
          answer: this.finalAnswer?.substring(0, 100) + '...',
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle
        });
        this.saveStatus = `⚠️ 메시지 저장 오류: ${error.message}`;
        
        // 오류 발생 시 재시도 로직 제거 - 중복 저장 방지
        console.log('❌ LangGraph 메시지 저장 오류. 재시도하지 않음.');
      } finally {
        this.isSavingMessage = false;
        console.log('🔄 저장 프로세스 완료, isSavingMessage 초기화');
      }
    },
    
    // LangGraph 결과를 메시지로 저장 (기존 함수 - 폴백용)
    async saveLangGraphMessage(result) {
      try {
        if (!this.$store.state.currentConversation) {
          await this.$store.dispatch('createConversation');
        }
        
        const conversationId = this.$store.state.currentConversation.id;
        const question = this.originalInput || 'LangGraph 분석 요청';
        
        // SSE 결과 구조에 맞게 답변 추출
        let answer = '분석 결과가 없습니다.';
        if (result.result && result.result.response) {
          answer = result.result.response.answer || result.result.response.final_answer || '분석 결과가 없습니다.';
        } else if (result.response) {
          answer = result.response.answer || result.response.final_answer || '분석 결과가 없습니다.';
        } else if (this.finalAnswer) {
          answer = this.finalAnswer;
        }
        
        console.log('saveLangGraphMessage에서 저장할 데이터:', {
          question: question,
          answer: answer,
          extractedKeywords: this.extractedKeywords,
          extractedDbSearchTitle: this.extractedDbSearchTitle,
          resultStructure: result
        });
        
        // 키워드와 문서 제목 데이터 준비
        let keywordData = this.extractedKeywords;
        let dbSearchTitleData = this.extractedDbSearchTitle;
        
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
          originalInput: this.originalInput,
          augmentedKeywords: this.augmentedKeywords,
          searchResults: this.searchResults.slice(0, 5),
          finalAnswer: answer,
          analysisImageUrl: this.analysisImageUrl, // 이미지 URL 저장 추가
          currentStep: this.currentStep,
          extractedKeywords: keywordData,
          extractedDbSearchTitle: dbSearchTitleData
        };
        
        console.log('💾 저장할 LangGraph 상태:', langGraphState);
        
        // 메시지 생성 API 호출
        const response = await fetch(`https://report-collection/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: question,
            q_mode: 'search',  // LangGraph 실행은 항상 검색 모드
            assistant_response: answer,
            skip_llm: true,  // 첫 번째 질문은 LangGraph 답변만 사용, 별도 LLM 처리 안함
            keyword: JSON.stringify(langGraphState), // 전체 상태를 JSON으로 저장
            db_search_title: Array.isArray(dbSearchTitleData) ? JSON.stringify(dbSearchTitleData) : dbSearchTitleData,
            image: this.analysisImageUrl,  // 이미지 URL 전송
            user_name: this.$store.state.user?.username || '사용자'
          })
        });
        
        if (response.ok) {
          const messageData = await response.json();
          console.log('✅ LangGraph 메시지 저장 완료:', messageData);
          
          // 대화 제목 업데이트 (질문의 첫 50자로)
          if (this.$store.state.currentConversation) {
            const conversationTitle = question.length > 50 ? question.substring(0, 50) + '...' : question;
            
            try {
              const titleUpdateResponse = await fetch(`https://report-collection/api/conversations/${conversationId}`, {
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
                console.log('✅ 대화 제목 업데이트 완료:', conversationTitle);
                // 스토어의 현재 대화 제목도 업데이트
                this.$store.commit('updateConversationTitle', {
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
          await this.$store.dispatch('fetchConversations');
          
        } else {
          console.error('❌ LangGraph 메시지 저장 실패:', response.status, response.statusText);
          const errorText = await response.text();
          console.error('❌ 오류 응답 내용:', errorText);
        }
      } catch (error) {
        console.error('LangGraph 메시지 저장 중 오류:', error);
      }
    },
    
    // 폴백 랭그래프 플로우 (오류 발생 시)
    async fallbackRangraphFlow(inputText, error = null) {
      // 오류 정보를 저장하여 답변에 포함
      this.langGraphError = error;
      
      // 오류 발생 시 간단한 메시지만 표시
      this.currentStep = 1;
      this.isSearching = false; // 오류 시 검색 상태 해제
      this.augmentedKeywords = [];
      this.searchResults = [];
      this.finalAnswer = '';
      
      // 오류 메시지 표시
      this.finalAnswer = `⚠️ **시스템 오류**: 
LangGraph API 연결에 실패했습니다.

**오류 정보**:
• API 오류: ${error?.message || 'LangGraph API 호출 실패'}
• API 엔드포인트: /api/llm/langgraph → 404 Not Found

**해결 방안**:
• LangGraph 서버가 실행 중인지 확인하세요
• API 엔드포인트가 올바른지 확인하세요
• WebSocket 서버가 8000번 포트에서 실행 중인지 확인하세요
