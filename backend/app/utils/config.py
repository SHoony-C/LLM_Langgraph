import os
from dotenv import load_dotenv  

# Load environment variables
load_dotenv()  # 주석 처리

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# OpenAI API 설정 상태 확인
def check_openai_config():
    """OpenAI API 설정 상태를 확인하는 함수"""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "aaa":
        print("⚠️  [CONFIG] OpenAI API 키가 설정되지 않았습니다.")
        print("   환경변수 OPENAI_API_KEY를 설정하거나 .env 파일에 추가해주세요.")
        return False
    
    if not OPENAI_BASE_URL or OPENAI_BASE_URL == "aaa":
        print("⚠️  [CONFIG] OpenAI Base URL이 설정되지 않았습니다.")
        print("   환경변수 OPENAI_BASE_URL을 설정하거나 .env 파일에 추가해주세요.")
        return False
    
    print(f"✅ [CONFIG] OpenAI API 설정 확인됨")
    print(f"   Base URL: {OPENAI_BASE_URL}")
    print(f"   API Key: {'설정됨' if OPENAI_API_KEY else '미설정'}")
    return True

# 설정 상태 확인
IS_OPENAI_CONFIGURED = check_openai_config()

IMAGE_BASE_URL = "https://10.172.107.182"
IMAGE_PATH_PREFIX = "/imageview"


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
ACCESS_TOKEN_EXPIRE_MINUTES = 300


# Vector Database Configuration
QDRANT_HOST = "localhost"  # 프로토콜 제거 - QdrantClient host 파라미터는 호스트명만 필요
QDRANT_PORT = 6333
QDRANT_COLLECTION = "RC"


# Server Configuration
HOST = "0.0.0.0"
PORT = 8000

# OAuth/IDP Configuration
IDP_Config = {
    'ClientId': '844891853332-s785qgm7br1io04pbvtpsic4kqce8d7o.apps.googleusercontent.com',  # Google OAuth Client ID
    'RedirectUri': 'http://localhost:8000/api/auth/acs',  # Callback URL
    'AuthorizeUrl': 'https://accounts.google.com/o/oauth2/v2/auth',
    'CertFile_Path': '../certificates/',  # Directory where certificates are stored
    'CertFile_Name': 'public_key.pem',  # Public key file name for JWT verification
    'Frontend_Redirect_Uri': 'http://localhost:8000',  # Frontend URL to redirect after auth
    'Scopes': 'openid profile email',  # OAuth scopes (email 추가)
    'ResponseType': 'code id_token',  # OAuth response type (implicit flow with id_token only)
    'UsePublicClient': True,  # Set to True for public client (no client secret)
} 
