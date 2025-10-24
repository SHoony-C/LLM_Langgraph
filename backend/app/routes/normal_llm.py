import os
import openai
from openai import AsyncOpenAI
import asyncio
import json
import httpx
import uuid
from fastapi import APIRouter, HTTPException, Response, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.utils.config import (
    OPENAI_API_KEY, OPENAI_BASE_URL,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
    IMAGE_BASE_URL, IMAGE_PATH_PREFIX, IS_OPENAI_CONFIGURED
)
from app.database import get_db
from app.models import Conversation, Message, User
from app.utils.auth import get_current_user
from app.utils.questionJudge import (
    judge_question_type,
    get_conversation_langgraph_context,
    log_question_processing
)
from sqlalchemy.orm import Session
from app.routes.llm_class import (
    StreamRequest,
)
from datetime import datetime

# Create router 
router = APIRouter()

# 환경 변수 로딩 확인
print(f"[Config] OpenAI API Key: {'설정됨' if OPENAI_API_KEY else '설정되지 않음'}")
print(f"[Config] Qdrant: {QDRANT_HOST}:{QDRANT_PORT} (컬렉션: {QDRANT_COLLECTION or '설정되지 않음'})")



# 일반 LLM 채팅 엔드포인트 (streaming 지원)
@router.post("/chat/stream")
async def stream_chat_with_llm(request: StreamRequest, http_request: Request, db: Session = Depends(get_db)):
    """Stream a response from general LLM chat using async method"""
    try:
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            return Response(content="Error: OpenAI API 키가 설정되지 않았습니다.", media_type="text/plain")
        
        print(f"[Chat Stream] ========== LLM 스트리밍 채팅 시작 ==========")
        print(f"[Chat Stream] 요청 정보:")
        print(f"[Chat Stream] - 질문: {request.question}")
        print(f"[Chat Stream] - 대화 ID: {request.conversation_id}")
        print(f"[Chat Stream] - conversation_id 타입: {type(request.conversation_id)}")
        print(f"[Chat Stream] - conversation_id가 None인가?: {request.conversation_id is None}")
        
        # 대화 히스토리 구성
        system_content = "당신은 도움이 되는 AI 어시스턴트입니다. 이전 대화의 맥락을 고려하여 답변해주세요."
        
        # 랭그래프 컨텍스트가 있는 경우 시스템 메시지에 추가
        if request.include_langgraph_context and request.langgraph_context:
            langgraph_context = request.langgraph_context
            print(f"[Chat Stream] 랭그래프 컨텍스트 포함: {langgraph_context}")
            
            # 문서 정보를 시스템 메시지에 추가
            if langgraph_context.get('documents'):
                documents_info = f"\n\n참고할 수 있는 문서 정보:\n"
                for i, doc in enumerate(langgraph_context['documents'][:5], 1):  # 최대 5개 문서만
                    documents_info += f"{i}. {doc.get('title', '제목 없음')}\n"
                    if doc.get('content'):
                        # 내용이 너무 길면 잘라내기
                        content = doc['content'][:500] + "..." if len(doc['content']) > 500 else doc['content']
                        documents_info += f"   내용: {content}\n"
                    documents_info += "\n"
                
                system_content += documents_info
                system_content += "\n위 문서들을 참고하여 질문에 답변해주세요. 문서에 없는 정보는 추측하지 말고 '문서에서 해당 정보를 찾을 수 없습니다'라고 답변해주세요."
        
        messages = [{"role": "system", "content": system_content}]
        
        if request.conversation_id:
            try:
                # 해당 대화의 이전 메시지들 가져오기 (최근 10개만)
                conversation_messages = db.query(Message).filter(
                    Message.conversation_id == request.conversation_id
                ).order_by(Message.created_at.asc()).limit(10).all()
                
                print(f"[Chat Stream] 이전 대화 메시지 {len(conversation_messages)}개 로드")
                print(f"[Chat Stream] ========== 이전 대화 히스토리 상세 정보 ==========")
                
                # 이전 대화를 messages에 추가
                for i, msg in enumerate(conversation_messages):
                    print(f"[Chat Stream] DB 메시지 {i+1}: ID={msg.id}, role={msg.role}, created_at={msg.created_at}")
                    if msg.question:
                        print(f"[Chat Stream] 질문: {msg.question}")
                        messages.append({"role": "user", "content": msg.question})
                    if msg.ans:
                        print(f"[Chat Stream] 답변: {msg.ans}")
                        messages.append({"role": "assistant", "content": msg.ans})
                    print(f"[Chat Stream] ----------------------------------------")
                
                print(f"[Chat Stream] ========== 이전 대화 히스토리 로드 완료 ==========")
                        
            except Exception as e:
                print(f"[Chat Stream] 대화 히스토리 로드 실패: {e}")
                # 히스토리 로드 실패해도 계속 진행
        
        # 현재 질문 추가
        messages.append({"role": "user", "content": request.question})
        
        print(f"[Chat Stream] 전송할 메시지 개수: {len(messages)}")
        print(f"[Chat Stream] ========== OpenAI API에 전송할 전체 메시지 내용 ==========")
        print(f"[Chat Stream] ==========전체 메시지 내용 : ")
        print(f"{messages}")
        
        print(f"[Chat Stream] ========== 전체 메시지 내용 끝 ==========")
        
        # 스트리밍 방식 사용 - DB 저장 포함
        return StreamingResponse(
            get_streaming_response_with_db_save(messages, http_request, request, db),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            }
        )
        
    except Exception as e:
        print(f"[Chat Stream] LLM 스트리밍 채팅 오류: {str(e)}")
        import traceback
        print(f"[Chat Stream] 오류 상세: {traceback.format_exc()}")
        return Response(content=f"Error: {str(e)}", media_type="text/plain")


