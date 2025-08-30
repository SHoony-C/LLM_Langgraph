# websocket_server.py
import asyncio
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter


router = APIRouter(prefix="/ws", tags=["ws"])


# Redis 비동기 클라이언트 초기화
redis_client = aioredis.Redis(host="10.172.107.182", port=8005, decode_responses=True)
pubsub = redis_client.pubsub()
channel_name = "langgraph_node_status"

# 연결된 WebSocket 클라이언트 목록
clients: set[WebSocket] = set()

_broadcast_task: asyncio.Task | None = None
_started = False  # 중복 기동 방지 플래그

@router.websocket("/node_end")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    print(f"[connected] {websocket.client}")
    try:
        # 클라이언트로부터 들어오는 메시지가 필요 없으면
        # 주기적 ping/pong만 유지하거나 receive_text()는 생략 가능
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
        print(f"[disconnected] {websocket.client}")

async def broadcast(message: str):
    # 반복 도중 remove 충돌 방지
    for ws in list(clients):
        try:
            await ws.send_text(message)
        except Exception:
            clients.discard(ws)

async def redis_listener_loop():
    await pubsub.subscribe(CHANNEL)
    print(f"[redis] Subscribed: {CHANNEL}")
    try:
        # get_message + sleep 대신 listen()으로 블로킹 루프(폴링 제거)
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            await broadcast(msg["data"])
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.close()
        await redis_pubsub.close()

@router.on_event("startup")
async def startup_event():
    global _broadcast_task, _started
    if _started:
        return  # 이미 실행 중이면 재기동 금지
    _started = True
    _broadcast_task = asyncio.create_task(redis_listener_loop())

@router.on_event("shutdown")
async def shutdown_event():
    global _broadcast_task
    if _broadcast_task:
        _broadcast_task.cancel()
        with contextlib.suppress(Exception):
            await _broadcast_task



# @router.websocket("/node_end")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     clients.add(websocket)
#     print(f"[connected] {websocket.client}")
#     try:
#         while True:
#             await websocket.receive_text()  # 클라이언트 ping 유지
#     except WebSocketDisconnect:
#         clients.remove(websocket)
#         print(f"[disconnected] {websocket.client}")

# # Redis → WebSocket 브로드캐스트 루프
# async def redis_listener_loop():
#     await pubsub.subscribe(channel_name)
#     print(f"[redis] Subscribed to channel: {channel_name}")
#     while True:
#         message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
#         if message:
#             data = message["data"]
#             await broadcast(data)
#         await asyncio.sleep(0.1)

# # 연결된 모든 클라이언트에 전송
# async def broadcast(message: str):
#     dead_clients = []
#     for ws in clients:
#         try:
#             await ws.send_text(message)
#         except Exception:
#             dead_clients.append(ws)
#     for dc in dead_clients:
#         clients.remove(dc)

# # 서버 시작 시 Redis 리스너 등록
# @router.on_event("startup")
# async def startup_event():
#     asyncio.create_task(redis_listener_loop())



# from fastapi.responses import HTMLResponse
  
# # 단순 HTML 테스트용
# @router.get("/")
# def get():
#     return HTMLResponse("""
#     <html><body>
#     <script>
#         let ws = new WebSocket("ws://localhost:8000/ws");
#         ws.onmessage = (event) => console.log("Node update:", event.data);
#     </script>
#     LangGraph 상태 수신 테스트
#     </body></html>
#     """)



아래는 프론트 샘플?
<!DOCTYPE html>
<html>
  <body>
    <h2>Redis 메시지 수신</h2>
    <div id="messages"></div>

    <script>
      // WebSocket 서버 주소 (예: FastAPI/Flask 등에서 띄운 ws 엔드포인트)
      const socket = new WebSocket("ws://localhost:8000/ws");

      // 연결이 성공적으로 열렸을 때
      socket.onopen = () => {
        console.log("WebSocket 연결 성공");
        // 서버에 초기 메시지를 보낼 수도 있음
        socket.send("Hello from browser");
      };

      // 서버에서 메시지를 받았을 때
      socket.onmessage = (event) => {
        console.log("메시지 수신:", event.data);
        const msgDiv = document.getElementById("messages");
        msgDiv.innerHTML += `<p>${event.data}</p>`;
      };

      // 연결이 닫혔을 때
      socket.onclose = () => {
        console.log("WebSocket 연결 종료");
      };

      // 에러 발생 시
      socket.onerror = (error) => {
        console.error("WebSocket 에러:", error);
      };
    </script>
  </body>
</html>






