import { ref, computed } from 'vue'

export function useLanggraph() {
 
  // 랭그래프 상태
  const showLanggraph = ref(false)
  const currentStep = ref(0)
  const originalInput = ref('')
  const augmentedKeywords = ref([])
  const isSearching = ref(false)
  const searchResults = ref([])
  const searchedDocuments = ref([])
  const hasSearchCompleted = ref(false)
  const isGeneratingAnswer = ref(false)
  const finalAnswer = ref('')
  const streamingAnswer = ref('')
  const isStreamingAnswer = ref(false)
  const analysisImageUrl = ref('')
  const imageLoadFailed = ref(false)
  const failedImageUrl = ref('')
  const lastImageUrl = ref('')
  const langGraphError = ref(null)
  const extractedKeywords = ref(null)
  const extractedDbSearchTitle = ref(null)
  const isDoneProcessed = ref(false)
  
  // 랭그래프 복원 관련
  const lastRestoredConversationId = ref(null)
  const lastRestoredMessageCount = ref(0)
  
  // 실시간 기능 보존을 위한 상태
  const isNewConversation = ref(true)
  const isRestoringConversation = ref(false)
  const isFirstQuestionInSession = ref(true)
  const isFollowupQuestion = ref(false)
  const isLanggraphJustCompleted = ref(false) // 랭그래프 완료 직후 플래그
  
  // 계산된 속성
  const progressPercentage = computed(() => (currentStep.value / 4) * 100)
  
  // 랭그래프 초기화
  const resetLanggraph = () => {
    showLanggraph.value = false
    currentStep.value = 0
    originalInput.value = ''
    augmentedKeywords.value = []
    searchResults.value = []
    finalAnswer.value = ''
    analysisImageUrl.value = ''
    lastImageUrl.value = ''
    langGraphError.value = null
    isSearching.value = false
    isGeneratingAnswer.value = false
    extractedKeywords.value = null
    extractedDbSearchTitle.value = null
  }
  
  const resetLanggraphState = () => {
    resetLanggraph()
    isFirstQuestionInSession.value = true
  }
  
  // 키워드 분류
  const categorizeKeyword = (keyword, index) => {
    const keywordLower = keyword.toLowerCase()
    
    if (index === 0) return '원본'
    
    if (keywordLower.includes('분석') || keywordLower.includes('analysis') || keywordLower.includes('데이터')) {
      return '분석'
    } else if (keywordLower.includes('개선') || keywordLower.includes('향상') || keywordLower.includes('최적화')) {
      return '개선'
    } else if (keywordLower.includes('전략') || keywordLower.includes('계획') || keywordLower.includes('방안')) {
      return '전략'
    } else if (keywordLower.includes('성과') || keywordLower.includes('결과') || keywordLower.includes('효과')) {
      return '성과'
    } else if (keywordLower.includes('관리') || keywordLower.includes('운영') || keywordLower.includes('시스템')) {
      return '관리'
    } else if (keywordLower.includes('기술') || keywordLower.includes('개발') || keywordLower.includes('솔루션')) {
      return '기술'
    } else if (keywordLower.includes('비즈니스') || keywordLower.includes('사업') || keywordLower.includes('경영')) {
      return '비즈니스'
    } else if (keywordLower.includes('프로세스') || keywordLower.includes('절차') || keywordLower.includes('워크플로우')) {
      return '프로세스'
    } else {
      const categories = ['핵심', '관련', '확장', '부가']
      return categories[(index - 1) % categories.length]
    }
  }
  
  return {
    // 상태
    showLanggraph,
    currentStep,
    originalInput,
    augmentedKeywords,
    isSearching,
    searchResults,
    searchedDocuments,
    hasSearchCompleted,
    isGeneratingAnswer,
    finalAnswer,
    streamingAnswer,
    isStreamingAnswer,
    analysisImageUrl,
    imageLoadFailed,
    failedImageUrl,
    lastImageUrl,
    langGraphError,
    extractedKeywords,
    extractedDbSearchTitle,
    isDoneProcessed,
    lastRestoredConversationId,
    lastRestoredMessageCount,
    isNewConversation,
    isRestoringConversation,
    isFirstQuestionInSession,
    isFollowupQuestion,
    isLanggraphJustCompleted,
    
    // 계산된 속성
    progressPercentage,
    
    // 메서드
    resetLanggraph,
    resetLanggraphState,
    categorizeKeyword,
  }
}
