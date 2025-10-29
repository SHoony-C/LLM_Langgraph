# To Do List(문제)
- 📡 SSE 메시지 파싱 오류: SyntaxError: Unterminated string in JSON at position 1137 (line 1 column 1138)
- image 저장도 조회도 안돼
- image_url [ 0:"/appdata/RC/images/temp_title_whole.jpg" ] 여기서 앞부분 대체
https://10.172.107.182/imageview/
이건 로그도 추가해
ssemessagehandler.js
- DB Contents - image_url 에 저장은 잘돼
근데 이것도 url 변경해야함

- 프론트 추가질문 실시간 작동안돼
  랭그래프 정보 복원 완료: {showLanggraph: true, currentStep: 4, hasOriginalInput: true, hasFinalAnswer: true, finalAnswerLength: 1293, …}
additionalQuestionHandler.js:29 💬 추가 질문 스트리밍 답변 실행 시작: 아주 간단히
additionalQuestionHandler.js:57 ✅ 추가 질문 영구 메시지 ID 발급 완료: {userMessage: {…}, assistantMessage: {…}, q_mode: null, keyword: null, db_contents: null}
MessageList.vue:149 🔄 currentConversation 변경 감지
additionalQuestionHandler.js:106 📤 추가 질문 요청 데이터: {question: '아주 간단히', conversation_id: 2, message_id: 4, generate_image: false, include_langgraph_context: false, …}
additionalQuestionHandler.js:107 📤 추가 질문 요청 상세:
additionalQuestionHandler.js:108   - question: 아주 간단히
additionalQuestionHandler.js:109   - conversation_id: 2
additionalQuestionHandler.js:110   - q_mode: add
additionalQuestionHandler.js:111   - generate_image: false
additionalQuestionHandler.js:116 📋 현재 대화 메시지 히스토리:
additionalQuestionHandler.js:117   - 총 메시지 수: 3
additionalQuestionHandler.js:119   - 메시지 1: {id: '2-user', role: 'user', question: '~
additionalQuestionHandler.js:119   - 메시지 2: {id: '3-user', role: 'user', question: '~
additionalQuestionHandler.js:119   - 메시지 3: {id: '4-user', role: 'user', question: '~
additionalQuestionHandler.js:168 📡 추가 질문 SSE 스트림 종료
additionalQuestionHandler.js:156 📡 추가 질문 SSE 스트림 완료

영역이 없는게 문제일 수도 있어

# 정보
- 벡터부터 아래로 변경
콜렉션 Name : "RC"
Point 정보
vector : { "text":"aaa" "summary_purpose":"bbb" "summary_result":"ccc" "summary_fb":"ddd" },
 document_name : temp_title.pptx,
  image_url [ 0:"/appdata/RC/images/temp_title_whole.jpg" ] index_rdb : 3 

프론트에서 보여줄 이미지 경로
image_url에서 /appdata/RC/images/ 이걸 https://10.172.107.182로 대체
실제 이미지 url : https://10.172.107.182/imageview/temp_title_whole.jpg





codex 액션추가
1. - 📡 SSE 메시지 파싱 오류: SyntaxError: Unterminated string in JSON at position 1137 (line 1 column 1138)
프론트에 이렇게 로그가 나오는데, 정상 실행은 돼. 예외처리 추가해봐

2. 랭그래프 4단계에서
- messages 테이블에 image 칼럼에 저장이 안돼
- db_contents 컬럼의 rawdata을 보면
 [{"res_id": "000b35b2-e390-5c46-83f6-9a4095ff9ddd", "res_score": 0.6904839924336491, "res_payload": 
{"vector": 
{"text": "~", "summary_result": "~", "summary_fb": "~."}, "document_name": "~", "image_url": ["/appdata/RC/images/imagename_whole.jpg"]
이렇게 저장은 잘돼 이걸 그대로 1번 문서껄 image_url에 저장하면서 앞부분 /appdata/RC/images/ -> https://10.172.107.182/imageview/로 url변경
"image_url": ["/appdata/RC/images/imagename_whole.jpg"] 이 db_contents 컬럼의 이미지 url rawdata도 앞부분 /appdata/RC/images/ -> https://10.172.107.182/imageview/로 url변경
로그도 추가해


3. 프론트 추가질문 실시간 작동안돼
  랭그래프 정보 복원 완료: {showLanggraph: true, currentStep: 4, hasOriginalInput: true, hasFinalAnswer: true, finalAnswerLength: 1293, …}
additionalQuestionHandler.js:29 💬 추가 질문 스트리밍 답변 실행 시작: 아주 간단히
additionalQuestionHandler.js:57 ✅ 추가 질문 영구 메시지 ID 발급 완료: {userMessage: {…}, assistantMessage: {…}, q_mode: null, keyword: null, db_contents: null}
MessageList.vue:149 🔄 currentConversation 변경 감지
additionalQuestionHandler.js:106 📤 추가 질문 요청 데이터: {question: '아주 간단히', conversation_id: 2, message_id: 4, generate_image: false, include_langgraph_context: false, …}
additionalQuestionHandler.js:107 📤 추가 질문 요청 상세:
additionalQuestionHandler.js:108   - question: 아주 간단히
additionalQuestionHandler.js:109   - conversation_id: 2
additionalQuestionHandler.js:110   - q_mode: add
additionalQuestionHandler.js:111   - generate_image: false
additionalQuestionHandler.js:116 📋 현재 대화 메시지 히스토리:
additionalQuestionHandler.js:117   - 총 메시지 수: 3
additionalQuestionHandler.js:119   - 메시지 1: {id: '2-user', role: 'user', question: '~
additionalQuestionHandler.js:119   - 메시지 2: {id: '3-user', role: 'user', question: '~
additionalQuestionHandler.js:119   - 메시지 3: {id: '4-user', role: 'user', question: '~
additionalQuestionHandler.js:168 📡 추가 질문 SSE 스트림 종료
additionalQuestionHandler.js:156 📡 추가 질문 SSE 스트림 완료

 - 스트리밍 답변은 안되지만 스트리밍이 끝나면 결과는 정확히 UI에 보이는 상황
 - 답변이 완료될 때까지 프론트 UI에 답변 영역이 없는 상황
스트리밍 시간 동안 프론트 UI에 영역이 할당 안돼서 안보이는건지, 정확히 확인해서 개선해
 - 로그도 추가
