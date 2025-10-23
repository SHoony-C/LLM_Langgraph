"""
질문 유형 판별 및 분기 처리 유틸리티
최초 질문과 추가 질문을 구분하여 적절한 처리 로직으로 라우팅
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from ..models import Conversation, Message, User
from ..database import get_db


def judge_question_type(conversation_id: Optional[int], db: Session) -> Dict[str, Any]:
    """
    질문이 최초 질문인지 추가 질문인지 판별
    
    Args:
        conversation_id: 대화 ID (None이면 새 대화)
        db: 데이터베이스 세션
        
    Returns:
        Dict: 판별 결과
    """
    print(f"[QUESTION_JUDGE] 질문 유형 판별 시작")
    print(f"[QUESTION_JUDGE] - 대화 ID: {conversation_id}")
    
    # 1. conversation_id가 None이면 새 대화 (최초 질문)
    if conversation_id is None:
        print(f"[QUESTION_JUDGE] ✅ 새 대화 - 최초 질문으로 판별")
        return {
            "is_first_question": True,
            "question_type": "first",
            "processing_method": "langgraph",
            "reason": "새 대화"
        }
    
    # 2. 대화 존재 확인
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        print(f"[QUESTION_JUDGE] ❌ 대화를 찾을 수 없음: {conversation_id}")
        return {
            "is_first_question": True,
            "question_type": "first",
            "processing_method": "langgraph",
            "reason": "존재하지 않는 대화 - 새 대화로 처리"
        }
    
    # 3. 대화의 메시지 수 확인
    message_count = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()
    
    print(f"[QUESTION_JUDGE] - 메시지 수: {message_count}")
    
    if message_count == 0:
        print(f"[QUESTION_JUDGE] ✅ 빈 대화 - 최초 질문으로 판별")
        return {
            "is_first_question": True,
            "question_type": "first",
            "processing_method": "langgraph",
            "reason": "빈 대화"
        }
    
    # 4. LangGraph 정보가 있는 메시지 확인
    langgraph_messages = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.q_mode.in_(['search', None])  # LangGraph 메시지
    ).all()
    
    has_langgraph_info = len(langgraph_messages) > 0
    
    print(f"[QUESTION_JUDGE] - LangGraph 메시지 수: {len(langgraph_messages)}")
    print(f"[QUESTION_JUDGE] - LangGraph 정보 존재: {has_langgraph_info}")
    
    if not has_langgraph_info:
        print(f"[QUESTION_JUDGE] ✅ LangGraph 정보 없음 - 최초 질문으로 판별")
        return {
            "is_first_question": True,
            "question_type": "first",
            "processing_method": "langgraph",
            "reason": "LangGraph 정보 없음"
        }
    
    # 5. 추가 질문으로 판별
    print(f"[QUESTION_JUDGE] ✅ 기존 대화 - 추가 질문으로 판별")
    return {
        "is_first_question": False,
        "question_type": "followup",
        "processing_method": "llm_with_context",
        "reason": "기존 대화의 추가 질문"
    }


def get_conversation_langgraph_context(conversation_id: int, db: Session) -> Dict[str, Any]:
    """
    대화에서 LangGraph 컨텍스트 정보 추출
    
    Args:
        conversation_id: 대화 ID
        db: 데이터베이스 세션
        
    Returns:
        Dict: LangGraph 컨텍스트
    """
    print(f"[CONTEXT_EXTRACTOR] LangGraph 컨텍스트 추출 시작: {conversation_id}")
    
    context = {
        "documents": [],
        "keywords": [],
        "first_question": None,
        "first_answer": None,
        "has_search_results": False
    }
    
    try:
        # LangGraph 정보가 있는 메시지 찾기
        langgraph_messages = db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.q_mode.in_(['search', None])
        ).order_by(Message.created_at.asc()).all()
        
        if not langgraph_messages:
            print(f"[CONTEXT_EXTRACTOR] LangGraph 메시지 없음")
            return context
        
        # 첫 번째 LangGraph 메시지에서 정보 추출
        first_langgraph_msg = langgraph_messages[0]
        context["first_question"] = first_langgraph_msg.question
        context["first_answer"] = first_langgraph_msg.ans
        
        # 키워드 정보 추출
        if first_langgraph_msg.keyword:
            try:
                import json
                keywords = json.loads(first_langgraph_msg.keyword) if isinstance(first_langgraph_msg.keyword, str) else first_langgraph_msg.keyword
                if isinstance(keywords, list):
                    context["keywords"] = keywords
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[CONTEXT_EXTRACTOR] 키워드 파싱 실패: {e}")
                context["keywords"] = [first_langgraph_msg.keyword] if first_langgraph_msg.keyword else []
        
        # 검색 결과 정보 추출
        if first_langgraph_msg.db_contents:
            try:
                import json
                db_contents = json.loads(first_langgraph_msg.db_contents)
                if isinstance(db_contents, list):
                    context["documents"] = db_contents[:5]  # 최대 5개 문서
                    context["has_search_results"] = True
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[CONTEXT_EXTRACTOR] DB 내용 파싱 실패: {e}")
        
        print(f"[CONTEXT_EXTRACTOR] 추출된 컨텍스트:")
        print(f"[CONTEXT_EXTRACTOR] - 첫 질문: {context['first_question']}")
        print(f"[CONTEXT_EXTRACTOR] - 키워드 수: {len(context['keywords'])}")
        print(f"[CONTEXT_EXTRACTOR] - 문서 수: {len(context['documents'])}")
        print(f"[CONTEXT_EXTRACTOR] - 검색 결과 존재: {context['has_search_results']}")
        
    except Exception as e:
        print(f"[CONTEXT_EXTRACTOR] ❌ 컨텍스트 추출 오류: {e}")
        import traceback
        print(f"[CONTEXT_EXTRACTOR] 오류 상세: {traceback.format_exc()}")
    
    return context


def create_llm_context_for_followup(conversation_id: int, db: Session) -> str:
    """
    추가 질문을 위한 LLM 컨텍스트 생성
    
    Args:
        conversation_id: 대화 ID
        db: 데이터베이스 세션
        
    Returns:
        str: LLM용 컨텍스트 문자열
    """
    print(f"[LLM_CONTEXT] 추가 질문용 컨텍스트 생성: {conversation_id}")
    
    # LangGraph 컨텍스트 추출
    context = get_conversation_langgraph_context(conversation_id, db)
    
    if not context["first_question"]:
        print(f"[LLM_CONTEXT] ❌ 첫 번째 질문 정보 없음")
        return "이전 대화 정보를 찾을 수 없습니다."
    
    # 컨텍스트 문자열 구성
    context_parts = [
        f"[원본 질문] {context['first_question']}",
        f"[원본 답변] {context['first_answer'] or '답변 없음'}"
    ]
    
    # 키워드 정보 추가
    if context["keywords"]:
        keywords_str = ", ".join(context["keywords"][:10])  # 최대 10개
        context_parts.append(f"[검색 키워드] {keywords_str}")
    
    # 문서 정보 추가
    if context["documents"]:
        context_parts.append(f"[참고 문서] {len(context['documents'])}개 문서")
        for i, doc in enumerate(context["documents"][:3], 1):  # 최대 3개 문서만
            doc_title = doc.get("document_name", f"문서 {i}")
            doc_summary = doc.get("summary_result", "")[:100] if doc.get("summary_result") else ""
            context_parts.append(f"  {i}. {doc_title}")
            if doc_summary:
                context_parts.append(f"     요약: {doc_summary}...")
    
    context_string = "\n".join(context_parts)
    
    print(f"[LLM_CONTEXT] 생성된 컨텍스트 길이: {len(context_string)}자")
    print(f"[LLM_CONTEXT] 컨텍스트 미리보기: {context_string[:200]}...")
    
    return context_string


def should_use_langgraph(conversation_id: Optional[int], db: Session) -> bool:
    """
    LangGraph를 사용해야 하는지 판별 (간단한 헬퍼 함수)
    
    Args:
        conversation_id: 대화 ID
        db: 데이터베이스 세션
        
    Returns:
        bool: LangGraph 사용 여부
    """
    judgment = judge_question_type(conversation_id, db)
    return judgment["is_first_question"]


def get_processing_endpoint(conversation_id: Optional[int], db: Session) -> str:
    """
    적절한 처리 엔드포인트 반환
    
    Args:
        conversation_id: 대화 ID
        db: 데이터베이스 세션
        
    Returns:
        str: 엔드포인트 경로
    """
    judgment = judge_question_type(conversation_id, db)
    
    if judgment["is_first_question"]:
        return "/langgraph/stream"
    else:
        return "/langgraph/followup/stream"


def log_question_processing(question: str, judgment: Dict[str, Any], user_id: Optional[int] = None):
    """
    질문 처리 로그 기록
    
    Args:
        question: 사용자 질문
        judgment: 판별 결과
        user_id: 사용자 ID
    """
    print(f"[QUESTION_LOG] 질문 처리 로그")
    print(f"[QUESTION_LOG] - 질문: {question[:50]}...")
    print(f"[QUESTION_LOG] - 유형: {judgment['question_type']}")
    print(f"[QUESTION_LOG] - 처리 방법: {judgment['processing_method']}")
    print(f"[QUESTION_LOG] - 이유: {judgment['reason']}")
    print(f"[QUESTION_LOG] - 사용자 ID: {user_id}")


# 편의 함수들
def is_first_question(conversation_id: Optional[int], db: Session) -> bool:
    """첫 번째 질문인지 확인"""
    return should_use_langgraph(conversation_id, db)


def is_followup_question(conversation_id: Optional[int], db: Session) -> bool:
    """추가 질문인지 확인"""
    return not should_use_langgraph(conversation_id, db)
