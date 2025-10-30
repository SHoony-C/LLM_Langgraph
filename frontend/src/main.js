import { createApp } from 'vue'
import { createStore } from 'vuex'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import ChatHistory from './views/ChatHistory.vue'

// Vue 디버깅 설정
if (process.env.NODE_ENV === 'development') {
  // Vue DevTools 활성화 (안전한 방식)
  try {
    // 기존 DevTools 훅이 있으면 활성화만 시도
    if (window.__VUE_DEVTOOLS_GLOBAL_HOOK__ && typeof window.__VUE_DEVTOOLS_GLOBAL_HOOK__ === 'object') {
      window.__VUE_DEVTOOLS_GLOBAL_HOOK__.enabled = true;
    }
  } catch (error) {
    // DevTools 설정 실패는 무시 (개발 도구이므로 필수가 아님)
    console.warn('[Vue Debug] DevTools 설정 실패 (무시됨):', error.message);
  }
  
  // Vue 개발 모드 활성화
  // console.log('[Vue Debug] 개발 모드 활성화됨');
}

// OAuth 토큰 처리 함수
async function processOAuthToken(idToken, state) {
  try {
    // OAuth 처리 시작을 즉시 알림
    // // console.log('[AUTH] processOAuthToken 시작 - oauth_processing 플래그 설정');
    sessionStorage.setItem('oauth_processing', 'true');
    
    // 처리 시작 시 기존 플래그들 정리
    sessionStorage.removeItem('sso_processed');
    
    // 요청 본문 구성
    const requestBody = `id_token=${encodeURIComponent(idToken)}&state=${encodeURIComponent(state)}`;
    
    // 백엔드의 acs 엔드포인트로 id_token 전송
    const response = await fetch('https://report-collection/api/auth/acs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: requestBody,
      credentials: 'include' // 쿠키 포함
    });
    
    if (response.ok) {
      // 응답에서 사용자 정보 추출 시도
      try {
        const responseText = await response.text();
        
        // URL에서 OAuth 파라미터 제거
        window.history.replaceState({}, document.title, window.location.pathname);
        
        // 응답에서 사용자 정보를 직접 추출하여 store에 설정
        try {
          const responseData = JSON.parse(responseText);
          
          if (responseData.success && responseData.user) {
            // 백엔드 JWT 토큰만 사용
            if (responseData.access_token) {
              // // console.log('responseData : ',responseData)
              store.commit('setAuth', {
                token: responseData.access_token,  // 백엔드 JWT 토큰만
                user: {
                  username: responseData.user.username,
                  email: responseData.user.mail,
                  loginid: responseData.user.loginid,
                  deptname: responseData.user.deptname,
                  id: responseData.user.userid
                }
              });
            } else {
              // console.error('[AUTH] 백엔드에서 access_token을 받지 못했습니다.');
              throw new Error('백엔드 인증 실패');
            }
            
            // localStorage에 JWT 토큰 저장
            localStorage.setItem('access_token', responseData.access_token);
            localStorage.setItem('user_info', JSON.stringify(responseData.user));
            
            // // console.log('[AUTH] 백엔드 JWT 토큰 설정 완료 (processOAuthToken):', {
            //   token: responseData.access_token.substring(0, 20) + '...',
            //   user: responseData.user.username
            // });
            
            // 인증 성공 후 대화 목록 가져오기
            // console.log('[AUTH] 대화 목록 가져오기 시작');
            try {
              await store.dispatch('fetchConversations');
              // console.log('[AUTH] 대화 목록 가져오기 완료');
            } catch (error) {
              console.error('[AUTH] 대화 목록 가져오기 실패:', error);
            }
            
            // 인증 성공 표시 및 Vue Router로 이동 (window.location 사용 금지)
            hasProcessedOAuth = true;
            isProcessingOAuth = false;
            
            // OAuth 처리 완료 플래그 설정
            sessionStorage.setItem('sso_processed', 'true');
            sessionStorage.removeItem('oauth_processing');
            
            // // console.log('[AUTH] OAuth 처리 완료, Vue Router로 이동');
            
            // Vue Router가 준비된 후 이동 (지연 증가)
            setTimeout(() => {
              if (router && router.push) {
                // // console.log('[AUTH] 홈페이지로 이동 중...');
                router.push('/').then(() => {
                  // // console.log('[AUTH] 홈페이지 이동 완료');
                  
                  // 추가 대기 후 플래그 정리 (중복 리다이렉트 방지)
                  setTimeout(() => {
                    sessionStorage.setItem('sso_processed', 'true');
                    sessionStorage.removeItem('oauth_processing');
                    // // console.log('[AUTH] OAuth 플래그 최종 정리 완료');
                  }, 500);
                  
                }).catch(error => {
                  console.error('[AUTH] 홈페이지 이동 실패:', error);
                  // 라우터 이동 실패 시 직접 URL 변경
                  try {
                    window.location.href = '/';
                  } catch (e) {
                    console.error('[AUTH] URL 변경도 실패:', e);
                  }
                });
              }
            }, 200); // 지연 시간 증가
            return;
          }
        } catch (parseError) {
          // 응답 파싱 실패 시 localStorage에서 시도
          setTimeout(() => {
            const accessToken = getStoredToken();
            const userInfo = getStoredUserInfo();
            
            if (accessToken && userInfo) {
              try {
                // store에 인증 정보 설정 (통일된 방식)
                store.commit('setAuth', {
                  token: accessToken,
                  user: userInfo

                });
                
                // 인증 성공 후 대화 목록 가져오기
                // // console.log('[AUTH] localStorage 복원 후 대화 목록 가져오기');
                store.dispatch('fetchConversations').then(() => {
                  // console.log('[AUTH] localStorage 복원 후 대화 목록 가져오기 완료');
                }).catch(error => {
                  console.error('[AUTH] localStorage 복원 후 대화 목록 가져오기 실패:', error);
                });
                
                // 인증 성공 후 홈페이지로 이동
                window.location.href = '/';
                return;
              } catch (error) {
                window.location.reload();
              }
            } else {
              window.location.reload();
            }
          }, 100); // 100ms 지연 후 쿠키 읽기 시도
        }
        
      } catch (error) {
        // 오류 발생 시 페이지 새로고침
        window.location.reload();
      }
    } else {
      throw new Error(`OAuth processing failed: ${response.status}`);
    }
  } catch (error) {
    // 오류 발생 시 URL에서 OAuth 파라미터 제거
    window.history.replaceState({}, document.title, window.location.pathname);
    
    // 오류 발생 시 모든 OAuth 플래그 정리
    sessionStorage.removeItem('oauth_processing');
    sessionStorage.removeItem('sso_processed');
    isProcessingOAuth = false;
    hasProcessedOAuth = false;
    
    console.error('[AUTH] processOAuthToken 오류:', error);
    
    // 오류 발생 시 samsung SSO로 리다이렉트
    setTimeout(() => {
      try {
        window.location.replace('https://report-collection/api/auth/auth_sh');
      } catch (redirectError) {
        console.error('[AUTH] SSO 리다이렉트 실패:', redirectError);
      }
    }, 1000);
  }
}

