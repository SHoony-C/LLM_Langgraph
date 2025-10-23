from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import timedelta
import uuid
import json
import secrets
import urllib.parse
from jose import jwt, JWTError
from starlette.datastructures import Headers

from urllib.parse import urlsplit, urlunsplit, parse_qs, unquote_plus
from html import escape
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.hazmat.backends import default_backend
# httpx 제거 - 더 이상 samsung API 호출하지 않음

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
import time, os
from typing import Optional, Tuple, Any, Dict


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
        deptname=user_data.deptname,
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
                dept_name = decoded_token.get('deptname')
                
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
                        loginid=loginid,
                        deptname = deptname 
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
SESSION_COOKIE_NAME = "llm_mini"
SESSION_SIGN_SECRET = os.getenv("SESSION_SIGN_SECRET", "aaaaa")

# 교환 토큰(초단기, 1회성) – IP 콜백 → 도메인으로 권한 이관
EXCHANGE_SIGN_SECRET = os.getenv("EXCHANGE_SIGN_SECRET", "bbbbbb")
EXCHANGE_TTL_SEC = int(os.getenv("EXCHANGE_TTL_SEC", "60"))  # 60초

# 교환 이후 최종 쿠키를 심을 퍼블릭 베이스 URL
# 운영 값 예: https://report-collection
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

# =========================
# 유틸: 세션/교환 토큰
# =========================
def _mint_session_jwt(db_user: User | Any) -> str:
    now = int(time.time())
    payload = {
        "username": db_user.username,
        "mail": getattr(db_user, "mail", "") or "",
        "loginid": getattr(db_user, "loginid", "") or "",
        "deptname": getattr(db_user, "deptname", "") or "",
        "iat": now,
        "exp": now + 60 * 60 * 8,  # 8h
    }
    return jwt.encode(payload, SESSION_SIGN_SECRET, algorithm="HS256")


def _mint_exchange_jwt(db_user: User | Any) -> str:
    now = int(time.time())
    payload = {
        "sub": getattr(db_user, "loginid", "") or getattr(db_user, "username", ""),
        "uid": getattr(db_user, "id", None),
        "u": db_user.username,
        "m": getattr(db_user, "mail", "") or "",
        "deptname": getattr(db_user, "deptname", "") or "",
        "iat": now,
        "exp": now + EXCHANGE_TTL_SEC,
        "typ": "session_exchange",
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, EXCHANGE_SIGN_SECRET, algorithm="HS256")


def _decode_exchange_jwt(token: str) -> dict:
    return jwt.decode(
        token,
        EXCHANGE_SIGN_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


# =========================
# Bearer 추출(+ /me 유틸)
# =========================
def _extract_bearer_token(headers: Headers) -> Optional[str]:
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth:
        return None
    parts = auth.strip().split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0], parts[1]
    if scheme.lower() != "bearer":
        return None
    return token


