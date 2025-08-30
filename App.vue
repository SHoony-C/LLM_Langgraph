<template>
  <div id="app" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
    <div v-if="isLoading" class="loading-screen">
      <div class="loading-content">
        <div class="loading-logo">
          <img src="@/assets/logo.png" alt="Logo" />
        </div>
        <div class="loading-text">
          <h2>I-TAP</h2>
          <p>Visualizing AI Imagination...</p>
        </div>
        <div class="loading-animation">
          <div class="loading-ring"></div>
          <div class="loading-ring"></div>
          <div class="loading-ring"></div>
          <div class="loading-dots">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
          </div>
        </div>
      </div>
    </div>
    <AppSidebar @sidebar-toggle="handleSidebarToggle" />
    <div class="main-wrapper">
      <main class="main-content">
        <router-view />
      </main>
      <MainFooter />
    </div>
    
    <!-- Login Modal -->
    <LoginModal 
      v-if="showLoginModal" 
      :show="showLoginModal"
      @close="showLoginModal = false"
      @login-success="handleLoginSuccess"
    />
  </div>
</template>

<script>
import { computed, ref, onMounted, provide } from 'vue'
import { useStore } from 'vuex'
import { useRouter, useRoute } from 'vue-router'
import AppSidebar from '@/views/Sidebar.vue'
import LoginModal from '@/components/login_modal.vue'
import MainFooter from '@/views/m0_footer.vue'

export default {
  name: 'App',
  components: {
    AppSidebar,
    LoginModal,
    MainFooter
  },
  setup() {
    const store = useStore()
    const router = useRouter()
    const route = useRoute()
    const isLoading = ref(true)
    const showLoginModal = ref(false)

    const username = computed(() => store.state.auth.user?.username || '게스트')
    const isAuthenticated = computed(() => store.getters['auth/isAuthenticated'])
    const isAuthChecked = computed(() => store.getters['auth/isAuthChecked'])
    
    const currentPath = computed(() => {
      const paths = {
        '/': '대시보드',
        '/workflow': '워크플로우',
        '/monitoring': '모니터링',
        '/settings': '설정'
      }
      return paths[route.path] || '대시보드'
    })

    const logout = async () => {
      await store.dispatch('auth/logout')
      router.push('/login')
    }
    
    const handleLoginSuccess = () => {
      showLoginModal.value = false
    }

    const isSidebarCollapsed = ref(false)

    const handleSidebarToggle = (isCollapsed) => {
      isSidebarCollapsed.value = isCollapsed
    }
    
    // 사이드바 상태를 provide로 제공
    provide('isSidebarCollapsed', isSidebarCollapsed)
    
    // Check for URL parameters from OAuth redirects
    const checkForAuthRedirect = async () => {
      console.log('App.vue - 인증 리다이렉트 확인 시작')
      console.log('현재 URL:', window.location.href)
      console.log('URL 해시 존재:', !!window.location.hash)
      
      // 환경변수 기반 SSO 조건부 처리
      const useSSO = process.env.VUE_APP_USE_SSO === 'true'
      
      if (!useSSO) {
        console.log('개발 환경: SSO 리다이렉트 처리 건너뜀')
        return true
      }
      
      // URL 해시나 쿼리 파라미터에서 토큰을 찾기 위해 
      // Vuex 스토어의 handleAuthRedirect 액션을 직접 호출
      try {
        console.log('auth/handleAuthRedirect 호출')
        const success = await store.dispatch('auth/handleAuthRedirect')
        
        if (success) {
          console.log('인증 성공, 세션 유지')
          
          // Clean URL after processing
          if (window.location.search || window.location.hash) {
            console.log('URL 파라미터 제거')
            window.history.replaceState({}, document.title, window.location.pathname)
          }
          
          // 메인 페이지로 리다이렉트 (이미 메인 페이지라면 새로고침하지 않음)
          if (router.currentRoute.value.path !== '/main') {
            router.push('/main')
          }
          return true
        } else {
          console.error('토큰 검증 실패')
          showLoginModal.value = true
          return false
        }
      } catch (error) {
        console.error('OAuth 리다이렉트 처리 오류:', error)
        showLoginModal.value = true
        return false
      }
    }
    
    // Check authentication status
    const checkAuth = async () => {
      // 환경변수 기반 SSO 조건부 처리
      const useSSO = process.env.VUE_APP_USE_SSO === 'true'
      
      if (!useSSO) {
        console.log('개발 환경: 인증 체크 건너뜀')
        return
      }
      
      // 먼저 로컬 스토리지에 저장된 토큰이 있는지 확인
      const token = localStorage.getItem('token');
      
      if (token) {
        // 이미 토큰이 있으면 직접 인증 상태만 확인
        const isLoggedIn = await store.dispatch('auth/checkAuth');
        
        if (!isLoggedIn) {
          // 토큰이 있지만 유효하지 않은 경우
          // /admin 경로가 아니면 바로 SSO 로그인으로 리다이렉트
          if (!route.path.startsWith('/admin')) {
            window.location.href = 'http://localhost:8000/api/auth/google/login';
            return;
          }
          // /admin 경로인 경우에만 로그인 모달 표시
          showLoginModal.value = true;
        }
      } else {
        // 토큰이 없는 경우
        // /admin 경로인 경우에는 checkForAuthRedirect를 실행하지 않고 바로 로그인 모달 표시
        if (route.path.startsWith('/admin')) {
          showLoginModal.value = true;
          return;
        }
        
        // /admin 경로가 아닌 경우에만 checkForAuthRedirect 실행
        const redirectSuccess = await checkForAuthRedirect();
        
        if (!redirectSuccess) {
          // 리다이렉트 파라미터도 없고 토큰도 없는 경우
          // 바로 SSO 로그인으로 리다이렉트
          window.location.href = 'http://localhost:8000/api/auth/google/login';
        }
      }
    }

    onMounted(async () => {
      // Simulate loading time while checking auth
      await checkAuth()
      
      setTimeout(() => {
        isLoading.value = false
      }, 1000)
    })

    return {
      username,
      currentPath,
      logout,
      isSidebarCollapsed,
      handleSidebarToggle,
      isLoading,
      isAuthenticated,
      isAuthChecked,
      showLoginModal,
      handleLoginSuccess
    }
  }
}
</script>

