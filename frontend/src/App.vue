<template>
  <div class="app" :class="{ 'dark-mode': true, 'collapsed-sidebar': isSidebarCollapsed }">
    <aside class="sidebar">
      <div class="sidebar-controls">
        <div class="new-chat-btn" @click="newConversation">
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
            :key="conversation.id || `temp-${conversation.created_at}`" 
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
                <div class="user-popup-email">{{ currentUser ? (currentUser.email || 'No Email') : 'No Email' }}</div>
                <div class="user-popup-email">{{ currentUser ? (currentUser.deptname || 'No deptname') : 'No deptname' }}</div>
              </div>
            </div>
            <div class="user-popup-menu">
              <a
                href="https://go/nrdvoc"
                target="_blank"
                rel="noopener noreferrer"
                class="menu-item"
                style="text-decoration:none; color:inherit; cursor:pointer; position:relative; z-index:10;"
                onclick="event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation(); window.open(this.href, '_blank', 'noopener'); return false;"
              >
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                User VOE
              </a>
              <a
                href="https://confluence.samsungds.net/spaces/DAE/pages/2420017795/%EB%B6%88%EB%B0%B1+%EA%B0%9C%EB%B0%9C+%ED%98%84%ED%99%A9%ED%8C%90"
                target="_blank"
                rel="noopener noreferrer"
                class="menu-item"
                style="text-decoration:none; color:inherit; cursor:pointer; position:relative; z-index:10;"
                onclick="event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation(); window.open(this.href, '_blank', 'noopener'); return false;"
              >
                <svg class="menu-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                  <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
                RC Info
              </a>
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
    async newConversation() {
      // Home 컴포넌트에 새 대화 신호 전송 (실제 생성은 Home.vue에서 처리)
      this.$store.commit('setNewConversationTrigger', Date.now());
    },
    handleUserProfileClick(event) {
      // 단순히 사용자 팝업 토글만 수행 (인증 상태 확인 없음)
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      this.isUserPopupOpen = !this.isUserPopupOpen;
    },
    async logout() {
      try {
        // // console.log('[APP] 로그아웃 시작');
        
        // 사용자 팝업 닫기
        this.isUserPopupOpen = false;
        
        // 백엔드 로그아웃 API 호출
        const jwtToken = localStorage.getItem('access_token');
        if (jwtToken) {
          try {
            await fetch('http://localhost:8000/api/auth/logout', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${jwtToken}`,
                'Content-Type': 'application/json'
              }
            });
            // console.log('[APP] 백엔드 로그아웃 API 호출 완료');
          } catch (apiError) {
            console.warn('[APP] 백엔드 로그아웃 API 호출 실패 (계속 진행):', apiError.message);
          }
        }
        
        // Vuex store의 logout action 실행 (토큰 및 상태 정리)
        await this.$store.dispatch('logout');
        // console.log('[APP] 클라이언트 상태 정리 완료');
                
        // OAuth 처리 플래그 초기화
        sessionStorage.removeItem('oauth_processing');
        sessionStorage.removeItem('sso_processed');
        sessionStorage.removeItem('logout_redirect');
        
        // 로그아웃 완료 후 즉시 SSO 로그인으로 리다이렉트
        // console.log('[APP] 로그아웃 완료 - SSO 로그인으로 리다이렉트');
        setTimeout(() => {
          try {
            window.location.replace('http://localhost:8000/api/auth/auth_sh');
          } catch (error) {
            try {
              window.location.href = 'http://localhost:8000/api/auth/auth_sh';
            } catch (error2) {
              console.error('SSO 리다이렉트 실패:', error2);
            }
          }
        }, 500); // 0.5초 후 리다이렉트
        
      } catch (error) {
        console.error('[APP] 로그아웃 처리 중 오류:', error);
        
        // 에러가 발생해도 기본 정리 수행
        this.isUserPopupOpen = false;
        
        // 강제로 상태 정리
        this.$store.dispatch('logout');
        
        sessionStorage.removeItem('oauth_processing');
        sessionStorage.removeItem('sso_processed');
        sessionStorage.removeItem('logout_redirect');
        
        // 에러 발생 시에도 SSO 로그인으로 리다이렉트
        setTimeout(() => {
          try {
            window.location.replace('http://localhost:8000/api/auth/auth_sh');
          } catch (error) {
            try {
              window.location.href = 'http://localhost:8000/api/auth/auth_sh';
            } catch (error2) {
              console.error('SSO 리다이렉트 실패:', error2);
            }
          }
        }, 500);
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
          // console.log('[APP] JWT 토큰이 없음 - 로그아웃 처리');
          this.$store.dispatch('logout');
          return;
        }
        
        const response = await fetch('http://localhost:8000/api/auth/me', {
          method: 'GET',
          headers: { 
            'Authorization': `Bearer ${jwtToken}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include'
        });
        
        if (!response.ok) {
          // console.log('토큰 검증 실패:', response.status, response.statusText);
          
          // 응답 본문 확인 (디버깅용)
          try {
            await response.text();
            // console.log('토큰 검증 실패 응답:', errorText);
          } catch (e) {
            // console.log('응답 본문 읽기 실패');
          }
          
          if (response.status === 401) {
            // 토큰 만료 시 자동 SSO 로그인으로 리다이렉트
            // console.log('[APP] 토큰 만료 감지 - 자동 SSO 로그인으로 리다이렉트');
            setTimeout(() => {
              try {
                window.location.replace('http://localhost:8000/api/auth/auth_sh');
              } catch (error) {
                window.location.href = 'http://localhost:8000/api/auth/auth_sh';
              }
            }, 500);
          } else {
            this.$store.dispatch('logout');
          }
        } else {
          // 인증된 사용자의 대화 목록 가져오기 (중복 호출 방지)
          if (!this._conversationsFetched) {
            this._conversationsFetched = true;
            this.$store.dispatch('fetchConversations');
          }
        }
      } catch (error) {
        console.error('토큰 검증 중 오류:', error);
        
        // 네트워크 오류인지 확인
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
          console.error('[APP] 네트워크 오류 - 백엔드 서버 연결 실패');
          // 네트워크 오류 시에는 로그아웃하지 않고 재시도 또는 사용자에게 알림
          return;
        }
        
        this.$store.dispatch('logout');
      }
    },
    async selectConversation(conversation) {
      try {
        console.log('🔄 대화 선택 시작:', conversation.id);
        
        // 대화의 메시지를 별도로 가져오기
        const response = await fetch(`http://localhost:8000/api/conversations/${conversation.id}/messages`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          // console.log('✅ API 응답 성공:', {
          //   conversationId: data.conversation_id,
          //   messageCount: data.messages?.length || 0
          // });
          
          // 메시지가 포함된 대화 객체 생성
          const conversationWithMessages = {
            ...conversation,
            messages: data.messages || []
          };
          
          // console.log('📝 생성된 대화 객체:', {
          //   id: conversationWithMessages.id,
          //   messageCount: conversationWithMessages.messages.length,
          //   firstMessage: conversationWithMessages.messages[0] ? {
          //     id: conversationWithMessages.messages[0].id,
          //     role: conversationWithMessages.messages[0].role,
          //     q_mode: conversationWithMessages.messages[0].q_mode
          //   } : null
          // });
          
          // 대화를 store에 설정 (랭그래프 복원 트리거)
          this.$store.commit('setCurrentConversation', conversationWithMessages);
          this.$store.commit('setShouldScrollToBottom', true);

          // Home 컴포넌트에 기존 대화 선택 신호 전송 (실시간 기능 비활성화용)
          this.$store.commit('setConversationRestored', true);
          
          // URL 파라미터는 사용하지 않음 (현재 상태 기반 복원)
          
          console.log('✅ 대화 선택 완료:', {
            conversationId: conversation.id,
            messageCount: data.messages?.length || 0
          });
        } else {
          const errorText = await response.text();
          console.error('❌ 대화 메시지 가져오기 실패:', {
            status: response.status,
            statusText: response.statusText,
            error: errorText
          });
          // 실패 시 메시지 없는 대화로 설정
          this.$store.commit('setCurrentConversation', conversation);
        }
      } catch (error) {
        console.error('❌ 대화 선택 오류:', error);
        // 오류 시 메시지 없는 대화로 설정
        this.$store.commit('setCurrentConversation', conversation);
      }
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
      if (!conversation) {
        return 'New Conversation';
      }
      
      // 백엔드에서 전달된 title 필드 사용
      if (conversation.title && conversation.title !== 'New Conversation') {
        return conversation.title;
      }
      
      return 'New Conversation';
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
      // 모든 복사 관련 이벤트 허용
      const allowEvent = (e) => {
        e.stopPropagation();
        return true;
      };
      
      // 선택 시작 이벤트 허용
      document.addEventListener('selectstart', allowEvent, { capture: true, passive: false });
      
      // 우클릭 컨텍스트 메뉴 허용
      document.addEventListener('contextmenu', allowEvent, { capture: true, passive: false });
      
      // 복사 이벤트 허용
      document.addEventListener('copy', allowEvent, { capture: true, passive: false });
      
      // 마우스 이벤트 허용
      document.addEventListener('mousedown', allowEvent, { capture: true, passive: false });
      document.addEventListener('mouseup', allowEvent, { capture: true, passive: false });
      document.addEventListener('mousemove', allowEvent, { capture: true, passive: false });
      
      // 키보드 복사 단축키 허용 (Ctrl+C, Ctrl+A)
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
          if (e.key === 'c' || e.key === 'C' || e.key === 'a' || e.key === 'A' || e.key === 'v' || e.key === 'V') {
            e.stopPropagation();
            return true;
          }
        }
        return true;
      }, { capture: true, passive: false });
      
      // 드래그 이벤트 허용
      document.addEventListener('dragstart', allowEvent, { capture: true, passive: false });
      
      // CSS 클래스로 복사 허용 강제 적용 (TrustedScript 오류 방지)
      document.body.classList.add('text-selection-enabled');
      
    },
    handleSSOCallback() {
      // URL에서 토큰 파라미터 확인 (백엔드 /acs에서 리다이렉트된 경우)
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      const user = urlParams.get('username');
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
        // console.log('사용자 정보 전체 : ', urlParams)
        // 추가 사용자 정보 가져오기
        const mail = urlParams.get('mail') || '';
        const loginid = urlParams.get('loginid') || '';
        const username = urlParams.get('username') || '';
        const deptname = urlParams.get('deptname') || '';
        
        // 토큰을 스토어에 저장하고 로그인 상태로 설정
        this.$store.commit('setAuth', { 
          token, 
          user: { 
            username: user, 
            mail: mail, 
            loginid: username,
            id: loginid,
            deptname : deptname
          } 
        });

        // 로그인 후 새 대화 플래그 설정
        this.$store.commit('setLoginNewConversation', true);
        
        
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
        
        // // console.log('[APP] handleSSOCallback - OAuth 처리 완료 플래그 설정됨');
        
        return true; // 토큰 처리 완료
      }
      
      // samsung OAuth 코드가 있는 경우 (표준 OAuth 흐름)
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
        window.location.href = `http://localhost:8000/api/auth/acs?code=${code}&state=${state}`;
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
      
      fetch('http://localhost:8000/api/auth/acs', {
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

            // 로그인 후 새 대화 플래그 설정
            this.$store.commit('setLoginNewConversation', true);
                        
            // URL 해시 정리
            const url = new URL(window.location);
            url.hash = '';
            window.history.replaceState({}, document.title, url);
            
            // 대화 목록 가져오기
            this.$store.dispatch('fetchConversations');
            
            // OAuth 처리 완료 플래그 설정
            sessionStorage.setItem('sso_processed', 'true');
            sessionStorage.removeItem('oauth_processing');
            
            // // console.log('[APP] processOAuthFromHash - OAuth 처리 완료 플래그 설정됨');
            
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

        fetch('http://localhost:8000/api/auth/acs', {
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

              // 로그인 후 새 대화 플래그 설정
              this.$store.commit('setLoginNewConversation', true);


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
      function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
      }
      
      const accessToken = getCookie('access_token');
      const userInfoCookie = getCookie('user_info');
      const ssoProcessed = getCookie('sso_processed');
      
      // console.log('[APP] Checking cookies - access_token:', !!accessToken, 'user_info:', !!userInfoCookie, 'sso_processed:', ssoProcessed);
      
      if (accessToken && userInfoCookie) {
        try {
          // URL 디코딩 후 JSON 파싱
          const decodedUserInfo = decodeURIComponent(userInfoCookie);
          // console.log('[APP] Decoded user_info:', decodedUserInfo);
          const userInfo = JSON.parse(decodedUserInfo);
          
          // localStorage에 저장
          localStorage.setItem('access_token', accessToken);
          localStorage.setItem('user_info', JSON.stringify(userInfo));
          if (ssoProcessed) {
            sessionStorage.setItem('sso_processed', ssoProcessed);
          }
          
          // 스토어에 인증 정보 설정
          this.$store.commit('setAuth', {
            token: accessToken,
            user: userInfo
          });

          // 로그인 후 새 대화 플래그 설정
          this.$store.commit('setLoginNewConversation', true);
                  
          // 대화 목록 가져오기
          this.$store.dispatch('fetchConversations');
          
          // console.log('[APP] 쿠키에서 인증 정보 복원 완료');
          
          // 쿠키 정리 (보안상 이유로)
          document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=report-collection;';
          document.cookie = 'user_info=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; report-collection;';
          document.cookie = 'sso_processed=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; report-collection;';
          
          return true;
        } catch (error) {
          console.error('[APP] 쿠키 파싱 실패:', error);
          return false;
        }
      }
      
      return false;
    }
  },
  async created() {
    // OAuth 처리 중인 경우 중복 처리 방지
    if (sessionStorage.getItem('oauth_processing') === 'true') {
      // // console.log('[APP] OAuth 처리 중 - created 라이프사이클 중단');
      return; // 추가 처리 중단
    }
    
    // SSO 처리 완료된 경우 중복 처리 방지
    if (sessionStorage.getItem('sso_processed') === 'true') {
      // // console.log('[APP] SSO 처리 완료됨 - created 라이프사이클 중단');
      return;
    }
    
    // URL에 OAuth 파라미터가 있는 경우 OAuth 처리를 우선 진행
    const currentHash = window.location.hash;
    const currentUrlParams = new URLSearchParams(window.location.search);
    const hasOAuthInHash = currentHash && currentHash.includes('id_token');
    const hasOAuthInQuery = currentUrlParams.get('code') || currentUrlParams.get('id_token') || currentUrlParams.get('error');
    
    if (hasOAuthInHash || hasOAuthInQuery) {
      // // console.log('[APP] OAuth 파라미터 발견 - OAuth 처리 우선 진행, created 라이프사이클 중단');
      
      // OAuth 처리가 진행 중임을 표시
      sessionStorage.setItem('oauth_processing', 'true');
      
      // OAuth 처리를 다른 라이프사이클에서 처리하도록 함
      return;
    }
    
    // 먼저 쿠키에서 인증 정보 확인
    const hasAuthCookies = this.checkAuthCookies();
    if (hasAuthCookies) {
      // // console.log('[APP] 쿠키에서 인증 정보 복원됨');
      return;
    }
    
    // URL 해시에서 OAuth 파라미터 확인 (samsung OAuth 콜백)
    if (currentHash && currentHash.includes('id_token')) {
      // // console.log('[APP] URL 해시에서 OAuth 파라미터 발견 - 처리 시작');
      this.processOAuthFromHash(currentHash);
      return;
    }
    
    // URL 쿼리 파라미터에서 OAuth 콜백 확인
    if (hasOAuthInQuery) {
      // // console.log('[APP] URL 쿼리에서 OAuth 파라미터 발견 - 처리 시작');
      this.processOAuthFromQuery(currentUrlParams);
      return;
    }
    
    // SSO 콜백 처리 (가장 먼저 실행)
    const hasToken = this.handleSSOCallback();
    
    // SSO 콜백으로 토큰을 받은 경우 중복 인증 체크를 건너뜀
    if (hasToken) {
      // // console.log('[APP] SSO 콜백 처리됨 - 추가 처리 중단');
      return;
    }
    
    // localStorage에서 기존 인증 정보 확인
    const jwtToken = localStorage.getItem('access_token');
    const userInfo = localStorage.getItem('user_info');
    
    if (jwtToken && userInfo) {
      try {
        // 기존 토큰으로 인증 상태 복원
        const userData = JSON.parse(userInfo);
        this.$store.commit('setAuth', {
          token: jwtToken,
          user: userData
        });
        
        // // console.log('[APP] localStorage에서 인증 상태 복원됨');
        
        // 토큰 유효성 검사
        const response = await fetch('http://localhost:8000/api/auth/me', {
          headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        
        if (response.ok) {
          // // console.log('[APP] 토큰 유효성 검사 통과');
          // 인증된 사용자의 대화 목록 가져오기 (중복 호출 방지)
          if (!this._conversationsFetched) {
            this._conversationsFetched = true;
            this.$store.dispatch('fetchConversations');
          }
          return;
        } else {
          // // console.log('[APP] 토큰 만료됨 - 자동 SSO 로그인으로 리다이렉트');
          // console.log('[APP] 토큰 만료 감지 - 자동 SSO 로그인으로 리다이렉트');
          setTimeout(() => {
            try {
              window.location.replace('http://localhost:8000/api/auth/auth_sh');
            } catch (error) {
              window.location.href = 'http://localhost:8000/api/auth/auth_sh';
            }
          }, 500);
        }
      } catch (error) {
        console.error('[APP] 인증 정보 복원 실패:', error);
        this.$store.dispatch('logout');
      }
    }
    
    // 로그아웃 플래그 정리
    const isLogoutRedirect = sessionStorage.getItem('logout_redirect') === 'true';
    if (isLogoutRedirect) {
      // // console.log('[APP] 로그아웃 직후 - 플래그 정리');
      sessionStorage.removeItem('logout_redirect');
      return; // 로그아웃 직후에는 자동 리다이렉트 방지
    }
    
    // OAuth 처리가 완료되지 않은 상태에서만 인증 상태 확인
    // OAuth 처리 중이거나 이미 처리 완료된 경우 자동 리다이렉트 방지
    const hasProcessedOAuth = sessionStorage.getItem('sso_processed') === 'true';
    const isProcessingOAuth = sessionStorage.getItem('oauth_processing') === 'true';
    
    // console.log('[APP] Auth check - hasProcessedOAuth:', hasProcessedOAuth, 'isProcessingOAuth:', isProcessingOAuth);
    // console.log('[APP] Store authenticated:', this.$store.state.isAuthenticated);
    // console.log('[APP] LocalStorage tokens:', !!localStorage.getItem('access_token'), !!localStorage.getItem('user_info'));
    
    if (!hasProcessedOAuth && !isProcessingOAuth) {
      // localStorage에 토큰이 있는지 먼저 확인
      const hasLocalAuth = localStorage.getItem('access_token') && localStorage.getItem('user_info');
      
      // 인증되지 않은 상태에서만 samsung SSO로 리다이렉트
      if (!this.$store.state.isAuthenticated && !hasLocalAuth) {
        // console.log('[APP] 인증되지 않음 - SSO로 리다이렉트');
        setTimeout(() => {
          try {
            window.location.replace('http://localhost:8000/api/auth/auth_sh');
          } catch (error) {
            try {
              window.location.href = 'http://localhost:8000/api/auth/auth_sh';
            } catch (error2) {
              console.error('SSO 리다이렉트 실패:', error2);
            }
          }
        }, 1000); // 1초 후 리다이렉트 (페이지 로딩 완료 대기)
      } else if (hasLocalAuth && !this.$store.state.isAuthenticated) {
        // localStorage에 토큰이 있지만 store에 없는 경우 store 업데이트
        // console.log('[APP] localStorage에서 인증 정보 복원 중...');
        try {
          const userData = JSON.parse(localStorage.getItem('user_info'));
          this.$store.commit('setAuth', {
            token: localStorage.getItem('access_token'),
            user: userData
          });
          // console.log('[APP] Store 인증 상태 복원 완료');
        } catch (error) {
          console.error('[APP] Store 복원 실패:', error);
        }
      }
    } else {
      // console.log('[APP] OAuth 처리 완료 또는 진행 중 - 자동 리다이렉트 건너뛰기');
    }
  },
  mounted() {
    // // console.log('현재 사용자 정보:', this.currentUser)
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
          
          // 인증 상태 복원 후 대화 목록 가져오기
          // // console.log('[APP] 인증 상태 복원 후 대화 목록 가져오기');
          if (!this._conversationsFetched) {
            this._conversationsFetched = true;
            this.$store.dispatch('fetchConversations').then(() => {
              // console.log('[APP] mounted에서 대화 목록 가져오기 완료');
            }).catch(error => {
              console.error('[APP] mounted에서 대화 목록 가져오기 실패:', error);
            });
          }
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

