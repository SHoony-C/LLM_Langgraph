import { createApp } from 'vue'
import { createStore } from 'vuex'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import ChatHistory from './views/ChatHistory.vue'

// OAuth 토큰 처리 함수
async function processOAuthToken(idToken, state) {
  try {
    // 요청 본문 구성
    const requestBody = `id_token=${encodeURIComponent(idToken)}&state=${encodeURIComponent(state)}`;
    
    // 백엔드의 acs 엔드포인트로 id_token 전송
    const response = await fetch('http://localhost:8001/api/auth/acs', {
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
            // store에 인증 정보 설정
            store.commit('setAuthToken', responseData.access_token || 'oauth_token');
            store.commit('setUser', {
              username: responseData.user.username,
              email: responseData.user.mail,
              loginid: responseData.user.loginid,
              id: responseData.user.userid
            });
            
            // 인증 성공 후 홈페이지로 이동
            window.location.href = '/';
            return;
          }
        } catch (parseError) {
          // 응답 파싱 실패 시 localStorage에서 시도
          setTimeout(() => {
            const accessToken = getStoredToken();
            const userInfo = getStoredUserInfo();
            
            if (accessToken && userInfo) {
              try {
                const userData = JSON.parse(userInfo);
                
                // store에 인증 정보 설정
                store.commit('setAuthToken', accessToken);
                store.commit('setUser', {
                  username: userData.username,
                  email: userData.mail,
                  loginid: userData.loginid,
                  id: userData.userid
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
        const userData = JSON.parse(userInfo);
        
        // store에 인증 정보 설정
        store.commit('setAuthToken', accessToken);
        store.commit('setUser', {
          username: userData.username,
          email: userData.mail,
          loginid: userData.loginid,
          id: userData.userid
        });
      } catch (error) {
        // 에러 처리
      }
    }
    
    return true;
  }
  
  return false;
}



// localStorage에서 토큰과 사용자 정보를 읽는 함수
function getStoredToken() {
  return localStorage.getItem('access_token');
}

function getStoredUserInfo() {
  const userInfo = localStorage.getItem('user_info');
  if (userInfo) {
    try {
      return JSON.parse(userInfo);
    } catch (e) {
      return null;
    }
  }
  return null;
}

// localStorage에서 인증 정보를 가져와서 store에 설정
function initializeAuthFromStorage() {
  const accessToken = getStoredToken();
  const userInfo = getStoredUserInfo();
  
  if (accessToken && userInfo) {
    try {
      // URL 파라미터 형식으로 파싱 (username=value&mail=value&...)
      const userData = {};
      const params = userInfo.split('&');
      
      for (const param of params) {
        if (param.includes('=')) {
          const [key, value] = param.split('=', 2);
          userData[key] = decodeURIComponent(value || '');
        }
      }
      
      // 필수 필드 확인
      if (userData.username && userData.userid) {
        // store가 초기화된 후에만 호출
        if (typeof store !== 'undefined' && store.commit) {
          // store에 인증 정보 설정
          store.commit('setAuthToken', accessToken);
          store.commit('setUser', {
            username: userData.username,
            email: userData.mail || '',
            loginid: userData.loginid || '',
            id: userData.userid
          });
          
          // 인증 상태 확인을 위한 API 호출
          fetch('http://localhost:8001/api/auth/me', {
            headers: { 'Authorization': `Bearer ${accessToken}` }
          })
          .then(response => {
            if (response.ok) {
              // 토큰이 유효한 경우
              console.log('Token validation successful');
            } else {
              // 토큰이 유효하지 않은 경우 localStorage 삭제
              console.log('Token validation failed, clearing storage');
              localStorage.removeItem('access_token');
              localStorage.removeItem('user_info');
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
      } else {
        console.log('Missing required user info fields');
        // 필수 필드가 없는 경우 localStorage 삭제
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
      }
    } catch (error) {
      console.error('Error parsing user info from storage:', error);
      console.log('Raw storage value:', userInfo);
      // 파싱 실패 시 localStorage 삭제
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
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
      apiKey: localStorage.getItem('openai_api_key') || '',
      apiKeySet: !!localStorage.getItem('openai_api_key'),
      apiKeyError: null,
      llamaApiKey: localStorage.getItem('llama_api_key') || '',
      llamaApiBase: localStorage.getItem('llama_api_base') || '',
      llamaApiEndpoint: localStorage.getItem('llama_api_endpoint') || '/llama4/1/llama/aiserving/llama-4/maverick/v1/completions',
      llamaApiSet: !!localStorage.getItem('llama_api_key'),
      llamaApiError: null,
      token: localStorage.getItem('auth_token') || '',
      user: JSON.parse(localStorage.getItem('user') || 'null'),
      isAuthenticated: !!localStorage.getItem('auth_token'),
      isStreaming: false,
      streamingMessage: '',
      shouldScrollToBottom: false,
      _feedbackUpdateTrigger: 0 // 피드백 업데이트 강제 반응성 트리거
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
    setCurrentConversation(state, conversation) {
      console.log('setCurrentConversation 호출:', {
        newConversationId: conversation?.id,
        currentConversationId: state.currentConversation?.id,
        isSame: state.currentConversation && conversation && 
                state.currentConversation.id === conversation.id
      });
      
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
    setApiKey(state, apiKey) {
      state.apiKey = apiKey;
      state.apiKeySet = !!apiKey;
      localStorage.setItem('openai_api_key', apiKey);
    },
    setApiKeyError(state, error) {
      state.apiKeyError = error;
    },
    setAuth(state, { token, user }) {
      console.log('[AUTH] setAuth called with token:', token ? token.substring(0, 20) + '...' : 'null');
      
      // 토큰 형식 확인 (JWT는 3개의 점으로 구분된 부분으로 구성)
      if (token && token.split('.').length === 3) {
        try {
          const header = JSON.parse(atob(token.split('.')[0]));
          console.log('[AUTH] Token header:', header);
          console.log('[AUTH] Token algorithm:', header.alg);
        } catch (e) {
          console.log('[AUTH] Error parsing token header:', e);
        }
      }
      
      state.token = token;
      state.user = user;
      state.isAuthenticated = true;
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('access_token', token);
      localStorage.setItem('user_info', JSON.stringify(user));
      
      // 상태 업데이트 후 강제 반응성 트리거
      state._feedbackUpdateTrigger++;
    },
    setAuthToken(state, token) {
      console.log('[AUTH] setAuthToken called with token:', token ? token.substring(0, 20) + '...' : 'null');
      
      // 토큰 형식 확인 (JWT는 3개의 점으로 구분된 부분으로 구성)
      if (token && token.split('.').length === 3) {
        try {
          const header = JSON.parse(atob(token.split('.')[0]));
          console.log('[AUTH] Token header:', header);
          console.log('[AUTH] Token algorithm:', header.alg);
        } catch (e) {
          console.log('[AUTH] Error parsing token header:', e);
        }
      }
      
      state.token = token;
      state.isAuthenticated = !!token;
      localStorage.setItem('auth_token', token);
      localStorage.setItem('access_token', token);
      
      // 쿠키에도 토큰 저장 (백엔드와 동기화)
      if (token) {
        document.cookie = `auth_token=${token}; path=/; max-age=${30 * 60}; SameSite=Lax`;
      }
      
      // 상태 업데이트 후 강제 반응성 트리거
      state._feedbackUpdateTrigger++;
    },
    setUser(state, user) {
      state.user = user;
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('user_info', JSON.stringify(user));
      
      // 상태 업데이트 후 강제 반응성 트리거
      state._feedbackUpdateTrigger++;
    },
    clearAuth(state) {
      state.token = '';
      state.user = null;
      state.isAuthenticated = false;
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
      state.streamingMessage += content;
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
    setLlamaApiSettings(state, { apiKey, apiBase, apiEndpoint }) {
      state.llamaApiKey = apiKey;
      state.llamaApiSet = !!apiKey;
      
      if (apiBase) {
        state.llamaApiBase = apiBase;
      }
      
      if (apiEndpoint) {
        state.llamaApiEndpoint = apiEndpoint;
      }
      
      // 로컬 스토리지에 저장
      localStorage.setItem('llama_api_key', apiKey);
      localStorage.setItem('llama_api_base', state.llamaApiBase);
      localStorage.setItem('llama_api_endpoint', state.llamaApiEndpoint);
    },
    setLlamaApiError(state, error) {
      state.llamaApiError = error;
    }
  },
  actions: {
    // 인증 에러 공통 처리 함수
    handleAuthError({ commit }) {
      commit('clearAuth');
      commit('setConversations', []);
      commit('setCurrentConversation', null);
      
      // 구글 SSO로 즉시 리다이렉트
      try {
        window.location.replace('http://localhost:8001/api/auth/auth_sh');
      } catch (error) {
        try {
          window.location = 'http://localhost:8001/api/auth/auth_sh';
        } catch (error2) {
          alert('인증 오류 리다이렉트에 실패했습니다. 수동으로 로그인해주세요.');
        }
      }
    },
    
    async register(context, userData) {
      const response = await fetch('http://localhost:8001/api/auth/register', {
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
      
      const response = await fetch('http://localhost:8001/api/auth/token', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }
      
      const data = await response.json();
      
      const userResponse = await fetch('http://localhost:8001/api/auth/me', {
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
      await dispatch('fetchConversations');
      
      return true;
    },
    
    logout({ commit }) {
      commit('clearAuth');
      commit('setConversations', []);
      commit('setCurrentConversation', null);
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
        
        const response = await fetch('http://localhost:8001/api/conversations', {
          headers,
          credentials: 'include' // 쿠키 포함
        });
        
        if (!response.ok) {
          if (response.status === 401) {
            // 인증 오류인 경우 로그아웃 처리
            await this.dispatch('handleAuthError');
            return;
          }
          throw new Error(`Error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // 현재 선택된 대화 ID 저장
        const currentConversationId = state.currentConversation ? state.currentConversation.id : null;
        
        commit('setConversations', data);
        
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
      } catch (error) {
        commit('setConversations', []);
      }
    },
    
    async createConversation({ commit, state }) {
      try {
        if (!state.isAuthenticated) return null;
        
        // 올바른 JWT 토큰을 localStorage에서 가져와서 사용
        const headers = { 'Content-Type': 'application/json' };
        const jwtToken = localStorage.getItem('access_token');
        if (jwtToken) {
          headers['Authorization'] = `Bearer ${jwtToken}`;
        }
        
        const response = await fetch('http://localhost:8001/api/conversations', {
          method: 'POST',
          headers,
          credentials: 'include' // 쿠키 포함
        });
        
        if (!response.ok) {
          // 401 에러인 경우 인증 에러 처리
          if (response.status === 401) {
            await this.dispatch('handleAuthError');
            return null;
          }
          throw new Error(`Status: ${response.status} ${response.statusText}`);
        }
        
        const conversation = await response.json();
        
        if (!Array.isArray(state.conversations)) {
          commit('setConversations', []);
        }
        
        commit('addConversation', conversation);
        return conversation;
      } catch (error) {
        console.error('Error creating conversation:', error);
        return null;
      }
    },
    
    async deleteConversation({ commit, state }, conversationId) {
      try {
        if (!state.isAuthenticated) return;
        
        const response = await fetch(`http://localhost:8001/api/conversations/${conversationId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
          credentials: 'include' // 쿠키 포함
        });
        
        // 401 에러인 경우 인증 에러 처리
        if (response.status === 401) {
          await this.dispatch('handleAuthError');
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
        
        const response = await fetch(`http://localhost:8001/api/conversations/${state.currentConversation.id}/messages`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: text, 
            model: 'gpt-3.5-turbo' // 고정값으로 변경
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
        
        const response = await fetch(`http://localhost:8001/api/messages/${messageId}/feedback`, {
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
            await this.dispatch('handleAuthError');
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
    
    async updateApiKey({ commit }, apiKey) {
      try {
        commit('setApiKeyError', null);
        
        const response = await fetch('http://localhost:8001/api/set-api-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to set API key');
        }
        
        commit('setApiKey', apiKey);
        return { success: true };
      } catch (error) {

        commit('setApiKeyError', error.message);
        return { success: false, error: error.message };
      }
    },
    
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
        const response = await fetch('http://localhost:8001/api/stream', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: text, 
            model: 'gpt-3.5-turbo', // 고정값으로 변경
            conversation_id: currentConversationId
            }),
            credentials: 'include' // CORS 인증 정보 전송
        });
          
          if (!response.ok) {
            // 401 에러인 경우 인증 에러 처리
            if (response.status === 401) {
              await this.dispatch('handleAuthError');
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
                  commit('updateStreamingMessage', jsonData.text);
                  accumulatedMessage += jsonData.text;
                }
                if (jsonData.image_url) {
                  imageUrl = jsonData.image_url;
                }
              } catch (e) {
                // JSON이 아닌 일반 텍스트인 경우
                commit('updateStreamingMessage', content);
                accumulatedMessage += content;
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
        const saveResponse = await fetch(`http://localhost:8001/api/conversations/${currentConversationId}/messages/stream`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify({ 
            question: text, 
            model: 'gpt-3.5-turbo', // 고정값으로 변경
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
            model: 'gpt-3.5-turbo', // 고정값으로 변경
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
    
    async loginWithToken({ commit, dispatch }, token) {
      try {
        // Set token in store
        const userResponse = await fetch('http://localhost:8001/api/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` },
          credentials: 'include' // 쿠키 포함
        });
        
        if (!userResponse.ok) {
          throw new Error('Failed to get user information');
        }
        
        const userData = await userResponse.json();
        
        commit('setAuth', {
          token: token,
          user: userData
        });
        
        // localStorage에 JWT 토큰 저장
        localStorage.setItem('access_token', token);
        
        commit('setConversations', []);
        commit('setCurrentConversation', null);
        await dispatch('fetchConversations');
        
        return true;
      } catch (error) {
        console.error('Error authenticating with token:', error);
        throw error;
      }
    },
    
    async updateLlamaApiSettings({ commit }, { apiKey, apiBase, apiEndpoint }) {
      try {
        commit('setLlamaApiError', null);
        
        const response = await fetch('http://localhost:8001/api/set-custom-api-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_key: apiKey,
            api_base: apiBase,
            api_endpoint: apiEndpoint
          })
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to set Llama API settings');
        }
        
        commit('setLlamaApiSettings', { apiKey, apiBase, apiEndpoint });
        return { success: true };
      } catch (error) {
        console.error('Error setting Llama API settings:', error);
        commit('setLlamaApiError', error.message);
        return { success: false, error: error.message };
      }
    }
  }
});

// store 생성 후에 쿠키에서 인증 정보 초기화
setTimeout(() => {
      initializeAuthFromStorage();
  
  // OAuth 파라미터 확인 및 처리
  if (checkAndProcessOAuthParams()) {
    // OAuth 처리 시작
  }
}, 0);

// OAuth 토큰 처리 중인지 확인하는 플래그
let isProcessingOAuth = false;
let hasProcessedOAuth = false; // OAuth 처리가 이미 완료되었는지 확인하는 플래그

const requireAuth = (to, from, next) => {
  // OAuth 콜백 경로인 경우 바로 통과
  if (to.path === '/oauth_callback') {
    next();
    return;
  }
  
  // OAuth 토큰 처리 중인 경우 잠시 대기
  if (isProcessingOAuth) {
    // OAuth 처리 완료를 기다림 (최대 5초)
    let waitCount = 0;
    const maxWait = 50; // 5초 (100ms * 100)
    
    const checkAuth = () => {
      waitCount++;
      
      if (!isProcessingOAuth || waitCount >= maxWait) {
        if (store.state.isAuthenticated) {
          next();
        } else {
          next(false);
          setTimeout(() => {
            try {
              window.location.replace('http://localhost:8001/api/auth/auth_sh');
            } catch (error) {
              try {
                window.location = 'http://localhost:8001/api/auth/auth_sh';
              } catch (error2) {
                alert('OAuth 리다이렉트에 실패했습니다. 수동으로 로그인해주세요.');
              }
            }
          }, 100);
        }
      } else {
        setTimeout(checkAuth, 100);
      }
    };
    checkAuth();
    return;
  }
  
  // 이미 인증된 경우 바로 통과
  if (store.state.isAuthenticated && store.state.token) {
    next();
    return;
  }
  
  // URL에 OAuth 토큰이 있는 경우 처리 중으로 표시
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  const hash = window.location.hash;
  
  if (token || (hash && (hash.includes('access_token') || hash.includes('id_token')))) {
    isProcessingOAuth = true;
    next();
    return;
  }
  
  // 이미 OAuth 처리가 완료된 경우 중복 처리 방지
  if (hasProcessedOAuth) {
    next();

    return;
  }
  
  // 모든 보호된 경로에서 구글 SSO로 리다이렉트
  
  // 강제 리다이렉트를 위한 여러 방법 시도
  next(false);
  
  // 즉시 리다이렉트 시도 (타임아웃 없이)
  
  try {
    // 방법 1: window.location.replace 사용
    const redirectUrl = 'http://localhost:8001/api/auth/auth_sh';
    
    // 현재 페이지와 리다이렉트 URL 비교
    if (window.location.href === redirectUrl) {
      return;
    }
    
    // 리다이렉트 시도
    
    // 먼저 백엔드 서버 연결 테스트
    fetch('http://localhost:8001/api/auth/auth_sh', { 
      method: 'HEAD',
      mode: 'no-cors' // CORS 우회 시도
    })
    .then(() => {
      // 서버가 응답하면 리다이렉트 실행
      window.location.replace(redirectUrl);
    })
    .catch(() => {
      // 서버 연결 실패해도 리다이렉트 시도
      window.location.replace(redirectUrl);
    });
    
    // 리다이렉트가 실제로 작동하는지 확인
    setTimeout(() => {
      if (window.location.href !== redirectUrl) {
        // 방법 1: href 사용
        try {
          window.location.href = redirectUrl;
        } catch (error) {
          // 에러 처리
        }
        
        // 방법 2: assign 사용
        setTimeout(() => {
          if (window.location.href !== redirectUrl) {
            try {
              window.location.assign(redirectUrl);
            } catch (error) {
              // 에러 처리
            }
          }
        }, 200);
        
        // 방법 3: 직접 할당
        setTimeout(() => {
          if (window.location.href !== redirectUrl) {
            try {
              window.location = redirectUrl;
            } catch (error) {
              // 에러 처리
            }
          }
        }, 400);
        
        // 방법 4: form submit을 통한 리다이렉트
        setTimeout(() => {
          if (window.location.href !== redirectUrl) {
            try {
              const form = document.createElement('form');
              form.method = 'GET';
              form.action = redirectUrl;
              document.body.appendChild(form);
              form.submit();
            } catch (error) {
              // 에러 처리
            }
          }
        }, 600);
        
        // 방법 5: iframe을 통한 리다이렉트
        setTimeout(() => {
          if (window.location.href !== redirectUrl) {
            try {
              const iframe = document.createElement('iframe');
              iframe.src = redirectUrl;
              iframe.style.display = 'none';
              document.body.appendChild(iframe);
            } catch (error) {
              // 에러 처리
            }
          }
        }, 800);
        
        // 최후의 수단: 사용자에게 수동 리다이렉트 안내
        setTimeout(() => {
          if (window.location.href !== redirectUrl) {
            alert(`인증이 필요합니다. 자동 리다이렉트에 실패했습니다.\n\n수동으로 다음 URL로 이동해주세요:\n${redirectUrl}`);
          }
        }, 1000);
      }
    }, 1000);
    
  } catch (error) {
    try {
      // 방법 2: window.location.assign 사용
      window.location.assign('http://localhost:8001/api/auth/auth_sh');
    } catch (error2) {
      // 방법 3: 직접 URL 변경
      try {
        window.location = 'http://localhost:8001/api/auth/auth_sh';
      } catch (error3) {
        // 최후의 수단: 사용자에게 수동 리다이렉트 안내
        alert('인증이 필요합니다. 자동 리다이렉트에 실패했습니다. 수동으로 로그인 페이지로 이동해주세요.');
      }
    }
  }
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
                loginid: payload.sub,
                id: payload.sub
              };
              
              // 백엔드에서 인증 토큰 발급 받기
              fetch('http://localhost:8001/api/auth/token', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                  username: user.username,
                  id_token: id_token,
                  access_token: access_token,
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
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('user_info', JSON.stringify(backendUser));
          
          store.commit('setAuth', {
            token: data.access_token,
            user: backendUser
          });
        })
                      .catch((error) => {
          console.error('Backend authentication failed:', error);
          // 백엔드 인증 실패 시 사용자에게 알림
          alert('백엔드 인증에 실패했습니다. 다시 시도해주세요.');
          // 인증 실패 시 SSO 페이지로 리다이렉트
          window.location.replace('http://localhost:8001/api/auth/auth_sh');
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
                    
                    // 인증 상태가 제대로 설정되었는지 확인
                    if (store.state.isAuthenticated && localStorage.getItem('access_token')) {
                      router.push('/');
                    } else {
                      try {
                        window.location.replace('http://localhost:8001/api/auth/auth_sh');
                      } catch (error) {
                        try {
                          window.location = 'http://localhost:8001/api/auth/auth_sh';
                        } catch (error2) {
                          alert('OAuth 콜백 리다이렉트에 실패했습니다. 수동으로 로그인해주세요.');
                        }
                      }
                    }
                  });
              });
            } catch (error) {
              console.error("OAuth Token Processing Error:", error);
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
  // 이미 OAuth 처리가 완료된 경우 중복 처리 방지
  if (hasProcessedOAuth) {
    return;
  }
  
  // OAuth 처리 시작 표시
  isProcessingOAuth = true;
  
  // 1. 쿼리 파라미터에서 토큰 확인 (일반 로그인)
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  // 2. URL 해시에서 토큰 확인 (Google OAuth)
  let hashToken = null;
  let idToken = null;
  
  if (window.location.hash) {
    // URL 해시 파싱
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    hashToken = hashParams.get('access_token');
    idToken = hashParams.get('id_token');
    
    if (hashToken && idToken) {
      // 해시 제거
      const url = new URL(window.location);
      url.hash = '';
      window.history.replaceState({}, document.title, url);
      
      // id_token 디코딩 (JWT)
      try {
        // Base64 URL 디코딩
        const base64Url = idToken.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        
        const payload = JSON.parse(jsonPayload);
        
        // 사용자 정보 설정
        const user = {
          username: payload.name || "User",
          mail: payload.email || "",
          loginid: payload.sub,
          id: payload.sub // 백엔드 ID 대신 sub 사용
        };
        
        // 백엔드에서 인증 토큰 발급 받기
        fetch('http://localhost:8001/api/auth/token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: user.username,
            id_token: idToken,
            access_token: hashToken,
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
          store.commit('setAuth', {
            token: data.access_token,
            user: backendUser
          });
        })
        .catch((error) => {
          console.error('Backend authentication failed:', error);
          // 백엔드 인증 실패 시 사용자에게 알림
          alert('백엔드 인증에 실패했습니다. 다시 시도해주세요.');
          // 인증 실패 시 SSO 페이지로 리다이렉트
          window.location.replace('http://localhost:8001/api/auth/auth_sh');
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
              
              // 인증 상태가 제대로 설정되었는지 확인
              if (store.state.isAuthenticated && localStorage.getItem('access_token')) {
                router.push('/');
              } else {
                try {
                  window.location.replace('http://localhost:8001/api/auth/auth_sh');
                } catch (error) {
                  try {
                    window.location = 'http://localhost:8001/api/auth/auth_sh';
                  } catch (error2) {
                    alert('checkForAuthToken 리다이렉트에 실패했습니다. 수동으로 로그인해주세요.');
                  }
                }
              }
            });
        });
        
        return; // 함수 종료
      } catch (error) {
        console.error("ID 토큰 처리 오류:", error);
        isProcessingOAuth = false; // 오류 시에도 플래그 초기화
      }
    }
  }
  
  // 3. 일반 쿼리 파라미터 토큰 처리 (기존 로직)
  if (token) {
    // Clear URL parameters but keep the path
    const url = new URL(window.location);
    url.search = '';
    window.history.replaceState({}, document.title, url);
    
    // Login with token
    store.dispatch('loginWithToken', token)
      .then(() => {
        isProcessingOAuth = false;
        router.push('/');
      })
      .catch(error => {
        console.error("Auto-login failed:", error);
        isProcessingOAuth = false;
        router.push('/login');
      });
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
app.use(store);
app.use(router);
app.mount('#app'); 