<style>
:root {
  /* Primary Colors */
  --primary-50: #f5f3ff;
  --primary-100: #ede9fe;
  --primary-200: #ddd6fe;
  --primary-300: #c4b5fd;
  --primary-400: #a78bfa;
  --primary-500: #8b5cf6;
  --primary-600: #7c3aed;
  --primary-700: #6d28d9;
  
  /* Gray Colors */
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: var(--gray-100);
  overflow-x: hidden;
  width: 100%;
  max-width: 100vw;
}

html {
  overflow-x: hidden;
  width: 100%;
  max-width: 100vw;
}

#app {
  min-height: 100vh;
  display: flex;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  position: relative;
}

.loading-screen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  animation: fadeOut 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  animation-delay: 2.5s;
  overflow: hidden;
}

.loading-screen::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: 
    radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.1) 0%, transparent 50%),
    linear-gradient(45deg, rgba(124, 58, 237, 0.1) 0%, transparent 100%);
  animation: pulseBg 6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  animation: slideUp 1s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 1;
}

.loading-logo {
  width: 120px;
  height: 120px;
  position: relative;
  animation: float 4s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  margin-top: -1rem;
}

.loading-logo::before {
  content: '';
  position: absolute;
  top: -10px;
  left: -10px;
  right: -10px;
  bottom: -10px;
  background: linear-gradient(45deg, var(--primary-600), var(--primary-400));
  border-radius: 50%;
  filter: blur(20px);
  opacity: 0.5;
  animation: pulseGlow 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.loading-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  position: relative;
  z-index: 1;
}

.loading-text {
  text-align: center;
  position: relative;
}

.loading-text h2 {
  font-size: 2.5rem;
  background: linear-gradient(45deg, var(--primary-400), var(--primary-600));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.5rem;
  font-weight: 700;
  text-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
}

.loading-text p {
  color: #a97ccf;
  font-size: 1.1rem;
  position: relative;
  font-weight: 500;
  text-shadow: 0 2px 8px rgba(162, 143, 143, 0.3);
}

.loading-text p::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--primary-400), transparent);
  animation: scanLine 2s linear infinite;
}

