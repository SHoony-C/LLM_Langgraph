from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from ..database import get_db
from ..models import Conversation, Message, User
from ..schemas import Conversation as ConversationSchema
from ..schemas import ConversationCreate, MessageRequest, MessageResponse
from ..utils.auth import get_current_user
from .llm import get_llm_response

router = APIRouter()

# 스트리밍 응답 저장을 위한 클래스 추가
class StreamMessageRequest(MessageRequest):
    assistant_response: Optional[str] = None
    image_url: Optional[str] = None

# 대화 요약 및 아이콘 유형을 가져오는 함수
def get_conversation_summary(conversation, db: Session):
    """대화 내용을 기반으로 요약 및 적절한 아이콘 유형을 생성"""
    
    # 대화가 없거나 메시지가 없는 경우 기본값 반환
    if not conversation or not conversation.messages:
        return {
            "title": "New Conversation",
            "icon_type": "general"
        }
    
    # 첫 번째 사용자 메시지를 찾음
    first_user_message = None
    for message in conversation.messages:
        if message.role == "user":
            first_user_message = message
            break
    
    if not first_user_message:
        return {
            "title": "New Conversation",
            "icon_type": "general"
        }
    
    # 대화 내용에서 키워드를 찾아 아이콘 유형 결정
    message_text = first_user_message.question.lower()
    icon_type = "general"
    
    # 확장된 키워드 기반 아이콘 유형 분류
    if any(keyword in message_text for keyword in ["이미지", "그림", "사진", "image", "picture", "photo", "draw", "png", "jpg"]):
        icon_type = "image"
    elif any(keyword in message_text for keyword in ["코드", "프로그래밍", "개발", "code", "program", "function", "script", "dev", "api", "class", "python", "javascript", "java"]):
        icon_type = "code"
    elif any(keyword in message_text for keyword in ["문서", "보고서", "글", "요약", "정리", "document", "paper", "article", "summarize", "summary", "text", "책", "book"]):
        icon_type = "document"
    elif any(keyword in message_text for keyword in ["수학", "계산", "방정식", "math", "calculate", "equation", "formula", "algebra", "미분", "적분", "calculus"]):
        icon_type = "math"
    elif any(keyword in message_text for keyword in ["그래프", "차트", "graph", "chart", "plot", "데이터 시각화", "visualization"]):
        icon_type = "graph"
    elif any(keyword in message_text for keyword in ["분석", "통계", "analysis", "analytics", "statistics", "데이터 분석", "data analysis"]):
        icon_type = "analysis"
    elif any(keyword in message_text for keyword in ["데이터", "data", "dataset", "database", "json", "csv", "excel"]):
        icon_type = "data"
    elif any(keyword in message_text for keyword in ["대시보드", "dashboard", "panel", "admin", "monitor", "관리자", "모니터링"]):
        icon_type = "dashboard"
    elif any(keyword in message_text for keyword in ["ai", "인공지능", "artificial intelligence", "machine learning", "ml", "딥러닝", "deep learning", "neural network"]):
        icon_type = "ai"
    elif any(keyword in message_text for keyword in ["검색", "찾기", "search", "find", "query", "lookup"]):
        icon_type = "search"
    elif any(keyword in message_text for keyword in ["번역", "translate", "translation", "language", "영어", "한국어", "japanese", "chinese"]):
        icon_type = "translation"
    elif any(keyword in message_text for keyword in ["오디오", "소리", "음성", "음악", "audio", "sound", "voice", "music", "song", "podcast"]):
        icon_type = "audio"
    elif any(keyword in message_text for keyword in ["비디오", "영상", "동영상", "video", "movie", "film", "youtube", "streaming"]):
        icon_type = "video"
    elif any(keyword in message_text for keyword in ["디자인", "design", "ui", "ux", "interface", "웹디자인", "그래픽", "graphic"]):
        icon_type = "design"
    elif any(keyword in message_text for keyword in ["지도", "map", "location", "gps", "위치", "navigation", "네비게이션"]):
        icon_type = "map"
    elif any(keyword in message_text for keyword in ["과학", "science", "physics", "chemistry", "biology", "물리", "화학", "생물"]):
        icon_type = "science"
    elif any(keyword in message_text for keyword in ["금융", "finance", "money", "investment", "stock", "주식", "투자", "재테크"]):
        icon_type = "finance"
    elif any(keyword in message_text for keyword in ["건강", "health", "medical", "medicine", "doctor", "hospital", "wellness", "의학", "병원"]):
        icon_type = "health"
    elif any(keyword in message_text for keyword in ["뉴스", "news", "article", "media", "journalist", "기사", "미디어", "기자"]):
        icon_type = "news"
    elif any(keyword in message_text for keyword in ["날씨", "weather", "forecast", "climate", "temperature", "기상", "기후", "온도"]):
        icon_type = "weather"
    elif any(keyword in message_text for keyword in ["일정", "스케줄", "calendar", "schedule", "appointment", "event", "meeting", "미팅", "약속"]):
        icon_type = "calendar"
    elif any(keyword in message_text for keyword in ["할일", "태스크", "task", "todo", "to-do", "project", "목표", "goal", "프로젝트"]):
        icon_type = "task"
    else:
        icon_type = "general"
    
    # 첫 메시지를 기반으로 제목 생성 (최대 50자)
    title = first_user_message.question[:50]
    if len(first_user_message.question) > 50:
        title += "..."
    
    return {
        "title": title,
        "icon_type": icon_type
    }

