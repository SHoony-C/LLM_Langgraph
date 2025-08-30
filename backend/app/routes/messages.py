from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from ..database import get_db
from ..models import Message, Conversation, User
from ..schemas import FeedbackRequest, MessageCreate, MessageResponse
from ..utils.auth import get_current_user
from datetime import datetime
from typing import Optional

router = APIRouter()

@router.post("/messages/{message_id}/feedback")
def submit_feedback(
    message_id: int, 
    feedback_request: FeedbackRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a message"""
    print(f"[DEBUG] Feedback request for message_id: {message_id}, feedback: {feedback_request.feedback}")
    
    # Check if message exists
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        print(f"[DEBUG] Message {message_id} not found in database")
        # 현재 사용자의 모든 메시지 ID를 출력하여 디버깅
        user_messages = db.query(Message).join(Conversation).filter(Conversation.user_id == current_user.id).all()
        available_ids = [msg.id for msg in user_messages]
        print(f"[DEBUG] Available message IDs for user {current_user.id}: {available_ids}")
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found. Available IDs: {available_ids}")
    
    print(f"[DEBUG] Found message: id={message.id}, question='{message.question[:50] if message.question else 'N/A'}...', ans='{(message.ans or '')[:50]}...'")
    
    # Check if message belongs to current user's conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == message.conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        print(f"[DEBUG] Message {message_id} does not belong to user {current_user.id}")
        raise HTTPException(status_code=403, detail="Not authorized to access this message")
    
    # Update message feedback
    message.feedback = feedback_request.feedback
    db.commit()
    
    print(f"[DEBUG] Successfully updated feedback for message {message_id} to '{feedback_request.feedback}'")
    return {"success": True}

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
def create_message(conversation_id: int, message: MessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new message in a conversation"""
    print(f"[DB_SAVE] ====== 메시지 저장 시작 ======")
    print(f"[DB_SAVE] conversation_id: {conversation_id}")
    print(f"[DB_SAVE] 사용자: {current_user.loginid or current_user.username}")
    print(f"[DB_SAVE] 요청된 user_name: {message.user_name}")
    print(f"[DB_SAVE] 전체 요청 데이터: {message}")
    print(f"[DB_SAVE] 질문: {message.question}")
    print(f"[DB_SAVE] 답변: {message.ans[:100] if message.ans else 'None'}...")
    print(f"[DB_SAVE] q_mode: {message.q_mode}")
    print(f"[DB_SAVE] 키워드: {message.keyword}")
    print(f"[DB_SAVE] 문서제목: {message.db_search_title}")
    print(f"[DB_SAVE] 요청 URL: /api/conversations/{conversation_id}/messages")
    
    try:
        # Check if the conversation exists and belongs to the user
        print(f"[DB_SAVE] 대화 존재 여부 확인 중...")
        print(f"[DB_SAVE] 찾는 conversation_id: {conversation_id}")
        print(f"[DB_SAVE] 현재 사용자 ID: {current_user.id}")
        
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if conversation:
            print(f"[DB_SAVE] ✅ 대화 발견: ID={conversation.id}, 제목={conversation.title}")
        else:
            print(f"[ERROR] Conversation {conversation_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # 데이터 검증 및 정리
        question = message.question.strip() if message.question else ""
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # ans 필드나 assistant_response 필드 중 하나를 사용
        ans = ""
        if message.ans:
            ans = message.ans.strip()
        elif hasattr(message, 'assistant_response') and message.assistant_response:
            ans = message.assistant_response.strip()
        else:
            ans = ""
        q_mode = message.q_mode or "search"  # 기본값은 search
        keyword = message.keyword
        db_search_title = message.db_search_title
        
        # 키워드 데이터 처리 (JSON 문자열인 경우 파싱하여 검증)
        if keyword and isinstance(keyword, str):
            try:
                # JSON 문자열인지 확인
                if keyword.startswith('[') and keyword.endswith(']'):
                    import json
                    parsed_keywords = json.loads(keyword)
                    if isinstance(parsed_keywords, list):
                        keyword = keyword  # 유효한 JSON 문자열이면 그대로 사용
                    else:
                        keyword = "[]"  # 빈 배열 문자열
                else:
                    keyword = "[]"  # 빈 배열 문자열
            except (json.JSONDecodeError, Exception) as e:
                print(f"[WARNING] 키워드 파싱 실패, 빈 배열로 설정: {e}")
                keyword = "[]"
        elif keyword is None:
            keyword = "[]"
        
        # db_search_title 데이터 처리
        if db_search_title and isinstance(db_search_title, str):
            try:
                if db_search_title.startswith('[') and db_search_title.endswith(']'):
                    import json
                    parsed_titles = json.loads(db_search_title)
                    if isinstance(parsed_titles, list):
                        db_search_title = db_search_title
                    else:
                        db_search_title = "[]"
                else:
                    db_search_title = "[]"
            except (json.JSONDecodeError, Exception) as e:
                print(f"[WARNING] 문서 제목 파싱 실패, 빈 배열로 설정: {e}")
                db_search_title = "[]"
        elif db_search_title is None:
            db_search_title = "[]"
        
        print(f"[DB_SAVE] 최종 데이터:")
        print(f"[DB_SAVE] question: {question}")
        print(f"[DB_SAVE] ans: {ans}")
        print(f"[DB_SAVE] q_mode: {q_mode}")
        print(f"[DB_SAVE] keyword: {keyword}")
        print(f"[DB_SAVE] db_search_title: {db_search_title}")
        
        # Create the message
        db_message = Message(
            conversation_id=conversation_id,
            question=question,
            ans=ans,  # ans 필드 사용
            role=message.role or "user",
            q_mode=q_mode,
            user_name=message.user_name or current_user.username,
            keyword=keyword,
            db_search_title=db_search_title
        )
        
        print(f"[DB_SAVE] 📝 메시지 객체 생성 완료")
        
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        print(f"[DB_SAVE] ✅ 메시지 저장 완료")
        print(f"[DB_SAVE] 생성된 메시지 ID: {db_message.id}")
        
        return MessageResponse(
            userMessage=db_message,
            assistantMessage=db_message,
            q_mode=db_message.q_mode,
            keyword=db_message.keyword,
            db_search_title=db_message.db_search_title
        )
        
    except ValidationError as e:
        print(f"[DB_SAVE] ❌ 데이터 검증 오류: {e}")
        raise HTTPException(status_code=422, detail=f"데이터 검증 실패: {str(e)}")
    except IntegrityError as e:
        print(f"[DB_SAVE] ❌ 데이터베이스 무결성 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail="데이터베이스 제약조건 위반")
    except Exception as e:
        print(f"[DB_SAVE] ❌ 예상치 못한 오류: {e}")
        import traceback
        print(f"[DB_SAVE] 오류 상세: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"메시지 저장 실패: {str(e)}") 