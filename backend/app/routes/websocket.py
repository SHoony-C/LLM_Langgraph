import asyncio
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import contextlib
from app.utils.config import REDIS_HOST, REDIS_PORT, REDIS_CHANNEL

router = APIRouter(prefix="/ws", tags=["ws"])

# Redis 비동기 클라이언트 초기화 (config 사용)
redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
pubsub = redis_client.pubsub()
channel_name = REDIS_CHANNEL

print(f"[WebSocket] Redis 설정: {REDIS_HOST}:{REDIS_PORT}, 채널: {REDIS_CHANNEL}")

# 연결된 WebSocket 클라이언트 목록
clients: set[WebSocket] = set()

_broadcast_task: asyncio.Task | None = None
_started = False  # 중복 기동 방지 플래그

@router.websocket("/node_end")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    print(f"[WebSocket] 🔗 클라이언트 연결: {websocket.client}")
    print(f"[WebSocket] 📊 현재 연결된 클라이언트 수: {len(clients)}")
    print(f"[WebSocket] 📡 Redis 리스너 상태: {'실행 중' if _broadcast_task and not _broadcast_task.done() else '중지됨'}")
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
        print(f"[WebSocket] 🔌 클라이언트 연결 해제: {websocket.client}")
        print(f"[WebSocket] 📊 남은 클라이언트 수: {len(clients)}")
    except Exception as e:
        print(f"[WebSocket] ❌ 오류 발생: {e}")
        clients.discard(websocket)
        print(f"[WebSocket] 📊 남은 클라이언트 수: {len(clients)}")

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
        print(f"[redis] 🔗 Redis 연결 시도: {REDIS_HOST}:{REDIS_PORT}")
        print(f"[redis] 📡 구독할 채널: {channel_name}")
        
        await pubsub.subscribe(channel_name)
        print(f"[redis] 🔔 구독 완료: {channel_name}")
        
        # Redis 연결 테스트
        await redis_client.ping()
        print(f"[redis] ✅ Redis 서버 연결 확인됨")
        
        print(f"[redis] 👂 메시지 대기 중... (채널: {channel_name})")
        
        # get_message + sleep 대신 listen()으로 블로킹 루프(폴링 제거)
        async for msg in pubsub.listen():
            print(f"[redis] 📨 원시 메시지 수신: {msg}")
            if msg.get("type") != "message":
                print(f"[redis] ⏭️ 메시지 타입 무시: {msg.get('type')}")
                continue
            print(f"[redis] ✅ 유효한 메시지 수신: {msg['data'][:100]}...")
            print(f"[redis] 🔔 {len(clients)}개 WebSocket 클라이언트에게 브로드캐스트")
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