def _resolve_current_user_from_request(request: Request, db: Session) -> User:
    """
    우선순위:
      1) 세션 쿠키(SESSION_COOKIE_NAME = llm_mini)
      2) Authorization: Bearer {token} (기존 access_token 경로)
    둘 중 하나 성공 시 DB 사용자 반환, 아니면 401
    """
    print(f"[AUTH] 사용자 인증 시도 시작")
    
    # 1) 세션 쿠키
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie:
        print(f"[AUTH] 세션 쿠키 발견: {SESSION_COOKIE_NAME}")
        try:
            data = jwt.decode(cookie, SESSION_SIGN_SECRET, algorithms=["HS256"], options={"verify_aud": False})
            username = data.get("username")
            loginid = data.get("loginid")
            deptname = data.get("deptname")
            print(f"[AUTH] 쿠키 데이터: username={username}, loginid={loginid}, deptname={deptname}")
            
            user = None
            if loginid:
                user = db.query(User).filter(User.loginid == loginid).first()
                print(f"[AUTH] loginid로 사용자 검색 결과: {user is not None}")
            if not user and username:
                user = db.query(User).filter(User.username == username).first()
                print(f"[AUTH] username으로 사용자 검색 결과: {user is not None}")
            if not user and deptname:
                user = db.query(User).filter(User.deptname == deptname).first()
                print(f"[AUTH] deptname으로 사용자 검색 결과: {user is not None}")
            if user:
                print(f"[AUTH] 세션 쿠키로 사용자 인증 성공: {user.username}")
                return user
        except JWTError as e:
            print(f"[AUTH] 세션 쿠키 JWT 디코딩 실패: {str(e)}")
            pass  # 쿠키가 깨졌으면 Bearer 시도
        except Exception as e:
            print(f"[AUTH] 세션 쿠키 처리 중 예상치 못한 오류: {str(e)}")
            pass

    # 2) Bearer
    bearer = _extract_bearer_token(request.headers)
    if bearer:
        print(f"[AUTH] Bearer 토큰 발견")
        try:
            # 서명검증없이 sub만 뽑아 DB 조회(기존 access_token 호환 목적)
            payload = jwt.get_unverified_claims(bearer)
            sub = payload.get("sub")
            print(f"[AUTH] Bearer 토큰 sub: {sub}")
            if sub:
                user = db.query(User).filter(User.username == sub).first()
                if user:
                    print(f"[AUTH] Bearer 토큰으로 사용자 인증 성공: {user.username}")
                    return user
                else:
                    print(f"[AUTH] Bearer 토큰 sub에 해당하는 사용자 없음: {sub}")
        except Exception as e:
            print(f"[AUTH] Bearer 토큰 처리 중 오류: {str(e)}")
            pass
    else:
        print(f"[AUTH] Bearer 토큰 없음")

    print(f"[AUTH] 모든 인증 방법 실패")
    raise HTTPException(status_code=401, detail="Not authenticated")


