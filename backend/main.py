import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.routes import conversations, normal_llm, langgraph, auth
from app.database import Base, engine
from fastapi.staticfiles import StaticFiles


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LLM-mini API",
    version="1.0.0",
    openapi_url="/api/openapi.json",  # ★ 핵심: /api로 고정
    # redoc_url="/redoc",
    # swagger_ui_parameters={"docExpansion": "full"}
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080", 
        "http://127.0.0.1:8080", 
        "http://localhost:8000", 
        "http://127.0.0.1:8000", 
        "http://report-collection:8080",
        "https://10.172.117.173"
    ],  # Allow frontend ports
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],  # 모든 HTTP 메서드 허용
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],  # 필요한 헤더들 명시적으로 허용
    expose_headers=["*"],  # Expose all headers
    max_age=3600,  # CORS preflight 캐시 시간 설정
)


# Global OPTIONS handler for all routes
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """모든 경로에 대한 OPTIONS 요청 처리"""
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:8080", 
        "http://127.0.0.1:8080", 
        "http://localhost:8000", 
        "http://127.0.0.1:8000"
    ]
    
    response = Response()
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8080"
    
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
# messages router 제거됨 - conversations에서 처리
app.include_router(normal_llm.router, prefix="/api/normal_llm", tags=["normal_llm"])
app.include_router(langgraph.router, prefix="/api/langgraph", tags=["langgraph"])


@app.get("/")
def read_root():
    return {"message": "Welcome to LLM-mini API"}

from app.utils.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True) 
