import { ref } from 'vue'

export function useSSE() {
  const isStreaming = ref(false)
  const streamingMessage = ref('')
  const streamingVisible = ref(false)
  
  // SSE 스트리밍으로 LangGraph 실행
  const executeLangGraphWithSSE = async (inputText, homeInstance) => {
    // AbortController 생성 및 전역 저장
    const controller = new AbortController()
    window.sseController = controller
    
    try {
      // 인증 토큰 가져오기
      const token = localStorage.getItem('access_token')
      
      const response = await fetch('http://localhost:8000/api/langgraph/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({
          question: inputText
        }),
        signal: controller.signal
      })
      
      if (!response.ok) {
        throw new Error(`SSE 요청 실패: ${response.status}`)
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      let streamActive = true
      while (streamActive) {
        const { done, value } = await reader.read()
        
        if (done) {
          streamActive = false
          break
        }
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            
            if (data === '[DONE]') {
              return
            }
            
            if (data.trim()) {
              try {
                const parsedData = JSON.parse(data)
                
                if (parsedData.heartbeat) {
                  continue
                }
                
                if (parsedData.error) {
                  console.error('❌ SSE 에러:', parsedData.error)
                  throw new Error(parsedData.error)
                }
                
                await homeInstance.handleSSEMessage(parsedData)
                
              } catch (parseError) {
                console.error('❌ SSE 메시지 파싱 오류:', parseError, 'Data:', data)
              }
            }
          }
        }
      }
      
    } catch (error) {
      if (error.name === 'AbortError') {
        return
      }
      console.error('❌ SSE 스트리밍 오류:', error)
      throw error
    }
  }
  
  return {
    isStreaming,
    streamingMessage,
    streamingVisible,
    executeLangGraphWithSSE
  }
}