def get_conversation_context(conversation_id: int, db: Session) -> dict:
    """대화의 컨텍스트와 히스토리 가져오기 (Judge 함수 사용)"""
    try:
        # Judge 함수를 사용하여 LangGraph 컨텍스트 추출
        langgraph_context = get_conversation_langgraph_context(conversation_id, db)
        
        # 해당 대화의 모든 메시지 가져오기 (시간순 정렬)
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        print(f"[CONTEXT] 대화 ID {conversation_id}의 메시지 {len(messages)}개 로드")
        
        # 첫 번째 질문 찾기 (LangGraph 컨텍스트에서)
        first_message = None
        if langgraph_context["first_question"]:
            # 첫 번째 질문 메시지 찾기
            for msg in messages:
                if msg.question == langgraph_context["first_question"]:
                    first_message = msg
                    print(f"[CONTEXT] 첫 번째 질문 발견: 메시지 ID {msg.id}")
                    break
        
        # 대화 히스토리 구성
        conversation_history = []
        for msg in messages:
            if msg.question:
                conversation_history.append({"role": "user", "content": msg.question})
            if msg.ans:
                conversation_history.append({"role": "assistant", "content": msg.ans})
        
        return {
            "first_message": first_message,
            "conversation_history": conversation_history,
            "message_count": len(messages),
            "langgraph_context": langgraph_context
        }
        
    except Exception as e:
        print(f"[CONTEXT] 대화 컨텍스트 로드 오류: {e}")
        return {
            "first_message": None,
            "conversation_history": [],
            "message_count": 0,
            "langgraph_context": {}
        }

