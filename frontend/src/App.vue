<template>
  <div class="app" :class="{ 'dark-mode': true, 'collapsed-sidebar': isSidebarCollapsed }">
    <aside class="sidebar">
      <div class="sidebar-controls">
        <div class="new-chat-btn" @click="$store.dispatch('createConversation')">
          <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
        </div>
        <div class="toggle-sidebar-btn" @click="toggleSidebar">
          <svg class="toggle-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </div>
      </div>
      
      <div class="conversations-list">
        <transition-group name="list">
          <div 
            v-for="conversation in $store.state.conversations" 
            :key="conversation.id" 
            class="conversation-item"
            :class="{ active: $store.state.currentConversation && conversation.id === $store.state.currentConversation.id }"
            @click="selectConversation(conversation)"
          >
            <div class="conversation-icon">
              {{ getConversationIcon(conversation.icon_type) }}
            </div>
            <div class="conversation-content">
              {{ getConversationTitle(conversation) }}
            </div>
            <div class="conversation-actions">
              <button class="delete-btn" @click.stop="deleteConversation(conversation.id)">
                <svg class="delete-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </div>
        </transition-group>
      </div>
    </aside>
    
    <main class="main">
      <div class="header">
        <div class="title">Report Collection</div>
        
        <div class="user-profile" @click.stop="handleUserProfileClick">
          <div class="user-avatar">
            <span v-if="currentUser && currentUser.username" class="user-initial">
              {{ currentUser.username.charAt(0).toUpperCase() }}
            </span>
            <svg v-else class="user-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </div>
          <div class="user-popup" v-if="isUserPopupOpen">
            <div class="user-popup-header">
              <div class="user-popup-avatar">
                <svg class="user-popup-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </div>
              <div class="user-popup-info">
                <div class="user-popup-name">{{ currentUser ? currentUser.username : 'No Username' }}</div>
                <div class="user-popup-email">{{ currentUser ? (currentUser.mail || 'No Email') : 'No Email' }}</div>
                <div class="user-popup-details">{{ currentUser ? (currentUser.loginid || currentUser.id || 'No ID') : 'No Details' }}</div>
              </div>
            </div>
            <div class="user-popup-menu">
              <div class="menu-item" @click="showApiKeyModal = true">
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>
                </svg>
                Set OpenAI API Key
              </div>
              <div class="menu-item" @click="showLlamaApiModal = true">
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>
                </svg>
                Set Custom Llama API
              </div>
              <div class="menu-item">
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                Profile Settings
              </div>
              <div class="menu-item">
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                  <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
                Add Links
              </div>
              <div class="menu-item">
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
                Security
              </div>
              <div class="menu-item" @click="logout">
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                Logout
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    
    <!-- API Key Modal -->
    <div class="modal-overlay" v-if="showApiKeyModal" @click.self="showApiKeyModal = false">
      <div class="modal-container">
        <div class="modal-header">
          <h3>Set OpenAI API Key</h3>
          <button class="close-btn" @click="showApiKeyModal = false">×</button>
        </div>
        <div class="modal-body">
          <p class="api-key-info">Your API key is stored locally in your browser and sent directly to the API. We never store your API key on our servers.</p>
          
          <div class="form-group">
            <label for="apiKey">OpenAI API Key</label>
            <input 
              type="text" 
              id="apiKey" 
              v-model="apiKeyInput" 
              placeholder="sk-..." 
              :class="{ 'error': $store.state.apiKeyError }"
            />
            <p class="error-message" v-if="$store.state.apiKeyError">{{ $store.state.apiKeyError }}</p>
            <p class="api-key-status" v-if="$store.state.apiKeySet && !$store.state.apiKeyError">
              <svg class="check-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              API Key is set
            </p>
          </div>
          
          <p class="api-key-help">
            Don't have an API key? <a href="https://platform.openai.com/account/api-keys" target="_blank">Get one from OpenAI</a>
          </p>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="showApiKeyModal = false">Cancel</button>
          <button 
            class="save-btn" 
            @click="saveApiKey" 
            :disabled="!apiKeyInput.trim().startsWith('sk-')">
            Save API Key
          </button>
        </div>
      </div>
    </div>

    <!-- Custom Llama API Modal -->
    <div class="modal-overlay" v-if="showLlamaApiModal" @click.self="showLlamaApiModal = false">
      <div class="modal-container">
        <div class="modal-header">
          <h3>Set Custom Llama API</h3>
          <button class="close-btn" @click="showLlamaApiModal = false">×</button>
        </div>
        <div class="modal-body">
          <p class="api-key-info">Configure your custom Llama API settings. Your API key is stored locally in your browser.</p>
          
          <div class="form-group">
            <label for="llamaApiKey">Custom API Key</label>
            <input 
              type="text" 
              id="llamaApiKey" 
              v-model="llamaApiKeyInput" 
              placeholder="" 
            />
          </div>
          
          <div class="form-group">
            <label for="llamaApiBase">API Base URL (Optional)</label>
            <input 
              type="text" 
              id="llamaApiBase" 
              v-model="llamaApiBaseInput" 
              placeholder="" 
            />
          </div>
          
          <div class="form-group">
            <label for="llamaApiEndpoint">API Endpoint (Optional)</label>
            <input 
              type="text" 
              id="llamaApiEndpoint" 
              v-model="llamaApiEndpointInput" 
              placeholder="" 
            />
          </div>
          
          <p class="api-key-help">
            If you provide just the API key, the default endpoint will be used.
          </p>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="showLlamaApiModal = false">Cancel</button>
          <button 
            class="save-btn" 
            @click="saveLlamaApiSettings" 
            :disabled="!llamaApiKeyInput.trim()">
            Save API Settings
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      isDarkMode: true,
      isSidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true' || false,
      isUserPopupOpen: false,
      showApiKeyModal: false,
      showLlamaApiModal: false,
      apiKeyInput: '',
      llamaApiKeyInput: '',
      llamaApiBaseInput: '',
      llamaApiEndpointInput: '',
    }
  },
  computed: {
    // 사용자 정보 반응성 개선
    currentUser() {
      return this.$store.state.user;
    },
    isUserAuthenticated() {
      // localStorage의 JWT 토큰이 있으면 인증된 것으로 간주
      const jwtToken = localStorage.getItem('access_token');
      return jwtToken && this.$store.state.isAuthenticated;
    },
  },
  watch: {
    // 사용자 정보 변경 감지
    currentUser: {
              handler() {
        
      },
      deep: true,
      immediate: true
    },
    isUserAuthenticated: {
              handler() {

      },
      immediate: true
    }
  },
  methods: {
    toggleDarkMode() {
      this.isDarkMode = !this.isDarkMode;
      localStorage.setItem('darkMode', this.isDarkMode);
    },
    toggleSidebar() {
      this.isSidebarCollapsed = !this.isSidebarCollapsed;
      localStorage.setItem('sidebarCollapsed', this.isSidebarCollapsed);
    },
    handleUserProfileClick(event) {
      // localStorage에서 JWT 토큰 확인
      const jwtToken = localStorage.getItem('access_token');
      
      // 로그인이 안되면 SSO로 리다이렉트
      if (!jwtToken || !this.isUserAuthenticated || !this.currentUser) {
        console.log('인증 상태 확인:', {
          jwtToken: !!jwtToken,
          isUserAuthenticated: this.isUserAuthenticated,
          currentUser: !!this.currentUser
        });
        window.location.href = 'http://localhost:8001/api/auth/auth_sh';
        return;
      }
      
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      this.isUserPopupOpen = !this.isUserPopupOpen;
    },
    async logout() {
      try {

        
        // 사용자 팝업 닫기
        this.isUserPopupOpen = false;
        
        // 로그아웃 리다이렉트 플래그 설정 (무한 리다이렉트 방지)
        sessionStorage.setItem('logout_redirect', 'true');
        
        // Vuex store의 logout action 실행
        await this.$store.dispatch('logout');
        

        
        // 로그아웃 후 로그인 페이지로 리다이렉트
        // 무한 리다이렉트 방지를 위해 직접 SSO로 이동하지 않음
        window.location.href = 'http://localhost:8001/api/auth/auth_sh';
        
      } catch (error) {
        console.error('Error during logout:', error);
        
        // 에러가 발생해도 기본 정리 수행
        this.isUserPopupOpen = false;
        
        // 로그아웃 리다이렉트 플래그 설정
        sessionStorage.setItem('logout_redirect', 'true');
        
        // 강제로 로그인 페이지로 이동
        window.location.href = 'http://localhost:8001/api/auth/auth_sh';
      }
    },
    async saveApiKey() {
      if (!this.apiKeyInput.trim().startsWith('sk-')) {
        this.$store.commit('setApiKeyError', 'Invalid API key format. It should start with "sk-"');
        return;
      }
      
      const result = await this.$store.dispatch('updateApiKey', this.apiKeyInput.trim());
      if (result.success) {
        this.showApiKeyModal = false;
      }
    },
    deleteConversation(conversationId) {
      if (confirm('Are you sure you want to delete this conversation?')) {
        this.$store.dispatch('deleteConversation', conversationId);
      }
    },
    async validateAuthToken() {
      try {
        // localStorage에서 JWT 토큰 가져오기
        const jwtToken = localStorage.getItem('access_token');
        
        if (!jwtToken) {
          console.log('JWT 토큰이 없음');
          this.$store.dispatch('logout');
          window.location.href = 'http://localhost:8001/api/auth/auth_sh';
          return;
        }
        
        const response = await fetch('http://localhost:8001/api/auth/me', {
          headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        
        if (!response.ok) {
          console.log('토큰 검증 실패:', response.status);
          this.$store.dispatch('logout');
          
          // 구글 SSO로 리다이렉트
          window.location.href = 'http://localhost:8001/api/auth/auth_sh';
        } else {
          // 인증된 사용자의 대화 목록 가져오기
          this.$store.dispatch('fetchConversations');
        }
      } catch (error) {
        console.error('토큰 검증 중 오류:', error);
        this.$store.dispatch('logout');
        
        // 구글 SSO로 리다이렉트
        window.location.href = 'http://localhost:8001/api/auth/auth_sh';
      }
    },
    selectConversation(conversation) {
      console.log('대화 선택됨:', {
        conversationId: conversation.id,
        conversationTitle: this.getConversationTitle(conversation),
        messageCount: conversation.messages?.length || 0,
        messages: conversation.messages?.map(m => ({
          id: m.id,
          role: m.role,
          q_mode: m.q_mode,
          question: m.question?.substring(0, 50) + '...',
          hasAns: !!m.ans
        })) || []
      });
      
      // 대화를 store에 설정 (랭그래프 복원 트리거)
      this.$store.commit('setCurrentConversation', conversation);
      this.$store.commit('setShouldScrollToBottom', true);
      
      console.log('setCurrentConversation 호출 완료, store 상태:', {
        currentConversation: this.$store.state.currentConversation,
        hasMessages: this.$store.state.currentConversation?.messages?.length > 0
      });
    },
    async saveLlamaApiSettings() {
      try {
        const result = await this.$store.dispatch('updateLlamaApiSettings', {
          apiKey: this.llamaApiKeyInput,
          apiBase: this.llamaApiBaseInput || undefined,
          apiEndpoint: this.llamaApiEndpointInput || undefined
        });
        
        if (result.success) {
          this.showLlamaApiModal = false;
        }
              } catch (error) {
          // 에러 처리
        }
    },
    adjustTextareaHeight() {
      const textarea = this.$refs.inputField;
      if (!textarea) return;
      
      // 높이 초기화
      textarea.style.height = 'auto';
      
      // 스크롤 높이에 맞게 높이 조정 (최대 150px까지)
      const newHeight = Math.min(textarea.scrollHeight, 150);
      textarea.style.height = newHeight + 'px';
    },
    getConversationTitle(conversation) {
      if (!conversation || !conversation.messages || conversation.messages.length === 0) {
        return 'New Conversation';
      }
      
      const firstUserMessage = conversation.messages.find(m => m.role === 'user');
      if (firstUserMessage && firstUserMessage.question) {
        const title = firstUserMessage.question.slice(0, 30);
        return title.length < firstUserMessage.question.length ? `${title}...` : title;
      }
      
      return `chat${conversation.id}`;
    },
    getConversationIcon(iconType) {
      const iconMap = {
        "image": "🖼️",
        "code": "💻",
        "document": "📄",
        "math": "🧮",
        "general": "💬",
        "graph": "📊",
        "analysis": "📈",
        "data": "🔢",
        "dashboard": "📱",
        "ai": "🤖",
        "search": "🔍",
        "translation": "🔤",
        "audio": "🎵",
        "video": "🎬",
        "design": "🎨",
        "map": "🗺️",
        "science": "🔬",
        "finance": "💰",
        "health": "⚕️",
        "news": "📰",
        "weather": "☁️",
        "calendar": "📅",
        "task": "✅"
      };
      
      return iconMap[iconType] || "💬";
    },
    formatDate(dateString) {
      if (!dateString) return '';
      
      const date = new Date(dateString);
      const now = new Date();
      
      if (date.toDateString() === now.toDateString()) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    },
    closeDropdowns(event) {
      // Close dropdowns when clicking outside
      if (!event.target.closest('.user-profile')) {
        this.isUserPopupOpen = false;
      }
    },
    enableCopying() {
      // 모든 요소에서 복사 차단 방지
      document.addEventListener('selectstart', (e) => {
        e.stopPropagation();
        return true;
      });
      
      document.addEventListener('contextmenu', (e) => {
        e.stopPropagation();
        return true;
      });
      
      // 복사 이벤트 허용
      document.addEventListener('copy', (e) => {
        e.stopPropagation();
        return true;
      });
      
      // 선택 이벤트 허용
      document.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        return true;
      });
      
      console.log('복사 기능이 활성화되었습니다.');
    },
    handleSSOCallback() {
      // URL에서 토큰 파라미터 확인 (백엔드 /acs에서 리다이렉트된 경우)
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const user = urlParams.get('user');
      const error = urlParams.get('error');
      
      if (error) {
        console.error('SSO Error:', error);
        
        // 더 자세한 오류 정보 가져오기
        const details = urlParams.get('details') || '';
        if (details) {
          console.error('SSO Error Details:', details);
        }
        
        // 에러 파라미터 제거
        const url = new URL(window.location);
        url.search = '';
        window.history.replaceState({}, document.title, url);
        
        // OAuth 처리 중 플래그 제거
        sessionStorage.removeItem('oauth_processing');
        return false;
      }
      
      if (token && user) {
        // 추가 사용자 정보 가져오기
        const mail = urlParams.get('mail') || '';
        const loginid = urlParams.get('loginid') || '';
        const userid = urlParams.get('userid') || '';
        
        // 토큰을 스토어에 저장하고 로그인 상태로 설정
        this.$store.commit('setAuth', { 
          token, 
          user: { 
            username: user, 
            mail: mail, 
            loginid: loginid,
            id: userid || loginid || user // userid가 있으면 사용, 없으면 loginid, 없으면 username 사용
          } 
        });
        
        // 사용자 정보가 제대로 설정되었는지 확인하고, 필요시 백엔드에서 새로 가져오기
        setTimeout(() => {
          if (!this.$store.state.user || !this.$store.state.user.username) {
            this.$store.dispatch('fetchUserInfo');
          }
        }, 500);
        
        // 토큰 파라미터 제거
        const url = new URL(window.location);
        url.search = '';
        window.history.replaceState({}, document.title, url);
        
        // 대화 목록 가져오기
        this.$store.dispatch('fetchConversations');
        
        // 홈 페이지로 리다이렉트 (무한 리다이렉트 방지)
        if (this.$router.currentRoute.value.path !== '/') {
          this.$router.push('/');
        }
        
        // SSO 처리 완료 플래그 설정
        sessionStorage.setItem('sso_processed', 'true');
        
        // OAuth 처리 중 플래그 제거
        sessionStorage.removeItem('oauth_processing');
        
        return true; // 토큰 처리 완료
      }
      
      // Google OAuth 코드가 있는 경우 (표준 OAuth 흐름)
      const code = urlParams.get('code');
      const state = urlParams.get('state');
      
      if (code && state) {
        // 이미 처리 중인 OAuth인지 확인
        if (sessionStorage.getItem('oauth_processing') === 'true') {
          return true;
        }
        
        // OAuth 처리 중 플래그 설정
        sessionStorage.setItem('oauth_processing', 'true');
        
        // 백엔드의 /acs 엔드포인트로 리다이렉트하여 처리
        window.location.href = `http://localhost:8001/api/auth/acs?code=${code}&state=${state}`;
        return true; // OAuth 처리 진행 중
      }
      
      return false; // SSO 콜백 처리 없음
    },
    processOAuthFromHash(hash) {
      const hashParams = new URLSearchParams(hash.substring(1));
      const idToken = hashParams.get('id_token');
      const state = hashParams.get('state');
      
      if (!idToken || !state) {
        return;
      }
      
      // 백엔드로 토큰 전송
      const requestBody = `id_token=${encodeURIComponent(idToken)}&state=${encodeURIComponent(state)}`;
      
      fetch('http://localhost:8001/api/auth/acs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: requestBody,
        credentials: 'include' // 쿠키 포함
      })
      .then(response => {
        if (response.ok) {
          return response.text();
        } else {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
      })
      .then(responseText => {
        try {
          const data = JSON.parse(responseText);
          
          if (data.success && data.user) {
            // 사용자 정보를 스토어에 저장
            this.$store.commit('setAuth', {
              token: data.token || idToken, // 백엔드에서 토큰을 반환하지 않는 경우 idToken 사용
              user: data.user
            });
            
            // URL 해시 정리
            const url = new URL(window.location);
            url.hash = '';
            window.history.replaceState({}, document.title, url);
            
            // 대화 목록 가져오기
            this.$store.dispatch('fetchConversations');
            
            // OAuth 처리 완료 플래그 설정
            sessionStorage.setItem('sso_processed', 'true');
            sessionStorage.removeItem('oauth_processing');
            
            // 페이지 리로드 없이 인증 상태 업데이트
            this.$forceUpdate();
            
          } else {
            sessionStorage.removeItem('oauth_processing');
          }
        } catch (parseError) {
          sessionStorage.removeItem('oauth_processing');
        }
      })
      .catch(() => {
        sessionStorage.removeItem('oauth_processing');
      });
    },
    processOAuthFromQuery(urlParams) {
      const code = urlParams.get('code');
      const idToken = urlParams.get('id_token');
      const state = urlParams.get('state');
      const error = urlParams.get('error');

      if (error) {
        const url = new URL(window.location);
        url.search = '';
        window.history.replaceState({}, document.title, url);
        sessionStorage.removeItem('oauth_processing');
        return false;
      }

      if (code && idToken) {
        const requestBody = `code=${encodeURIComponent(code)}&id_token=${encodeURIComponent(idToken)}&state=${encodeURIComponent(state)}`;

        fetch('http://localhost:8001/api/auth/acs', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: requestBody,
          credentials: 'include'
        })
        .then(response => {
          if (response.ok) {
            return response.text();
          } else {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
        })
        .then(responseText => {
          try {
            const data = JSON.parse(responseText);

            if (data.success && data.user) {
              this.$store.commit('setAuth', {
                token: data.token || idToken,
                user: data.user
              });

              const url = new URL(window.location);
              url.search = '';
              window.history.replaceState({}, document.title, url);
              this.$store.dispatch('fetchConversations');
              sessionStorage.setItem('sso_processed', 'true');
              sessionStorage.removeItem('oauth_processing');
              this.$forceUpdate();
              return true;
            } else {
              sessionStorage.removeItem('oauth_processing');
              return false;
            }
          } catch (parseError) {
            sessionStorage.removeItem('oauth_processing');
            return false;
          }
        })
        .catch(() => {
          sessionStorage.removeItem('oauth_processing');
          return false;
        });
        return true; // 토큰 처리 진행 중
      }
      return false; // SSO 콜백 처리 없음
    },
    checkAuthCookies() {
      // 쿠키에서 인증 정보 확인
      const cookies = document.cookie.split(';');
      let accessToken = null;
      let userInfo = null;
      
      for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token') {
          accessToken = value;
        } else if (name === 'user_info') {
          try {
            userInfo = JSON.parse(decodeURIComponent(value));
          } catch (e) {
            console.error('Error parsing user_info cookie:', e);
          }
        }
      }
      
      if (accessToken && userInfo) {
        // 스토어에 인증 정보 설정
        this.$store.commit('setAuth', {
          token: accessToken,
          user: userInfo
        });
        
        // 대화 목록 가져오기
        this.$store.dispatch('fetchConversations');
        
        return true;
      }
      
      return false;
    }
  },
  async created() {
    // OAuth 처리 중인 경우 중복 처리 방지
    if (sessionStorage.getItem('oauth_processing') === 'true') {
      return; // 추가 처리 중단
    }
    
    // 먼저 쿠키에서 인증 정보 확인
    const hasAuthCookies = this.checkAuthCookies();
    if (hasAuthCookies) {
      return;
    }
    
    // URL 해시에서 OAuth 파라미터 확인 (Google OAuth 콜백)
    const hash = window.location.hash;
    if (hash && hash.includes('id_token')) {
      this.processOAuthFromHash(hash);
      return;
    }
    
    // URL 쿼리 파라미터에서 OAuth 콜백 확인
    const urlParams = new URLSearchParams(window.location.search);
    const hasOAuthParams = urlParams.get('code') || urlParams.get('id_token') || urlParams.get('error');
    if (hasOAuthParams) {
      this.processOAuthFromQuery(urlParams);
      return;
    }
    
    // SSO 콜백 처리 (가장 먼저 실행)
    const hasToken = this.handleSSOCallback();
    
    // SSO 콜백으로 토큰을 받은 경우 중복 인증 체크를 건너뜀
    if (hasToken) {
      return;
    }
    
    // 새 세션을 시작할 때 사용자 인증 상태 확인
    if (this.$store.state.isAuthenticated) {
      try {
        // localStorage에서 JWT 토큰 가져오기
        const jwtToken = localStorage.getItem('access_token');
        
        if (!jwtToken) {
          console.log('JWT 토큰이 없음');
          this.$store.dispatch('logout');
          return;
        }
        
        const response = await fetch('http://localhost:8001/api/auth/me', {
          headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        
        if (!response.ok) {
          this.$store.dispatch('logout');
          
          // 무한 리다이렉트 방지: 이미 SSO 처리 중이 아닌 경우에만 리다이렉트
          if (sessionStorage.getItem('oauth_processing') !== 'true') {
            window.location.href = 'http://localhost:8001/api/auth/auth_sh';
          }
        } else {
          // 인증된 사용자의 대화 목록 가져오기
          this.$store.dispatch('fetchConversations');
        }
      } catch (error) {
        this.$store.dispatch('logout');
        
        // 무한 리다이렉트 방지: 이미 SSO 처리 중이 아닌 경우에만 리다이렉트
        if (sessionStorage.getItem('oauth_processing') !== 'true') {
          window.location.href = 'http://localhost:8001/api/auth/auth_sh';
        }
      }
    } else {
      // 로그인 상태가 아니면 대화 데이터 초기화
      this.$store.commit('setConversations', []);
      this.$store.commit('setCurrentConversation', null);
      
      // URL에 이미 OAuth 코드나 토큰이 있는 경우 SSO 리다이렉트하지 않음
      const urlParams = new URLSearchParams(window.location.search);
      const hasOAuthParams = urlParams.get('code') || urlParams.get('token') || urlParams.get('error');
      
      // 로그아웃 후 자동 리다이렉트 방지: 사용자가 명시적으로 로그인하려고 할 때만 리다이렉트
      const isLogoutRedirect = sessionStorage.getItem('logout_redirect') === 'true';
      
      if (!hasOAuthParams && sessionStorage.getItem('oauth_processing') !== 'true' && !isLogoutRedirect) {
        // 무한 리다이렉트 방지: OAuth 처리 중이 아닌 경우에만 리다이렉트
        window.location.href = 'http://localhost:8001/api/auth/auth_sh';
      }
      
      // 로그아웃 리다이렉트 플래그 정리
      if (isLogoutRedirect) {
        sessionStorage.removeItem('logout_redirect');
      }
    }
    
    // Fetch conversations when app loads
    this.$store.dispatch('fetchConversations');
  },
  mounted() {
    // 참조가 존재하는지 확인 후 접근
    if (this.$refs.inputField) {
      this.$refs.inputField.focus();
      this.adjustTextareaHeight(); // 초기 높이 설정
    }
    
    // Initialize API input fields
    this.apiKeyInput = this.$store.state.apiKey || '';
    this.llamaApiKeyInput = this.$store.state.llamaApiKey || '';
    this.llamaApiBaseInput = this.$store.state.llamaApiBase || '';
    this.llamaApiEndpointInput = this.$store.state.llamaApiEndpoint || '';
    
    // Check system preference for dark mode
    if (localStorage.getItem('darkMode') === null) {
      this.isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      localStorage.setItem('darkMode', this.isDarkMode);
    }
    
    // 인증 토큰 유효성 검사 (localStorage의 JWT 토큰 확인)
    const jwtToken = localStorage.getItem('access_token');
    const userInfo = localStorage.getItem('user_info');
    
    if (jwtToken && userInfo) {
      try {
        const userData = JSON.parse(userInfo);
        // store 상태와 localStorage 동기화
        if (!this.$store.state.isAuthenticated) {
          this.$store.commit('setAuth', {
            token: jwtToken,
            user: userData
          });
        }
        this.validateAuthToken();
      } catch (error) {
        console.error('Stored user info parsing error:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
      }
    }
    
    // Add click event listener to close dropdowns when clicking outside
    document.addEventListener('click', this.closeDropdowns);
    
    // 복사 허용 이벤트 핸들러 추가
    this.enableCopying();
  },
  beforeUnmount() {
    // Remove event listener before component is destroyed
    document.removeEventListener('click', this.closeDropdowns);
  }
};
</script>

<style>
@import './assets/styles/index.css';
</style>

