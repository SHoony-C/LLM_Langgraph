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

    // 로그인 완료 후 처리
    processLoginSuccess() {
      console.log('로그인 성공 처리');
    }
  },
  
  async mounted() {
    // 로그인 페이지 로딩 완료
    console.log('로그인 페이지 마운트됨');
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

<style>
@import '../assets/styles/login.css';
</style>