# 추가 질문 스트리밍 처리 엔드포인트
@router.post("/langgraph/followup/stream")
async def execute_followup_question_stream(request: StreamRequest, http_request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """추가 질문 스트리밍 처리 - 기존 RAG 컨텍스트와 대화 히스토리 활용"""
    try:
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            return Response(content="Error: OpenAI API 키가 설정되지 않았습니다.", media_type="text/plain")
        
        print(f"[FOLLOWUP_STREAM] 🔄 LLM 추가 질문 스트리밍 처리 시작: {request.question}")
        
        # 대화 ID 확인
        if not request.conversation_id:
            return Response(content="Error: 추가 질문은 conversation_id가 필요합니다", media_type="text/plain")
        
        # Judge 함수를 사용하여 질문 유형 확인
        judgment = judge_question_type(request.conversation_id, db)
        log_question_processing(request.question, judgment, current_user.id if current_user else None)
        
        if judgment["is_first_question"]:
            print(f"[FOLLOWUP_STREAM] ⚠️ 최초 질문이 추가 질문 엔드포인트로 전달됨")
            return Response(content="Error: 최초 질문은 /langgraph/stream 엔드포인트를 사용하세요", media_type="text/plain")
        
        # 기존 대화 컨텍스트에서 RAG 정보 추출 (Judge 함수 사용)
        context = get_conversation_context(request.conversation_id, db)
        
        if not context["first_message"]:
            print(f"[FOLLOWUP_STREAM] ⚠️ 첫 번째 질문 없음")
            return Response(content="Error: 첫 번째 질문을 찾을 수 없습니다", media_type="text/plain")
        
        # 첫 번째 질문의 RAG 검색 결과 활용
        first_message = context["first_message"]
        
        # DB에서 첫 번째 질문과 관련된 RAG 검색 결과 재구성
        # print(f"[FOLLOWUP_STREAM] 📄 첫 번째 질문 RAG 정보:")
        # print(f"[FOLLOWUP_STREAM]   질문: {first_message.question}")
        # print(f"[FOLLOWUP_STREAM]   키워드: {first_message.keyword}")
        # print(f"[FOLLOWUP_STREAM]   검색 문서: {first_message.db_contents}")
        
        # 실제 RAG 문서 내용 구성 (DB에 저장된 db_contents 재사용)
        document_title = "검색된 문서"
        actual_document_content = ""
        
        # DB에 저장된 db_contents에서 문서 내용 가져오기
        try:
            if first_message.db_contents:
                # JSON 파싱
                db_contents_list = json.loads(first_message.db_contents) if isinstance(first_message.db_contents, str) else first_message.db_contents
                
                if db_contents_list and len(db_contents_list) > 0:
                    # 첫 번째 문서 사용
                    top_doc = db_contents_list[0]
                    document_title = top_doc.get('document_name', '검색된 문서')
                    
                    # 모든 텍스트 필드 결합
                    text_parts = []
                    for field in ['text', 'summary_purpose', 'summary_result', 'summary_fb']:
                        if top_doc.get(field):
                            text_parts.append(top_doc[field])
                    
                    actual_document_content = " ".join(text_parts).strip() or "문서 내용 없음"
                    print(f"[FOLLOWUP_STREAM] DB에서 문서 내용 복원 성공: {document_title}")
                else:
                    actual_document_content = "저장된 문서 내용이 없습니다"
            else:
                actual_document_content = "저장된 검색 결과가 없습니다"
                
        except Exception as e:
            print(f"[FOLLOWUP_STREAM] DB 내용 파싱 오류: {e}")
            import traceback
            print(f"[FOLLOWUP_STREAM] 오류 상세: {traceback.format_exc()}")
            actual_document_content = "문서 내용을 가져올 수 없습니다"
        
        document_content = f"""
[원본 질문] {first_message.question}
[검색된 문서] {document_title}
[실제 문서 내용] {actual_document_content}
[이전 답변] {first_message.ans}
"""
        
        print(f"[FOLLOWUP_STREAM] 📄 재사용할 RAG 문서:")
        print(f"[FOLLOWUP_STREAM] 제목: {document_title}")
        print(f"[FOLLOWUP_STREAM] 내용: {actual_document_content}")
        
        # 대화 히스토리 구성 (첫 번째 질문과 답변만 포함)
        conversation_history = context["conversation_history"]
        print(f"[FOLLOWUP_STREAM] 💬 대화 히스토리: {len(conversation_history)}개 메시지")
        
        # 시스템 프롬프트 구성 (RAG 문서 기반)
        system_prompt = f"""당신은 도움이 되는 AI 어시스턴트입니다.
아래 정보를 바탕으로 추가 질문에 답변해주세요.

{document_content}

중요한 규칙:
1. 위에 제공된 실제 문서 내용만을 기반으로 답변하세요
2. 추가적인 정보나 일반적인 지식을 사용하지 마세요
3. 문서에 없는 내용은 "문서에서 해당 정보를 찾을 수 없습니다"라고 답변하세요
4. 한국어로 자연스럽게 답변하세요
5. 이전 대화 맥락을 고려하여 답변하세요"""
        
        # LLM API 호출을 위한 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]
        
        # 대화 히스토리 추가 (최근 10개 메시지만)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        messages.extend(recent_history)
        
        # 현재 질문 추가
        messages.append({"role": "user", "content": request.question})
        
        print(f"[FOLLOWUP_STREAM] 📤 LLM에 전송할 메시지 수: {len(messages)}")
        print(f"[FOLLOWUP_STREAM] 📝 현재 질문: {request.question}")
        print(f"[FOLLOWUP_STREAM] 👤 사용자: {current_user.username if current_user else 'None'}")
        
        # 스트리밍 방식 사용 - DB 저장 포함
        return StreamingResponse(
            get_streaming_response_with_db_save(messages, http_request, request, db, current_user),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            }
        )
        
    except Exception as e:
        print(f"[FOLLOWUP_STREAM] LLM 추가 질문 스트리밍 처리 오류: {str(e)}")
        import traceback
        print(f"[FOLLOWUP_STREAM] 오류 상세: {traceback.format_exc()}")
        return Response(content=f"Error: {str(e)}", media_type="text/plain")

