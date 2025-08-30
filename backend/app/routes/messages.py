from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
    print(f"[DB_SAVE] 답변: {message.assistant_response[:100] if message.assistant_response else 'None'}...")
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
        
        assistant_response = message.assistant_response.strip() if message.assistant_response else ""
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
                        keyword = str(keyword)  # 파싱 실패 시 문자열로 변환
                else:
                    keyword = str(keyword)  # 일반 문자열이면 그대로 사용
            except (json.JSONDecodeError, ValueError):
                keyword = str(keyword)  # JSON 파싱 실패 시 문자열로 변환
        
        # Create a single message with both question and answer
        # user_name은 프론트엔드에서 전달받은 값만 사용 (하드코딩 방지)
        single_message = Message(
            conversation_id=conversation_id,
            role="user",
            question=question,
            ans=assistant_response,
            q_mode=q_mode,
            keyword=keyword,
            db_search_title=db_search_title,
            model=message.model or "gpt-3.5-turbo",
            user_name=message.user_name,  # 프론트엔드에서 전달한 user_name만 사용
            image=message.image_url
        )
        
        print(f"[DEBUG] 생성할 메시지 객체: {single_message}")
        print(f"[DEBUG] q_mode: {single_message.q_mode}")
        print(f"[DEBUG] keyword: {single_message.keyword}")
        print(f"[DEBUG] db_search_title: {single_message.db_search_title}")
        print(f"[DEBUG] question 길이: {len(question)}")
        print(f"[DEBUG] answer 길이: {len(assistant_response)}")
        
        db.add(single_message)
        
        # Update conversation last_updated timestamp
        conversation.last_updated = datetime.utcnow()
        
        # 트랜잭션 커밋
        db.commit()
        
        print(f"[DB_SAVE] ✅ 메시지 저장 성공: ID={single_message.id}")
        print(f"[DB_SAVE] 저장된 데이터 요약:")
        print(f"[DB_SAVE]   - 질문: {question[:100]}{'...' if len(question) > 100 else ''}")
        print(f"[DB_SAVE]   - 답변: {assistant_response[:100]}{'...' if len(assistant_response) > 100 else ''}")
        print(f"[DB_SAVE]   - 모드: {q_mode}")
        print(f"[DB_SAVE]   - 키워드: {keyword[:100] if keyword else 'None'}")
        print(f"[DB_SAVE]   - 문서제목: {db_search_title[:100] if db_search_title else 'None'}")
        print(f"[DB_SAVE] ====== 메시지 저장 완료 ======")
        
        return {"id": single_message.id, "status": "success", "message": "Message saved successfully"}
        
    except HTTPException:
        # HTTP 예외는 그대로 재발생
        raise
    except Exception as e:
        # 데이터베이스 오류 등 기타 예외 처리
        print(f"[ERROR] 메시지 저장 중 예외 발생: {str(e)}")
        db.rollback()  # 트랜잭션 롤백
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 