from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    mail = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    loginid = Column(String(100), nullable=True)  # Add loginid field for SSO users
    deptname = Column(String(100), nullable=True)  # Add deptname field for department name
    
    # 관계 정의
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)  # 대화 제목
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False)  # 논리적 삭제 플래그
    
    # 사용자 관계 추가
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="conversations")
    
    # 기존 관계
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(Enum("user", "assistant", name="role_enum"))
    user_name = Column(String(45), nullable=True)
    question = Column(Text, nullable=False)
    ans = Column(Text, nullable=True)
    q_mode = Column(Enum("search", "add", name="q_mode_enum"), nullable=True)  # 질문 모드: search(검색) 또는 add(추가질문)
    keyword = Column(Text, nullable=True)  # 키워드 정보 저장
    db_search_title = Column(Text, nullable=True)  # 랭체인에서 찾은 문서 타이틀 저장
    image = Column(Text, nullable=True)  # 이미지 URL 저장
    feedback = Column(Enum("positive", "negative", name="feedback_enum"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Define relationship with Conversation
    conversation = relationship("Conversation", back_populates="messages") 