// URL에서 OAuth 파라미터 확인 및 처리
function checkAndProcessOAuthParams() {
  const hash = window.location.hash;
  if (hash && hash.includes('id_token=')) {
    const urlParams = new URLSearchParams(hash.substring(1));
    const idToken = urlParams.get('id_token');
    const state = urlParams.get('state');
    
    if (idToken && state) {
      processOAuthToken(idToken, state);
      return true;
    }
  }
  
  // URL 쿼리 파라미터에서 인증 성공 확인 (백엔드에서 리디렉트된 경우)
  const urlParams = new URLSearchParams(window.location.search);
  const authSuccess = urlParams.get('auth_success');
  const user = urlParams.get('user');
  
  if (authSuccess === 'true' && user) {
    // URL에서 OAuth 파라미터 제거
    window.history.replaceState({}, document.title, window.location.pathname);
    
    // localStorage에서 토큰을 읽어와서 store에 설정
    const accessToken = getStoredToken();
    const userInfo = getStoredUserInfo();
    
    if (accessToken && userInfo) {
      try {
        // // console.log('userData2 : ',userData)
        // store에 인증 정보 설정 (통일된 방식)
        store.commit('setAuth', {
          token: accessToken,
          user: userInfo

        });
      } catch (error) {
        // 에러 처리
        console.error('[AUTH] SSO 콜백 사용자 정보 설정 실패:', error);
      }
    }
    
    return true;
  }
  
  return false;
}



// localStorage에서 토큰과 사용자 정보를 읽는 함수
function getStoredToken() {
    return localStorage.getItem('access_token') || localStorage.getItem('auth_token');
}

function parseUserInfo(rawUser) {
  if (!rawUser) {
    return null;
  }

  if (typeof rawUser === 'object') {
    return rawUser;
  }

  try {
    return JSON.parse(rawUser);
  } catch (jsonError) {
    // 쿼리 문자열 형태(username=value&mail=value)를 파싱
    const parsedUser = {};
    const params = rawUser.split('&');

    for (const param of params) {
      if (param.includes('=')) {
        const [key, value] = param.split('=', 2);
        parsedUser[key] = decodeURIComponent(value || '');
      }
    }

    return Object.keys(parsedUser).length > 0 ? parsedUser : null;
  }
}

function normalizeUserData(user) {
  const parsedUser = parseUserInfo(user);

  if (!parsedUser) {
    return null;
  }

  const normalizedId = parsedUser.userid || parsedUser.id || parsedUser.user_id || parsedUser.sub || parsedUser.loginid || null;
  if (!normalizedId) {
    console.error('[AUTH] 사용자 ID를 확인할 수 없습니다.');
    return null;
  }

  const normalizedEmail = parsedUser.mail || parsedUser.email || '';
  const normalizedUsername = parsedUser.username || parsedUser.name || parsedUser.loginid ||
    parsedUser.loginId || (normalizedEmail ? normalizedEmail.split('@')[0] : `user-${normalizedId}`);
  const normalizedLoginId = parsedUser.loginid || parsedUser.loginId || normalizedId;
  const normalizedDept = parsedUser.deptname || parsedUser.department || parsedUser.dept || '';

  return {
    ...parsedUser,
    username: normalizedUsername,
    mail: parsedUser.mail || normalizedEmail,
    email: normalizedEmail,
    loginid: normalizedLoginId,
    deptname: normalizedDept,
    id: normalizedId,
    userid: normalizedId
  };
}

function getStoredUserInfo() {
  const storedUser = localStorage.getItem('user_info') || localStorage.getItem('user');
  return normalizeUserData(storedUser);
}

const initialToken = getStoredToken() || '';
const initialUser = getStoredUserInfo();

