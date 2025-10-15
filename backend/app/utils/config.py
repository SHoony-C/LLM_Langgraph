import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  
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


# Server Configuration
HOST = "0.0.0.0"
PORT = 8001

# OAuth/IDP Configuration
IDP_Config = {
    'ClientId': '844891853332-s785qgm7br1io04pbvtpsic4kqce8d7o.apps.googleusercontent.com',  # Google OAuth Client ID
    'RedirectUri': 'http://localhost:8001/api/auth/acs',  # Callback URL
    'AuthorizeUrl': 'https://accounts.google.com/o/oauth2/v2/auth',  # Google OAuth endpoint (초기 로그인에만 사용)
    'CertFile_Path': './certificates/',  # Directory where certificates are stored
    'CertFile_Name': 'public_key.pem',  # Public key file name for JWT verification
    'Frontend_Redirect_Uri': 'http://localhost:8081/',  # Frontend URL to redirect after auth
    'Scopes': 'openid email profile',  # OAuth scopes
    'ResponseType': 'id_token',  # OAuth response type (implicit flow with id_token only)
    'UsePublicClient': True,  # Set to True for public client (no client secret)
} 