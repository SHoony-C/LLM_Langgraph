# To Do List(문제)

1. SSE도 스트리밍 안돼
generation id 오류
SSE 파싱 관련
2. 추가 질문 스트리밍 안돼
3. package 버전 통일
4. 다시 열었을 때 키워드 색 매칭
5. 최초 접속 시, 로그인화면으로 바로 redirect 안돼 -> 무조건 로그인 안되면 redirect 되도록
6. 최초 가입해서 로그인했을 때, new conversation이 안생겨 있어
 LangGraph 4단계 분석 시작: dram bcat 불량
langGraphExecutor.js:117  ❌ prepare_message API 호출 오류: Error: 현재 대화가 없습니다.
    at gs (langGraphExecutor.js:81:13)
    at us (langGraphExecutor.js:41:38)
    at Proxy.sendChatMessage (Home.vue:187:17)
    at s (runtime-core.esm-bundler.js:199:19)
    at i (runtime-core.esm-bundler.js:206:17)
    at At (runtime-core.esm-bundler.js:6415:5)
    at Proxy.handleEnterKey (ChatInput.vue:55:12)
    at ChatInput.vue:8:33
    at Te.n.<computed>.n.<computed> (runtime-dom.esm-bundler.js:1707:12)
    at n.<computed>.n.<computed> (runtime-dom.esm-bundler.js:1730:14)
gs @ langGraphExecutor.js:117
LanggraphContainer.vue:298 🔍 [DEBUG] LanggraphContainer showLanggraph 변화: Object
langGraphExecutor.js:61  ❌ LangGraph 실행 오류: Error: 현재 대화가 없습니다.
    at gs (langGraphExecutor.js:81:13)
    at us (langGraphExecutor.js:41:38)
    at Proxy.sendChatMessage (Home.vue:187:17)
    at s (runtime-core.esm-bundler.js:199:19)
    at i (runtime-core.esm-bundler.js:206:17)
    at At (runtime-core.esm-bundler.js:6415:5)
    at Proxy.handleEnterKey (ChatInput.vue:55:12)
    at ChatInput.vue:8:33
    at Te.n.<computed>.n.<computed> (runtime-dom.esm-bundler.js:1707:12)
    at n.<computed>.n.<computed> (runtime-dom.esm-bundler.js:1730:14)
us @ langGraphExecutor.js:61
langGraphExecutor.js:307  ⚠️ 폴백 메시지 저장 실패: 현재 대화가 없습니다.