async def save_message_to_db(stream_request: StreamRequest, assistant_response: str, image_url: str = None, db: Session = None, current_user: User = None):
    """
    스트리밍 완료 후 메시지를 DB에 저장
    
    중요: 이 시스템에서는 질문과 답변이 하나의 Message row에 저장됩니다.
    - question 필드: 사용자 질문
    - ans 필드: AI 답변
    - role: 'user' (질문과 답변이 모두 user 메시지에 포함)
    - 별도의 assistant 메시지는 생성하지 않음
    """
    try:
        if not db:
            print(f"[DB_SAVE] ❌ DB 세션이 없음")
            return
            
        if not stream_request.conversation_id:
            print(f"[DB_SAVE] ❌ conversation_id가 없음 - 추가 질문은 conversation_id가 필수입니다")
            return
            
        print(f"[DB_SAVE] 💾 메시지 DB 저장 시작")
        print(f"[DB_SAVE] - 대화 ID: {stream_request.conversation_id}")
        print(f"[DB_SAVE] - 질문: {stream_request.question}")
        print(f"[DB_SAVE] - 답변 길이: {len(assistant_response)}자")
        print(f"[DB_SAVE] - 사용자: {current_user.username if current_user else 'None'}")
        
        # 대화 존재 확인
        conversation = db.query(Conversation).filter(
            Conversation.id == stream_request.conversation_id,
            Conversation.is_deleted == False
        ).first()
        
        if not conversation:
            print(f"[DB_SAVE] ❌ 대화를 찾을 수 없음: {stream_request.conversation_id}")
            return
        
        print(f"[DB_SAVE] ✅ 기존 대화 찾음 - 새 conversation 생성하지 않음")
            
        # 사용자 정보 확인 (current_user 우선, 없으면 conversation.user)
        user_name = "system"  # 기본값
        if current_user:
            user_name = current_user.loginid or current_user.username or "system"
            print(f"[DB_SAVE] - current_user에서 사용자명 가져옴: {user_name}")
        elif conversation.user:
            user_name = conversation.user.loginid or conversation.user.username or "system"
            print(f"[DB_SAVE] - conversation.user에서 사용자명 가져옴: {user_name}")
        
        # 중복 저장 방지 - 동일한 질문의 최근 메시지 확인 (30초 이내)
        from datetime import datetime, timedelta
        recent_time = datetime.utcnow() - timedelta(seconds=30)
        
        print(f"[DB_SAVE] 🔍 중복 저장 방지 확인:")
        print(f"[DB_SAVE]   - conversation_id: {stream_request.conversation_id}")
        print(f"[DB_SAVE]   - question: {stream_request.question[:50]}...")
        print(f"[DB_SAVE]   - recent_time: {recent_time}")
        
        existing_message = db.query(Message).filter(
            Message.conversation_id == stream_request.conversation_id,
            Message.question == stream_request.question,
            Message.created_at >= recent_time
        ).first()
        
        if existing_message:
            print(f"[DB_SAVE] ⚠️ 중복 메시지 감지됨. 기존 메시지 ID: {existing_message.id}")
            print(f"[DB_SAVE]   - 기존 메시지 생성 시간: {existing_message.created_at}")
            print(f"[DB_SAVE]   - 현재 시간: {datetime.utcnow()}")
            return
        
        # 메시지 생성 및 저장
        # 중요: 질문과 답변이 하나의 row에 저장되는 구조
        # - question: 사용자 질문
        # - ans: AI 답변 (스트리밍 완료된 내용)
        # - role: 'user' (질문과 답변이 모두 user 메시지에 포함)
        # q_mode는 conversation_id가 있는 경우 'add', 없는 경우 None
        # conversation_id가 있으면 기존 대화에 추가 질문이므로 'add'
        # conversation_id가 없으면 새 대화이므로 None (첫 번째 질문)
        q_mode_value = "add" if stream_request.conversation_id else None
        
        print(f"[DB_SAVE] - q_mode: {q_mode_value} (conversation_id: {stream_request.conversation_id})")
        
        message = Message(
            conversation_id=stream_request.conversation_id,
            role="user",
            question=stream_request.question,  # 사용자 질문
            ans=assistant_response,  # AI 답변 (스트리밍 완료된 내용)
            user_name=user_name,
            q_mode=q_mode_value,  # conversation_id가 있으면 'add', 없으면 None
            image=image_url
        )
        
        db.add(message)
        
        # 대화의 last_updated 시간 업데이트
        conversation.last_updated = datetime.utcnow()
        
        # 대화에 첫 번째 메시지인 경우 타이틀 설정 (추가 질문이 아닌 경우에만)
        if (not conversation.title or conversation.title == "New Conversation") and stream_request.q_mode != "add":
            title = stream_request.question[:50]
            if len(stream_request.question) > 50:
                title += "..."
            conversation.title = title
            print(f"[DB_SAVE] 📝 대화 타이틀 설정: {title}")
        
        db.commit()
        db.refresh(message)
        db.refresh(conversation)
        
        print(f"[DB_SAVE] ✅ 메시지 저장 완료. ID: {message.id}")
        
    except Exception as e:
        print(f"[DB_SAVE] ❌ DB 저장 오류: {str(e)}")
        import traceback
        print(f"[DB_SAVE] 오류 상세: {traceback.format_exc()}")
        if db:
            db.rollback()


