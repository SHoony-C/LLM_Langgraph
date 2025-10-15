from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid
import json
from urllib.parse import parse_qs, unquote_plus
from jose import jwt
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.hazmat.backends import default_backend
# httpx 제거 - 더 이상 Google API 호출하지 않음
from typing import Optional, Tuple, Any, Dict

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, User as UserSchema, Token, SSOModel, UserMap
from ..utils.auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)
from ..utils import config

router = APIRouter()

@router.post("/register", response_model=UserSchema)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """새 사용자 등록"""
    # 기존 사용자 확인
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_mail = db.query(User).filter(User.mail == user_data.mail).first()
    if db_mail:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 새 사용자 생성
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        mail=user_data.mail,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: Request, db: Session = Depends(get_db)):
    """토큰 갱신"""
    try:
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = auth_header.split(' ')[1]
        
        # 토큰 검증 (만료 여부는 무시)
        try:
            payload = jwt.decode(
                token, 
                config.SECRET_KEY, 
                algorithms=["HS256"],
                options={"verify_exp": False}  # 만료 시간 검증 비활성화
            )
            username = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # 사용자 확인
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # 새 토큰 생성
        access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        print(f"[AUTH] 토큰 갱신 성공: {username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] 토큰 갱신 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/token", response_model=Token)
async def login_for_access_token(request: Request, db: Session = Depends(get_db)):
    """로그인 및 토큰 발급"""
    is_sso = False
    body = {}
    
    try:
        # 요청 본문 가져오기 (JSON 형식)
        try:
            body = await request.json()
            is_sso = body.get('is_sso', False)
        except:
            # JSON이 아닌 경우 form 데이터로 시도
            body = {}
            is_sso = False
        
        # SSO 로그인 처리
        if is_sso:
            id_token_val = body.get('id_token')
            # access_token_val 제거 - 사용하지 않음
            username = body.get('username', '')
            
            if not id_token_val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="id_token is required for SSO authentication"
                )
            
            # JWT 디코딩 (모든 검증 비활성화)
            try:
                decode_options = {
                    "verify_signature": False,
                    "verify_aud": False, 
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_iss": False,
                    "verify_sub": False,
                    "verify_jti": False,
                    "verify_at_hash": False
                }
                
                decoded_token = jwt.decode(id_token_val, "", options=decode_options)
                
                # 사용자 정보 추출
                username = decoded_token.get('name', username)
                mail = decoded_token.get('email', '')
                loginid = decoded_token.get('sub')
                
                if not username:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username is required"
                    )
                
                # 기존 사용자 확인 또는 생성
                db_user = db.query(User).filter(User.username == username).first()
                
                if not db_user:
                    # 새 사용자 생성
                    hashed_password = get_password_hash(str(uuid.uuid4()))  # 임의 비밀번호 생성
                    db_user = User(
                        username=username,
                        mail=mail,
                        hashed_password=hashed_password,
                        loginid=loginid
                    )
                    db.add(db_user)
                    db.commit()
                    db.refresh(db_user)
                else:
                    # 기존 사용자 로그인 시 loginid 업데이트
                    if loginid and db_user.loginid != loginid:
                        db_user.loginid = loginid
                        db.commit()
                        db.refresh(db_user)
                
                # JWT 토큰 생성
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": db_user.username}, 
                    expires_delta=access_token_expires
                )
                
                return {"access_token": access_token, "token_type": "bearer"}
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid SSO token: {str(e)}"
                )
        
        # 일반 로그인 처리
        try:
            form_data = OAuth2PasswordRequestForm(
                username=body.get('username', ''),
                password=body.get('password', '')
            )
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required"
            )
        
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/me", response_model=UserSchema)
async def read_users_me(request: Request, current_user: User = Depends(get_current_user)):
    """현재 로그인된 사용자 정보 조회"""
    return current_user

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """사용자 로그아웃 처리"""
    try:
        print(f"[AUTH] 사용자 로그아웃: {current_user.username}")
        
        # 서버 측에서는 단순히 성공 응답만 반환
        # JWT 토큰은 stateless이므로 서버에서 무효화할 수 없음
        # 클라이언트에서 토큰을 삭제하는 것으로 처리
        
        return {
            "success": True,
            "message": "Successfully logged out",
            "username": current_user.username
        }
    except Exception as e:
        print(f"[AUTH] 로그아웃 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

    # Google OAuth 시작
@router.get('/auth_sh')
async def auth_sh():
    import secrets
    import urllib.parse
    
    client_id = config.IDP_Config['ClientId']
    redirect_uri = config.IDP_Config['RedirectUri']
    scopes = config.IDP_Config['Scopes']
    
    # nonce와 state 생성 (보안을 위해)
    nonce = secrets.token_hex(16)
    state = secrets.token_hex(16)
    
    # Google OAuth 매개변수 (Public Client - Implicit Flow)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "id_token",  # Public Client는 id_token 사용
        "scope": scopes,
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",  # 계정 선택 화면만 표시 (consent보다 가벼움)
        "access_type": "online"  # 온라인 액세스만 요청
    }
    
    # URL 생성 - AuthorizeUrl 사용
    auth_url = f"{config.IDP_Config['AuthorizeUrl']}?{urllib.parse.urlencode(params)}"
    
    return RedirectResponse(url=auth_url)

