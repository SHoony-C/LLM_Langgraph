from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from ..database import get_db
from ..models import Conversation, Message, User
from ..schemas import Conversation as ConversationSchema
from ..schemas import ConversationCreate, MessageRequest, MessageResponse, FeedbackRequest
from ..utils.auth import get_current_user

router = APIRouter()

# 스트리밍 응답 저장을 위한 클래스 추가
class StreamMessageRequest(MessageRequest):
    assistant_response: Optional[str] = None
    image_url: Optional[str] = None

# 대화 요약 및 아이콘 유형을 가져오는 함수
def get_conversation_summary(conversation, db: Session):
    """대화 내용을 기반으로 요약 및 적절한 아이콘 유형을 생성"""
    
    # conversations 목록 조회 시에는 메시지를 로드하지 않으므로 기본값 반환
    if not conversation:
        return {
            "title": "New Conversation",
            "icon_type": "general"
        }
    
    # conversations 테이블의 title이 있으면 사용
    if conversation.title and conversation.title != "New Conversation":
        # title 기반으로 아이콘 타입 결정
        title_lower = conversation.title.lower()
        icon_type = "general"
        
        # 확장된 키워드 기반 아이콘 유형 분류
        if any(keyword in title_lower for keyword in ["이미지", "그림", "사진", "image", "picture", "photo", "draw", "png", "jpg"]):
            icon_type = "image"
        elif any(keyword in title_lower for keyword in ["코드", "프로그래밍", "개발", "code", "program", "function", "script", "dev", "api", "class", "python", "javascript", "java"]):
            icon_type = "code"
        elif any(keyword in title_lower for keyword in ["문서", "보고서", "글", "요약", "정리", "document", "paper", "article", "summarize", "summary", "text", "책", "book"]):
            icon_type = "document"
        elif any(keyword in title_lower for keyword in ["수학", "계산", "방정식", "math", "calculate", "equation", "formula", "algebra", "미분", "적분", "calculus"]):
            icon_type = "math"
        elif any(keyword in title_lower for keyword in ["그래프", "차트", "graph", "chart", "plot", "데이터 시각화", "visualization"]):
            icon_type = "graph"
        elif any(keyword in title_lower for keyword in ["분석", "통계", "analysis", "analytics", "statistics", "데이터 분석", "data analysis"]):
            icon_type = "analysis"
        elif any(keyword in title_lower for keyword in ["데이터", "data", "dataset", "database", "json", "csv", "excel"]):
            icon_type = "data"
        elif any(keyword in title_lower for keyword in ["대시보드", "dashboard", "panel", "admin", "monitor", "관리자", "모니터링"]):
            icon_type = "dashboard"
        elif any(keyword in title_lower for keyword in ["ai", "인공지능", "artificial intelligence", "machine learning", "ml", "딥러닝", "deep learning", "neural network"]):
            icon_type = "ai"
        elif any(keyword in title_lower for keyword in ["검색", "찾기", "search", "find", "query", "lookup"]):
            icon_type = "search"
        elif any(keyword in title_lower for keyword in ["번역", "translate", "translation", "language", "영어", "한국어", "japanese", "chinese"]):
            icon_type = "translation"
        elif any(keyword in title_lower for keyword in ["오디오", "소리", "음성", "음악", "audio", "sound", "voice", "music", "song", "podcast"]):
            icon_type = "audio"
        elif any(keyword in title_lower for keyword in ["비디오", "영상", "동영상", "video", "movie", "film", "youtube", "streaming"]):
            icon_type = "video"
        elif any(keyword in title_lower for keyword in ["디자인", "design", "ui", "ux", "interface", "웹디자인", "그래픽", "graphic"]):
            icon_type = "design"
        elif any(keyword in title_lower for keyword in ["지도", "map", "location", "gps", "위치", "navigation", "네비게이션"]):
            icon_type = "map"
        elif any(keyword in title_lower for keyword in ["과학", "science", "physics", "chemistry", "biology", "물리", "화학", "생물"]):
            icon_type = "science"
        elif any(keyword in title_lower for keyword in ["금융", "finance", "money", "investment", "stock", "주식", "투자", "재테크"]):
            icon_type = "finance"
        elif any(keyword in title_lower for keyword in ["건강", "health", "medical", "medicine", "doctor", "hospital", "wellness", "의학", "병원"]):
            icon_type = "health"
        elif any(keyword in title_lower for keyword in ["뉴스", "news", "article", "media", "journalist", "기사", "미디어", "기자"]):
            icon_type = "news"
        elif any(keyword in title_lower for keyword in ["날씨", "weather", "forecast", "climate", "temperature", "기상", "기후", "온도"]):
            icon_type = "weather"
        elif any(keyword in title_lower for keyword in ["일정", "스케줄", "calendar", "schedule", "appointment", "event", "meeting", "미팅", "약속"]):
            icon_type = "calendar"
        elif any(keyword in title_lower for keyword in ["할일", "태스크", "task", "todo", "to-do", "project", "목표", "goal", "프로젝트"]):
            icon_type = "task"
        else:
            icon_type = "general"
        
        return {
            "title": conversation.title,
            "icon_type": icon_type
        }
    
    # title이 없거나 기본값인 경우 기본값 반환
    return {
        "title": "New Conversation",
        "icon_type": "general"
    }