async def get_streaming_response_with_db_save(messages: List[Dict], request: Request, stream_request: StreamRequest, db: Session, current_user: User = None):
    """Stream a response from LLM using AsyncOpenAI with custom headers and save to DB"""
    try:
        print(f"[LLM_STREAM_DB] 🚀 LLM 스트리밍 시작 (DB 저장 포함)")
        
        # 이미지 URL (이미지 생성이 요청된 경우)
        image_url = None
        if stream_request.generate_image:
            # 이미지 생성은 별도 시스템에서 처리
            print(f"[LLM_STREAM_DB] 이미지 생성 요청됨 (별도 시스템 필요)")
            image_url = None  # 실제 이미지 생성 시스템 연동 필요
        
        # API 키 검증
        if not IS_OPENAI_CONFIGURED:
            error_payload = json.dumps({'error': 'AI 서비스 설정이 완료되지 않았습니다. 관리자에게 문의해주세요.'}, ensure_ascii=False)
            yield (f"data: {error_payload}\n\n").encode("utf-8")
            yield "data: [DONE]\n\n".encode("utf-8")
            return

        # httpx 클라이언트 설정 (타임아웃 추가)
        httpx_client = httpx.AsyncClient(
            verify=False, 
            timeout=httpx.Timeout(30.0, connect=10.0)
        )

        # AsyncOpenAI 클라이언트 생성
        client = AsyncOpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                http_client=httpx_client,
                default_headers={
                    "x-dep-ticket": OPENAI_API_KEY,
                    "Send-System-Name": "ds2llm",
                    "User-Id": "c.seunghoon",
                    "User-Type": "AD_ID",
                    "Prompt-Msg-Id": str(uuid.uuid4()),
                    "Completion-Msg-Id": str(uuid.uuid4()),
                }
            )
            
        # 비동기 호출
        response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True,
            )
        
        print(f"[LLM_STREAM_DB] 📥 스트리밍 응답 시작")
        
        text_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                text_response += content
                
                try:
                    # 비-ASCII 문자 허용, UTF-8 bytes로 즉시 전송
                    payload = json.dumps({'content': content}, ensure_ascii=False)
                    yield (f"data: {payload}\n\n").encode("utf-8")
                    # 지연 제거 - 빠른 스트리밍을 위해
                except (ConnectionResetError, BrokenPipeError, OSError, ConnectionAbortedError, ConnectionError) as e:
                    # 클라이언트 연결이 끊어진 경우 조용히 종료
                    print(f"[LLM_STREAM_DB] Client disconnected during streaming lv2: {type(e).__name__}")
                    return
                except Exception as e:
                    print(f"[LLM_STREAM_DB] Unexpected error during streaming lv1: {str(e)}")
                    return
        
        # 스트리밍 완료 후 DB에 저장 (추가질문의 경우 이미 prepare에서 저장되었으므로 스킵)
        print(f"[LLM_STREAM_DB] 🔍 저장 조건 확인:")
        print(f"[LLM_STREAM_DB]   - conversation_id: {stream_request.conversation_id}")
        print(f"[LLM_STREAM_DB]   - q_mode: {getattr(stream_request, 'q_mode', 'None')}")
        print(f"[LLM_STREAM_DB]   - is_add_question: {getattr(stream_request, 'q_mode', None) == 'add'}")
        
        if not stream_request.conversation_id or getattr(stream_request, 'q_mode', None) != "add":
            try:
                print(f"[LLM_STREAM_DB] 💾 DB 저장 시작 (일반 질문)")
                await save_message_to_db(stream_request, text_response, image_url, db, current_user)
                print(f"[LLM_STREAM_DB] ✅ DB 저장 완료")
            except Exception as e:
                print(f"[LLM_STREAM_DB] ❌ DB 저장 실패: {str(e)}")
                # DB 저장 실패해도 스트리밍은 계속 진행
        else:
            # 추가질문인 경우 message_id가 있으면 기존 메시지 업데이트
            if hasattr(stream_request, 'message_id') and stream_request.message_id:
                try:
                    print(f"[LLM_STREAM_DB] 💾 기존 메시지 업데이트: message_id={stream_request.message_id}")
                    existing_message = db.query(Message).filter(
                        Message.id == stream_request.message_id,
                        Message.conversation_id == stream_request.conversation_id
                    ).first()
                    
                    if existing_message:
                        existing_message.ans = text_response
                        if image_url:
                            # 이미지 URL이 있는 경우 추가 처리 (필요시)
                            print(f"[LLM_STREAM_DB] 🖼️ 이미지 URL 저장: {image_url}")
                        db.commit()
                        print(f"[LLM_STREAM_DB] ✅ 메시지 업데이트 완료: {stream_request.message_id}")
                    else:
                        print(f"[LLM_STREAM_DB] ⚠️ 메시지를 찾을 수 없음: {stream_request.message_id}")
                except Exception as e:
                    print(f"[LLM_STREAM_DB] ❌ 메시지 업데이트 실패: {str(e)}")
                    db.rollback()
            else:
                print(f"[LLM_STREAM_DB] ⏭️ 추가질문 - message_id 없음, DB 저장 스킵")
                print(f"[LLM_STREAM_DB]   - prepare 엔드포인트에서 이미 메시지가 생성되었으므로 중복 저장 방지")
        
        # 텍스트 응답이 완료된 후 이미지 URL이 있으면 전송
        if image_url:
            try:
                response_data = {
                    "text": text_response,
                    "image_url": image_url
                }
                payload = json.dumps(response_data, ensure_ascii=False)
                yield (f"data: {payload}\n\n").encode("utf-8")
            except Exception as e:
                print(f"[LLM_STREAM_DB] Error sending image data: {str(e)}")
        
        print(f"[LLM_STREAM_DB] ✅ 스트리밍 완료")
        yield "data: [DONE]\n\n".encode("utf-8")
        
    except Exception as e:
        error_message = str(e)
        print(f"[LLM_STREAM_DB] Error in streaming response: {error_message}")
        import traceback
        print(f"[LLM_STREAM_DB] 오류 상세: {traceback.format_exc()}")
        
        try:
            # 연결 오류 타입별 처리
            if "APIConnectionError" in error_message or "Connection error" in error_message:
                error_desc = "AI 서비스에 연결할 수 없습니다. 네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요."
            elif "timeout" in error_message.lower():
                error_desc = "AI 서비스 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
            elif "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
                error_desc = "AI 서비스 인증에 문제가 있습니다. 관리자에게 문의해주세요."
            else:
                error_desc = "응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            
            error_payload = json.dumps({'error': error_desc}, ensure_ascii=False)
            yield (f"data: {error_payload}\n\n").encode("utf-8")
            yield "data: [DONE]\n\n".encode("utf-8")
        except Exception:
            # 에러 전송도 실패한 경우 조용히 종료
            return