# =========================
# 공개 API (/me, /logout)
# =========================
@router.get("/me", response_model=UserSchema)
async def read_users_me(request: Request, db: Session = Depends(get_db)):
    """현재 로그인된 사용자 정보 조회 (세션 쿠키 또는 Bearer 모두 지원)"""
    try:
        user = _resolve_current_user_from_request(request, db)
        return user
    except HTTPException as e:
        # 인증 실패 시 더 자세한 오류 정보 제공
        print(f"[AUTH] /me 엔드포인트 인증 실패: {e.detail}")
        raise e
    except Exception as e:
        # 예상치 못한 오류 처리
        print(f"[AUTH] /me 엔드포인트 예상치 못한 오류: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    """사용자 로그아웃 처리 (stateless)"""
    try:
        resp = JSONResponse({"success": True, "message": "Successfully logged out"})
        resp.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
        return resp
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed")


# =========================
# SSO 시작: IdP Authorize로 이동 (Redirect)
# =========================
@router.get("/auth_sh")
async def auth_sh():
    client_id = config.IDP_Config["ClientId"]
    # RedirectUri는 고정: https://10.172.117.173/api/auth/acs
    redirect_uri = config.IDP_Config["RedirectUri"]
    scopes = config.IDP_Config["Scopes"]

    nonce = secrets.token_hex(16)
    state = secrets.token_hex(16)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "id_token",
        "response_mode": "form_post",
        "scope": scopes,
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
        "access_type": "online",
    }
    auth_url = f"{config.IDP_Config['AuthorizeUrl']}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=303)


# =========================
# 콜백 바디 파서/응답 도우미
# =========================
def _normalize_oauth_params(raw_body: bytes) -> tuple[Optional[str], Optional[str]]:
    if not raw_body:
        return None, None

    text_body = raw_body.decode("utf-8", errors="ignore")

    # 1) urlencoded
    parsed = parse_qs(text_body, keep_blank_values=True)
    id_token = parsed.get("id_token", [None])[0]
    state = parsed.get("state", [None])[0]
    if id_token:
        return id_token, state

    # 2) json
    try:
        json_payload = json.loads(text_body)
        id_token = json_payload.get("id_token")
        state = json_payload.get("state")
        if id_token:
            return id_token, state
    except json.JSONDecodeError:
        pass

    # 3) 수동 파싱
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
    default_origin = config.IDP_Config["Frontend_Redirect_Uri"].rstrip("/")
    response.headers["Access-Control-Allow-Origin"] = origin_header or default_origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response


def _resolve_frontend_redirect(request: Request) -> str:
    configured = config.IDP_Config.get("Frontend_Redirect_Uri") if hasattr(config, "IDP_Config") else None
    if configured:
        parts = list(urlsplit(configured))
        if not parts[0]:
            parts[0] = request.url.scheme
        if not parts[1]:
            host_header = request.headers.get("host")
            if host_header:
                parts[1] = host_header
            else:
                host = request.url.hostname or ""
                port = request.url.port
                parts[1] = f"{host}:{port}" if port else host
        if not parts[2]:
            parts[2] = "/"
        return urlunsplit(parts)
    return str(request.base_url)


# =========================
# id_token → 사용자 upsert 유틸
# =========================
def _extract_user_fields(decoded_token: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    def _clean(v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return str(v)

    # Extract email
    mail_candidates = [
        decoded_token.get("email"),
        decoded_token.get("mail"),
        decoded_token.get("upn"),
        decoded_token.get("preferred_username"),
    ]
    mail = next((m for m in map(_clean, mail_candidates) if m), None)

    # Extract name (username)
    username_candidates = [
        decoded_token.get("name"),
        decoded_token.get("given_name"),
        decoded_token.get("family_name"),
        decoded_token.get("preferred_username"),
        decoded_token.get("loginid")
    ]
    username = next((u for u in map(_clean, username_candidates) if u), None)

    # Extract loginid (sub)
    loginid_candidates = [
        decoded_token.get("sub"),
        decoded_token.get("oid"),
        decoded_token.get("user_id"),
        decoded_token.get("sid"),
        decoded_token.get("id"),
        decoded_token.get("subject"),
    ]
    loginid = next((l for l in map(_clean, loginid_candidates) if l), None)
    deptname = decoded_token.get("deptname")

    print(f'Extracted fields - username: {username}, mail: {mail}, loginid: {loginid}, deptname: {deptname}')

    return username, mail, loginid, deptname


def _upsert_user_from_id_token(db_session: Session, decoded_token: dict) -> User:
    username, mail, loginid, deptname = _extract_user_fields(decoded_token)
    
    # loginid는 필수 (Google OAuth의 경우 sub 필드)
    if not loginid:
        raise HTTPException(status_code=400, detail="Missing loginid (sub field)")
    
    # username이 없으면 email에서 추출하거나 loginid 사용
    if not username:
        if mail and '@' in mail:
            username = mail.split('@')[0]  # email의 @ 앞부분을 username으로 사용
        elif loginid:
            username = loginid
        else:
            raise HTTPException(status_code=400, detail="Cannot determine username")
    
    # email이 없으면 기본값 설정
    if not mail:
        mail = ""

    db_user = db_session.query(User).filter(User.loginid == loginid).first()

    if not db_user:
        # 속성 보조 매칭
        lookup_filters = []
        if mail:
            lookup_filters.append(User.mail == mail)
        if username:
            lookup_filters.append(User.username == username)
        if lookup_filters:
            if len(lookup_filters) == 1:
                db_user = db_session.query(User).filter(lookup_filters[0]).first()
            else:
                db_user = db_session.query(User).filter(or_(*lookup_filters)).first()

    if not db_user:
        hashed_password = get_password_hash(str(uuid.uuid4()))
        db_user = User(username=username, mail=mail, hashed_password=hashed_password, loginid=loginid, deptname=deptname)
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
        if loginid and db_user.loginid != loginid:
            db_user.loginid = loginid
            updated = True
        if deptname and db_user.deptname != deptname:
            db_user.deptname = deptname
            updated = True
        if updated:
            db_session.commit()
            db_session.refresh(db_user)

    return db_user


# =========================
# 교환 엔드포인트: report-collection에서 세션 쿠키를 심는 곳
# =========================
@router.get("/exchange")
async def exchange(request: Request):
    print(f"[EXCHANGE] Exchange endpoint called with request: {request.url}")
    x = request.query_params.get("x")
    if not x:
        print("[EXCHANGE] Missing exchange token")
        raise HTTPException(status_code=400, detail="missing exchange token")
    try:
        payload = _decode_exchange_jwt(x)
        print(f"[EXCHANGE] Successfully decoded exchange token: {payload}")
    except JWTError as e:
        print(f"[EXCHANGE] Failed to decode exchange token: {e}")
        raise HTTPException(status_code=401, detail=f"invalid exchange: {e}")

    # 교환 페이로드 → 임시 사용자
    class TempUser:
        pass

    tmp = TempUser()
    tmp.username = payload.get("u")
    tmp.loginid  = payload.get("sub")
    tmp.mail     = payload.get("m", "")
    tmp.deptname     = payload.get("deptname", "")
    # print(f'''부서 : {tmp.deptname}''')

    if not tmp.username or not tmp.loginid:
        raise HTTPException(status_code=401, detail="invalid exchange payload")

    # 1) 최종 세션(httponly) 쿠키
    session_jwt = _mint_session_jwt(tmp)

    # 2) FE가 요구하는 'JWT access_token' 실제 발급
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": tmp.username},
        expires_delta=access_token_expires
    )

    # user_info는 /me로 보강 예정
    user_json = json.dumps({
        "username": tmp.username,
        "mail": tmp.mail,
        "loginid": tmp.loginid,
        "deptname": tmp.deptname,
        "userid": payload.get("uid")  # exchange 토큰에서 uid 사용
    }, ensure_ascii=False)

    # 3) 직접 프론트엔드로 리다이렉트하면서 쿠키 설정
    redirect_response = RedirectResponse(url="http://localhost:8080/", status_code=302)

    # 세션 쿠키(인증용, HttpOnly) - 백엔드 도메인용
    redirect_response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_jwt,
        httponly=True,
        secure=False,  # localhost에서는 false
        samesite="lax",
        max_age=60 * 60 * 8,
        path="/",
        domain="localhost"  # 모든 localhost 서브도메인에서 접근 가능
    )

    # 프론트엔드에서 읽을 수 있는 쿠키들
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,
        secure=False,  # localhost에서는 false
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        domain="localhost"
    )
    
    redirect_response.set_cookie(
        key="user_info",
        value=urllib.parse.quote(user_json),  # URL 인코딩
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        domain="localhost"
    )
    
    redirect_response.set_cookie(
        key="sso_processed",
        value="true",
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=60 * 60,  # 1시간
        path="/",
        domain="localhost"
    )

    return redirect_response
    
    # 대안: 직접 프론트엔드로 리다이렉트 (위의 HTML 방식이 작동하지 않는 경우)
    # redirect_response = RedirectResponse(url="http://localhost:8080/", status_code=302)
    # redirect_response.set_cookie(key=SESSION_COOKIE_NAME, value=session_jwt, httponly=True, secure=True, samesite="lax", max_age=60 * 60 * 8, path="/")
    # redirect_response.set_cookie(key="access_token", value=access_token, httponly=False, secure=True, samesite="lax", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")
    # return redirect_response


# =========================
# ACS: RedirectUri(고정 IP) 콜백
#  - 여기선 세션을 '심지 말고'
#  - report-collection /exchange로 303
# =========================
@router.post("/acs")
@router.get("/acs")
@router.options("/acs")
async def acs(request: Request):
    # Preflight
    if request.method == "OPTIONS":
        resp = Response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE, PATCH"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Max-Age"] = "3600"
        return resp

    # POST: IdP form_post
    if request.method == "POST":
        raw_body = await request.body()
        id_token, state = _normalize_oauth_params(raw_body)
        if not id_token:
            err = JSONResponse({"success": False, "error": "Missing id_token", "state": state}, status_code=400)
            return _apply_cors_headers(err, request)

        # id_token 디코드 + 사용자 upsert
        try:
            decoded_token = jwt.decode(
                id_token,
                "",
                algorithms=["HS256"],  # 서명 미검증 옵션 사용
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_iss": False,
                    "verify_sub": False,
                    "verify_jti": False,
                    "verify_at_hash": False,
                },
            )
            print(f"Decoded JWT token: {decoded_token}")
        except Exception as exc:
            err = JSONResponse({"success": False, "error": "Token decoding failed", "details": str(exc)}, status_code=400)
            return _apply_cors_headers(err, request)

        db_gen = get_db()
        db_session = next(db_gen)
        try:
            db_user = _upsert_user_from_id_token(db_session, decoded_token)
            # ★ ACS에서는 세션 쿠키를 심지 않음 ★
            x = _mint_exchange_jwt(db_user)
            exchange_url = f"{PUBLIC_BASE_URL}/api/auth/exchange?x={urllib.parse.quote(x)}"
            print(f"[ACS] Redirecting to exchange URL: {exchange_url}")
            return RedirectResponse(url=exchange_url, status_code=303)
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    # GET: (드물게) id_token이 쿼리로 오는 경우
    if request.method == "GET":
        try:
            id_token = request.query_params.get("id_token")
            state = request.query_params.get("state")
            error = request.query_params.get("error")

            if error:
                return RedirectResponse(
                    url=f"{config.IDP_Config['Frontend_Redirect_Uri']}?error={error}",
                    status_code=303,
                )

            if id_token and state:
                try:
                    decoded_token = jwt.decode(
                        id_token,
                        "",
                        algorithms=["HS256"],
                        options={
                            "verify_signature": False,
                            "verify_aud": False,
                            "verify_exp": False,
                            "verify_nbf": False,
                            "verify_iat": False,
                            "verify_iss": False,
                            "verify_sub": False,
                            "verify_jti": False,
                            "verify_at_hash": False,
                        },
                    )
                    print(f"Decoded JWT token (GET): {decoded_token}")
                except Exception as exc:
                    return RedirectResponse(
                        url=f"{config.IDP_Config['Frontend_Redirect_Uri']}?error=Token+processing+failed&msg={str(exc)}",
                        status_code=303,
                    )

                db_gen = get_db()
                db_session = next(db_gen)
                try:
                    db_user = _upsert_user_from_id_token(db_session, decoded_token)
                    x = _mint_exchange_jwt(db_user)
                    exchange_url = f"{PUBLIC_BASE_URL}/api/auth/exchange?x={urllib.parse.quote(x)}"
                    print(f"[ACS-GET] Redirecting to exchange URL: {exchange_url}")
                    return RedirectResponse(url=exchange_url, status_code=303)
                finally:
                    try:
                        next(db_gen)
                    except StopIteration:
                        pass

            # 기타: 프론트로 복귀
            return RedirectResponse(url=config.IDP_Config["Frontend_Redirect_Uri"], status_code=303)

        except Exception as e:
            return RedirectResponse(
                url=f"{config.IDP_Config['Frontend_Redirect_Uri']}?error=Authentication+failed&msg={str(e)}",
                status_code=303,
            )

    # 기타 메서드
    return RedirectResponse(url=config.IDP_Config["Frontend_Redirect_Uri"], status_code=303)


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
