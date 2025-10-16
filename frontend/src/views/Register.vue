<template>
  <div class="auth-page">
    <div class="auth-container">
      <div class="auth-header">
        <h1>회원가입</h1>
        <p>LLM-mini 계정 생성하기</p>
      </div>
      
      <div class="auth-form">
        <div class="form-group">
          <label for="username">사용자 이름</label>
          <input 
            type="text" 
            id="username" 
            v-model="username" 
            placeholder="사용자 이름을 입력하세요" 
          />
        </div>
        
        <div class="form-group">
          <label for="email">이메일</label>
          <input 
            type="email" 
            id="email" 
            v-model="email" 
            placeholder="이메일을 입력하세요" 
          />
        </div>
        
        <div class="form-group">
          <label for="deptname">부서명</label>
          <input 
            type="text" 
            id="deptname" 
            v-model="deptname" 
            placeholder="부서명을 입력하세요 (선택사항)" 
          />
        </div>
        
        <div class="form-group">
          <label for="password">비밀번호</label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            placeholder="비밀번호를 입력하세요" 
          />
        </div>
        
        <div class="form-group">
          <label for="confirmPassword">비밀번호 확인</label>
          <input 
            type="password" 
            id="confirmPassword" 
            v-model="confirmPassword" 
            placeholder="비밀번호를 다시 입력하세요" 
          />
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <button 
          class="auth-button" 
          @click="register" 
          :disabled="isLoading || !isFormValid"
        >
          <span v-if="!isLoading">회원가입</span>
          <span v-else class="loading-spinner"></span>
        </button>
        
        <p class="auth-link">
          이미 계정이 있으신가요? <router-link to="/login">로그인</router-link>
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
      email: '',
      deptname: '',
      password: '',
      confirmPassword: '',
      isLoading: false,
      error: null
    }
  },
  computed: {
    isFormValid() {
      return (
        this.username && 
        this.email && 
        this.password && 
        this.confirmPassword && 
        this.password === this.confirmPassword &&
        this.password.length >= 6
      );
    }
  },
  methods: {
    async register() {
      if (!this.isFormValid) {
        if (!this.username || !this.email || !this.password) {
          this.error = '모든 필드를 입력해주세요';
        } else if (this.password !== this.confirmPassword) {
          this.error = '비밀번호가 일치하지 않습니다';
        } else if (this.password.length < 6) {
          this.error = '비밀번호는 최소 6자 이상이어야 합니다';
        }
        return;
      }
      
      this.isLoading = true;
      this.error = null;
      
      try {
        await this.$store.dispatch('register', {
          username: this.username,
          email: this.email,
          deptname: this.deptname,
          password: this.password
        });
        
        // 가입 및 로그인 성공 후 홈으로 이동
        this.$router.push('/');
      } catch (error) {
        this.error = error.message || '회원가입에 실패했습니다. 다시 시도해주세요';
      } finally {
        this.isLoading = false;
      }
    }
  },
  // 이미 로그인되어 있으면 홈으로 리다이렉트
  beforeMount() {
    if (this.$store.state.isAuthenticated) {
      this.$router.push('/');
    }
  }
}
</script>

<style>
@import '../assets/styles/register.css';
</style>