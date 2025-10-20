<template>
  <div v-if="show" class="search-result-popup-overlay" @click="closePopup">
    <div class="search-result-popup" @click.stop>
      <div class="popup-header">
        <h3>검색 결과 상세</h3>
        <button class="close-btn" @click="closePopup">×</button>
      </div>
      <div class="popup-content" v-if="result">
        <div class="popup-section">
          <h4>📄 문서 제목</h4>
          <p>{{ result.res_payload?.document_name || result.title || '제목 없음' }}</p>
        </div>
        <div class="popup-section">
          <h4>📊 유사도 점수</h4>
          <p>{{ (result.res_score || result.score || 0).toFixed(4) }}</p>
        </div>
        <div class="popup-section">
          <h4>📝 요약</h4>
          <p>{{ result.res_payload?.vector?.summary_result || result.summary || '요약 없음' }}</p>
        </div>
        <div class="popup-section">
          <h4>📖 전체 내용</h4>
          <p class="full-text">{{ result.res_payload?.vector?.text || result.text || '내용 없음' }}</p>
        </div>
        <div v-if="getImageUrls(result.res_payload?.vector?.image_url || result.image_url).length > 0" class="popup-section">
          <h4>🖼️ 관련 이미지</h4>
          <div class="popup-image-container">
            <div v-for="(imageUrl, index) in getImageUrls(result.res_payload?.vector?.image_url || result.image_url)" :key="index" class="image-item">
              <img 
                :src="getFullImageUrl(imageUrl)" 
                :alt="`${result.res_payload?.document_name || result.title} - 이미지 ${index + 1}`"
                class="popup-image"
                @error="handleImageError"
                @load="handleImageLoad"
              />
            </div>
            <div v-if="imageLoading" class="image-loading">
              <div class="spinner"></div>
              <span>이미지 로딩 중...</span>
            </div>
            <div v-if="imageError" class="image-error">
              <span>🖼️ 이미지를 불러올 수 없습니다</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SearchResultPopup',
  props: {
    show: {
      type: Boolean,
      default: false
    },
    result: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      imageLoading: false,
      imageError: false
    };
  },
  methods: {
    closePopup() {
      this.$emit('close');
    },
    getImageUrls(imageUrl) {
      console.log('🖼️ 원본 이미지 URL 데이터:', imageUrl);
      
      if (!imageUrl) return [];
      
      // 배열인 경우
      if (Array.isArray(imageUrl)) {
        const processedUrls = imageUrl.map(url => {
          console.log('🔍 처리 중인 URL:', url);
          // "0:"/appdata/RC/images/daily_note_19_whole.jpg" 형식에서 실제 URL 추출
          if (typeof url === 'string' && url.includes(':')) {
            const extractedUrl = url.split(':').slice(1).join(':'); // 첫 번째 콜론 이후 부분
            console.log('✅ 추출된 URL:', extractedUrl);
            return extractedUrl;
          }
          return url;
        }).filter(url => url); // 빈 문자열 제거
        
        console.log('🎯 최종 처리된 URL 배열:', processedUrls);
        return processedUrls;
      }
      
      // 문자열인 경우
      if (typeof imageUrl === 'string') {
        if (imageUrl.includes(':')) {
          const extractedUrl = imageUrl.split(':').slice(1).join(':');
          console.log('✅ 문자열에서 추출된 URL:', extractedUrl);
          return extractedUrl ? [extractedUrl] : [];
        }
        return [imageUrl];
      }
      
      return [];
    },
    getFullImageUrl(url) {
      if (!url) return '';
      console.log('🔗 변환 전 URL:', url);
      // "/appdata/RC/images/" → "https://10.172.107.182/imageview/"
      const fullUrl = url.replace(/^\/appdata\/RC\/images\//, 'https://10.172.107.182/imageview/');
      console.log('🔗 변환 후 URL:', fullUrl);
      return fullUrl;
    },
    handleImageError(event) {
      this.imageLoading = false;
      this.imageError = true;
      console.error('이미지 로딩 실패:', event.target.src);
    },
    handleImageLoad() {
      this.imageLoading = false;
      this.imageError = false;
      console.log('이미지 로딩 성공');
    }
  },
  watch: {
    show(newVal) {
      if (newVal && this.result?.image_url) {
        this.imageLoading = true;
        this.imageError = false;
      }
    }
  }
};
</script>

<style scoped>
/* 검색 결과 팝업 스타일 */
.search-result-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.search-result-popup {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { 
    transform: translateY(50px);
    opacity: 0;
  }
  to { 
    transform: translateY(0);
    opacity: 1;
  }
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.popup-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: white;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.popup-content {
  padding: 24px;
}

.popup-section {
  margin-bottom: 24px;
}

.popup-section:last-child {
  margin-bottom: 0;
}

.popup-section h4 {
  margin: 0 0 12px 0;
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 8px;
}

.popup-section p {
  margin: 0;
  color: #6b7280;
  line-height: 1.6;
}

.full-text {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.popup-image-container {
  text-align: center;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  position: relative;
}

.image-item {
  margin-bottom: 16px;
}

.image-item:last-child {
  margin-bottom: 0;
}

.popup-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.image-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: #6b7280;
}

.image-error {
  padding: 20px;
  color: #ef4444;
  text-align: center;
}

.image-error p {
  font-size: 0.8rem;
  color: #9ca3af;
  margin-top: 8px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
