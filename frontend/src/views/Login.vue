<template>
  <div class="auth-page">
    <div class="auth-container">
      <div class="auth-header">
        <h1>관리자 로그인</h1>
        <p>관리자 계정으로 로그인하세요</p>
      </div>
      
      <div class="auth-form">
        <div class="form-group">
          <label for="username">사용자 이름</label>
          <input 
            type="text" 
            id="username" 
            v-model="username" 
            placeholder="사용자 이름을 입력하세요"
            @keyup.enter="login"
          />
        </div>
        
        <div class="form-group">
          <label for="password">비밀번호</label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            placeholder="비밀번호를 입력하세요" 
            @keyup.enter="login"
          />
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <button 
          class="auth-button" 
          @click="login" 
          :disabled="isLoading || !username || !password"
        >
          <span v-if="!isLoading">로그인</span>
          <span v-else class="loading-spinner"></span>
        </button>
        
        <p class="auth-link">
          계정이 없으신가요? <router-link to="/register">회원가입</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      username: '',
      password: '',
      isLoading: false,
      error: null
    }
  },
  methods: {
    async login() {
      if (!this.username || !this.password) {
        this.error = '사용자 이름과 비밀번호를 입력해주세요';
        return;
      }
      
      this.isLoading = true;
      this.error = null;
      
      try {
        await this.$store.dispatch('login', {
          username: this.username,
          password: this.password
        });
        
        // 로그인 성공 후 관리자 페이지로 이동
        this.$router.push('/admin');
      } catch (error) {
        this.error = error.message || '로그인에 실패했습니다. 다시 시도해주세요';
      } finally {
        this.isLoading = false;
      }
    },

    // OAuth 콜백 처리
    async processOAuthCallback() {
      try {
        // URL에서 OAuth 파라미터 확인
        const urlParams = new URLSearchParams(window.location.search);
        const error = urlParams.get('error');
        const msg = urlParams.get('msg');
        
        if (error) {
          this.error = decodeURIComponent(error).replace(/\+/g, ' ');
          if (msg) {
            this.error += ': ' + decodeURIComponent(msg).replace(/\+/g, ' ');
          }
          
          // 에러 파라미터 제거
          const url = new URL(window.location);
          url.search = '';
          window.history.replaceState({}, document.title, url);
          return;
        }

        // 쿠키에서 인증 정보 확인
        const accessToken = this.getCookie('access_token');
        const userInfo = this.getCookie('user_info');
        
        if (accessToken && userInfo) {
                      try {
              const userData = JSON.parse(userInfo);
              
              // store에 인증 정보 설정
              this.$store.commit('setAuthToken', accessToken);
              this.$store.commit('setUser', {
                username: userData.username,
                email: userData.mail,
                loginid: userData.loginid,
                id: userData.userid
              });
              
              // 쿠키에서 파라미터 제거
              const url = new URL(window.location);
              url.search = '';
              window.history.replaceState({}, document.title, url);
              
              // 로그인 성공 후 홈페이지로 이동
              this.$router.push('/');
              return;
            } catch (parseError) {
              // 에러 처리
            }
        }
              } catch (error) {
          // 에러 처리
        }
    },

    // 쿠키 읽기 함수
    getCookie(name) {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
      return null;
    }
  },
  
  // 컴포넌트 마운트 시 OAuth 콜백 처리
  async mounted() {
    // OAuth 콜백 처리
    await this.processOAuthCallback();
  },
  
  // 이미 로그인되어 있으면 관리자 페이지로 리다이렉트
  beforeMount() {
    if (this.$store.state.isAuthenticated) {
      this.$router.push('/admin');
      return;
    }
  }
}
</script>

<style scoped>
@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(180deg); }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(50px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes rainbow {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
  overflow: hidden;
}

.auth-page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%234facfe' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='4'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  animation: float 25s ease-in-out infinite;
  z-index: -1;
}

.auth-page::after {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(79, 172, 254, 0.15) 0%, transparent 50%);
  animation: float 20s linear infinite reverse;
  z-index: -1;
  pointer-events: none;
}

.auth-container {
  width: 420px;
  max-width: 90vw;
  padding: 40px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 20px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  animation: slideInUp 0.8s ease-out;
  position: relative;
  overflow: hidden;
}

.auth-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  animation: shimmer 3s ease-in-out infinite;
}

.auth-header {
  text-align: center;
  margin-bottom: 35px;
}

.auth-header h1 {
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
  animation: rainbow 4s ease infinite;
  filter: drop-shadow(0 0 10px rgba(79, 172, 254, 0.3));
}

.auth-header p {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1rem;
  font-weight: 300;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.form-group label {
  font-size: 0.95rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.form-group input {
  padding: 16px 20px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-size: 1rem;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  color: white;
  outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.form-group input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.form-group input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 20px rgba(79, 172, 254, 0.4);
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.15);
}

.error-message {
  color: #ff6b6b;
  font-size: 0.9rem;
  padding: 12px 16px;
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.3);
  border-radius: 10px;
  backdrop-filter: blur(10px);
  animation: slideInUp 0.4s ease-out;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.auth-button {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  background-size: 200% 200%;
  color: white;
  border: none;
  padding: 18px;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  justify-content: center;
  align-items: center;
  height: 54px;
  box-shadow: 0 8px 25px rgba(79, 172, 254, 0.4);
  position: relative;
  overflow: hidden;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  animation: rainbow 5s ease infinite;
}

.auth-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.6s;
}

.auth-button:hover::before {
  left: 100%;
}

.auth-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 35px rgba(79, 172, 254, 0.6);
  animation: pulse 1s infinite;
}

.auth-button:disabled {
  background: rgba(93, 93, 93, 0.6);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
  animation: none;
}

.auth-link {
  text-align: center;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 20px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.auth-link a {
  color: var(--accent-light);
  text-decoration: none;
  font-weight: 600;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  transition: all 0.3s;
  position: relative;
}

.auth-link a::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  transition: width 0.3s;
}

.auth-link a:hover::after {
  width: 100%;
}

.auth-link a:hover {
  filter: drop-shadow(0 0 8px rgba(79, 172, 254, 0.6));
}

.loading-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .auth-container {
    width: 90vw;
    padding: 30px 20px;
  }
  
  .auth-header h1 {
    font-size: 1.6rem;
  }
  
  .form-group input {
    padding: 14px 16px;
  }
  
  .auth-button {
    padding: 16px;
    height: 50px;
  }
}

/* Enhanced focus styles */
.form-group input:focus + label {
  color: var(--accent-color);
}

/* Floating label effect */
.form-group {
  position: relative;
}

.form-group input:focus,
.form-group input:not(:placeholder-shown) {
  padding-top: 20px;
  padding-bottom: 12px;
}

.form-group input:focus + label,
.form-group input:not(:placeholder-shown) + label {
  transform: translateY(-8px) scale(0.85);
  color: var(--accent-color);
}
</style> 