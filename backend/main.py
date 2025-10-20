import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.routes import conversations, llm, auth
from app.database import Base, engine
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LLM-mini API",
    version="1.0.0",
    openapi_url="/api/openapi.json",  # ★ 핵심: /api로 고정
    docs_url=None,
    redoc_url="/redoc",
    swagger_ui_parameters={"docExpansion": "full"}
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8080", "https://report-collection","https://10.172.117.173"],  # Allow frontend ports
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=3600,  # CORS preflight 캐시 시간 설정
)
# 임시 이미지 URL을 위한 static 파일 서빙 추가
app.mount("/api/static", StaticFiles(directory="./static"), name="static")
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="/api/static/swaggers/swagger-ui-bundle.js",
        swagger_css_url="/api/static/swaggers/swagger-ui.css",
        swagger_favicon_url="/api/static/favicon-32x32.png",  # 옵션
        
    )

# Global OPTIONS handler for all routes
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """모든 경로에 대한 OPTIONS 요청 처리"""
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "https://report-collection"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
# messages router 제거됨 - conversations에서 처리
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])


@app.get("/")
def read_root():
    return {"message": "Welcome to LLM-mini API"}

from app.utils.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True) 
