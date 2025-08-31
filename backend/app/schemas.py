from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from fastapi import Form

# 사용자 스키마
class UserBase(BaseModel):
    username: str
    mail: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    # Add loginid field that's optional to maintain backward compatibility
    loginid: Optional[str] = None
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# UserMap for SSO token mapping
class UserMap(BaseModel):
    # Google OAuth에 맞게 필드 매핑
    username: Optional[str] = None  # name 필드로 매핑
    mail: Optional[str] = None  # email 필드로 매핑
    loginid: Optional[str] = None  # sub 필드로 매핑
    picture: Optional[str] = None  # 프로필 이미지 URL
    
    # Google OAuth 추가 필드 - 사용하지 않지만 검증을 통과하기 위해 선언
    at_hash: Optional[str] = None
    aud: Optional[str] = None
    iss: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    nbf: Optional[int] = None
    nonce: Optional[str] = None
    jti: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    azp: Optional[str] = None
    email_verified: Optional[bool] = None
    
    class Config:
        # 추가 필드 허용 (알 수 없는 필드도 처리)
        extra = "ignore"
    
    def __init__(self, **data):
        # Google OAuth 응답 필드 매핑
        if 'name' in data and not data.get('username'):
            data['username'] = data.pop('name')
        if 'email' in data and not data.get('mail'):
            data['mail'] = data.pop('email')
        if 'sub' in data and not data.get('loginid'):
            data['loginid'] = data.pop('sub')
        
        # 특별한 처리가 필요한 필드가 있을 수 있음
        # 여기서는 특별한 처리 없이 모든 필드를 허용
        
        super().__init__(**data)

# SSO Model for OAuth
class SSOModel(BaseModel):
    id_token: str = Form(...)
    code: Optional[str] = Form(None)
    
    @classmethod
    def as_form(cls, id_token: str = Form(...), code: Optional[str] = Form(None)):
        return cls(id_token=id_token, code=code)

# Message schemas
class MessageBase(BaseModel):
    role: str
    user_name: Optional[str] = None
    question: str
    ans: Optional[str] = None
    q_mode: Optional[str] = None  # 질문 모드: search(검색) 또는 add(추가질문)
    keyword: Optional[str] = None  # 키워드 정보
    db_search_title: Optional[str] = None  # 랭체인에서 찾은 문서 타이틀
    feedback: Optional[str] = None

class MessageCreate(BaseModel):
    question: str
    ans: Optional[str] = None  # 답변 필드 추가
    role: Optional[str] = "user"  # 역할 필드 추가
    q_mode: Optional[str] = None  # 질문 모드: search(검색) 또는 add(추가질문)
    assistant_response: Optional[str] = None
    user_name: Optional[str] = None
    keyword: Optional[str] = None  # 키워드 정보
    db_search_title: Optional[str] = None  # 랭체인에서 찾은 문서 타이틀
    skip_llm: Optional[bool] = False  # LLM 재호출 방지 플래그

class Message(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Conversation schemas
class ConversationBase(BaseModel):
    pass

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: int
    created_at: datetime
    messages: List[Message] = []
    
    class Config:
        orm_mode = True

# API request and response schemas
class MessageRequest(BaseModel):
    question: str
    user_name: Optional[str] = None
    skip_llm: Optional[bool] = False  # LLM 재호출 방지 플래그
    assistant_response: Optional[str] = None  # 이미 생성된 답변 (skip_llm이 true일 때 사용)
    q_mode: Optional[str] = None  # 질문 모드: search(검색) 또는 add(추가질문)
    keyword: Optional[str] = None  # 키워드 정보
    db_search_title: Optional[str] = None  # 랭체인에서 찾은 문서 타이틀

class FeedbackRequest(BaseModel):
    feedback: Optional[str]

class MessageResponse(BaseModel):
    userMessage: Message
    assistantMessage: Message
    q_mode: Optional[str] = None  # 질문 모드: search(검색) 또는 add(추가질문)
    keyword: Optional[str] = None  # 키워드 정보
    db_search_title: Optional[str] = None  # 랭체인에서 찾은 문서 타이틀
    
    class Config:
        orm_mode = True 