from app.utils.questionJudge import (
    judge_question_type,
    )

# 질문 유형 판별 함수 (Judge 함수 사용)
def is_first_question_in_conversation(conversation_id: int, db: Session) -> bool:
    """대화에서 첫 번째 질문인지 확인 (Judge 함수 사용)"""
    judgment = judge_question_type(conversation_id, db)
    return judgment["is_first_question"]