// localStorage에서 인증 정보를 가져와서 store에 설정
function initializeAuthFromStorage() {
  const accessToken = getStoredToken();
  const userInfo = getStoredUserInfo();

  if (accessToken && userInfo) {
    try {
      if (typeof store !== 'undefined' && store.commit) {
        store.commit('setAuth', {
          token: accessToken,
          user: userInfo
        });

        // 인증 상태 확인을 위한 API 호출
        fetch('https://report-collection/api/auth/me', {
          method: 'GET',
          headers: { 
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include'
        })
        .then(response => {
          if (response.ok) {
            // console.log('Token validation successful');
          } else {
            // console.log('Token validation failed:', response.status, response.statusText);
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user');
            if (typeof store !== 'undefined' && store.commit) {
              store.commit('clearAuth');
            }
          }
        })
        .catch(error => {
          console.error('Token validation error:', error);
          
          // 네트워크 오류인지 확인
          if (error.name === 'TypeError' && error.message.includes('fetch')) {
            console.error('[MAIN] 네트워크 오류 - 백엔드 서버 연결 실패');
            // 네트워크 오류 시에는 인증 상태를 유지
            return;
          }
          
          if (typeof store !== 'undefined' && store.commit) {
            store.commit('clearAuth');
          }
        });
      }
    } catch (error) {
      console.error('Error restoring auth from storage:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      if (typeof store !== 'undefined' && store.commit) {
        store.commit('clearAuth');
      }
    }
  }
}

// Create Vuex store
const store = createStore({
  state() {
    return {
      conversations: [],
      currentConversation: null,
      feedbackUpdateTrigger: 0,
      llamaApiKey: localStorage.getItem('llama_api_key') || '',
      llamaApiBase: localStorage.getItem('llama_api_base') || '',
      llamaApiEndpoint: localStorage.getItem('llama_api_endpoint') || '/llama4/1/llama/aiserving/llama-4/maverick/v1/completions',
      llamaApiSet: !!localStorage.getItem('llama_api_key'),
      llamaApiError: null,
      token: initialToken,
      user: initialUser,
      isAuthenticated: !!(initialToken && initialUser),
      isStreaming: false,
      streamingMessage: '',
      shouldScrollToBottom: false,
      conversationRestored: false, // 대화 복원 상태
      loginNewConversation: false // 로그인 후 새 대화창 플래그
    }
  },
  mutations: {
    setConversations(state, conversations) {
      state.conversations = Array.isArray(conversations) ? conversations : [];
    },
    addConversation(state, conversation) {
      if (!Array.isArray(state.conversations)) {
        state.conversations = [];
      }
      state.conversations.unshift(conversation);
    },
    setNewConversationTrigger(state) {
      state._newConversationTrigger = Date.now();
    },
    removeConversation(state, conversationId) {
      if (!Array.isArray(state.conversations)) {
        state.conversations = [];
        return;
      }
      state.conversations = state.conversations.filter(c => c.id !== conversationId);
      if (state.currentConversation && state.currentConversation.id === conversationId) {
        state.currentConversation = state.conversations.length > 0 ? state.conversations[0] : null;
      }
    },

    updateConversationTitle(state, { conversationId, title }) {
      // 대화 목록에서 제목 업데이트
      if (Array.isArray(state.conversations)) {
        const conversation = state.conversations.find(c => c.id === conversationId);
        if (conversation) {
          conversation.title = title;
        }
      }
      
      // 현재 대화의 제목도 업데이트
      if (state.currentConversation && state.currentConversation.id === conversationId) {
        state.currentConversation.title = title;
      }
    },

    setCurrentConversation(state, conversation) {
      // // console.log('setCurrentConversation 호출:', {
      //   newConversationId: conversation?.id,
      //   currentConversationId: state.currentConversation?.id,
      //   isSame: state.currentConversation && conversation && 
      //           state.currentConversation.id === conversation.id
      // });
      
      // 항상 대화를 설정 (동일한 대화도 다시 설정하여 랭그래프 복원 트리거)
      state.currentConversation = conversation;
      
      // sessionStorage에 현재 대화 ID 저장 (새로고침 시 복원용)
      if (conversation && conversation.id) {
        sessionStorage.setItem('currentConversationId', conversation.id.toString());
      } else {
        sessionStorage.removeItem('currentConversationId');
      }
      
      // 강제 반응성 트리거
      state._conversationUpdateTrigger = Date.now();
    },
    addMessage(state, { conversationId, message }) {
      if (!Array.isArray(state.conversations)) {
        return;
      }
      const conversation = state.conversations.find(c => c.id === conversationId);
      if (conversation) {
        if (!Array.isArray(conversation.messages)) {
          conversation.messages = [];
        }
        conversation.messages.push(message);
      }
    },
    addMessageToCurrentConversation(state, message) {
      if (state.currentConversation) {
        if (!Array.isArray(state.currentConversation.messages)) {
          state.currentConversation.messages = [];
        }
        state.currentConversation.messages.push(message);
      }
    },
    updateMessageAnswer(state, { messageId, answer }) {
      console.log('🔍 [DEBUG] updateMessageAnswer mutation 호출:', { messageId, answerLength: answer?.length });
      if (state.currentConversation && Array.isArray(state.currentConversation.messages)) {
        const message = state.currentConversation.messages.find(m => m.id === messageId || m.backend_id === messageId);
        if (message) {
          console.log('🔍 [DEBUG] 메시지 찾음, ans 필드 업데이트:', message.id);
          message.ans = answer;
          console.log('🔍 [DEBUG] 메시지 업데이트 완료');
        } else {
          console.warn('⚠️ updateMessageAnswer: 메시지를 찾을 수 없음:', messageId);
        }
      } else {
        console.warn('⚠️ updateMessageAnswer: currentConversation 또는 messages가 없음');
      }
    },
    updateMessageId(state, { tempId, realId, additionalData }) {
      if (state.currentConversation && Array.isArray(state.currentConversation.messages)) {
        const message = state.currentConversation.messages.find(m => m.id === tempId);
        if (message) {
          // ID만 조용히 업데이트 (깜빡임 방지)
          message.id = realId;
          // 추가 데이터가 있으면 병합
          if (additionalData) {
            Object.assign(message, additionalData);
          }
          console.log(`✅ 메시지 ID 업데이트 완료: ${tempId} → ${realId}`);
        } else {
          console.warn(`⚠️ 업데이트할 메시지를 찾을 수 없음: ${tempId}`);
        }
      }
    },
    updateMessageContent(state, { messageId, content, image }) {
      if (state.currentConversation && Array.isArray(state.currentConversation.messages)) {
        const message = state.currentConversation.messages.find(m => m.id === messageId);
        if (message) {
          message.ans = content;
          if (image) {
            message.image = image;
          }
          console.log(`✅ 메시지 내용 업데이트 완료: ${messageId}`);
        } else {
          console.warn(`⚠️ 업데이트할 메시지를 찾을 수 없음: ${messageId}`);
        }
      }
    },
    updateFeedback(state, { conversationId, messageId, feedback }) {
      // 현재 대화 찾기
      const conversation = state.conversations.find(c => c.id === conversationId);
      if (!conversation) return;
      
      // 해당 메시지 찾기
      const messageIndex = conversation.messages.findIndex(m => m.id === messageId);
      if (messageIndex === -1) return;
      
      // 메시지 객체를 새로 생성하여 교체 (Vue 반응성 보장)
      const updatedMessage = {
        ...conversation.messages[messageIndex],
        feedback: feedback
      };
      
      // 배열의 해당 인덱스를 새 객체로 교체
      conversation.messages.splice(messageIndex, 1, updatedMessage);
      
      // currentConversation이 같은 대화를 참조하고 있다면 동기화
      if (state.currentConversation && state.currentConversation.id === conversationId) {
        const currentMessageIndex = state.currentConversation.messages.findIndex(m => m.id === messageId);
        if (currentMessageIndex !== -1) {
          state.currentConversation.messages.splice(currentMessageIndex, 1, updatedMessage);
        }
      }
      
      // 강제 업데이트를 위한 트리거 증가
      state.feedbackUpdateTrigger = (state.feedbackUpdateTrigger || 0) + 1;
      
      console.log('✅ 피드백 상태 업데이트:', {
        messageId,
        feedback,
        trigger: state.feedbackUpdateTrigger,
        currentConversationId: state.currentConversation?.id,
        conversationId
      });
    },
    setApiKeyError(state, error) {
      state.apiKeyError = error;
    },
    setAuth(state, { token, user }) {
      // // console.log('[AUTH] setAuth called with token:', token ? token.substring(0, 20) + '...' : 'null');
      
      // 토큰 형식 확인 (JWT는 3개의 점으로 구분된 부분으로 구성)
      if (token && token.split('.').length === 3) {
        try {
          const header = JSON.parse(atob(token.split('.')[0]));
          // // console.log('[AUTH] Token header:', header);
          // // console.log('[AUTH] Token algorithm:', header.alg);
          
          // HS256 알고리즘인지 확인 (백엔드 JWT 토큰만 허용)
          if (header.alg === 'HS256') {
            // // console.log('[AUTH] 백엔드 JWT 토큰 확인됨');
          } else {
            console.error('[AUTH] 오류: HS256이 아닌 토큰은 허용되지 않음:', header.alg);
            return;
          }
        } catch (e) {
          // // console.log('[AUTH] Error parsing token header:', e);
        }
      }
      
      // HS256 토큰만 설정 (기타 토큰 차단)
      if (token && token.split('.').length === 3) {
        try {
          const header = JSON.parse(atob(token.split('.')[0]));
          if (header.alg !== 'HS256') {
            console.error('[AUTH] 토큰 설정이 차단되었습니다. 백엔드 JWT 토큰만 사용 가능합니다.');
            return; // 토큰 설정 중단
          }
        } catch (e) {
          // console.error('[AUTH] 토큰 헤더 파싱 실패:', e);
          // console.error('[AUTH] 잘못된 토큰 형식입니다.');
          return; // 토큰 설정 중단
        }
      } else if (token && token !== 'oauth_token') {
        // JWT가 아닌 토큰도 차단 (oauth_token 제외)
        // console.error('[AUTH] JWT 형식이 아닌 토큰 차단됨:', token.substring(0, 20) + '...');
        return; // 토큰 설정 중단
      }

      const normalizedUser = normalizeUserData(user);
      if (!normalizedUser) {
        console.error('[AUTH] 유효하지 않은 사용자 정보로 인해 인증 상태를 설정할 수 없습니다.');
        return;
      }

      // 사용자가 변경되었는지 확인
      const previousUserId = state.user ? state.user.id || state.user.loginid : null;
      const newUserId = normalizedUser ? normalizedUser.id || normalizedUser.loginid : null;
      const userChanged = previousUserId && newUserId && previousUserId !== newUserId;
      
      if (userChanged) {
        // console.log('[STORE] 사용자 변경 감지 - 대화 목록 초기화');
        // console.log('[STORE] 이전 사용자:', previousUserId, '새 사용자:', newUserId);
        // 사용자가 변경된 경우 대화 목록 초기화
        state.conversations = [];
        state.currentConversation = null;
      }
      
      state.token = token;
      state.user = normalizedUser;
      state.isAuthenticated = !!token;
      
      // localStorage에 토큰 저장 (API 요청용)
      localStorage.setItem('access_token', token);
      localStorage.setItem('user_info', JSON.stringify(normalizedUser));
      
      // 기존 auth_token과 user도 저장 (호환성 유지)
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user', JSON.stringify(normalizedUser));
      
    },
    setUser(state, user) {
      state.user = user;
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('user_info', JSON.stringify(user));
      
      // 사용자 정보만 업데이트 (토큰은 setAuth에서 관리)
    },
    clearAuth(state) {
      state.token = '';
      state.user = null;
      state.isAuthenticated = false;
      state.loginNewConversation = false; // 인증 정리 시 플래그 리셋
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      
      // 쿠키도 정리 (기존 코드와의 호환성을 위해)
      document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
      document.cookie = 'user_info=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    },
    setIsStreaming(state, isStreaming) {
      state.isStreaming = isStreaming;
    },
    updateStreamingMessage(state, content) {
      state.streamingMessage = content;
    },
    clearStreamingMessage(state) {
      state.streamingMessage = '';
    },
    addStreamingMessageToConversation(state, { conversationId, message }) {
      const conversation = state.conversations.find(c => c.id === conversationId);
      if (conversation) {
        conversation.messages.push(message);
      }
      state.streamingMessage = '';
      state.isStreaming = false;
    },
    setShouldScrollToBottom(state, value) {
      state.shouldScrollToBottom = value;
    },
    setConversationRestored(state, value) {
      state.conversationRestored = value;
    },
    setLoginNewConversation(state, value) {
      state.loginNewConversation = value;
    },
  },
  actions: {
    // 인증 에러 공통 처리 함수
    handleAuthError({ commit }) {
      commit('clearAuth');
      commit('setConversations', []);
      commit('setCurrentConversation', null);
      
      // // console.log('인증 오류 발생 - 상태 정리만 수행');
    },
    
    async register(context, userData) {
      const response = await fetch('https://report-collection/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Registration failed');
      }
      
      return await this.dispatch('login', {
        username: userData.username,
        password: userData.password
      });
    },
    
    async login({ commit, dispatch }, { username, password }) {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await fetch('https://report-collection/api/auth/token', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }
      
      const data = await response.json();
      
      const userResponse = await fetch('https://report-collection/api/auth/me', {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });
      
      if (!userResponse.ok) {
        throw new Error('Failed to get user information');
      }
      
      const userData = await userResponse.json();
      
      commit('setAuth', {
        token: data.access_token,
        user: userData
      });
      
      commit('setConversations', []);
      commit('setCurrentConversation', null);
      commit('setLoginNewConversation', true); // 로그인 후 새 대화창 플래그 설정
      await dispatch('fetchConversations');
      
      return true;
    },
    
    logout({ commit }) {
      commit('clearAuth');
      commit('setConversations', []);
      commit('setCurrentConversation', null);
      commit('setLoginNewConversation', false); // 로그아웃 시 플래그 리셋
      
      // OAuth 플래그 초기화
      resetOAuthFlags();
    },
    
    async fetchConversations({ commit, state }) {
      try {
        if (!state.isAuthenticated) {
          commit('setConversations', []);
          commit('setCurrentConversation', null);
          return;
        }
        
        // 올바른 JWT 토큰을 localStorage에서 가져와서 사용
        const headers = {};
        const jwtToken = localStorage.getItem('access_token');
        if (jwtToken) {
          headers['Authorization'] = `Bearer ${jwtToken}`;
        }
        
        const response = await fetch('https://report-collection/api/conversations', {
          headers,
          credentials: 'include' // 쿠키 포함
        });
        
        if (!response.ok) {
          if (response.status === 401) {
            // 인증 오류인 경우 로그아웃 처리
            commit('clearAuth');
            return;
          }
          throw new Error(`Error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // 디버깅: 메시지 데이터 확인
        // console.log('📥 대화 목록 가져옴:', data.length, '개');
        data.forEach(conv => {
          // console.log(`📋 대화 ${conv.id}: ${conv.messages.length}개 메시지`);
          conv.messages.forEach(() => {
            // console.log(`  - 메시지 ${msg.id}: role=${msg.role}, ans 길이=${msg.ans ? msg.ans.length : 0}`);
          });
        });
        
        // 현재 선택된 대화 ID 저장 (store 또는 sessionStorage에서)
        let currentConversationId = state.currentConversation ? state.currentConversation.id : null;
        
        // 새로고침 시 sessionStorage에서 대화 ID 복원
        if (!currentConversationId) {
          const savedConversationId = sessionStorage.getItem('currentConversationId');
          if (savedConversationId) {
            currentConversationId = parseInt(savedConversationId, 10);
            // console.log('🔄 새로고침 - sessionStorage에서 대화 ID 복원:', currentConversationId);
          }
        }
        
        commit('setConversations', data);
        
        // 로그인 후 새 대화 플래그가 설정된 경우 자동 선택 방지
        if (state.loginNewConversation) {
          // 로그인 후에는 대화를 자동으로 선택하지 않음
          commit('setCurrentConversation', null);
          sessionStorage.removeItem('currentConversationId'); // 세션 스토리지 정리
        } else {
          // 현재 대화가 없거나 기존 선택한 대화가 있으면 해당 대화 유지
          if (currentConversationId && data.length > 0) {
            const existingConversation = data.find(c => c.id === currentConversationId);
            if (existingConversation) {
              // 현재 대화에 메시지가 있으면 보존 (랭그래프 완료 시 메시지 손실 방지)
              if (state.currentConversation && state.currentConversation.messages && state.currentConversation.messages.length > 0) {
                console.log('✅ 기존 메시지 보존:', state.currentConversation.messages.length, '개');
                // 메시지를 보존하면서 대화 정보만 업데이트
                const updatedConversation = {
                  ...existingConversation,
                  messages: state.currentConversation.messages // 기존 메시지 보존
                };
                commit('setCurrentConversation', updatedConversation);
                console.log('✅ 대화 정보 업데이트 완료 (메시지 보존):', currentConversationId);
              } else {
                // 메시지가 없으면 그대로 설정
                commit('setCurrentConversation', existingConversation);
                console.log('✅ 기존 대화 복원 완료:', currentConversationId);
              }
            } else {
              // 선택한 대화가 삭제된 경우 첫 번째 대화 선택
              commit('setCurrentConversation', data[0]);
              sessionStorage.setItem('currentConversationId', data[0].id);
            }
          } else if (!state.currentConversation && data.length > 0) {
            commit('setCurrentConversation', data[0]);
            sessionStorage.setItem('currentConversationId', data[0].id);
          }
        }
      } catch (error) {
        commit('setConversations', []);
      }
    },
    
    async createConversation({ commit, state }) {
      try {
        // // console.log('[STORE] 새 대화 생성 시작...');
        
        if (!state.isAuthenticated) {
          console.error('[STORE] 인증되지 않음 - 대화 생성 불가');
          return null;
        }
        
        // JWT 토큰 준비
        const jwtToken = localStorage.getItem('access_token');
        if (!jwtToken) {
          console.error('[STORE] JWT 토큰 없음 - 대화 생성 불가');
          return null;
        }
        
        // 최적화된 요청 헤더
        const headers = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwtToken}`
        };
        
        // API 호출 (타임아웃 설정으로 더 빠른 응답)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5초 타임아웃
        
        const response = await fetch('https://report-collection/api/conversations', {
          method: 'POST',
          headers,
          credentials: 'include',
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          if (response.status === 401) {
            console.error('[STORE] 인증 실패 - 로그아웃 처리');
            commit('clearAuth');
            return null;
          }
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const conversation = await response.json();
        // // console.log('[STORE] 새 대화 생성 성공:', conversation.id);
        
        // 상태 업데이트
        if (!Array.isArray(state.conversations)) {
          commit('setConversations', []);
        }
        
        commit('addConversation', conversation);
        // // console.log('[STORE] 대화 목록에 추가 완료');
        
        return conversation;
      } catch (error) {
        if (error.name === 'AbortError') {
          console.error('[STORE] 대화 생성 타임아웃');
        } else {
          console.error('[STORE] 대화 생성 오류:', error);
        }
        return null;
      }
    },
    
    async deleteConversation({ commit, state }, conversationId) {
      try {
        if (!state.isAuthenticated) return;
        
        const response = await fetch(`https://report-collection/api/conversations/${conversationId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
          credentials: 'include' // 쿠키 포함
        });
        
        // 401 에러인 경우 로그아웃 처리
        if (response.status === 401) {
          commit('clearAuth');
          return;
        }
        
        if (response.ok) {
          commit('removeConversation', conversationId);
        }
      } catch (error) {
        console.error('Error deleting conversation:', error);
      }
    },
    
    async sendMessage({ commit, state }, { text }) {
      try {
        if (!state.isAuthenticated) return;
        
        if (!state.currentConversation) {
          console.error('⚠️ 메시지 전송 실패: 현재 대화가 없습니다.');
          return;
        }
        
        const response = await fetch(`https://report-collection/api/conversations/${state.currentConversation.id}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: text
          }),
          credentials: 'include' // 쿠키 포함
        });
        
        const data = await response.json();
        
        commit('addMessage', {
          conversationId: state.currentConversation.id,
          message: data.userMessage
        });
        
        commit('addMessage', {
          conversationId: state.currentConversation.id,
          message: data.assistantMessage
        });
        
        return data;
      } catch (error) {
        console.error('Error sending message:', error);
      }
    },
    
    async submitFeedback({ commit, state }, { messageId, feedback }) {
      try {
        if (!state.isAuthenticated) return;
        
        // 현재 메시지의 기존 피드백 상태 확인
        const currentConversation = state.currentConversation;
        if (!currentConversation) return;
        
        const message = currentConversation.messages.find(m => m.id === messageId);
        if (!message) {
          console.error('메시지를 찾을 수 없습니다:', messageId);
          return;
        }
        
        // 이제 모든 메시지는 영구 ID를 사용하므로 임시 ID 체크 제거
        
        // 토글 로직: 같은 피드백을 다시 클릭하면 null로 설정 (제거)
        const newFeedback = message.feedback === feedback ? null : feedback;
        const oldFeedback = message.feedback; // 롤백을 위해 기존값 저장
        
        // console.log('피드백 전송:', {
        //   messageId,
        //   feedback: newFeedback,
        //   isTemporaryId
        // });
        
        // Optimistic Update: API 호출 전에 먼저 UI 업데이트
        commit('updateFeedback', {
          conversationId: state.currentConversation.id,
          messageId,
          feedback: newFeedback
        });
        
        // currentConversation의 메시지도 직접 업데이트 (즉시 반영)
        const currentMessage = state.currentConversation.messages.find(m => m.id === messageId);
        if (currentMessage) {
          currentMessage.feedback = newFeedback;
        }
        
        // 백엔드 API 요청 데이터 로깅
        const requestData = { feedback: newFeedback };
        
        // 메시지에서 backend_id 추출 (우선순위: backend_id > messageId에서 -assistant 제거)
        let cleanMessageId;
        if (message.backend_id) {
          cleanMessageId = message.backend_id;
          console.log('✅ backend_id 사용:', cleanMessageId);
        } else {
          // fallback: messageId에서 -assistant 부분 제거
          cleanMessageId = String(messageId).replace('-assistant', '');
          console.log('⚠️ fallback ID 사용:', cleanMessageId);
        }
        
        // 백엔드 ID가 숫자인지 확인
        if (isNaN(cleanMessageId)) {
          console.error('유효하지 않은 메시지 ID:', messageId, 'backend_id:', message.backend_id);
          alert('메시지 ID가 유효하지 않습니다.');
          return;
        }
        
        const response = await fetch(`https://report-collection/api/messages/${cleanMessageId}/feedback`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify(requestData),
          credentials: 'include' // 쿠키 포함
        });
        
        if (!response.ok) {
          // API 호출 실패시 롤백
          commit('updateFeedback', {
            conversationId: state.currentConversation.id,
            messageId,
            feedback: oldFeedback
          });
          
          // 401 에러인 경우 로그아웃 처리
          if (response.status === 401) {
            commit('clearAuth');
            return;
          }
          
          const errorText = await response.text();
          let errorData;
          try {
            errorData = JSON.parse(errorText);
          } catch (e) {
            errorData = { detail: errorText };
          }
          
          console.error('피드백 제출 실패:', {
            status: response.status,
            messageId: cleanMessageId,
            originalMessageId: messageId,
            backend_id: message.backend_id,
            error: errorData.detail || errorText
          });
          
          throw new Error(`Failed to submit feedback: ${errorData.detail || errorText}`);
        }
        
        // 피드백 업데이트 성공 시 UI 트리거 증가 (즉시 반영)
        console.log('✅ 피드백 업데이트 완료:', {
          messageId,
          feedback: newFeedback
        });
        

        
      } catch (error) {

        // 네트워크 에러 등의 경우에만 에러 알림
        if (!error.message.includes('세션이 만료')) {
          alert(`피드백 전송 중 오류가 발생했습니다: ${error.message}`);
        }
      }
    },
    
    // OpenAI API Key 관련 action 제거됨 - 서버 .env에서 관리
    
    async sendStreamingMessage({ commit, state }, { text }) {
      try {
        if (!state.isAuthenticated) return;
        
        if (!state.currentConversation) {
          console.error('⚠️ 스트리밍 메시지 전송 실패: 현재 대화가 없습니다.');
          return;
        }
        
        const currentConversationId = state.currentConversation.id;
        
        // 1. 먼저 영구 message_id 발급
        const prepareResponse = await fetch(`https://report-collection/api/conversations/${currentConversationId}/messages/prepare`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: text,
            conversation_id: currentConversationId
          }),
          credentials: 'include'
        });
        
        if (!prepareResponse.ok) {
          if (prepareResponse.status === 401) {
            await this.dispatch('handleAuthError');
            return;
          }
          throw new Error(`Prepare message failed: ${prepareResponse.status}`);
        }
        
        const preparedData = await prepareResponse.json();
        console.log('✅ 영구 메시지 ID 발급 완료:', preparedData);
        
        // 2. 영구 ID로 메시지 추가 (피드백 버튼 비활성화 상태)
        const userMessage = {
          id: `${preparedData.userMessage.id}-user`,
          conversation_id: currentConversationId,
          role: 'user',
          question: text,
          ans: '',
          created_at: new Date().toISOString(),
          backend_id: preparedData.userMessage.id
        };
        
        commit('addMessage', {
          conversationId: currentConversationId,
          message: userMessage
        });
        
        commit('setIsStreaming', true);
        commit('clearStreamingMessage');
        
        // 에러 처리 개선을 위해 try-catch 사용
        try {
        const response = await fetch('https://report-collection/api/stream', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: text, 

            conversation_id: currentConversationId
            }),
            credentials: 'include' // CORS 인증 정보 전송
        });
          
          if (!response.ok) {
            // 401 에러인 경우 로그아웃 처리
            if (response.status === 401) {
              commit('setIsStreaming', false);
              commit('clearAuth');
              return;
            }
            throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
          }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedMessage = '';
        let imageUrl = null;
        
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
                
                // 3. 스트리밍 완료 시 메시지 내용 업데이트
                try {
                  const completeResponse = await fetch(`https://report-collection/api/messages/${preparedData.assistantMessage.id}/complete`, {
                    method: 'PUT',
                    headers: { 
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    },
                    body: JSON.stringify({ 
                      assistant_response: accumulatedMessage,
                      image_url: imageUrl
                    }),
                    credentials: 'include'
                  });
                  
                  if (completeResponse.ok) {
                    console.log('✅ 메시지 완료 처리 성공');
                    
                    // 프론트엔드에서도 메시지 내용 업데이트
                    commit('updateMessageContent', {
                      messageId: `${preparedData.assistantMessage.id}-assistant`,
                      content: accumulatedMessage,
                      image: imageUrl
                    });
                  } else {
                    console.warn('⚠️ 메시지 완료 처리 실패:', completeResponse.status);
                  }
                } catch (completeError) {
                  console.warn('⚠️ 메시지 완료 처리 오류:', completeError);
                }
                
                break;
              }
              
              try {
                // 이미지 URL이 JSON 형식으로 전송된 경우 처리
                const jsonData = JSON.parse(content);
                if (jsonData.text) {
                  accumulatedMessage += jsonData.text;
                  commit('updateStreamingMessage', accumulatedMessage);
                }
                if (jsonData.image_url) {
                  imageUrl = jsonData.image_url;
                }
              } catch (e) {
                // JSON이 아닌 일반 텍스트인 경우
                accumulatedMessage += content;
                commit('updateStreamingMessage', accumulatedMessage);
              }
            }
          }
        }
        
        // assistantMessage는 이미 영구 ID로 생성되었으므로 제거
        
          // 백엔드 저장 시도
          try {
        const saveResponse = await fetch(`https://report-collection/api/conversations/${currentConversationId}/messages/stream`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: text, 

            assistant_response: accumulatedMessage,
            image_url: imageUrl // 이미지 URL 추가
              }),
              credentials: 'include' // CORS 인증 정보 전송
        });
        
        if (saveResponse.ok) {
          const savedData = await saveResponse.json();

          
          // 실제 데이터베이스 ID로 메시지 업데이트
          const conversation = state.conversations.find(c => c.id === currentConversationId);
          if (conversation && conversation.messages) {
            // User 메시지 ID 업데이트
            const userMessageIndex = conversation.messages.findIndex(m => m.id === userMessage.id && m.role === 'user');
            if (userMessageIndex !== -1) {
              conversation.messages[userMessageIndex].id = savedData.userMessage.id;

            }
            
            // Assistant 메시지는 사용하지 않으므로 제거됨
          }
        } else if (saveResponse.status === 401) {
          // 401 에러인 경우 인증 에러 처리
          await this.dispatch('handleAuthError');
          return;
        }
          } catch (saveError) {
            console.warn('Failed to save message to backend, but UI was updated:', saveError);
            // UI는 이미 업데이트 되었으므로 사용자에게 에러를 표시하지 않음
          }
        
        return { userMessage };
        } catch (streamError) {
          // 스트리밍 오류 발생 시에도 대화는 계속 되도록 처리
          console.error('Streaming error:', streamError);
          
          // 스트리밍 실패 시 user 메시지의 ans 필드에 에러 메시지 추가
          const userMessages = state.conversations.find(c => c.id === currentConversationId)?.messages?.filter(m => m.role === 'user') || [];
          if (userMessages.length > 0) {
            const lastUserMessage = userMessages[userMessages.length - 1];
            lastUserMessage.ans = '죄송합니다. 메시지를 처리하는 중 오류가 발생했습니다. 다시 시도해 주세요.';
          }
          
          
          return { userMessage };
        }
      } catch (error) {
        console.error('Error in streaming message:', error);
        commit('setIsStreaming', false);
      }
    },
    
  }
});


