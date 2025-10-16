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
    print(f"[websocket] 🔔 브로드캐스트: {len(clients)}개 클라이언트")
    
    # 반복 도중 remove 충돌 방지
    for ws in list(clients):
        try:
            await ws.send_text(message)
        except Exception as e:
            print(f"[websocket] ❌ 전송 실패: {e}")
            clients.discard(ws)

async def redis_listener_loop():
    try:
        print(f"[redis] 🔗 Redis 연결 시도: {redis_client}")
        await pubsub.subscribe(channel_name)
        print(f"[redis] 🔔 구독 완료: {channel_name}")
        
        # Redis 연결 테스트
        await redis_client.ping()
        print(f"[redis] ✅ Redis 서버 연결 확인됨")
        
        # get_message + sleep 대신 listen()으로 블로킹 루프(폴링 제거)
        async for msg in pubsub.listen():
            print(f"[redis] 📨 원시 메시지 수신: {msg}")
            if msg.get("type") != "message":
                print(f"[redis] ⏭️ 메시지 타입 무시: {msg.get('type')}")
                continue
            print(f"[redis] ✅ 유효한 메시지 수신: {msg['data'][:100]}...")
            await broadcast(msg["data"])
    except asyncio.CancelledError:
        print(f"[redis] ❌ Redis 리스너 취소됨")
        pass
    except Exception as e:
        print(f"[redis] ❌ Redis 리스너 오류: {e}")
        import traceback
        print(f"[redis] 오류 상세: {traceback.format_exc()}")
    finally:
        print(f"[redis] 🔚 Redis 연결 종료 중...")
        try:
            await pubsub.close()
            await redis_client.close()
        except Exception as e:
            print(f"[redis] Redis 연결 종료 중 오류: {e}")

# Startup/Shutdown 이벤트를 main.py에서 처리하도록 변경
async def start_redis_listener():
    """Redis 리스너 시작"""
    global _broadcast_task, _started
    if _started:
        print("[Redis] 이미 시작됨 - 중복 기동 방지")
        return
    _started = True
    print("[Redis] 🚀 Redis 리스너 시작 중...")
    _broadcast_task = asyncio.create_task(redis_listener_loop())
    print("[Redis] ✅ Redis 리스너 시작 완료")

async def stop_redis_listener():
    """Redis 리스너 중지"""
    global _broadcast_task
    if _broadcast_task:
        print("[Redis] 🛑 Redis 리스너 중지 중...")
        _broadcast_task.cancel()
        with contextlib.suppress(Exception):
            await _broadcast_task
        print("[Redis] ✅ Redis 리스너 중지 완료")

