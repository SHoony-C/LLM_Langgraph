from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.responses import RedirectResponse
from typing import Dict, Any, Optional
import uuid
from jose import jwt
import json
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from sqlalchemy.orm import Session
from models.user_models import User
from db_config import get_db, MYSQL_SETTINGS
from pydantic import BaseModel
import config
import httpx
import secrets
import urllib.parse
import traceback
import hashlib

# 액세스 토큰 만료 시간 (분)
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 비밀번호 해싱 함수
def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 액세스 토큰 생성 함수
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.AUTH_SETTINGS['SECRET_KEY'], algorithm=config.AUTH_SETTINGS['ALGORITHM'])
    return encoded_jwt

# SSO 모델 (ID 토큰 등을 위한 모델)
class SSOModel(BaseModel):
    id_token: str = None

# 사용자 정보 매핑 클래스
class UserMap:
    def __init__(self, **kwargs):
        self.username = kwargs.get('name', kwargs.get('preferred_username', ''))
        self.mail = kwargs.get('email', '')
        # loginid 필드 제거
        # 추가 필드가 필요하면 여기에 추가

router = APIRouter()

@router.get("/google/login")
async def google_login():
    """Redirect to Google authentication"""
    try:
        # 디버깅을 위한 로그 추가
        print("\n===== Google OAuth 로그인 시작 =====\n")
        
        # config.py에서 클라이언트 ID 사용
        client_id = config.IDP_Config['ClientId']
        redirect_uri = config.IDP_Config['RedirectUri']  # /api/auth/acs를 리다이렉트 URI로 사용
        response_type = config.IDP_Config['ResponseType']
        scopes = config.IDP_Config['Scopes']
        
        # OAuth 세부 정보 출력
        print(f"클라이언트 ID: {client_id}")
        print(f"리디렉션 URI: {redirect_uri}")
        print(f"응답 타입: {response_type}")
        print(f"스코프: {scopes}")
        print(f"IDP 설정: {config.IDP_Config}")
        
        # nonce와 state 생성 (보안을 위해)
        nonce = secrets.token_hex(16)
        state = secrets.token_hex(16)
        
        # Google OAuth 매개변수
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": response_type,  # "id_token token" 사용
            "scope": scopes,
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",  # 항상 계정 선택 화면 표시
            "include_granted_scopes": "true"  # 이전에 승인된 권한도 포함
        }
        
        # URL 생성 - AuthorizeUrl 사용
        auth_url = f"{config.IDP_Config['AuthorizeUrl']}?{urllib.parse.urlencode(params)}"
        print(f"OAuth 인증 URL: {auth_url}")
        
        print("===== OAuth 로그인 리다이렉트 =====\n")
        return RedirectResponse(url=auth_url)
    except Exception as e:
        print(f"로그인 리다이렉트 오류: {str(e)}")
        print(traceback.format_exc())
        return {"error": str(e)}

