import asyncio
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import contextlib

router = APIRouter(prefix="/ws", tags=["ws"])

# Redis 비동기 클라이언트 초기화
redis_client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)
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
        # 클라이언트로부터 메시지를 받되, Redis 메시지도 처리할 수 있도록
        # 짧은 타임아웃으로 설정
        while True:
            try:
                # 1초 타임아웃으로 메시지 대기
                message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                print(f"[websocket] 클라이언트로부터 메시지 수신: {message}")
            except asyncio.TimeoutError:
                # 타임아웃 시 계속 루프 (Redis 메시지 처리 가능)
                continue
    except WebSocketDisconnect:
        clients.discard(websocket)
        print(f"[disconnected] {websocket.client}")
    except Exception as e:
        print(f"[websocket] 오류 발생: {e}")
        clients.discard(websocket)

async def broadcast(message: str):
    print(f"[websocket] Redis 메시지 브로드캐스트 시작: {message[:100]}...")
    # 반복 도중 remove 충돌 방지
    for ws in list(clients):
        try:
            await ws.send_text(message)
            print(f"[websocket] 메시지 전송 성공: {ws.client}")
        except Exception as e:
            print(f"[websocket] 메시지 전송 실패: {ws.client}, 오류: {e}")
            clients.discard(ws)
    print(f"[websocket] 브로드캐스트 완료, 연결된 클라이언트: {len(clients)}")

async def redis_listener_loop():
    await pubsub.subscribe(channel_name)
    print(f"[redis] Subscribed: {channel_name}")
    try:
        # get_message + sleep 대신 listen()으로 블로킹 루프(폴링 제거)
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            print(f"[redis] 메시지 수신: {msg['data'][:100]}...")
            await broadcast(msg["data"])
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.close()
        await redis_client.close()

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