async def get_streaming_response_async(messages: List[Dict], request: Request, generate_image: bool = False):
    """Stream a response from LLM using AsyncOpenAI with custom headers"""
    try:
        print(f"[LLM_STREAM] 🚀 LLM 스트리밍 시작")
        
        # 이미지 URL (이미지 생성이 요청된 경우)
        image_url = None
        if generate_image:
            # 이미지 생성은 별도 시스템에서 처리
            print(f"[LLM_STREAM] 이미지 생성 요청됨 (별도 시스템 필요)")
            image_url = None  # 실제 이미지 생성 시스템 연동 필요
        
        # API 키 검증
        if not IS_OPENAI_CONFIGURED:
            error_payload = json.dumps({'error': 'AI 서비스 설정이 완료되지 않았습니다. 관리자에게 문의해주세요.'}, ensure_ascii=False)
            yield (f"data: {error_payload}\n\n").encode("utf-8")
            yield "data: [DONE]\n\n".encode("utf-8")
            return

        # httpx 클라이언트 설정 (타임아웃 추가)
        httpx_client = httpx.AsyncClient(
            verify=False, 
            timeout=httpx.Timeout(30.0, connect=10.0)
        )

        # print(f"[messages 확인] {messages}")              
        

        # AsyncOpenAI 클라이언트 생성
        client = AsyncOpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                http_client=httpx_client,
                default_headers={
                    "x-dep-ticket": OPENAI_API_KEY,
                    "Send-System-Name": "ds2llm",
                    "User-Id": "c.seunghoon",
                    "User-Type": "AD_ID",
                    "Prompt-Msg-Id": str(uuid.uuid4()),
                    "Completion-Msg-Id": str(uuid.uuid4()),
                }
            )
            
        # 비동기 호출
        response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True,
            )
        
        print(f"[LLM_STREAM] 📥 스트리밍 응답 시작")
        
        text_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                text_response += content
                
                try:
                    # 비-ASCII 문자 허용, UTF-8 bytes로 즉시 전송
                    payload = json.dumps({'content': content}, ensure_ascii=False)
                    yield (f"data: {payload}\n\n").encode("utf-8")
                    # 지연 제거 - 빠른 스트리밍을 위해
                except (ConnectionResetError, BrokenPipeError, OSError, ConnectionAbortedError, ConnectionError) as e:
                    # 클라이언트 연결이 끊어진 경우 조용히 종료
                    print(f"[LLM_STREAM] Client disconnected during streaming lv2: {type(e).__name__}")
                    return
                except Exception as e:
                    print(f"[LLM_STREAM] Unexpected error during streaming lv1: {str(e)}")
                    return
        
        # 텍스트 응답이 완료된 후 이미지 URL이 있으면 전송
        if image_url:
            try:
                response_data = {
                    "text": text_response,
                    "image_url": image_url
                }
                payload = json.dumps(response_data, ensure_ascii=False)
                yield (f"data: {payload}\n\n").encode("utf-8")
            except Exception as e:
                print(f"[LLM_STREAM] Error sending image data: {str(e)}")
        
        print(f"[LLM_STREAM] ✅ 스트리밍 완료")
        yield "data: [DONE]\n\n".encode("utf-8")
        
    except Exception as e:
        error_message = str(e)
        print(f"[LLM_STREAM] Error in streaming response: {error_message}")
        import traceback
        print(f"[LLM_STREAM] 오류 상세: {traceback.format_exc()}")
        
        try:
            # 연결 오류 타입별 처리
            if "APIConnectionError" in error_message or "Connection error" in error_message:
                error_desc = "AI 서비스에 연결할 수 없습니다. 네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요."
            elif "timeout" in error_message.lower():
                error_desc = "AI 서비스 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
            elif "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
                error_desc = "AI 서비스 인증에 문제가 있습니다. 관리자에게 문의해주세요."
            else:
                error_desc = "응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            
            error_payload = json.dumps({'error': error_desc}, ensure_ascii=False)
            yield (f"data: {error_payload}\n\n").encode("utf-8")
            yield "data: [DONE]\n\n".encode("utf-8")
        except Exception:
            # 에러 전송도 실패한 경우 조용히 종료
            return