// store 생성 후에 쿠키에서 인증 정보 초기화
setTimeout(() => {
  // 페이지 새로고침 시 SSO 완료 플래그 정리 (새로운 세션이므로)
  const currentUrl = window.location.href;
  if (!currentUrl.includes('id_token') && !currentUrl.includes('code=') && !currentUrl.includes('state=')) {
    // OAuth 콜백이 아닌 일반 페이지 접근 시에만 플래그 정리
    if (performance.navigation.type === performance.navigation.TYPE_RELOAD || 
        performance.navigation.type === performance.navigation.TYPE_NAVIGATE) {
      // // console.log('[AUTH] 새로운 세션 시작 - OAuth 플래그 정리');
      resetOAuthFlags();
    }
  }
  
  initializeAuthFromStorage();
  
  // OAuth 파라미터 확인 및 처리
  if (checkAndProcessOAuthParams()) {
    // OAuth 처리 시작
  }
}, 0);

// OAuth 토큰 처리 중인지 확인하는 플래그
let isProcessingOAuth = false;
let hasProcessedOAuth = false; // OAuth 처리가 이미 완료되었는지 확인하는 플래그

// OAuth 플래그 초기화 함수
function resetOAuthFlags() {
  isProcessingOAuth = false;
  hasProcessedOAuth = false;
  sessionStorage.removeItem('oauth_processing');
  sessionStorage.removeItem('sso_processed');
  // // console.log('[AUTH] OAuth 플래그 초기화됨');
}

