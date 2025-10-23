import { ref } from 'vue'

export function useScroll() {
  const scrollThrottled = ref(false)
  const scrollTimeout = ref(null)
  const lastMessageHeight = ref(0)
  const lastScrollPosition = ref(0)
  const observer = ref(null)
  const scrollPending = ref(false)
  
  // 스크롤 최적화 - 통합된 쓰로틀링 적용
  const scrollToBottom = (chatMessagesRef) => {
    if (scrollPending.value) {
      return
    }
    
    scrollPending.value = true
    
    requestAnimationFrame(() => {
      if (chatMessagesRef) {
        const scrollEl = chatMessagesRef
        scrollEl.scrollTop = scrollEl.scrollHeight
      }
      scrollPending.value = false
    })
  }
  
  // 랭그래프 컨테이너로 스크롤
  const scrollToLanggraph = () => {
    const LanggraphContainer = document.querySelector('.langgraph-container')
    if (LanggraphContainer) {
      LanggraphContainer.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      })
      LanggraphContainer.scrollTop = 0
    }
  }
  
  // 랭그래프 컨테이너를 최하단으로 스크롤
  const scrollToLanggraphBottom = (chatMessagesRef) => {
    const LanggraphContainer = document.querySelector('.langgraph-container')
    if (LanggraphContainer) {
      LanggraphContainer.scrollTop = LanggraphContainer.scrollHeight
      
      if (chatMessagesRef) {
        const chatContainer = chatMessagesRef
        chatContainer.scrollTop = chatContainer.scrollHeight
      }
    }
  }
  
  // 스크롤 위치 안정화
  const preserveScrollPosition = (chatMessagesRef) => {
    if (chatMessagesRef) {
      lastScrollPosition.value = chatMessagesRef.scrollTop
    }
  }
  
  const restoreScrollPosition = (chatMessagesRef) => {
    if (chatMessagesRef) {
      chatMessagesRef.scrollTop = lastScrollPosition.value
    }
  }
  
  // 안전한 focus 메서드
  const safeFocus = (inputFieldRef) => {
    if (inputFieldRef && inputFieldRef.focus) {
      try {
        inputFieldRef.focus()
      } catch (error) {
        console.warn('Focus failed:', error)
      }
    }
  }
  
  // textarea 높이 조정
  const adjustTextareaHeight = (inputFieldRef) => {
    if (!inputFieldRef) return
    
    try {
      inputFieldRef.style.height = 'auto'
      const newHeight = Math.min(inputFieldRef.scrollHeight, 150)
      inputFieldRef.style.height = newHeight + 'px'
    } catch (error) {
      console.warn('Textarea height adjustment failed:', error)
    }
  }
  
  return {
    scrollThrottled,
    scrollTimeout,
    lastMessageHeight,
    lastScrollPosition,
    observer,
    scrollPending,
    scrollToBottom,
    scrollToLanggraph,
    scrollToLanggraphBottom,
    preserveScrollPosition,
    restoreScrollPosition,
    safeFocus,
    adjustTextareaHeight
  }
}
