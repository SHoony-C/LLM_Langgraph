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

    console.log('🚀 [SSE] LangGraph 스트리밍 요청 시작', {
      inputPreview: inputText?.slice(0, 50) || '',
      hasToken: !!localStorage.getItem('access_token')
    })
    
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
        console.error('❌ [SSE] 스트리밍 응답 실패', {
          status: response.status,
          statusText: response.statusText
        })
        throw new Error(`SSE 요청 실패: ${response.status}`)
      }

      console.log('✅ [SSE] 스트리밍 응답 수신 성공 - 데이터 읽기 시작')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let lastLoggedGeneratorId = null

      const processEventsFromBuffer = async () => {
        let boundaryIndex = buffer.indexOf('\n\n')

        while (boundaryIndex !== -1) {
          const rawEvent = buffer.slice(0, boundaryIndex)
          buffer = buffer.slice(boundaryIndex + 2)

          const lines = rawEvent.split('\n')
          let dataPayload = ''

          for (const line of lines) {
            if (!line.trim()) continue
            if (line.startsWith('data:')) {
              dataPayload += line.slice(5).trimStart()
            }
          }

          if (!dataPayload) {
            console.log('⚠️ [SSE] data 필드를 찾지 못한 이벤트', rawEvent)
            boundaryIndex = buffer.indexOf('\n\n')
            continue
          }

          if (dataPayload === '[DONE]') {
            console.log('🏁 [SSE] [DONE] 토큰 수신 - 스트림 종료 예정')
            return true
          }

          try {
            const parsedData = JSON.parse(dataPayload)

            const generatorId = parsedData.generator_id || parsedData.generatorId || lastLoggedGeneratorId
            if (generatorId && generatorId !== lastLoggedGeneratorId) {
              lastLoggedGeneratorId = generatorId
            }

            console.log('🧭 [SSE] 파싱된 메시지', {
              generatorId: generatorId || 'unknown',
              stage: parsedData.stage || 'unknown',
              status: parsedData.status || 'unknown',
              node: parsedData.node_name || parsedData.node || 'n/a',
              event: parsedData.event || 'n/a',
              hasResult: !!parsedData.result
            })

            if (parsedData.heartbeat) {
              console.log('❤️ [SSE] 하트비트 수신')
              boundaryIndex = buffer.indexOf('\n\n')
              continue
            }

            if (parsedData.error) {
              console.error('❌ SSE 에러:', parsedData.error)
              throw new Error(parsedData.error)
            }

            await homeInstance.handleSSEMessage({
              ...parsedData,
              generator_id: parsedData.generator_id || parsedData.generatorId || lastLoggedGeneratorId
            })
          } catch (parseError) {
            console.error('❌ SSE 메시지 파싱 오류:', parseError, 'Data:', dataPayload)
          }

          boundaryIndex = buffer.indexOf('\n\n')
        }

        return false
      }

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          console.log('ℹ️ [SSE] 스트림 종료 신호 수신 (reader done)')
          // 남아있는 버퍼 처리 (텍스트 디코더 플러시)
          const remaining = decoder.decode()
          if (remaining) {
            buffer += remaining
          }
          const shouldStop = await processEventsFromBuffer()
          if (shouldStop) {
            return
          }
          break
        }

        const chunk = decoder.decode(value, { stream: true })
        if (!chunk) {
          continue
        }

        buffer += chunk
        console.log('📦 [SSE] 원시 청크 수신', { chunk, bufferLength: buffer.length })

        const shouldStop = await processEventsFromBuffer()
        if (shouldStop) {
          return
        }
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('⏹️ [SSE] AbortController에 의해 스트림이 중단됨')
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