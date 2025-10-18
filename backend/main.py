import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.routes import conversations, llm, auth
from app.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LLM-mini API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8081"],  # Allow frontend ports
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=3600,  # CORS preflight 캐시 시간 설정
)

# Global OPTIONS handler for all routes
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """모든 경로에 대한 OPTIONS 요청 처리"""
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
# messages router 제거됨 - conversations에서 처리
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
# WebSocket 제거됨 - SSE 방식 사용

@app.get("/")
def read_root():
    return {"message": "Welcome to LLM-mini API"}

from app.utils.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True) 