# 기존 대화 목록 API를 수정하여 요약 정보 제공
@router.get("/conversations", response_model=List[Dict])
def get_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """사용자의 모든 대화 목록 조회"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 사용자의 모든 대화 가져오기 (삭제되지 않은 것만)
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).order_by(Conversation.created_at.desc()).all()
    
    # 각 대화에 요약 정보 추가 (conversations 테이블의 title 기반)
    result = []
    for conversation in conversations:
        # 대화 정보를 사전으로 변환 (conversations 테이블의 title 사용)
        conv_dict = {
            "id": conversation.id,
            "title": conversation.title,  # conversations 테이블의 title 필드 사용
            "created_at": conversation.created_at,
            "last_updated": conversation.last_updated,
            "messages": []  # 사이드바에서는 메시지 내용 불필요
        }
        
        print(f"[CONVERSATION] 대화 {conversation.id}: title='{conversation.title}', last_updated={conversation.last_updated}")
        
        # 아이콘 타입은 동적으로 생성 (LangGraph 여부 확인)
        summary_info = get_conversation_summary(conversation, db)
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
    """논리적으로 대화를 삭제 (is_deleted=1로 설정)"""
    # Check if conversation exists and belongs to current user (삭제되지 않은 것만)
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 논리적 삭제: is_deleted를 True로 설정
    conversation.is_deleted = True
    db.commit()
    
    return {"success": True, "message": f"Conversation {conversation_id} deleted"}

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: int, 
    message_request: MessageRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to a conversation and get AI response"""
    # Check if conversation exists and belongs to current user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
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
            assistant_response = await get_llm_response(message_request.question)
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
    print(f"[MESSAGE] 💾 메시지 저장 - conversation_id: {conversation_id}, q_mode: {message_request.q_mode}")
    
    message = Message(
        conversation_id=conversation_id,
        role="user",
        question=message_request.question,
        ans=assistant_response,
        user_name=user_name,
        q_mode=message_request.q_mode,
        keyword=message_request.keyword,
        db_contents=message_request.db_contents,
        image=message_request.image
    )
    
    try:
        db.add(message)
        # 대화의 last_updated 시간 업데이트
        from datetime import datetime
        conversation.last_updated = datetime.utcnow()
        
        # 대화에 첫 번째 메시지인 경우 타이틀 설정 (추가 질문이 아닌 경우에만)
        # q_mode가 'add'가 아닌 경우에만 타이틀 업데이트 (첫 번째 질문: None, 'search' 등)
        should_update_title = (
            (not conversation.title or conversation.title == "New Conversation") and 
            message_request.q_mode != "add"
        )
        
        if should_update_title:
            title = message_request.question[:50]
            if len(message_request.question) > 50:
                title += "..."
            conversation.title = title
            print(f"[MESSAGE] 📝 대화 타이틀 설정: {title}")
        else:
            print(f"[MESSAGE] 📝 대화 타이틀 업데이트 건너뛰기: q_mode={message_request.q_mode}, current_title='{conversation.title}'")
        
        db.commit()
        db.refresh(message)
        db.refresh(conversation)
        print(f"[MESSAGE] ✅ 메시지 저장 및 대화 업데이트 완료. ID: {message.id}")
    except Exception as e:
        print(f"[MESSAGE] ❌ 저장 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 오류: {str(e)}")
    
    return MessageResponse(
        userMessage=message,
        assistantMessage=message
    )