# 기존 대화 목록 API를 수정하여 요약 정보 제공
@router.get("/conversations", response_model=List[Dict])
def get_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """사용자의 모든 대화 목록 조회"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 사용자의 모든 대화 가져오기
    conversations = db.query(Conversation).filter(Conversation.user_id == current_user.id).order_by(Conversation.created_at.desc()).all()
    
    # 각 대화에 요약 정보 추가
    result = []
    for conversation in conversations:
        # 대화 정보를 사전으로 변환
        conv_dict = {
            "id": conversation.id,
            "created_at": conversation.created_at,
            "messages": []
        }
        
        # 각 메시지를 user와 assistant로 분리하여 추가
        for message in conversation.messages:
            # User 메시지 추가 (랭그래프 정보 포함)
            conv_dict["messages"].append({
                "id": message.id,
                "role": "user",
                "text": message.question,
                "question": message.question,
                "model": message.model,
                "feedback": message.feedback,
                "image": message.image,
                "created_at": message.created_at,
                "user_name": message.user_name,
                "q_mode": message.q_mode,  # 랭그래프 모드 추가
                "keyword": message.keyword,  # 키워드 추가
                "db_search_title": message.db_search_title  # 문서 검색 타이틀 추가
            })
            
            # Assistant 메시지 추가 (답변이 있는 경우에만)
            if message.ans:
                conv_dict["messages"].append({
                    "id": message.id,  # 실제 데이터베이스 메시지 ID 사용
                    "role": "assistant", 
                    "text": message.ans,
                    "ans": message.ans,
                    "question": message.question,
                    "model": message.model,
                    "feedback": message.feedback,
                    "image": message.image,
                    "created_at": message.created_at,
                    "q_mode": message.q_mode,  # 랭그래프 모드 추가
                    "keyword": message.keyword,  # 키워드 추가
                    "db_search_title": message.db_search_title  # 문서 검색 타이틀 추가
                })
        
        # 요약 정보 추가
        summary_info = get_conversation_summary(conversation, db)
        conv_dict["title"] = summary_info["title"]
        conv_dict["icon_type"] = summary_info["icon_type"]
        
        result.append(conv_dict)
    
    return result

@router.post("/conversations", response_model=ConversationSchema)
def create_conversation(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new conversation for the current user"""
    # Create a new conversation
    conversation = Conversation(user_id=current_user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a conversation and all its messages"""
    # Check if conversation exists and belongs to current user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete all messages in the conversation
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    
    # Delete the conversation
    db.delete(conversation)
    db.commit()
    
    return {"success": True, "message": f"Conversation {conversation_id} deleted"}

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
def create_message(
    conversation_id: int, 
    message_request: MessageRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to a conversation and get AI response"""
    # Check if conversation exists and belongs to current user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get LLM response
    try:
        assistant_response = get_llm_response(message_request.question, message_request.model)
    except Exception as e:
        assistant_response = f"Sorry, I encountered an error: {str(e)}"
    
    # Create single message with both question and answer
    message = Message(
        conversation_id=conversation_id,
        role="user",
        question=message_request.question,
        ans=assistant_response,
        model=message_request.model,
        user_name=current_user.loginid or current_user.username  # SSO 로그인 계정 ID 사용
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return MessageResponse(
        userMessage=message,
        assistantMessage=message
    )

@router.post("/conversations/{conversation_id}/messages/stream")
def save_stream_message(
    conversation_id: int, 
    message_request: StreamMessageRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """스트리밍으로 받은 메시지를 저장"""
    # 대화가 존재하고 현재 사용자에게 속하는지 확인
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 단일 메시지 생성 (질문과 답변 모두 포함)
    message = Message(
        conversation_id=conversation_id,
        role="user",
        question=message_request.question,
        ans=message_request.assistant_response or "",
        model=message_request.model,
        user_name=current_user.loginid or current_user.username,  # SSO 로그인 계정 ID 사용
        image=message_request.image_url  # 이미지 URL 추가
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return MessageResponse(
        userMessage=message,
        assistantMessage=message
    ) 