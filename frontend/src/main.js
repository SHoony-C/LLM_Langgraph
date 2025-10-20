import { createApp } from 'vue'
import { createStore } from 'vuex'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import ChatHistory from './views/ChatHistory.vue'

// OAuth 토큰 처리 함수
async function processOAuthToken(idToken, state) {
  try {
    // OAuth 처리 시작을 즉시 알림
    // console.log('[AUTH] processOAuthToken 시작 - oauth_processing 플래그 설정');
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
              // console.log('responseData : ',responseData)
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
            
            // console.log('[AUTH] 백엔드 JWT 토큰 설정 완료 (processOAuthToken):', {
            //   token: responseData.access_token.substring(0, 20) + '...',
            //   user: responseData.user.username
            // });
            
            // 인증 성공 후 대화 목록 가져오기
            console.log('[AUTH] 대화 목록 가져오기 시작');
            try {
              await store.dispatch('fetchConversations');
              console.log('[AUTH] 대화 목록 가져오기 완료');
            } catch (error) {
              console.error('[AUTH] 대화 목록 가져오기 실패:', error);
            }
            
            // 인증 성공 표시 및 Vue Router로 이동 (window.location 사용 금지)
            hasProcessedOAuth = true;
            isProcessingOAuth = false;
            
            // OAuth 처리 완료 플래그 설정
            sessionStorage.setItem('sso_processed', 'true');
            sessionStorage.removeItem('oauth_processing');
            
            // console.log('[AUTH] OAuth 처리 완료, Vue Router로 이동');
            
            // Vue Router가 준비된 후 이동 (지연 증가)
            setTimeout(() => {
              if (router && router.push) {
                // console.log('[AUTH] 홈페이지로 이동 중...');
                router.push('/').then(() => {
                  // console.log('[AUTH] 홈페이지 이동 완료');
                  
                  // 추가 대기 후 플래그 정리 (중복 리다이렉트 방지)
                  setTimeout(() => {
                    sessionStorage.setItem('sso_processed', 'true');
                    sessionStorage.removeItem('oauth_processing');
                    // console.log('[AUTH] OAuth 플래그 최종 정리 완료');
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
                // console.log('[AUTH] localStorage 복원 후 대화 목록 가져오기');
                store.dispatch('fetchConversations').then(() => {
                  console.log('[AUTH] localStorage 복원 후 대화 목록 가져오기 완료');
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
        // console.log('userData2 : ',userData)
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

  const normalizedId = parsedUser.userid || parsedUser.id || parsedUser.user_id || parsedUser.sub || null;
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
          headers: { 'Authorization': `Bearer ${accessToken}` }
        })
        .then(response => {
          if (response.ok) {
            console.log('Token validation successful');
          } else {
            console.log('Token validation failed, clearing storage');
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
      _feedbackUpdateTrigger: 0, // 피드백 업데이트 강제 반응성 트리거
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
      state.currentConversation = conversation;
      
      // 새 대화 선택 시 랭그래프 관련 상태 초기화를 위한 트리거
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
      // console.log('setCurrentConversation 호출:', {
      //   newConversationId: conversation?.id,
      //   currentConversationId: state.currentConversation?.id,
      //   isSame: state.currentConversation && conversation && 
      //           state.currentConversation.id === conversation.id
      // });
      
      // 항상 대화를 설정 (동일한 대화도 다시 설정하여 랭그래프 복원 트리거)
      state.currentConversation = conversation;
      
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
    updateFeedback(state, { conversationId, messageId, feedback }) {
      // 전체 conversations 배열을 완전히 새로 생성
      const newConversations = state.conversations.map(conversation => {
        if (conversation.id !== conversationId) {
          return conversation; // 다른 대화는 그대로 유지
        }
        
        // 해당 대화의 메시지들을 완전히 새로 생성
        const newMessages = conversation.messages.map(message => {
          if (message.id !== messageId) {
            return message; // 다른 메시지는 그대로 유지
          }
          
          // 해당 메시지만 새로운 객체로 생성
          const updatedMessage = {
            ...message,
            feedback: feedback
          };
          
          return updatedMessage;
        });
        
        // 대화 객체도 완전히 새로 생성
        return {
          ...conversation,
          messages: newMessages
        };
      });
      
      // 상태 전체를 새로운 배열로 교체
      state.conversations = newConversations;
      
      // 현재 대화도 업데이트
      if (state.currentConversation && state.currentConversation.id === conversationId) {
        const updatedCurrentConversation = newConversations.find(c => c.id === conversationId);
        state.currentConversation = updatedCurrentConversation;
      }
      
      // 반응성 트리거 업데이트
      state._feedbackUpdateTrigger = Date.now();
    },
    setApiKeyError(state, error) {
      state.apiKeyError = error;
    },
    setAuth(state, { token, user }) {
      // console.log('[AUTH] setAuth called with token:', token ? token.substring(0, 20) + '...' : 'null');
      
      // 토큰 형식 확인 (JWT는 3개의 점으로 구분된 부분으로 구성)
      if (token && token.split('.').length === 3) {
        try {
          const header = JSON.parse(atob(token.split('.')[0]));
          // console.log('[AUTH] Token header:', header);
          // console.log('[AUTH] Token algorithm:', header.alg);
          
          // HS256 알고리즘인지 확인 (백엔드 JWT 토큰만 허용)
          if (header.alg === 'HS256') {
            // console.log('[AUTH] 백엔드 JWT 토큰 확인됨');
          } else {
            console.error('[AUTH] 오류: HS256이 아닌 토큰은 허용되지 않음:', header.alg);
            return;
          }
        } catch (e) {
          // console.log('[AUTH] Error parsing token header:', e);
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

      
      state.token = token;
      state.user = normalizedUser;
      state.isAuthenticated = !!token;
      
      // localStorage에 토큰 저장 (API 요청용)
      localStorage.setItem('access_token', token);
      localStorage.setItem('user_info', JSON.stringify(normalizedUser));
      
      // 기존 auth_token과 user도 저장 (호환성 유지)
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user', JSON.stringify(normalizedUser));
      
      // 상태 업데이트 후 강제 반응성 트리거
      state._feedbackUpdateTrigger++;
    },
    setUser(state, user) {
      state.user = user;
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('user_info', JSON.stringify(user));
      
      // 사용자 정보만 업데이트 (토큰은 setAuth에서 관리)
      // 상태 업데이트 후 강제 반응성 트리거
      state._feedbackUpdateTrigger++;
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
      
      // console.log('인증 오류 발생 - 상태 정리만 수행');
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
        
        // 현재 선택된 대화 ID 저장
        const currentConversationId = state.currentConversation ? state.currentConversation.id : null;
        
        commit('setConversations', data);
        
        // 로그인 후 새 대화 플래그가 설정된 경우 자동 선택 방지
        if (state.loginNewConversation) {
          // 로그인 후에는 대화를 자동으로 선택하지 않음
          commit('setCurrentConversation', null);
        } else {
          // 로그인 후 새 대화 플래그가 설정된 경우 자동 선택 방지
        if (state.loginNewConversation) {
          // 로그인 후에는 대화를 자동으로 선택하지 않음
          commit('setCurrentConversation', null);
        } else {
          // 현재 대화가 없거나 기존 선택한 대화가 있으면 해당 대화 유지
          if (currentConversationId && data.length > 0) {
            const existingConversation = data.find(c => c.id === currentConversationId);
            if (existingConversation) {
              commit('setCurrentConversation', existingConversation);
            } else {
              // 선택한 대화가 삭제된 경우 첫 번째 대화 선택
              commit('setCurrentConversation', data[0]);
            }
          } else if (!state.currentConversation && data.length > 0) {
              commit('setCurrentConversation', data[0]);
            }
          }
        }
      } catch (error) {
        commit('setConversations', []);
      }
    },
    
    async createConversation({ commit, state }) {
      try {
        // console.log('[STORE] 새 대화 생성 시작...');
        
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
        // console.log('[STORE] 새 대화 생성 성공:', conversation.id);
        
        // 상태 업데이트
        if (!Array.isArray(state.conversations)) {
          commit('setConversations', []);
        }
        
        commit('addConversation', conversation);
        // console.log('[STORE] 대화 목록에 추가 완료');
        
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
          await this.dispatch('createConversation');
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
        if (!message) return;
        
        // 토글 로직: 같은 피드백을 다시 클릭하면 null로 설정 (제거)
        const newFeedback = message.feedback === feedback ? null : feedback;
        const oldFeedback = message.feedback; // 롤백을 위해 기존값 저장
        

        
        // Optimistic Update: API 호출 전에 먼저 UI 업데이트
        commit('updateFeedback', {
          conversationId: state.currentConversation.id,
          messageId,
          feedback: newFeedback
        });
        
        // 백엔드 API 요청 데이터 로깅
        const requestData = { feedback: newFeedback };
        
        const response = await fetch(`https://report-collection/api/messages/${messageId}/feedback`, {
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
          throw new Error(`Failed to submit feedback: ${errorData.detail || errorText}`);
        }
        

        
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
        
        let currentConversationId;
        
        if (!state.currentConversation) {
          const newConversation = await this.dispatch('createConversation');
          if (!newConversation) {
            throw new Error('Failed to create conversation');
          }
          currentConversationId = newConversation.id;
        } else {
          currentConversationId = state.currentConversation.id;
        }
        
        const userMessage = {
          id: Date.now(),
          conversation_id: currentConversationId,
          role: 'user',
          question: text,
          model: 'gpt-3.5-turbo', // 고정값으로 변경
          created_at: new Date().toISOString()
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
        
        const assistantMessage = {
          id: Date.now() + 1,
          conversation_id: currentConversationId,
          role: 'assistant',
          question: text,
          ans: accumulatedMessage,
          model: 'gpt-3.5-turbo', // 고정값으로 변경
          created_at: new Date().toISOString()
        };
        
        // 이미지 URL이 있는 경우 추가
        if (imageUrl) {
          assistantMessage.image = imageUrl;
        }
        
        commit('addStreamingMessageToConversation', {
          conversationId: currentConversationId,
          message: assistantMessage
        });
        
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
            
            // Assistant 메시지 ID 업데이트
            const assistantMessageIndex = conversation.messages.findIndex(m => m.id === assistantMessage.id && m.role === 'assistant');
            if (assistantMessageIndex !== -1) {
              conversation.messages[assistantMessageIndex].id = savedData.assistantMessage.id;

            }
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
        
        return { userMessage, assistantMessage };
        } catch (streamError) {
          // 스트리밍 오류 발생 시에도 대화는 계속 되도록 처리
          console.error('Streaming error:', streamError);
          
          // 스트리밍 실패 시 간단한 에러 메시지를 응답으로 추가
          const errorMessage = {
            id: Date.now() + 1,
            conversation_id: currentConversationId,
            role: 'assistant',
            question: text,
            ans: '죄송합니다. 메시지를 처리하는 중 오류가 발생했습니다. 다시 시도해 주세요.',

            created_at: new Date().toISOString()
          };
          
          commit('addMessage', {
            conversationId: currentConversationId,
            message: errorMessage
          });
          
          return { userMessage, assistantMessage: errorMessage };
        }
      } catch (error) {
        console.error('Error in streaming message:', error);
        commit('setIsStreaming', false);
      }
    },
    
  }
});
