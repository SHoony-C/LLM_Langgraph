from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User   
from ..schemas import TokenData

# 설정
SECRET_KEY = "your-super-secret-key-here-make-it-long-and-random-for-production"  # 실제 운영에서는 환경 변수로 처리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240  # 4시간 (4 * 60분)

# 비밀번호 암호화
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db, username, password):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # 알고리즘을 명시적으로 설정
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 토큰을 헤더에서 먼저 시도
    if not token:
        # 헤더에 토큰이 없으면 쿠키에서 시도
        token = request.cookies.get('access_token') or request.cookies.get('auth_token')
    
    if not token:
        print("No token found in headers or cookies")
        raise credentials_exception
    
    # print(f"Token source: {'header' if token == Depends(oauth2_scheme) else 'cookie'}")
    # print(f"Request headers: {dict(request.headers)}")
    # print(f"Request cookies: {dict(request.cookies)}")
    
    try:
        # print(f"Validating token: {token[:20]}...")  # 토큰 앞부분만 로깅
        # print(f"Using algorithm: {ALGORITHM}")
        # print(f"Using secret key: {SECRET_KEY[:10]}...")
        
        # 토큰 헤더 확인 (알고리즘 검증)
        try:
            header = jwt.get_unverified_header(token)
            # print(f"Token header: {header}")
            if header.get('alg') != ALGORITHM:
                print(f"Token algorithm mismatch: expected {ALGORITHM}, got {header.get('alg')}")
                raise credentials_exception
        except Exception as header_error:
            print(f"Error reading token header: {header_error}")
        
        # 토큰 검증 시도
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print(f"Token validation failed: no username in payload")
            raise credentials_exception
        # print(f"Token validation successful for user: {username}")
        token_data = TokenData(username=username)
    except JWTError as e:
        print(f"JWT decode error: {str(e)}")
        print(f"Token: {token[:50]}...")
        print(f"Algorithm: {ALGORITHM}")
        print(f"Secret key length: {len(SECRET_KEY)}")
        raise credentials_exception
    except Exception as e:
        print(f"Unexpected error in token validation: {str(e)}")
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        print(f"User not found in database: {username}")
        raise credentials_exception
    
    # print(f"User authenticated successfully: {username}")
    return user 
