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
            user_message = {
                "id": message.id,
                "role": "user",
                "text": message.question,
                "question": message.question,
                "feedback": message.feedback,
                "created_at": message.created_at,
                "user_name": message.user_name,
                "q_mode": message.q_mode,  # 랭그래프 모드 추가
                "keyword": message.keyword,  # 키워드 추가
                "db_search_title": message.db_search_title  # 문서 검색 타이틀 추가
            }
            conv_dict["messages"].append(user_message)
            
            # Assistant 메시지 추가 (답변이 있는 경우에만)
            if message.ans:
                assistant_message = {
                    "id": message.id,  # 실제 데이터베이스 메시지 ID 사용
                    "role": "assistant", 
                    "text": message.ans,
                    "ans": message.ans,
                    "question": message.question,
                    "feedback": message.feedback,
                    "created_at": message.created_at,
                    "q_mode": message.q_mode,  # 랭그래프 모드 추가
                    "keyword": message.keyword,  # 키워드 추가
                    "db_search_title": message.db_search_title  # 문서 검색 타이틀 추가
                }
                conv_dict["messages"].append(assistant_message)
        
        # LangGraph 정보 확인 (간소화된 로그)
        has_langgraph = any(msg.get('keyword') or msg.get('db_search_title') for msg in conv_dict['messages'])
        if has_langgraph:
            print(f"[CONVERSATION] 📊 대화 {conversation.id}: LangGraph 정보 포함")
        
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
    
    # LLM 응답 생성 (skip_llm 플래그가 true이면 이미 제공된 assistant_response 사용)
    if message_request.skip_llm and message_request.assistant_response:
        # 랭그래프에서 이미 생성된 답변 사용 (LLM 재호출 방지)
        assistant_response = message_request.assistant_response
        print(f"[MESSAGE] LLM 재호출 건너뛰기 - 이미 제공된 답변 사용: {len(assistant_response)}자")
    else:
        # 일반적인 경우 LLM 호출
        try:
            assistant_response = get_llm_response(message_request.question)
        except Exception as e:
            assistant_response = f"Sorry, I encountered an error: {str(e)}"
    
    # 메시지 생성 로그 (간소화)
    print(f"[MESSAGE] 📋 새 메시지: q_mode={message_request.q_mode}, skip_llm={message_request.skip_llm}")
    
    # user_name 검증 및 설정
    user_name = current_user.loginid or current_user.username
    if not user_name:
        print(f"[ERROR] user_name이 없음. current_user: {current_user}")
        raise HTTPException(status_code=400, detail="사용자 정보가 유효하지 않습니다")
    
    print(f"[MESSAGE] 사용자명 설정: {user_name}")
    
    # 중복 저장 방지 - 동일한 질문과 사용자의 최근 메시지 확인 (30초 이내)
    from datetime import datetime, timedelta
    recent_time = datetime.utcnow() - timedelta(seconds=30)
    
    existing_message = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.question == message_request.question,
        Message.user_name == user_name,
        Message.created_at >= recent_time
    ).first()
    
    if existing_message:
        print(f"[WARNING] 중복 메시지 감지됨. 기존 메시지 ID: {existing_message.id}")
        return MessageResponse(
            userMessage=existing_message,
            assistantMessage=existing_message
        )
    
    # 메시지 생성 및 저장
    message = Message(
        conversation_id=conversation_id,
        role="user",
        question=message_request.question,
        ans=assistant_response,
        user_name=user_name,
        q_mode=message_request.q_mode,
        keyword=message_request.keyword,
        db_search_title=message_request.db_search_title
    )
    
    try:
        db.add(message)
        db.commit()
        db.refresh(message)
        print(f"[MESSAGE] ✅ 메시지 저장 완료. ID: {message.id}")
    except Exception as e:
        print(f"[MESSAGE] ❌ 저장 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 오류: {str(e)}")
    
    return MessageResponse(
        userMessage=message,
        assistantMessage=message
    )

@router.get("/conversations/{conversation_id}/related")
def find_related_conversations(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """추가 질문 대화에서 원본 LangGraph 정보가 있는 관련 대화 찾기"""
    # 현재 대화 확인
    current_conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not current_conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 현재 대화의 모든 메시지가 q_mode='add'인지 확인 (추가 질문만 있는 대화)
    current_messages = current_conversation.messages
    if not current_messages:
        return {"related_conversation": None, "message": "No messages in current conversation"}
    
    # 현재 대화에 LangGraph 정보가 있는지 먼저 확인
    has_langgraph_info = any(
        msg.keyword or msg.db_search_title or msg.q_mode in [None, 'search']
        for msg in current_messages
    )
    
    if has_langgraph_info:
        return {"related_conversation": None, "message": "Current conversation already has LangGraph info"}
    
    # 모든 메시지가 추가 질문(q_mode='add')인지 확인
    all_add_messages = all(msg.q_mode == 'add' for msg in current_messages)
    
    if not all_add_messages:
        return {"related_conversation": None, "message": "Current conversation is not an add-only conversation"}
    
    # 사용자의 다른 대화들을 시간순으로 검색 (최근 것부터)
    other_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.id != conversation_id
    ).order_by(Conversation.created_at.desc()).all()
    
    # 각 대화에서 LangGraph 정보가 있는 메시지 찾기
    for conversation in other_conversations:
        for message in conversation.messages:
            # LangGraph 정보가 있는 메시지 확인
            if message.keyword or message.db_search_title or message.q_mode in [None, 'search']:
                # 관련 대화 정보 반환 (메시지 포함)
                conv_dict = {
                    "id": conversation.id,
                    "created_at": conversation.created_at,
                    "messages": []
                }
                
                # 메시지들을 user/assistant 형태로 변환
                for msg in conversation.messages:
                    # User 메시지
                    user_message = {
                        "id": msg.id,
                        "role": "user",
                        "text": msg.question,
                        "question": msg.question,
                        "feedback": msg.feedback,
                        "created_at": msg.created_at,
                        "user_name": msg.user_name,
                        "q_mode": msg.q_mode,
                        "keyword": msg.keyword,
                        "db_search_title": msg.db_search_title
                    }
                    conv_dict["messages"].append(user_message)
                    
                    # Assistant 메시지 (답변이 있는 경우)
                    if msg.ans:
                        assistant_message = {
                            "id": msg.id,
                            "role": "assistant",
                            "text": msg.ans,
                            "ans": msg.ans,
                            "question": msg.question,
                            "feedback": msg.feedback,
                            "created_at": msg.created_at,
                            "q_mode": msg.q_mode,
                            "keyword": msg.keyword,
                            "db_search_title": msg.db_search_title
                        }
                        conv_dict["messages"].append(assistant_message)
                
                return {
                    "related_conversation": conv_dict,
                    "message": f"Found related conversation with LangGraph info: {conversation.id}"
                }
    
    return {"related_conversation": None, "message": "No related conversation with LangGraph info found"}

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
    
    # user_name 검증 및 설정
    user_name = current_user.loginid or current_user.username
    if not user_name:
        print(f"[ERROR] stream user_name이 없음. current_user: {current_user}")
        raise HTTPException(status_code=400, detail="사용자 정보가 유효하지 않습니다")
    
    print(f"[STREAM] 사용자명 설정: {user_name}")
    
    # 단일 메시지 생성 (질문과 답변 모두 포함)
    message = Message(
        conversation_id=conversation_id,
        role="user",
        question=message_request.question,
        ans=message_request.assistant_response or "",
        user_name=user_name  # 검증된 사용자명 사용
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return MessageResponse(
        userMessage=message,
        assistantMessage=message
    ) 