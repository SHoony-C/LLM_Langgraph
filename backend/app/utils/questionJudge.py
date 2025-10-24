"""
질문 유형 판별 및 분기 처리 유틸리티
최초 질문과 추가 질문을 구분하여 적절한 처리 로직으로 라우팅
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from ..models import Conversation, Message, User
from ..database import get_db


# judge_question_type 함수는 프론트엔드에서 처리하므로 제거됨


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


# judge_question_type 관련 함수들은 프론트엔드에서 처리하므로 제거됨
