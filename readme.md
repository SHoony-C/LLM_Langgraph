# To Do List(Out)
- 기본 모델 선택 기능
- 로그인 사소한 오류

# To Do List(In)
- 현재 su 내용 push

# LLM UI New

LangGraph와 Redis WebSocket을 통합한 AI 워크플로우 시스템입니다.

## 주요 기능

### 🚀 LangGraph 워크플로우
- **노드 기반 AI 워크플로우**: 키워드 증강 → RAG 검색 → 재순위 → 답변 생성
- **실시간 진행 상황 추적**: 각 노드의 실행 상태를 실시간으로 모니터링
- **조건부 분기**: 검색 결과 품질에 따른 동적 워크플로우 분기

### 🔌 Redis WebSocket 통합
- **실시간 상태 브로드캐스팅**: LangGraph 노드 상태를 WebSocket으로 실시간 전송
- **비동기 통신**: Redis pub/sub을 통한 효율적인 메시지 전달
- **연결 관리**: 자동 재연결 및 연결 상태 모니터링

### 🎯 AI 분석 도메인
- **범용 AI 분석**: 다양한 도메인에 대한 지능형 분석
- **키워드 자동 증강**: 입력 질의를 기반으로 AI 키워드 자동 생성
- **구조화된 답변**: 검색 결과를 기반으로 한 체계적인 분석 보고서 생성

## 시스템 아키텍처

```
사용자 입력 → LangGraph 워크플로우 → Redis → WebSocket → 프론트엔드
                ↓
        [키워드증강 → RAG검색 → 재순위 → 답변생성]
                ↓
            Redis pub/sub → WebSocket 브로드캐스트
```

## 설치 및 실행

### 백엔드 설정

1. **의존성 설치**
```bash
cd backend
pip install -r requirements.txt
```

2. **환경 변수 설정**
```bash
# .env 파일 생성
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_CHANNEL=langgraph_node_status
```

3. **Redis 서버 실행**
```bash
# Redis 서버 시작 (기본 포트 6379)
redis-server
```

4. **백엔드 서버 실행**
```bash
cd backend
python main.py
```

### 프론트엔드 설정

1. **의존성 설치**
```bash
cd frontend
npm install
```

2. **개발 서버 실행**
```bash
npm run serve
```

## API 엔드포인트

### LangGraph API
- `POST /api/llm/langgraph`: LangGraph 워크플로우 실행
- `POST /api/llm/stream`: 스트리밍 응답 (LangGraph 기반)

### WebSocket API
- `WS /ws/node_end`: 실시간 노드 상태 수신

## 워크플로우 노드

1. **node_rc_init**: 초기화 및 입력 검증
2. **node_rc_keyword**: 키워드 증강 및 도메인 분류
3. **node_rc_rag**: 벡터 데이터베이스 검색
4. **node_rc_rerank**: 검색 결과 재순위 및 품질 평가
5. **node_rc_answer**: 최종 답변 생성
6. **node_rc_plain_answer**: 기본 답변 (검색 결과 없음 시)

## 개발 가이드

### 새로운 노드 추가
```python
async def new_node(state: SearchState) -> SearchState:
    # 노드 로직 구현
    await publish_node_status("new_node", "completed", {"result": data})
    return updated_state
```

### WebSocket 메시지 처리
```javascript
this.websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.node === 'new_node') {
        // 노드별 처리 로직
    }
};
```

## 문제 해결

### Redis 연결 오류
- Redis 서버가 실행 중인지 확인
- 포트 6379가 사용 가능한지 확인
- 방화벽 설정 확인

### WebSocket 연결 실패
- 백엔드 서버가 실행 중인지 확인
- CORS 설정 확인
- 네트워크 연결 상태 확인

### LangGraph 실행 오류
- 의존성 패키지 버전 확인
- Python 환경 설정 확인
- 로그 메시지 확인

## 라이선스

MIT License

## 기여

프로젝트에 기여하고 싶으시다면 Pull Request를 보내주세요.

## Technologies Used

- Vue.js 3 with Vuex for state management
- FastAPI (Python) backend
- SQLAlchemy ORM
- MySQL database
- OpenAI API integration 




Package            Version
------------------ ---------
aiohappyeyeballs   2.6.1
aiohttp            3.11.18
aiosignal          1.3.2
anyio              4.9.0
async-timeout      5.0.1
asyncpg            0.28.0
attrs              25.3.0
bcrypt             3.2.0
certifi            2025.4.26
cffi               1.17.1
charset-normalizer 3.4.2
click              8.2.0
colorama           0.4.6
cryptography       44.0.3
dnspython          2.7.0
ecdsa              0.19.1
email_validator    2.2.0
exceptiongroup     1.3.0
fastapi            0.95.2
filelock           3.18.0
frozenlist         1.6.0
fsspec             2025.3.2
greenlet           3.2.2
h11                0.16.0
httpcore           1.0.9
httpx              0.28.1
huggingface-hub    0.31.2
idna               3.10
motor              3.3.1
multidict          6.4.3
numpy              1.24.3
openai             0.28.0
opencv-python      4.11.0.86
packaging          25.0
passlib            1.7.4
pillow             11.2.1
pip                23.0.1
propcache          0.3.1
pyasn1             0.4.8
pycparser          2.22
pydantic           1.10.8
pymongo            4.5.0
PyMySQL            1.1.1
python-dotenv      1.1.0
python-jose        3.4.0
python-multipart   0.0.20
PyYAML             6.0.2
regex              2024.11.6
requests           2.32.3
rsa                4.9.1
safetensors        0.5.3
setuptools         65.5.0
six                1.17.0
sniffio            1.3.1
SQLAlchemy         2.0.21
starlette          0.27.0
tokenizers         0.13.3
tqdm               4.67.1
transformers       4.33.1
typing_extensions  4.13.2
urllib3            2.4.0
uvicorn            0.22.0
yarl               1.20.0