import os
from dotenv import load_dotenv  

# Load environment variables
load_dotenv()  # 주석 처리

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "aaa")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "aaa")

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
QDRANT_HOST = "10.172.107.182"
QDRANT_PORT = 8001
QDRANT_COLLECTION = "RC"


# Server Configuration
HOST = "0.0.0.0"
PORT = 8000

# OAuth/IDP Configuration
IDP_Config = {
    'ClientId': '2818c60e-bf0a-42f2-9b9b-d6ab18063844',  
    'RedirectUri': 'https://10.172.117.173/api/auth/acs',  # Callback URL
    'AuthorizeUrl': 'https://stsds.secsso.net/adfs/oauth2/authorize/',  
    'CertFile_Path': '../certificates/',  # Directory where certificates are stored
    'CertFile_Name': 'public_key.pem',  # Public key file name for JWT verification
    'Frontend_Redirect_Uri': 'https://Report-Collection',  # Frontend URL to redirect after auth
    'Scopes': 'openid profile',  # OAuth scopes
    'ResponseType': 'code id_token',  # OAuth response type (implicit flow with id_token only)
    'UsePublicClient': True,  # Set to True for public client (no client secret)
} 
