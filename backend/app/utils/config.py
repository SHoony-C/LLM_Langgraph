import os
from dotenv import load_dotenv

# Load environment variables
# 프로젝트 루트와 backend 디렉토리에서 .env 파일 찾기
import pathlib
project_root = pathlib.Path(__file__).parent.parent.parent.parent  # 프로젝트 루트
backend_root = pathlib.Path(__file__).parent.parent.parent  # backend 디렉토리

# 여러 위치에서 .env 파일 로드 시도
env_loaded = False
for env_path in [project_root / '.env', backend_root / '.env']:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ [CONFIG] .env 파일 로드됨: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("⚠️ [CONFIG] .env 파일을 찾을 수 없습니다.")
    print(f"📝 [CONFIG] 다음 위치 중 하나에 .env 파일을 생성하세요:")
    print(f"   - {project_root / '.env'}")
    print(f"   - {backend_root / '.env'}")
    load_dotenv()  # 기본 로드

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# OpenAI API 키 확인 및 디버깅
if not OPENAI_API_KEY:
    print("⚠️ [CONFIG] OPENAI_API_KEY가 설정되지 않았습니다!")
    print("📝 [CONFIG] .env 파일에 다음과 같이 설정하세요:")
    print("   OPENAI_API_KEY=your-actual-openai-api-key")
    print("🔍 [CONFIG] 현재 .env 파일 위치를 확인하세요.")
else:
    print(f"✅ [CONFIG] OpenAI API Key 설정됨: {OPENAI_API_KEY[:10]}...{OPENAI_API_KEY[-4:]}")  
CUSTOM_LLAMA_API_KEY = ""
CUSTOM_LLAMA_API_ENDPOINT = ""
CUSTOM_LLAMA_API_BASE = ""

# Database Configuration
DATABASE_URL = "sqlite:///./app.db"

# MySQL Database Configuration (if using MySQL)
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "asdd*963"
DB_NAME = "llm_mini"

# Build MySQL DATABASE_URL if MySQL is configured
if all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# JWT Configuration
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Redis Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_CHANNEL = "langgraph_node_status"

# Vector Database Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "ppt_parsed"

# Image URL Configuration
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "https://your-image-server.com")
IMAGE_PATH_PREFIX = os.getenv("IMAGE_PATH_PREFIX", "/analysis")


# Server Configuration
HOST = "0.0.0.0"
PORT = 8000

# OAuth/IDP Configuration
IDP_Config = {
    'ClientId': '844891853332-s785qgm7br1io04pbvtpsic4kqce8d7o.apps.googleusercontent.com',  # Google OAuth Client ID
    'RedirectUri': 'http://localhost:8000/api/auth/acs',  # Callback URL
    'AuthorizeUrl': 'https://accounts.google.com/o/oauth2/v2/auth',  # Google OAuth endpoint (초기 로그인에만 사용)
    'CertFile_Path': './certificates/',  # Directory where certificates are stored
    'CertFile_Name': 'public_key.pem',  # Public key file name for JWT verification
    'Frontend_Redirect_Uri': 'http://localhost:8080/',  # Frontend URL to redirect after auth
    'Scopes': 'openid email profile',  # OAuth scopes
    'ResponseType': 'id_token',  # OAuth response type (implicit flow with id_token only)
    'UsePublicClient': True,  # Set to True for public client (no client secret)
} 