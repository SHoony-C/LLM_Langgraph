from typing import List
from pydantic import BaseModel
from typing import Optional
import asyncio

# 직접 구현한 텍스트 유사도 계산 클래스
class DirectSimilarityCalculator:
    def __init__(self):
        self.stopwords = {'은', '는', '이', '가', '을', '를', '에', '에서', '와', '과', '의', '로', '으로', '한', '하는', '하다', '있다', '없다', '그', '그것', '이것', '저것'}
        
    def preprocess_text(self, text: str) -> List[str]:
        """텍스트 전처리 및 토큰화"""
        import re
        # 특수문자 제거 및 소문자 변환
        cleaned_text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text.lower())
        # 토큰화
        tokens = cleaned_text.split()
        # 불용어 제거 및 길이 2 이상 토큰만 유지
        filtered_tokens = [token for token in tokens if token not in self.stopwords and len(token) >= 2]
        return filtered_tokens
    
    def calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """자카드 유사도 계산"""
        tokens1 = set(self.preprocess_text(text1))
        tokens2 = set(self.preprocess_text(text2))
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
            
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """코사인 유사도 계산 (TF 기반)"""
        tokens1 = self.preprocess_text(text1)
        tokens2 = self.preprocess_text(text2)
        
        # TF 계산
        tf1 = {}
        tf2 = {}
        
        for token in tokens1:
            tf1[token] = tf1.get(token, 0) + 1
        for token in tokens2:
            tf2[token] = tf2.get(token, 0) + 1
        
        # 전체 단어 집합
        all_tokens = set(tokens1 + tokens2)
        
        if not all_tokens:
            return 1.0
        
        # 벡터 생성
        vector1 = [tf1.get(token, 0) for token in all_tokens]
        vector2 = [tf2.get(token, 0) for token in all_tokens]
        
        # 코사인 유사도 계산
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = sum(a * a for a in vector1) ** 0.5
        magnitude2 = sum(b * b for b in vector2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
            
        return dot_product / (magnitude1 * magnitude2)
    
    def calculate_combined_similarity(self, text1: str, text2: str) -> float:
        """자카드와 코사인 유사도를 결합한 최종 유사도"""
        jaccard_sim = self.calculate_jaccard_similarity(text1, text2)
        cosine_sim = self.calculate_cosine_similarity(text1, text2)
        
        # 가중 평균 (자카드 0.4, 코사인 0.6)
        combined_sim = (jaccard_sim * 0.4) + (cosine_sim * 0.6)
        return combined_sim
    
    def find_similar_documents(self, query: str, documents: List[dict], top_k: int = 5) -> List[dict]:
        """쿼리와 유사한 문서들을 찾아 반환"""
        results = []
        
        for doc in documents:
            # 문서 텍스트 추출 - 모든 관련 필드 결합
            doc_title = doc.get('document_name', '')
            
            # 모든 텍스트 필드를 결합하여 풍부한 내용 생성
            text_parts = [doc_title]  # 제목은 항상 포함
            
            if 'vector' in doc and isinstance(doc['vector'], dict):
                vector_data = doc['vector']
                # 모든 텍스트 필드를 결합 (실제 DB 구조에 맞춤)
                for field in ['text', 'summary_purpose', 'summary_result', 'summary_fb']:
                    if field in vector_data and vector_data[field]:
                        text_parts.append(str(vector_data[field]))
            
            # 모든 텍스트를 공백으로 연결
            doc_text = " ".join(text_parts).strip()
            
            # 유사도 계산
            similarity = self.calculate_combined_similarity(query, doc_text)
            
            results.append({
                'document': doc,
                'similarity': similarity,
                'matched_text': doc_text[:200] + '...' if len(doc_text) > 200 else doc_text
            })
        
        # 유사도 순으로 정렬하여 상위 k개 반환
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

# 스트리밍 요청을 위한 클래스
class StreamRequest(BaseModel):
    question: str
    conversation_id: Optional[int] = None
    message_id: Optional[int] = None  # 영구 메시지 ID 추가
    generate_image: Optional[bool] = False  # 이미지 생성 플래그 추가
    # LangGraph 컨텍스트 필드 추가
    langgraph_context: Optional[dict] = None
    include_langgraph_context: Optional[bool] = False
    q_mode: Optional[str] = None  # 질문 모드 추가 (add, search 등)

# LangGraph 상태 정의
class SearchState(dict):
    question: str       # 사용자 입력 질의
    keyword: str       # 사용자 입력 질의
    candidates_each: List[dict] 
    candidates_total: List[dict] 
    response: List[dict]     # LLM이 생성한 응답
    generator_id: str   # SSE 제너레이터 ID

# SSE 스트리밍을 위한 제너레이터 클래스
class SSEGenerator:
    def __init__(self, generator_id: str):
        self.generator_id = generator_id
        self.message_queue = asyncio.Queue()
        self.is_active = True
        self.message_count = 0
        print(f"[SSE_GEN] 🆕 SSEGenerator 생성: {generator_id}")
        
    async def send_message(self, message: dict):
        """메시지를 큐에 추가"""
        if self.is_active:
            self.message_count += 1
            # print(f"[SSE_GEN] 📥 메시지 #{self.message_count} 큐에 추가: {message.get('stage', 'unknown')}:{message.get('status', 'unknown')}")
            await self.message_queue.put(message)
            # print(f"[SSE_GEN] ✅ 메시지 큐 추가 완료, 현재 큐 크기: {self.message_queue.qsize()}")
        else:
            print(f"[SSE_GEN] ❌ 비활성 제너레이터에 메시지 전송 시도: {self.generator_id}")
    
    async def close(self):
        """제너레이터 종료"""
        print(f"[SSE_GEN] 🔚 제너레이터 종료 시작: {self.generator_id}")
        self.is_active = False
        await self.message_queue.put(None)  # 종료 신호
        print(f"[SSE_GEN] ✅ 제너레이터 종료 완료: {self.generator_id}")