# 복호화 및 사용자 인증
@router.post('/acs')
@router.get('/acs')
async def acs(request: Request, form_data: SSOModel = None):
    print('\n===== ACS 엔드포인트 진입 =====\n')
    print(f"Request method: {request.method}")
    
    # 요청 정보 출력 (디버깅용)
    print(f"Request URL: {request.url}")
    print(f"Query params: {request.query_params}")
    print(f"Headers: {request.headers}")
    
    # GET 요청 처리 (Google OAuth 암시적 흐름)
    if request.method == "GET":
        try:
            print("GET 요청 처리: OAuth 암시적 흐름 처리 시작")
            
            # URL 파라미터에서 토큰 추출 시도
            # (주: URL 해시 #는 서버로 전송되지 않아 여기서 접근 불가)
            state = request.query_params.get('state', '')
            error = request.query_params.get('error', '')
            
            print(f"URL 파라미터: state={state}, error={error}")
            
            # 오류가 있는 경우 오류 페이지로 리다이렉트
            if error:
                front_url = config.IDP_Config['Frontend_Redirect_Uri']
                error_redirect = f"{front_url}?error={error}"
                print(f"오류 발생, 리다이렉트: {error_redirect}")
                return RedirectResponse(
                    url=error_redirect,
                    status_code=303
                )
            
            # URL 해시(#)의 토큰을 프론트엔드로 전달하기 위한 HTML 페이지 반환
            # 클라이언트 측에서 URL 해시 파라미터를 추출하고 프론트엔드로 리다이렉트
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth 인증 처리</title>
                <script>
                    // 페이지 로드 시 URL 해시에서 토큰 추출
                    window.onload = function() {
                        console.log('토큰 추출 스크립트 실행');
                        
                        // URL 해시가 있는 경우
                        if (window.location.hash) {
                            console.log('URL 해시 발견:', window.location.hash);
                            
                            // 해시(#) 부분에서 id_token과 access_token 추출
                            const fragment = window.location.hash.substring(1);
                            const params = new URLSearchParams(fragment);
                            
                            const id_token = params.get('id_token');
                            const access_token = params.get('access_token');
                            const token_type = params.get('token_type');
                            
                            console.log('추출된 토큰:', 
                                id_token ? 'ID 토큰 있음' : 'ID 토큰 없음', 
                                access_token ? 'Access 토큰 있음' : 'Access 토큰 없음'
                            );
                            
                            // 토큰이 있는 경우 프론트엔드로 리다이렉트
                            if (id_token || access_token) {
                                // 방법 1: 토큰을 쿼리 파라미터로 전달 (# 대신 ?로)
                                const redirectUrl = '""" + config.IDP_Config['Frontend_Redirect_Uri'] + """';
                                const tokenParams = [];
                                
                                if (id_token) {
                                    tokenParams.push('id_token=' + encodeURIComponent(id_token));
                                }
                                if (access_token) {
                                    tokenParams.push('access_token=' + encodeURIComponent(access_token));
                                }
                                if (token_type) {
                                    tokenParams.push('token_type=' + encodeURIComponent(token_type));
                                }
                                
                                const finalUrl = redirectUrl + '?' + tokenParams.join('&');
                                console.log('리다이렉트 URL:', finalUrl);
                                window.location.href = finalUrl;
                            } else {
                                // 토큰이 없는 경우 오류 메시지와 함께 리다이렉트
                                window.location.href = '""" + config.IDP_Config['Frontend_Redirect_Uri'] + """?error=no_token&message=토큰을 찾을 수 없습니다';
                            }
                        } else {
                            console.log('URL 해시 없음');
                            // 해시가 없는 경우 오류 메시지와 함께 리다이렉트
                            window.location.href = '""" + config.IDP_Config['Frontend_Redirect_Uri'] + """?error=no_hash&message=인증 응답에 토큰이 없습니다';
                        }
                    };
                </script>
            </head>
            <body>
                <h2>인증 처리 중...</h2>
                <p>잠시만 기다려주세요. 자동으로 리다이렉트됩니다.</p>
            </body>
            </html>
            """
            
            return Response(content=html_content, media_type="text/html")
            
        except Exception as e:
            print(f"GET 요청 처리 오류: {str(e)}")
            print(traceback.format_exc())
            return RedirectResponse(
                url=f"{config.IDP_Config['Frontend_Redirect_Uri']}?error=Authentication+failed&msg={str(e)}", 
                status_code=303
            )
    
    # POST 요청 처리 로직
    if form_data is None:
        # form_data가 없는 경우 요청 본문에서 직접 id_token 추출 시도
        try:
            # JSON 형식으로 전송된 경우
            try:
                body = await request.json()
                id_token_val = body.get('id_token')
            except:
                # URL 인코딩 형식으로 전송된 경우
                body = await request.form()
                id_token_val = body.get('id_token')
            
            if not id_token_val:
                # Content-Type: application/x-www-form-urlencoded 형식으로 전송된 경우
                body_text = await request.body()
                body_params = dict(param.split('=') for param in body_text.decode('utf-8').split('&'))
                id_token_val = body_params.get('id_token')
            
            if not id_token_val:
                raise HTTPException(status_code=400, detail="id_token field is required")
                
            # 여기에서 SSOModel 형식으로 데이터 구성
            form_data = SSOModel(id_token=id_token_val)
        except Exception as e:
            print(f"POST 요청 처리 오류: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
    
    isLoad = False
    isError = False
    Error_MSG = ''
    claim_val = ''

    try:
        # 공개키 로드
        try:
            with open(config.IDP_Config['CertFile_Path'] + config.IDP_Config['CertFile_Name'], "rb") as f:
                public_key = serialization.load_pem_public_key(f.read())
        except FileNotFoundError:
            print("Warning: Certificate file not found. Using JWT without verification for development purposes.")
            # 개발 환경에서 임시로 처리 (토큰 검증 없이)
            id_token_val = form_data.id_token
            
            # JWT 토큰 분석 (검증 없이)
            decoded_token = jwt.decode(
                id_token_val, 
                "", 
                options={
                    "verify_signature": False,
                    "verify_aud": False, 
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_iss": False
                }
            )
            
            # 사용자 정보 생성 (개발 환경용)
            user_info = UserMap(**decoded_token)
            username = user_info.username
            mail = user_info.mail or f"{username}@example.com"
            
            # 데이터베이스 사용자 생성 또는 조회
            db = next(get_db())
            db_user = db.query(User).filter(User.username == username).first()
            
            if not db_user:
                # 새 사용자 생성
                hashed_password = get_password_hash(str(uuid.uuid4()))
                
                # 이메일 도메인을 기반으로 permission 설정
                permission = "user"  # 기본값
                if mail and '@' in mail:
                    domain = mail.split('@')[1].lower()
                    # 관리자로 지정할 도메인 목록
                    admin_domains = config.ADMIN_DOMAINS if hasattr(config, 'ADMIN_DOMAINS') else ["admin.com", "admin.org"]
                    if domain in admin_domains:
                        permission = "admin"
                        print(f"관리자 권한 부여: {mail} (도메인: {domain})")
                
                db_user = User(
                    username=username,
                    email=mail,
                    hashed_password=hashed_password,
                    permission=permission
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                print(f"사용자 등록 완료: ID={db_user.id}, 권한={permission}")
            else:
                # 기존 사용자 로그인 시 정보 업데이트
                if mail and db_user.email != mail:
                    db_user.email = mail
                    db.commit()
                    db.refresh(db_user)
            
            # JWT 토큰 생성
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": str(db_user.id)}, 
                expires_delta=access_token_expires
            )
            
            # 프론트엔드로 리다이렉트 (토큰 포함)
            redirect_url = f"{config.IDP_Config['Frontend_Redirect_Uri']}?token={access_token}&user={db_user.username}"
            return RedirectResponse(url=redirect_url, status_code=303)
        
        # 아래는 인증서가 있는 경우 실행됨
        id_token_val = form_data.id_token
        b_token = id_token_val.encode()

        header = jwt.get_unverified_header(b_token)
        print(f"JWT Header: {header}")

        # JWT 토큰 디코딩
        decode = jwt.decode(
            jwt=b_token, 
            key=public_key, 
            verify=True, 
            algorithms='RS256', 
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_nbf': False,
                'verify_aud': False,
                "verify_iat": False,
                "verify_iss": False
            }
        )
        
        json_str = json.dumps(decode)
        claim_val = json.loads(json_str)
        
        # 사용자 정보 추출 및 매핑
        user_info = UserMap(**claim_val)
        username = user_info.username
        mail = user_info.mail or f"{username}@example.com"
        
        # 기존 사용자 확인 또는 생성
        db = next(get_db())
        db_user = db.query(User).filter(User.username == username).first()
        
        if not db_user:
            # 새 사용자 생성
            hashed_password = get_password_hash(str(uuid.uuid4()))
            
            # 이메일 도메인을 기반으로 permission 설정
            permission = "user"  # 기본값
            if mail and '@' in mail:
                domain = mail.split('@')[1].lower()
                # 관리자로 지정할 도메인 목록
                admin_domains = config.ADMIN_DOMAINS if hasattr(config, 'ADMIN_DOMAINS') else ["admin.com", "admin.org"]
                if domain in admin_domains:
                    permission = "admin"
                    print(f"관리자 권한 부여: {mail} (도메인: {domain})")
            
            db_user = User(
                username=username,
                email=mail,
                hashed_password=hashed_password,
                permission=permission
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            print(f"사용자 등록 완료: ID={db_user.id}, 권한={permission}")
        else:
            # 기존 사용자 로그인 시 정보 업데이트
            if mail and db_user.email != mail:
                db_user.email = mail
                db.commit()
            
            # 기존 사용자 확인: ID=user.id
            print(f"기존 사용자 확인: ID={db_user.id}")
            # 기존 사용자 정보 업데이트 (loginid 제거)
            # 필요한 경우 다른 필드 업데이트
            if username and db_user.username != username:
                db_user.username = username
                db.commit()
        
        # JWT 토큰 생성
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(db_user.id)}, 
            expires_delta=access_token_expires
        )
        
        # 프론트엔드로 리다이렉트 (토큰 포함)
        redirect_url = f"{config.IDP_Config['Frontend_Redirect_Uri']}?token={access_token}&user={db_user.username}"
        return RedirectResponse(url=redirect_url, status_code=303)
        
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return RedirectResponse(
            url=f"{config.IDP_Config['Frontend_Redirect_Uri']}login?error=Authentication+failed", 
            status_code=303
        )

@router.get('/slo')
async def slo():
    """Sign out from SSO"""
    # Instead of redirecting to Google's logout URL which causes CORS errors
    # Return a success response that the frontend can handle
    return {"status": "success", "message": "Successfully logged out"}

@router.get("/check-auth")
async def check_auth(id_token: str = None, access_token: str = None, token: str = None, db: Session = Depends(get_db)):
    """Validate authentication token"""
    print("\n===== 토큰 검증 시작 =====")
    print(f"요청 파라미터: token={token is not None}, id_token={id_token is not None}, access_token={access_token is not None}")
    
    # 우선순위: ID 토큰 > 액세스 토큰 > JWT 토큰
    if not token and not id_token and not access_token:
        print("토큰 없음, 인증 실패")
        return {"authenticated": False}
    
    token_type = "unknown"
    
    try:
        print(f"토큰 검증 시도: JWT={token is not None}, ID={id_token is not None}, 액세스={access_token is not None}")
        
        # ID 토큰 처리 (Google OAuth에서 제공)
        if id_token:
            token_type = "id_token"
            print(f"ID 토큰 검증 시도: {id_token[:20]}...")
            
            try:
                # ID 토큰 디코딩 (서명 검증 없이)
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
                        "verify_at_hash": False  # at_hash 검증 비활성화
                    }
                )
                
                print(f"ID 토큰 디코딩 성공: {decoded_token}")
                
                # 사용자 정보 추출
                email = decoded_token.get('email')
                name = decoded_token.get('name', decoded_token.get('given_name', ''))
                sub = decoded_token.get('sub')
                
                if not email:
                    print("ID 토큰에 이메일 정보 없음")
                    return {"authenticated": False}
                
                print(f"ID 토큰에서 사용자 정보 추출: email={email}, name={name}")
                
                # 데이터베이스에서 사용자 조회
                user = db.query(User).filter(User.email == email).first()
                
                # 사용자가 없으면 새로 생성
                if not user:
                    print(f"새 사용자 등록: {email}, {name}")
                    # 임의 비밀번호 생성
                    hashed_password = get_password_hash(str(uuid.uuid4()))
                    
                    # 이메일 도메인을 기반으로 permission 설정
                    permission = "user"  # 기본값
                    if email and '@' in email:
                        domain = email.split('@')[1].lower()
                        # 관리자로 지정할 도메인 목록
                        admin_domains = config.ADMIN_DOMAINS if hasattr(config, 'ADMIN_DOMAINS') else ["admin.com", "admin.org"]
                        if domain in admin_domains:
                            permission = "admin"
                            print(f"관리자 권한 부여: {email} (도메인: {domain})")
                    
                    user = User(
                        username=name or email.split('@')[0],
                        email=email,
                        hashed_password=hashed_password,
                        permission=permission
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    print(f"사용자 등록 완료: ID={user.id}, 권한={permission}")
                else:
                    print(f"기존 사용자 확인: ID={user.id}")
                    # 기존 사용자 정보 업데이트 (loginid 제거)
                    # 필요한 경우 다른 필드 업데이트
                    if name and user.username != name:
                        user.username = name
                        db.commit()
                
                # 사용자 정보 반환
                print(f"ID 토큰 인증 성공, 반환할 사용자 정보: ID={user.id}, 사용자명={user.username}, 권한={user.permission}")
                return {
                    "authenticated": True,
                    "user": {
                        "id": str(user.id),
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.username,
                        "department": None,
                        "permission": user.permission,
                        "is_active": True
                    }
                }
            except Exception as e:
                print(f"ID 토큰 처리 오류: {str(e)}")
                print(traceback.format_exc())
                # 오류가 발생해도 계속 진행 (액세스 토큰 또는 JWT 토큰 시도)
        
        # 액세스 토큰 처리 (Google OAuth에서 제공)
        if access_token:
            token_type = "access_token"
            print(f"액세스 토큰 검증 시도: {access_token[:20]}...")
            
            try:
                # Google API로 사용자 정보 조회
                user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                
                # httpx를 사용하여 동기 요청 수행 (async 함수 내에서 사용 가능)
                async with httpx.AsyncClient() as client:
                    response = await client.get(user_info_url, headers=headers)
                    
                if response.status_code != 200:
                    print(f"Google API 오류: {response.status_code} - {response.text}")
                    # 액세스 토큰이 실패해도 다른 토큰 시도
                else:
                    user_info = response.json()
                    print(f"Google API 응답: {user_info}")
                    
                    email = user_info.get('email')
                    name = user_info.get('name', user_info.get('given_name', ''))
                    sub = user_info.get('sub')
                    
                    if not email:
                        print("액세스 토큰으로 이메일 정보를 가져오지 못함")
                        # 계속 진행 (JWT 토큰 시도)
                    else:
                        print(f"액세스 토큰에서 사용자 정보 추출: email={email}, name={name}")
                        
                        # 데이터베이스에서 사용자 조회
                        user = db.query(User).filter(User.email == email).first()
                        
                        # 사용자가 없으면 새로 생성
                        if not user:
                            print(f"새 사용자 등록: {email}, {name}")
                            # 임의 비밀번호 생성
                            hashed_password = get_password_hash(str(uuid.uuid4()))
                            
                            # 이메일 도메인을 기반으로 permission 설정
                            permission = "user"  # 기본값
                            if email and '@' in email:
                                domain = email.split('@')[1].lower()
                                # 관리자로 지정할 도메인 목록
                                admin_domains = config.ADMIN_DOMAINS if hasattr(config, 'ADMIN_DOMAINS') else ["admin.com", "admin.org"]
                                if domain in admin_domains:
                                    permission = "admin"
                                    print(f"관리자 권한 부여: {email} (도메인: {domain})")
                            
                            user = User(
                                username=name or email.split('@')[0],
                                email=email,
                                hashed_password=hashed_password,
                                permission=permission
                            )
                            db.add(user)
                            db.commit()
                            db.refresh(user)
                            print(f"사용자 등록 완료: ID={user.id}, 권한={permission}")
                        else:
                            print(f"기존 사용자 확인: ID={user.id}")
                            # 기존 사용자 정보 업데이트 (loginid 제거)
                            # 필요한 경우 다른 필드 업데이트
                            if name and user.username != name:
                                user.username = name
                                db.commit()
                        
                        # 사용자 정보 반환
                        print(f"액세스 토큰 인증 성공, 반환할 사용자 정보: ID={user.id}, 사용자명={user.username}, 권한={user.permission}")
                        return {
                            "authenticated": True,
                            "user": {
                                "id": str(user.id),
                                "username": user.username,
                                "email": user.email,
                                "full_name": user.username,
                                "department": None,
                                "permission": user.permission,
                                "is_active": True
                            }
                        }
            except Exception as e:
                print(f"액세스 토큰 처리 오류: {str(e)}")
                print(traceback.format_exc())
                # 오류가 발생해도 계속 진행 (JWT 토큰 시도)
        
        # JWT 토큰 검증 (기존 로직)
        if token:
            token_type = "jwt"
            print(f"JWT 토큰 검증 시도: {token[:20]}...")
            
            try:
                # 먼저 JWT가 Google ID 토큰인지 확인
                header = jwt.get_unverified_header(token)
                print(f"JWT 헤더: {header}")
                
                # Google의 RS256 토큰인 경우 ID 토큰과 동일하게 처리
                if header.get('alg') == 'RS256':
                    print("Google RS256 토큰으로 감지됨, ID 토큰 처리 방식으로 검증")
                    # ID 토큰과 동일한 방식으로 디코딩
                    decoded_token = jwt.decode(
                        token, 
                        "", 
                        options={
                            "verify_signature": False,
                            "verify_aud": False, 
                            "verify_exp": False,
                            "verify_nbf": False,
                            "verify_iat": False,
                            "verify_iss": False,
                            "verify_at_hash": False
                        }
                    )
                    
                    print(f"Google 토큰 디코딩 성공: {decoded_token}")
                    
                    # 사용자 정보 추출
                    email = decoded_token.get('email')
                    name = decoded_token.get('name', decoded_token.get('given_name', ''))
                    sub = decoded_token.get('sub')
                    
                    if not email:
                        print("토큰에 이메일 정보 없음")
                        return {"authenticated": False}
                    
                    print(f"토큰에서 사용자 정보 추출: email={email}, name={name}")
                    
                    # 데이터베이스에서 사용자 조회
                    user = db.query(User).filter(User.email == email).first()
                    
                    # 사용자가 없으면 새로 생성
                    if not user:
                        print(f"새 사용자 등록: {email}, {name}")
                        # 임의 비밀번호 생성
                        hashed_password = get_password_hash(str(uuid.uuid4()))
                        
                        # 이메일 도메인을 기반으로 permission 설정
                        permission = "user"  # 기본값
                        if email and '@' in email:
                            domain = email.split('@')[1].lower()
                            # 관리자로 지정할 도메인 목록
                            admin_domains = config.ADMIN_DOMAINS if hasattr(config, 'ADMIN_DOMAINS') else ["admin.com", "admin.org"]
                            if domain in admin_domains:
                                permission = "admin"
                                print(f"관리자 권한 부여: {email} (도메인: {domain})")
                        
                        user = User(
                            username=name or email.split('@')[0],
                            email=email,
                            hashed_password=hashed_password,
                            permission=permission
                        )
                        db.add(user)
                        db.commit()
                        db.refresh(user)
                        print(f"사용자 등록 완료: ID={user.id}, 권한={permission}")
                    else:
                        print(f"기존 사용자 확인: ID={user.id}")
                        # 기존 사용자 정보 업데이트 (loginid 제거)
                        # 필요한 경우 다른 필드 업데이트
                        if name and user.username != name:
                            user.username = name
                            db.commit()
                    
                    # 사용자 정보 반환
                    print(f"Google RS256 토큰 인증 성공, 반환할 사용자 정보: ID={user.id}, 사용자명={user.username}, 권한={user.permission}")
                    return {
                        "authenticated": True,
                        "user": {
                            "id": str(user.id),
                            "username": user.username,
                            "email": user.email,
                            "full_name": user.username,
                            "department": None,
                            "permission": user.permission,
                            "is_active": True
                        }
                    }
                
                # 기존 JWT 토큰 처리 (자체 발급한 HS256 토큰)
                payload = jwt.decode(
                    token,
                    config.AUTH_SETTINGS['SECRET_KEY'],
                    algorithms=[config.AUTH_SETTINGS['ALGORITHM']]
                )
                
                print("JWT 토큰 페이로드:", payload)
                
                # 토큰에서 사용자 ID 가져오기 (sub 필드에 저장됨)
                username = payload.get("sub")
                
                if not username:
                    print("토큰에 사용자 이름 없음")
                    return {"authenticated": False}
                
                # 데이터베이스에서 사용자 정보 가져오기
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    print(f"사용자를 찾을 수 없음: {username}")
                    return {"authenticated": False}
                
                # 사용자 정보 반환
                print(f"JWT 토큰 인증 성공, 반환할 사용자 정보: ID={user.id}, 사용자명={user.username}, 권한={user.permission}")
                return {
                    "authenticated": True,
                    "user": {
                        "id": str(user.id),
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.username,
                        "department": None,
                        "permission": user.permission,
                        "is_active": True
                    }
                }
            except Exception as e:
                print(f"JWT 토큰 검증 오류: {str(e)}")
                print(traceback.format_exc())
                return {"authenticated": False}
        
        # 모든 토큰 검증이 실패한 경우
        print("모든 토큰 검증 실패")
        return {"authenticated": False}
            
    except Exception as e:
        print(f"Check auth error ({token_type}): {str(e)}")
        print(traceback.format_exc())
        return {"authenticated": False} 