const requireAuth = (to, from, next) => {
  // OAuth 콜백 경로인 경우 바로 통과
  if (to.path === '/oauth_callback') {
    next();
    return;
  }
  
  // OAuth 토큰 처리 중인 경우 제한된 시간만 대기
  if (isProcessingOAuth) {
    // OAuth 처리 완료를 기다림 (최대 3초로 단축)
    let waitCount = 0;
    const maxWait = 15; // 3초 (200ms * 15)
    
    const checkAuth = () => {
      waitCount++;
      
      // 처리 완료되었거나 타임아웃된 경우
      if (!isProcessingOAuth || waitCount >= maxWait) {
        // 타임아웃된 경우 OAuth 플래그 강제 정리
        if (waitCount >= maxWait) {
          // // console.log('[AUTH] OAuth 처리 타임아웃 - 플래그 강제 정리');
          isProcessingOAuth = false;
          sessionStorage.removeItem('oauth_processing');
        }
        
        // 인증 상태 확인
        const storedToken = localStorage.getItem('access_token');
        const storedUserInfo = localStorage.getItem('user_info');
        
        if (storedToken && storedUserInfo && store.state.isAuthenticated) {
          // // console.log('[AUTH] 인증 확인됨 - 페이지 접근 허용');
          next();
        } else {
          // // console.log('[AUTH] 인증 실패 - samsung SSO로 리다이렉트');
          next(false); // 인증 실패 시 페이지 접근 차단
          // samsung SSO로 리다이렉트
          setTimeout(() => {
            try {
              window.location.replace('https://report-collection/api/auth/auth_sh');
            } catch (error) {
              try {
                window.location.href = 'https://report-collection/api/auth/auth_sh';
              } catch (error2) {
                console.error('SSO 리다이렉트 실패:', error2);
              }
            }
          }, 100);
        }
      } else {
        setTimeout(checkAuth, 200); // 대기 간격을 200ms로 증가
      }
    };
    checkAuth();
    return;
  }
  
  // 이미 인증된 경우 바로 통과 (store 상태 또는 localStorage 확인)
  if (store.state.isAuthenticated && store.state.token) {
    next();
    return;
  }
  
  // localStorage에서 토큰 확인 (store 상태와 동기화)
  const storedToken = localStorage.getItem('access_token');
  const storedUserInfo = localStorage.getItem('user_info');
  
  if (storedToken && storedUserInfo) {
    try {
      const userData = JSON.parse(storedUserInfo);
      // store에 인증 정보 설정
      store.commit('setAuth', {
        token: storedToken,
        user: userData
      });
      // // console.log('[AUTH] localStorage에서 인증 정보 복원됨');
      next();
      return;
    } catch (error) {
      console.error('Stored user info parsing error:', error);
      // 파싱 실패 시 localStorage 정리
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
    }
  }
  
  // URL에 OAuth 파라미터가 있는 경우 처리 중으로 표시
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  const hash = window.location.hash;
  
  if (token || (hash && (hash.includes('id_token')))) {
    isProcessingOAuth = true;
    next();
    return;
  }
  
  // OAuth 처리 완료 확인
  const hasProcessedOAuth = sessionStorage.getItem('sso_processed') === 'true';
  const isOAuthProcessing = sessionStorage.getItem('oauth_processing') === 'true';
  
  if (hasProcessedOAuth || isOAuthProcessing) {
    // OAuth 처리가 완료되었거나 진행 중인 경우
    // // console.log('[AUTH] OAuth 처리 완료/진행 중 - 접근 허용');
    
    // localStorage에서 토큰 확인으로 인증 상태 판단
    const storedToken = localStorage.getItem('access_token');
    const storedUserInfo = localStorage.getItem('user_info');
    
    if (storedToken && storedUserInfo) {
      // localStorage에 인증 정보가 있으면 접근 허용
      // // console.log('[AUTH] localStorage에 인증 정보 있음 - 접근 허용');
      
      // store 상태도 동기화
      try {
        const userData = JSON.parse(storedUserInfo);
        store.commit('setAuth', {
          token: storedToken,
          user: userData
        });
      } catch (error) {
        console.error('User info parsing error:', error);
      }
      
      next();
      return;
    } else {
      // OAuth 처리 중이지만 아직 토큰이 없는 경우 제한된 시간만 대기
      // // console.log('[AUTH] OAuth 처리 중 - 토큰 설정 대기');
      let retryCount = 0;
      const maxRetries = 6; // 최대 3초 대기 (500ms * 6)
      
      const checkAuthState = () => {
        retryCount++;
        const currentToken = localStorage.getItem('access_token');
        const currentUserInfo = localStorage.getItem('user_info');
        
        if (currentToken && currentUserInfo) {
          // // console.log('[AUTH] 토큰 설정 완료 - 접근 허용');
          try {
            const userData = JSON.parse(currentUserInfo);
            store.commit('setAuth', {
              token: currentToken,
              user: userData
            });
          } catch (error) {
            console.error('User info parsing error:', error);
          }
          next();
        } else if (retryCount >= maxRetries) {
          // // console.log('[AUTH] 토큰 설정 타임아웃 - OAuth 플래그 정리 후 리다이렉트');
          // 타임아웃 시 OAuth 플래그 정리
          sessionStorage.removeItem('oauth_processing');
          sessionStorage.removeItem('sso_processed');
          next(false);
          // samsung SSO로 리다이렉트
          setTimeout(() => {
            try {
              window.location.replace('https://report-collection/api/auth/auth_sh');
            } catch (error) {
              try {
                window.location.href = 'https://report-collection/api/auth/auth_sh';
              } catch (error2) {
                console.error('SSO 리다이렉트 실패:', error2);
              }
            }
          }, 100);
        } else {
          setTimeout(checkAuthState, 500);
        }
      };
      
      setTimeout(checkAuthState, 500);
      return;
    }
  }
  
  // 인증되지 않은 경우 samsung SSO로 리다이렉트
  // // console.log('[AUTH] 인증되지 않음 - SSO로 리다이렉트');
  next(false);
  
  // samsung SSO로 리다이렉트
  setTimeout(() => {
    try {
      window.location.replace('https://report-collection/api/auth/auth_sh');
    } catch (error) {
      try {
        window.location.href = 'https://report-collection/api/auth/auth_sh';
      } catch (error2) {
        alert('로그인이 필요합니다. 수동으로 로그인 페이지로 이동해주세요.');
      }
    }
  }, 100);
};

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { 
      path: '/', 
      component: Home
    },
    { 
      path: '/history', 
      component: ChatHistory
    },
    { 
      path: '/admin', 
      component: Home
    },
    { 
      path: '/oauth_callback', 
      redirect: to => {
        // Get hash from query string if available
        const hash = to.hash || to.query.hash || window.location.hash;
        if (hash) {
          // Process OAuth callback in the app
          const hashParams = new URLSearchParams(hash.substring(1));
          const access_token = hashParams.get('access_token');
          const id_token = hashParams.get('id_token');
          
          if (access_token && id_token) {
            // Extract user info from token and log in
            try {
              const base64Url = id_token.split('.')[1];
              const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
              const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
              }).join(''));
              
              const payload = JSON.parse(jsonPayload);
              
              // Set user info in store
              const user = {
                username: payload.name || "User",
                mail: payload.email || "",
                deptname: payload.deptname || "",
                loginid: payload.sub,
                id: payload.sub
              };
              
              // 백엔드에서 인증 토큰 발급 받기
              fetch('https://report-collection/api/auth/token', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                  username: user.username,
                  id_token: id_token,
                  // access_token 제거 - 백엔드에서 사용하지 않음
                  is_sso: true
                })
              })
              .then(response => {
                if (!response.ok) {
                  return response.json().then(errorData => {
                    console.warn("Backend authentication failed:", errorData);
                    throw new Error(errorData.detail || 'Backend authentication failed');
                  });
                }
                return response.json();
              })
                      .then(data => {
          // 백엔드에서 제공하는 토큰과 사용자 정보로 인증 설정
          const backendUser = data.user || user;
          
          // 토큰과 사용자 정보를 localStorage에 저장
          // 백엔드 JWT 토큰만 사용하도록 설정
          store.commit('setAuth', {
            token: data.access_token,  // 백엔드 JWT 토큰
            user: backendUser
          });
          
          // localStorage에 JWT 토큰 저장 (API 요청용)
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('user_info', JSON.stringify(backendUser));
          
          // // console.log('[AUTH] 백엔드 JWT 토큰 설정 완료:', {
          //   token: data.access_token.substring(0, 20) + '...',
          //   user: backendUser.username
          // });
        })
                      .catch((error) => {
          console.error('Backend authentication failed:', error);
          // 백엔드 인증 실패 시 사용자에게 알림
          alert('백엔드 인증에 실패했습니다. 다시 시도해주세요.');
          // 인증 실패 시 상태만 정리
          // // console.log('백엔드 인증 실패 - 상태 정리');
        })
              .finally(() => {
                // 대화 초기화 시도
                store.commit('setConversations', []);
                store.commit('setCurrentConversation', null);
                store.dispatch('fetchConversations')
                  .catch(error => {
                    console.error('대화 가져오기 실패:', error);
                  })
                  .finally(() => {
                    // OAuth 처리 완료 후 인증 상태 확인
                    isProcessingOAuth = false; // OAuth 처리 완료
                    hasProcessedOAuth = true; // OAuth 처리 완료 플래그 설정
                    
                    // OAuth 처리 완료 플래그 설정
                    sessionStorage.setItem('sso_processed', 'true');
                    sessionStorage.removeItem('oauth_processing');
                    
                    // 인증 상태가 제대로 설정되었는지 확인
                    if (store.state.isAuthenticated && localStorage.getItem('access_token')) {
                      router.push('/');
                    } else {
                      try {
                        // // console.log('인증 실패 - 상태만 정리');
                      } catch (error) {
                        try {
                          // // console.log('OAuth 처리 실패 - 상태만 정리');
                        } catch (error2) {
                          // // console.log('OAuth 인증 실패 - 상태만 정리');
                        }
                      }
                    }
                  });
              });
            } catch (error) {
              // console.error("OAuth Token Processing Error:", error);
              isProcessingOAuth = false; // 오류 시에도 플래그 초기화
            }
          }
        }
        
        // After processing OAuth data, redirect to home
        return '/';
      }
    }
  ]
});