# 복호화 및 사용자 인증
def _normalize_oauth_params(raw_body: bytes) -> tuple[str | None, str | None]:
    """Extract id_token/state values from a POST body."""

    if not raw_body:
        return None, None

    text_body = raw_body.decode("utf-8", errors="ignore")

    parsed = parse_qs(text_body, keep_blank_values=True)
    id_token = parsed.get("id_token", [None])[0]
    state = parsed.get("state", [None])[0]
    if id_token:
        return id_token, state

    try:
        json_payload = json.loads(text_body)
        id_token = json_payload.get("id_token")
        state = json_payload.get("state")
        if id_token:
            return id_token, state
    except json.JSONDecodeError:
        pass

    manual_params: dict[str, str] = {}
    for pair in text_body.split("&"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            continue
        manual_params[key] = unquote_plus(value)

    return manual_params.get("id_token"), manual_params.get("state")


def _apply_cors_headers(response: Response, request: Request) -> Response:
    origin_header = request.headers.get("Origin")
    default_origin = config.IDP_Config['Frontend_Redirect_Uri'].rstrip("/")
    response.headers["Access-Control-Allow-Origin"] = origin_header or default_origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response


def _build_success_response(request: Request, access_token: str, db_user: User):
    from fastapi.responses import JSONResponse

    response = JSONResponse(
        content={
            "success": True,
            "message": "Authentication successful",
            "access_token": access_token,
            "user": {
                "username": db_user.username,
                "mail": db_user.mail or "",
                "loginid": db_user.loginid or "",
                "userid": db_user.id
            }
        },
        status_code=200
    )

    response = _apply_cors_headers(response, request)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    user_info_cookie = (
        f"username={db_user.username}&mail={db_user.mail or ''}"
        f"&loginid={db_user.loginid or ''}&userid={db_user.id}"
    )
    response.set_cookie(
        key="user_info",
        value=user_info_cookie,
        httponly=False,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return response


def _finalize_db(db_gen, db_session: Session):
    if db_session is None:
        return
    try:
        next(db_gen)
    except StopIteration:
        pass


def _extract_user_fields(decoded_token: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (username, mail, loginid) from an id_token payload."""

    def _clean(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return str(value)

    mail_candidates = [
        decoded_token.get("email"),
        decoded_token.get("mail"),
        decoded_token.get("upn"),
        decoded_token.get("preferred_username"),
    ]
    mail = next((m for m in map(_clean, mail_candidates) if m), None)

    username_candidates = [
        decoded_token.get("name"),
        decoded_token.get("preferred_username"),
        decoded_token.get("unique_name"),
        decoded_token.get("given_name"),
        decoded_token.get("family_name"),
        mail,
    ]

    username = next((u for u in map(_clean, username_candidates) if u), None)

    loginid_candidates = [
        decoded_token.get("sub"),
        decoded_token.get("oid"),
        decoded_token.get("user_id"),
        decoded_token.get("sid"),
        decoded_token.get("id"),
        decoded_token.get("subject"),
        username,
    ]
    loginid = next((l for l in map(_clean, loginid_candidates) if l), None)

    return username, mail, loginid


def _process_id_token(request: Request, id_token: str):
    try:
        decoded_token = jwt.decode(
            id_token,
            "",
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
                "verify_iss": False,
                "verify_sub": False,
                "verify_jti": False,
                "verify_at_hash": False
            }
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        from fastapi.responses import JSONResponse
        error_response = JSONResponse(
            content={
                "success": False,
                "error": "Token decoding failed",
                "details": str(exc)
            },
            status_code=400
        )
        return _apply_cors_headers(error_response, request)

    username, mail, loginid = _extract_user_fields(decoded_token)

    if not username or not loginid:
        from fastapi.responses import JSONResponse
        error_response = JSONResponse(
            content={
                "success": False,
                "error": "Missing user information"
            },
            status_code=400
        )
        return _apply_cors_headers(error_response, request)

    db_gen = get_db()
    db_session = next(db_gen)

    try:
        db_user = db_session.query(User).filter(User.loginid == loginid).first()

        if not db_user:
            hashed_password = get_password_hash(str(uuid.uuid4()))
            db_user = User(
                username=username,
                mail=mail or "",
                hashed_password=hashed_password,
                loginid=loginid
            )
            db_session.add(db_user)
            db_session.commit()
            db_session.refresh(db_user)
        else:
            updated = False
            if mail and db_user.mail != mail:
                db_user.mail = mail
                updated = True
            if username and db_user.username != username:
                db_user.username = username
                updated = True
            if updated:
                db_session.commit()
                db_session.refresh(db_user)

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.username},
            expires_delta=access_token_expires
        )

        return _build_success_response(request, access_token, db_user)
    finally:
        _finalize_db(db_gen, db_session)


@router.post('/acs')
@router.get('/acs')
@router.options('/acs')  # OPTIONS 요청 처리 추가
async def acs(request: Request):
    # OPTIONS 요청 처리 (preflight)
    if request.method == "OPTIONS":
        from fastapi.responses import Response
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"  # 모든 오리진 허용 (개발 환경)
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
    
    # POST 요청 처리 (프론트엔드에서 id_token 전송)
    if request.method == "POST":
        raw_body = await request.body()
        id_token, state = _normalize_oauth_params(raw_body)

        if not id_token:
            from fastapi.responses import JSONResponse
            error_response = JSONResponse(
                content={
                    "success": False,
                    "error": "Missing id_token",
                    "state": state
                },
                status_code=400
            )
            return _apply_cors_headers(error_response, request)

        return _process_id_token(request, id_token)

    # GET 요청 처리 (Google OAuth 콜백)
    if request.method == "GET":
        try:
            # URL 파라미터에서 OAuth 코드 또는 id_token 추출
            code = request.query_params.get('code')
            id_token = request.query_params.get('id_token')  # Implicit Flow에서 직접 받음
            state = request.query_params.get('state')
            error = request.query_params.get('error')
            
            if error:
                print(f"OAuth error received: {error}")
                return RedirectResponse(
                    url=f"{config.IDP_Config['Frontend_Redirect_Uri']}?error={error}",
                    status_code=303
                )
            
            # Implicit Flow: id_token을 직접 받은 경우
            if id_token and state:
                response = _process_id_token(request, id_token)
                return response

            # Authorization Code Flow는 더 이상 사용하지 않음 (Google API 호출 제거)
            elif code and state:
                print("[AUTH] ⚠️ Authorization Code Flow는 지원하지 않습니다. Implicit Flow(id_token)를 사용해주세요.")
                return RedirectResponse(
                    url=f"{config.IDP_Config['Frontend_Redirect_Uri']}?error=Unsupported+flow&msg=Use+implicit+flow+with+id_token",
                    status_code=303
                )
            
            # OAuth 코드가 없는 경우 기본 리다이렉트
            return RedirectResponse(url=config.IDP_Config['Frontend_Redirect_Uri'], status_code=303)
            
        except Exception as e:
            return RedirectResponse(
                url=f"{config.IDP_Config['Frontend_Redirect_Uri']}?error=Authentication+failed&msg={str(e)}", 
                status_code=303
            )
    
    # 기본 응답 (POST나 GET이 아닌 경우)
    return RedirectResponse(url=config.IDP_Config['Frontend_Redirect_Uri'], status_code=303)

# 쿠키에서 토큰 및 사용자 정보 조회
@router.get('/cookie-info')
async def get_cookie_info(request: Request):
    """쿠키에서 토큰 및 사용자 정보를 조회하는 엔드포인트"""
    access_token = request.cookies.get('access_token')
    user_info_cookie = request.cookies.get('user_info')
    
    if not access_token or not user_info_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication cookies found"
        )
    
    try:
        user_info = json.loads(user_info_cookie)
        return {
            "access_token": access_token,
            "user_info": user_info
        }
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user info cookie format"
        )

# 로그아웃
@router.get('/slo')
async def slo():
    idp_url = config.IDP_Config['Idp.SignoutUrl']
    response = RedirectResponse(url=idp_url)
    return response 