@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화의 모든 메시지 조회 (대화 내용 표시용)"""
    try:
        # 대화 존재 확인
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다")
        
        # 모든 메시지 조회 (추가 질문 포함)
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        # 메시지를 user와 assistant로 분리하여 반환
        result_messages = []
        for message in messages:
            # User 메시지 추가
            user_message = {
                "id": message.id,
                "role": "user",
                "text": message.question,
                "question": message.question,
                "feedback": message.feedback,
                "created_at": message.created_at,
                "user_name": message.user_name,
                "q_mode": message.q_mode,
                "keyword": message.keyword,
                "db_contents": message.db_contents,
                "image": message.image
            }
            result_messages.append(user_message)
            
            # Assistant 메시지 추가 (답변이 있는 경우에만)
            if message.ans:
                # langgraph_result 구성 (keyword와 db_contents 기반)
                langgraph_result = None
                if message.keyword or message.db_contents:
                    try:
                        import json
                        langgraph_result = {
                            "question": message.question,
                            "answer": message.ans,
                            "keyword": message.keyword,
                            "documents": json.loads(message.db_contents) if message.db_contents else [],
                            "documents_count": len(json.loads(message.db_contents)) if message.db_contents else 0,
                            "sources": []  # 필요시 추가
                        }
                    except (json.JSONDecodeError, TypeError):
                        langgraph_result = {
                            "question": message.question,
                            "answer": message.ans,
                            "keyword": message.keyword,
                            "documents": [],
                            "documents_count": 0,
                            "sources": []
                        }
                
                assistant_message = {
                    "id": message.id,
                    "role": "assistant", 
                    "text": message.ans,
                    "ans": message.ans,
                    "question": message.question,
                    "feedback": message.feedback,
                    "created_at": message.created_at,
                    "q_mode": message.q_mode,
                    "keyword": message.keyword,
                    "db_contents": message.db_contents,
                    "image": message.image,
                    "langgraph_result": langgraph_result
                }
                result_messages.append(assistant_message)
        
        return {
            "conversation_id": conversation_id,
            "messages": result_messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CONVERSATION_MESSAGES] 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메시지 조회 오류: {str(e)}")

@router.get("/conversations/{conversation_id}/messages/latest")
def get_latest_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화의 최신 메시지들 조회 (피드백용)"""
    try:
        # 대화 존재 확인
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다")
        
        # 최신 사용자 메시지와 어시스턴트 메시지 조회
        latest_user_message = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.role == "user"
        ).order_by(Message.created_at.desc()).first()
        
        latest_assistant_message = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.role == "assistant"
        ).order_by(Message.created_at.desc()).first()
        
        return {
            "userMessage": latest_user_message,
            "assistantMessage": latest_assistant_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LATEST_MESSAGES] 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메시지 조회 오류: {str(e)}")

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
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not current_conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 현재 대화의 모든 메시지가 q_mode='add'인지 확인 (추가 질문만 있는 대화)
    current_messages = current_conversation.messages
    if not current_messages:
        return {"related_conversation": None, "message": "No messages in current conversation"}
    
    # 현재 대화에 LangGraph 정보가 있는지 먼저 확인
    has_langgraph_info = any(
        msg.keyword or msg.db_contents or msg.q_mode in [None, 'search']
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
        Conversation.id != conversation_id,
        Conversation.is_deleted == False
    ).order_by(Conversation.created_at.desc()).all()
    
    # 각 대화에서 LangGraph 정보가 있는 메시지 찾기
    for conversation in other_conversations:
        for message in conversation.messages:
            # LangGraph 정보가 있는 메시지 확인
            if message.keyword or message.db_contents or message.q_mode in [None, 'search']:
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
                        "db_contents": msg.db_contents,
                        "image": msg.image
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
                            "db_contents": msg.db_contents,
                            "image": msg.image
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
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
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

    # 대화의 last_updated 시간 업데이트
    from datetime import datetime
    conversation.last_updated = datetime.utcnow()
    
    # 대화에 첫 번째 메시지인 경우 타이틀 설정 (추가 질문이 아닌 경우에만)
    if (not conversation.title or conversation.title == "New Conversation") and message_request.q_mode != "add":
        title = message_request.question[:50]
        if len(message_request.question) > 50:
            title += "..."
        conversation.title = title
        print(f"[STREAM] 📝 대화 타이틀 설정: {title}")
    
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    
    return MessageResponse(
        userMessage=message,
        assistantMessage=message
    )

@router.put("/conversations/{conversation_id}")
def update_conversation_title(
    conversation_id: int,
    title_request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화 제목 업데이트"""
    # 대화가 존재하고 현재 사용자에게 속하는지 확인
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # 제목 업데이트
    new_title = title_request.get('title', '').strip()
    if new_title:
        conversation.title = new_title
        from datetime import datetime
        conversation.last_updated = datetime.utcnow()
        
        try:
            db.commit()
            db.refresh(conversation)
            print(f"[CONVERSATION] ✅ 대화 제목 업데이트 완료: {new_title}")
            return {"message": "Title updated successfully", "title": new_title}
        except Exception as e:
            print(f"[CONVERSATION] ❌ 제목 업데이트 오류: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"제목 업데이트 오류: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

@router.post("/messages/{message_id}/feedback")
def update_message_feedback(
    message_id: int,
    feedback_request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """메시지에 피드백 업데이트"""
    # 메시지가 존재하고 현재 사용자의 대화에 속하는지 확인
    message = db.query(Message).join(Conversation).filter(
        Message.id == message_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # 피드백 값 검증 (positive, negative, 또는 null만 허용)
    if feedback_request.feedback not in [None, "positive", "negative"]:
        raise HTTPException(status_code=400, detail="Invalid feedback value. Must be 'positive', 'negative', or null")
    
    # 피드백 업데이트
    message.feedback = feedback_request.feedback
    
    try:
        db.commit()
        db.refresh(message)
        print(f"[FEEDBACK] ✅ 메시지 {message_id} 피드백 업데이트: {feedback_request.feedback}")
    except Exception as e:
        print(f"[FEEDBACK] ❌ 피드백 업데이트 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"피드백 업데이트 오류: {str(e)}")
    
    return {
        "success": True,
        "message": "Feedback updated successfully",
        "feedback": message.feedback
    } 