.loading-animation {
  position: relative;
  width: 200px;
  height: 200px;
  margin: 2rem 0;
  perspective: 1000px;
}

.loading-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 4px solid transparent;
  border-top-color: var(--primary-600);
  animation: spin 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  box-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
  transform-style: preserve-3d;
}

.loading-ring:nth-child(1) {
  border-top-color: var(--primary-600);
  animation-delay: 0s;
  transform: rotateX(60deg) translateZ(0);
}

.loading-ring:nth-child(2) {
  border-top-color: var(--primary-400);
  animation-delay: 0.1s;
  transform: rotateX(45deg) translateZ(20px);
}

.loading-ring:nth-child(3) {
  border-top-color: var(--primary-200);
  animation-delay: 0.2s;
  transform: rotateX(30deg) translateZ(40px);
}

.loading-dots {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  gap: 0.5rem;
}

.loading-dot {
  width: 8px;
  height: 8px;
  background: var(--primary-600);
  border-radius: 50%;
  animation: bounce 1.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  box-shadow: 0 0 10px var(--primary-600);
}

.loading-dot:nth-child(1) {
  animation-delay: 0s;
}

.loading-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes spin {
  0% {
    transform: rotate(0deg) rotateX(60deg) translateZ(0);
  }
  100% {
    transform: rotate(360deg) rotateX(60deg) translateZ(0);
  }
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    box-shadow: 0 0 0 rgba(124, 58, 237, 0);
  }
  40% {
    transform: scale(1);
    box-shadow: 0 0 20px var(--primary-600);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(50px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

@keyframes pulseGlow {
  0%, 100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.1);
  }
}

@keyframes pulseBg {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 0.8;
  }
}

@keyframes scanLine {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

@keyframes fadeOut {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}

.sidebar {
  width: 280px;
  background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
  border-right: 1px solid var(--gray-200);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  position: fixed;
  height: 100vh;
  overflow-y: auto;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--gray-200);
}

.logo {
  height: 35px;
  width: auto;
}

.brand-name {
  font-weight: 700;
  color: var(--primary-700);
  font-size: 1.1rem;
  letter-spacing: -0.5px;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.nav-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gray-400);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.75rem;
  padding-left: 0.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1rem;
  color: var(--gray-600);
  text-decoration: none;
  border-radius: 0.75rem;
  transition: all 0.3s ease;
  font-weight: 500;
  letter-spacing: -0.3px;
}

.nav-item i {
  font-size: 1.1rem;
  width: 1.5rem;
  color: var(--gray-500);
}

.nav-item:hover {
  background: var(--primary-50);
  color: var(--primary-600);
}

.nav-item:hover i {
  color: var(--primary-600);
}

.nav-item.active {
  background: var(--primary-50);
  color: var(--primary-600);
  font-weight: 600;
}

.nav-item.active i {
  color: var(--primary-600);
}

.main-wrapper {
  display: flex;
  flex-direction: column;
  width: calc(100% - 250px);
  max-width: calc(100% - 250px);
  margin-left: 250px;
  transition: width 0.3s, max-width 0.3s, margin-left 0.3s;
  min-height: 100vh;
  position: relative;
}

.sidebar-collapsed .main-wrapper {
  width: calc(100% - 70px);
  max-width: calc(100% - 70px);
  margin-left: 70px;
}

.main-content {
  flex: 1;
  padding: 0;
  position: relative;
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}

.top-nav {
  background: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--gray-200);
}

.nav-brand span {
  font-weight: 600;
  color: var(--gray-800);
}

@media (max-width: 1200px) {
  .main-wrapper {
    margin-left: 0;
    width: 100%;
    max-width: 100%;
    transition: margin-left 0.3s ease;
  }
  
  .sidebar-collapsed .main-wrapper {
    margin-left: 250px;
    width: calc(100% - 250px);
    max-width: calc(100% - 250px);
  }
}

@media (max-width: 768px) {
  .main-wrapper {
    margin-left: 0;
    width: 100%;
    max-width: 100%;
  }
  
  .sidebar-collapsed .main-wrapper {
    margin-left: 0;
    width: 100%;
    max-width: 100%;
  }
}
</style> 