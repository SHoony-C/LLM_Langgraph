import { ref } from 'vue'
import { useStore } from 'vuex'

export function useMessages() {
  const store = useStore()
  
  // 메시지 관련 상태
  const isLoading = ref(false)
  const isCreatingConversation = ref(false)
  const isSavingMessage = ref(false)
  const saveStatus = ref('')
  
  // 메시지 포맷팅
  const formatAnswer = (text) => {
    if (!text) return ''
    
    let formattedText = text
    
    // 1. 헤더 처리 (### 큰 헤더)
    formattedText = formattedText.replace(/^### (.*$)/gm, '<h3 class="markdown-h3">$1</h3>')
    formattedText = formattedText.replace(/^## (.*$)/gm, '<h2 class="markdown-h2">$1</h2>')
    formattedText = formattedText.replace(/^# (.*$)/gm, '<h1 class="markdown-h1">$1</h1>')
    
    // 2. **텍스트** 형태를 <strong>텍스트</strong>로 변환 (중간 헤더)
    formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong class="markdown-bold">$1</strong>')
    
    // 3. 표(테이블) 처리
    const tableRegex = /(\|[^\n]+\|\n)+/g
    formattedText = formattedText.replace(tableRegex, (match) => {
      const lines = match.trim().split('\n')
      let tableHtml = '<table class="markdown-table">'
      
      lines.forEach((line, index) => {
        if (line.trim() && !line.match(/^\|[-\s|]+\|$/)) {
          const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell)
          if (cells.length > 0) {
            tableHtml += '<tr>'
            cells.forEach(cell => {
              if (index === 0) {
                tableHtml += `<th class="markdown-th">${cell}</th>`
              } else {
                tableHtml += `<td class="markdown-td">${cell}</td>`
              }
            })
            tableHtml += '</tr>'
          }
        }
      })
      
      tableHtml += '</table>'
      return tableHtml
    })
    
    // 4. 리스트 처리
    formattedText = formattedText.replace(/^- (.*$)/gm, '<li class="markdown-li">$1</li>')
    formattedText = formattedText.replace(/(<li class="markdown-li">.*<\/li>)/s, '<ul class="markdown-ul">$1</ul>')
    
    // 5. 번호 리스트 처리
    formattedText = formattedText.replace(/^\d+\. (.*$)/gm, '<li class="markdown-oli">$1</li>')
    formattedText = formattedText.replace(/(<li class="markdown-oli">.*<\/li>)/s, '<ol class="markdown-ol">$1</ol>')
    
    // 6. 코드 블록 처리
    formattedText = formattedText.replace(/```([\s\S]*?)```/g, '<pre class="markdown-code"><code>$1</code></pre>')
    formattedText = formattedText.replace(/`([^`]+)`/g, '<code class="markdown-inline-code">$1</code>')
    
    // 7. 줄바꿈 처리
    formattedText = formattedText.replace(/\n\n/g, '</p><p class="markdown-p">')
    formattedText = formattedText.replace(/\n/g, '<br>')
    
    // 8. 단락 태그로 감싸기
    if (!formattedText.includes('<p class="markdown-p">')) {
      formattedText = `<p class="markdown-p">${formattedText}</p>`
    } else {
      formattedText = `<p class="markdown-p">${formattedText}</p>`
    }
    
    return formattedText
  }
  
  // 피드백 처리
  const getMessageFeedback = (messageId, currentMessages) => {
    const message = currentMessages.find(m => m.id === messageId)
    return message ? message.feedback : null
  }
  
  const submitFeedback = async (messageId, feedback) => {
    await store.dispatch('submitFeedback', { messageId, feedback })
  }
  
  // 새 대화 생성
  const newConversation = async () => {
    if (isCreatingConversation.value) {
      console.log('[HOME] 새 대화 생성 중 - 중복 실행 방지')
      return
    }
    
    isCreatingConversation.value = true
    console.log('🔄 새 대화 UI 초기화 시작...')
    
    try {
      const newConversation = await store.dispatch('createConversation')
      if (newConversation) {
        store.commit('setCurrentConversation', newConversation)
        console.log('✅ 새 대화 생성 완료:', newConversation.id)
      } else {
        console.error('❌ 새 대화 생성 실패')
        alert('새 대화 생성에 실패했습니다. 다시 시도해주세요.')
      }
    } catch (error) {
      console.error('❌ 새 대화 생성 오류:', error)
      alert('새 대화 생성 중 오류가 발생했습니다.')
    }
    
    isCreatingConversation.value = false
    console.log('✅ 새 대화 UI 초기화 완료')
  }
  
  return {
    // 상태
    isLoading,
    isCreatingConversation,
    isSavingMessage,
    saveStatus,
    
    // 메서드
    formatAnswer,
    getMessageFeedback,
    submitFeedback,
    newConversation
  }
}