// Check for token in URL (from OAuth redirect)
const checkForAuthToken = () => {
  // 로그아웃 직후인 경우 OAuth 처리 건너뛰기
  const isLogoutRedirect = sessionStorage.getItem('logout_redirect') === 'true';
  if (isLogoutRedirect) {
    // // console.log('[AUTH] 로그아웃 직후 - OAuth 처리 건너뛰기');
    sessionStorage.removeItem('logout_redirect'); // 플래그 정리
    return;
  }
  
  // 이미 OAuth 처리가 완료된 경우 중복 처리 방지
  // // console.log('[AUTH] checkForAuthToken 시작:', {
  //   hasProcessedOAuth,
  //   isProcessingOAuth,
  //   currentUrl: window.location.href
  // });
  
  if (hasProcessedOAuth) {
    // // console.log('[AUTH] OAuth 이미 처리됨, 중복 실행 방지');
    return;
  }
  
  // 기존 처리 중 플래그가 있는 경우 정리 (새로운 처리 시작)
  if (sessionStorage.getItem('oauth_processing') === 'true') {
    // // console.log('[AUTH] 기존 OAuth 처리 플래그 정리');
    sessionStorage.removeItem('oauth_processing');
  }
  
  // OAuth 처리 시작 표시
  isProcessingOAuth = true;
  
  // 1. 쿼리 파라미터에서 토큰 확인 (일반 로그인)
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  // 2. URL 해시에서 samsung OAuth 파라미터 확인 (백엔드로만 전송, 프론트엔드에서는 사용하지 않음)
  if (window.location.hash) {
    // URL 해시 파싱
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const idToken = hashParams.get('id_token');
    const state = hashParams.get('state');
    
    if (idToken && state) {
      // OAuth 처리 시작을 즉시 알림
      // // console.log('[AUTH] OAuth 파라미터 발견 - 처리 시작');
      sessionStorage.setItem('oauth_processing', 'true');
      sessionStorage.removeItem('sso_processed'); // 기존 완료 플래그 제거
      
      // 해시 제거
      const url = new URL(window.location);
      url.hash = '';
      window.history.replaceState({}, document.title, url);
      
      processOAuthToken(idToken, state);
      
      // OAuth 처리 완료 표시
      hasProcessedOAuth = true;
      isProcessingOAuth = false;
      return; // 함수 종료
    }
  }
  
  // 3. 일반 쿼리 파라미터 토큰 처리 (기존 로직)
  if (token) {
    // Clear URL parameters but keep the path
    const url = new URL(window.location);
    url.search = '';
    window.history.replaceState({}, document.title, url);
    
    // Login with token (OAuth 처리가 완료되지 않은 경우에만)
    if (!hasProcessedOAuth) {
      store.dispatch('loginWithToken', token)
        .then(() => {
          hasProcessedOAuth = true;
          isProcessingOAuth = false;
          // // console.log('[AUTH] 토큰 로그인 완료, 홈으로 이동');
          router.push('/');
        })
        .catch(error => {
          console.error("Auto-login failed:", error);
          isProcessingOAuth = false;
          router.push('/login');
        });
    } else {
      // // console.log('[AUTH] OAuth 이미 처리됨, 중복 실행 방지');
      isProcessingOAuth = false;
    }
  } else {
    // 토큰이 없는 경우 처리 완료
    isProcessingOAuth = false;
  }
};

