
// store 생성 후에 쿠키에서 인증 정보 초기화
setTimeout(() => {
  // 페이지 새로고침 시 SSO 완료 플래그 정리 (새로운 세션이므로)
  const currentUrl = window.location.href;
  if (!currentUrl.includes('id_token') && !currentUrl.includes('code=') && !currentUrl.includes('state=')) {
    // OAuth 콜백이 아닌 일반 페이지 접근 시에만 플래그 정리
    if (performance.navigation.type === performance.navigation.TYPE_RELOAD || 
        performance.navigation.type === performance.navigation.TYPE_NAVIGATE) {
      // console.log('[AUTH] 새로운 세션 시작 - OAuth 플래그 정리');
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
  // console.log('[AUTH] OAuth 플래그 초기화됨');
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
          // console.log('[AUTH] OAuth 처리 타임아웃 - 플래그 강제 정리');
          isProcessingOAuth = false;
          sessionStorage.removeItem('oauth_processing');
        }
        
        // 인증 상태 확인
        const storedToken = localStorage.getItem('access_token');
        const storedUserInfo = localStorage.getItem('user_info');
        
        if (storedToken && storedUserInfo && store.state.isAuthenticated) {
          // console.log('[AUTH] 인증 확인됨 - 페이지 접근 허용');
          next();
        } else {
          // console.log('[AUTH] 인증 실패 - samsung SSO로 리다이렉트');
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
      // console.log('[AUTH] localStorage에서 인증 정보 복원됨');
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
    // console.log('[AUTH] OAuth 처리 완료/진행 중 - 접근 허용');
    
    // localStorage에서 토큰 확인으로 인증 상태 판단
    const storedToken = localStorage.getItem('access_token');
    const storedUserInfo = localStorage.getItem('user_info');
    
    if (storedToken && storedUserInfo) {
      // localStorage에 인증 정보가 있으면 접근 허용
      // console.log('[AUTH] localStorage에 인증 정보 있음 - 접근 허용');
      
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
      // console.log('[AUTH] OAuth 처리 중 - 토큰 설정 대기');
      let retryCount = 0;
      const maxRetries = 6; // 최대 3초 대기 (500ms * 6)
      
      const checkAuthState = () => {
        retryCount++;
        const currentToken = localStorage.getItem('access_token');
        const currentUserInfo = localStorage.getItem('user_info');
        
        if (currentToken && currentUserInfo) {
          // console.log('[AUTH] 토큰 설정 완료 - 접근 허용');
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
          // console.log('[AUTH] 토큰 설정 타임아웃 - OAuth 플래그 정리 후 리다이렉트');
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
  // console.log('[AUTH] 인증되지 않음 - SSO로 리다이렉트');
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
          
          // console.log('[AUTH] 백엔드 JWT 토큰 설정 완료:', {
          //   token: data.access_token.substring(0, 20) + '...',
          //   user: backendUser.username
          // });
        })
                      .catch((error) => {
          console.error('Backend authentication failed:', error);
          // 백엔드 인증 실패 시 사용자에게 알림
          alert('백엔드 인증에 실패했습니다. 다시 시도해주세요.');
          // 인증 실패 시 상태만 정리
          // console.log('백엔드 인증 실패 - 상태 정리');
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
                        // console.log('인증 실패 - 상태만 정리');
                      } catch (error) {
                        try {
                          // console.log('OAuth 처리 실패 - 상태만 정리');
                        } catch (error2) {
                          // console.log('OAuth 인증 실패 - 상태만 정리');
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
    // console.log('[AUTH] 로그아웃 직후 - OAuth 처리 건너뛰기');
    sessionStorage.removeItem('logout_redirect'); // 플래그 정리
    return;
  }
  
  // 이미 OAuth 처리가 완료된 경우 중복 처리 방지
  // console.log('[AUTH] checkForAuthToken 시작:', {
  //   hasProcessedOAuth,
  //   isProcessingOAuth,
  //   currentUrl: window.location.href
  // });
  
  if (hasProcessedOAuth) {
    // console.log('[AUTH] OAuth 이미 처리됨, 중복 실행 방지');
    return;
  }
  
  // 기존 처리 중 플래그가 있는 경우 정리 (새로운 처리 시작)
  if (sessionStorage.getItem('oauth_processing') === 'true') {
    // console.log('[AUTH] 기존 OAuth 처리 플래그 정리');
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
      // console.log('[AUTH] OAuth 파라미터 발견 - 처리 시작');
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
          // console.log('[AUTH] 토큰 로그인 완료, 홈으로 이동');
          router.push('/');
        })
        .catch(error => {
          console.error("Auto-login failed:", error);
          isProcessingOAuth = false;
          router.push('/login');
        });
    } else {
      // console.log('[AUTH] OAuth 이미 처리됨, 중복 실행 방지');
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
app.use(store);
app.use(router);
app.mount('#app'); 