// 전역 라우터 가드 추가
router.beforeEach((to, from, next) => {
  // OAuth 콜백 경로는 통과
  if (to.path === '/oauth_callback') {
    next();
    return;
  }
  
  // 인증이 필요한 경로들
  const protectedRoutes = ['/', '/history', '/admin'];
  if (protectedRoutes.includes(to.path)) {
    requireAuth(to, from, next);
  } else {
    next();
  }
});

// Execute on app start
checkForAuthToken();

const app = createApp(App);

// Vue 디버깅 설정 (앱 레벨)
if (process.env.NODE_ENV === 'development') {
  // Vue 앱 디버깅 활성화
  app.config.devtools = true;
  app.config.debug = true;
  
  // 성능 추적 활성화
  app.config.performance = true;
  
  // 전역 에러 핸들러 (디버깅용)
  app.config.errorHandler = (error, instance, info) => {
    console.error('[Vue Error Handler]', error);
    console.error('[Vue Error Info]', info);
    console.error('[Vue Instance]', instance);
  };
  
  // 전역 경고 핸들러 (디버깅용)
  app.config.warnHandler = (msg, instance, trace) => {
    console.warn('[Vue Warning]', msg);
    console.warn('[Vue Trace]', trace);
  };
  
  // console.log('[Vue Debug] Vue 앱 디버깅 설정 완료');
}

app.use(store);
app.use(router);

// 앱 마운트 후 디버깅 정보 출력
const mountedApp = app.mount('#app');

if (process.env.NODE_ENV === 'development') {
  // 전역 Vue 인스턴스 접근 가능하도록 설정
  window.__VUE_APP__ = mountedApp;
  window.__VUE_STORE__ = store;
  window.__VUE_ROUTER__ = router;
  
  // console.log('[Vue Debug] 전역 디버깅 객체 설정 완료');
  // console.log('[Vue Debug] window.__VUE_APP__, window.__VUE_STORE__, window.__VUE_ROUTER__ 사용 가능');
} 
