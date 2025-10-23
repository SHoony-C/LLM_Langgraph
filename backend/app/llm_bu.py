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
from langgraph.graph import END, StateGraph
from collections import defaultdict
from qdrant_client import QdrantClient
from app.utils.config import (
    OPENAI_API_KEY, OPENAI_BASE_URL,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
    IMAGE_BASE_URL, IMAGE_PATH_PREFIX, IS_OPENAI_CONFIGURED
)
from app.database import get_db
from app.models import Conversation, Message, User
from app.utils.auth import get_current_user
from sqlalchemy.orm import Session

from datetime import datetime

# Create router 
router = APIRouter()

# Redis 제거됨 - SSE 방식 사용

# 환경 변수 로딩 확인
print(f"[Config] OpenAI API Key: {'설정됨' if OPENAI_API_KEY else '설정되지 않음'}")
print(f"[Config] Qdrant: {QDRANT_HOST}:{QDRANT_PORT} (컬렉션: {QDRANT_COLLECTION or '설정되지 않음'})")

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

# 4차원 벡터 생성 함수
def generate_4d_vector(text: str) -> List[float]:
    """텍스트를 4차원 벡터로 변환"""
    import hashlib
    import struct
    
    # 텍스트를 해시로 변환하여 일관된 벡터 생성
    hash_obj = hashlib.md5(text.encode('utf-8'))
    hash_bytes = hash_obj.digest()
    
    # 4개의 float 값 생성 (0.0 ~ 1.0 범위)
    vector = []
    for i in range(4):
        # 4바이트씩 읽어서 float로 변환
        byte_chunk = hash_bytes[i*4:(i+1)*4]
        if len(byte_chunk) < 4:
            byte_chunk += b'\x00' * (4 - len(byte_chunk))
        
        # unsigned int로 변환 후 정규화
        uint_val = struct.unpack('>I', byte_chunk)[0]
        normalized_val = uint_val / (2**32 - 1)  # 0.0 ~ 1.0 범위로 정규화
        vector.append(normalized_val)
    
    return vector

# 벡터 기반 문서 검색 함수
async def direct_document_search(question_type: str, limit: int, queries: List[str], 
                               ip: str, port: int, collection: str) -> List[dict]:
    """벡터 기반 문서 검색"""
    try:
        print(f"[VECTOR_SEARCH] 벡터 검색 시작: {len(queries)}개 쿼리")
        
        # Qdrant 클라이언트 연결
        if ip.startswith(('http://', 'https://')):
            qdrant_url = f"{ip.rstrip('/')}" + (f":{port}" if not ip.endswith(f":{port}") else "")
            client = QdrantClient(url=qdrant_url)
        else:
            client = QdrantClient(host=ip, port=port)
        
        # 컬렉션 존재 확인
        try:
            collections = client.get_collections()
            if not collection or collection not in [col.name for col in collections.collections]:
                print(f"[VECTOR_SEARCH] 컬렉션 '{collection}' 사용 불가")
                return []
        except Exception as e:
            print(f"[VECTOR_SEARCH] Qdrant 연결 오류: {e}")
            return []
        
        all_results = []
        
        for query in queries:
            try:
                # 자체 4차원 벡터 생성
                query_vector = generate_4d_vector(query)
                
                # Qdrant에서 벡터 검색
                search_result = client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False
                )
                
                # 결과 변환
                for hit in search_result:
                    all_results.append({
                        'res_id': hit.id,
                        'res_score': hit.score,
                        'type_question': question_type,
                        'type_vector': 'custom_4d_vector',
                        'res_payload': hit.payload
                    })
                
                print(f"[VECTOR_SEARCH] '{query}' 검색 완료: {len(search_result)}건")
                
            except Exception as e:
                print(f"[VECTOR_SEARCH] 쿼리 '{query}' 검색 실패: {e}")
                # 벡터 검색 실패 시 텍스트 기반 검색으로 폴백
                fallback_results = await fallback_text_search([query], client, collection, limit)
                all_results.extend(fallback_results)
                continue
        
        # 점수 순으로 정렬하여 상위 결과 반환
        all_results.sort(key=lambda x: x['res_score'], reverse=True)
        final_results = all_results[:limit]
        
        print(f"[VECTOR_SEARCH] 최종 검색 결과: {len(final_results)}건")
        for i, result in enumerate(final_results[:3]):
            title = result['res_payload'].get('document_name', '제목없음')
            score = result['res_score']
            print(f"[VECTOR_SEARCH]   {i+1}. {title} (벡터 유사도: {score:.4f})")
        
        return final_results
        
    except Exception as e:
        print(f"[VECTOR_SEARCH] 검색 오류: {e}")
        return []

# 폴백용 텍스트 기반 검색
async def fallback_text_search(queries: List[str], client, collection: str, limit: int) -> List[dict]:
    """OpenAI API 미설정 시 폴백용 텍스트 검색"""
    try:
        # 모든 문서 가져오기
        scroll_result = client.scroll(
            collection_name=collection,
            limit=1000,
            with_payload=True
        )
        
        all_documents = []
        for point in scroll_result[0]:
            if point.payload:
                all_documents.append({
                    'id': point.id,
                    'payload': point.payload
                })
        
        if not all_documents:
            return []
        
        # 텍스트 기반 유사도 계산
        similarity_calc = DirectSimilarityCalculator()
        all_results = []
        
        for query in queries:
            query_results = similarity_calc.find_similar_documents(
                query=query,
                documents=[doc['payload'] for doc in all_documents],
                top_k=limit
            )
            
            for i, result in enumerate(query_results):
                if result['similarity'] > 0:  # 0점 제외
                    all_results.append({
                        'res_id': all_documents[i]['id'] if i < len(all_documents) else f"doc_{i}",
                        'res_score': result['similarity'],
                        'type_question': 'fallback',
                        'type_vector': 'text_similarity',
                        'res_payload': result['document']
                    })
        
        all_results.sort(key=lambda x: x['res_score'], reverse=True)
        return all_results[:limit]
        
    except Exception as e:
        print(f"[FALLBACK_SEARCH] 폴백 검색 오류: {e}")
        return []

# 기존 벡터 검색 함수들 제거 - 직접 검색으로 대체




# 스트리밍 요청을 위한 클래스
class StreamRequest(BaseModel):
    question: str
    conversation_id: Optional[int] = None
    generate_image: Optional[bool] = False  # 이미지 생성 플래그 추가
    # LangGraph 컨텍스트 필드 추가
    langgraph_context: Optional[dict] = None
    include_langgraph_context: Optional[bool] = False

# 이미지 URL (실제 이미지 생성 시스템에서 처리)
# SAMPLE_IMAGE_URLS = []

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

# SSE 스트리밍을 위한 전역 변수
sse_generators = {}

# SSE 상태 발행 함수
async def yield_node_status(generator_id: str, node_name: str, status: str, data: dict):
    """SSE를 통해 노드 상태를 발행"""
    # print(f"[SSE] 🔄 메시지 전송 시도: {node_name}:{status} (generator_id: {generator_id})")
    
    if generator_id not in sse_generators:
        print(f"[SSE] ❌ 제너레이터 ID가 없음 - {node_name}: {status}")
        print(f"[SSE] 현재 활성 제너레이터: {list(sse_generators.keys())}")
        return
        
    try:
        message = {
            "stage": node_name,
            "status": status,
            "result": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # print(f"[SSE] 📤 전송할 메시지: {message}")
        
        # SSE 제너레이터에 메시지 전송
        generator = sse_generators.get(generator_id)
        if generator and generator.is_active:
            await generator.send_message(message)
            # print(f"[SSE] ✅ 메시지 전송 성공: {node_name}:{status}")
            
            # 메시지가 큐에 제대로 들어갔는지 확인
            queue_size = generator.message_queue.qsize()
            # print(f"[SSE] 📊 메시지 큐 크기: {queue_size}")
            
            # 메시지 전송 후 지연 제거 - 빠른 스트리밍을 위해
        else:
            print(f"[SSE] ❌ 제너레이터가 유효하지 않음: {generator_id}")
            print(f"[SSE] 제너레이터 상태: active={generator.is_active if generator else 'None'}")
    except Exception as e:
        print(f"[SSE] ❌ 메시지 전송 실패: {node_name}:{status} - 오류: {e}")
        import traceback
        print(f"[SSE] 오류 상세: {traceback.format_exc()}")
        pass

# LangGraph 노드 함수들
async def node_rc_init(state: SearchState) -> SearchState:
    """초기화 노드"""
    print("[inform]: node_rc_init")
    
    
    # 단계 시작 상태 전송
    generator_id = state.get('generator_id')
    print(f"[NODE_INIT] 🔍 generator_id: {generator_id}")
    print(f"[NODE_INIT] 🔍 sse_generators 키: {list(sse_generators.keys())}")
    
    if generator_id:
        print(f"[NODE_INIT] 📤 A:started 메시지 전송 시작")
        await yield_node_status(
            generator_id,
            "A",
            "started",
            {
                "message": "초기화 단계 시작",
                "step": "A. 초기화"
            }
        )
        print(f"[NODE_INIT] ✅ A:started 메시지 전송 완료")
    else:
        print(f"[NODE_INIT] ❌ generator_id가 없음")
    
    try: 
        question = state['question']
        generator_id = state.get('generator_id')
        
        if generator_id:
            print(f"[NODE_INIT] 📤 A:completed 메시지 전송 시작")
            await yield_node_status(
                generator_id,
                "A",
                "completed",
                {
                    "message": "초기화 단계 완료",
                    "step": "A. 초기화 완료",
                    "question": question
                }
            )
            print(f"[NODE_INIT] ✅ A:completed 메시지 전송 완료")
        
        return {
            "question": question,
            "keyword": "",
            "candidates_each": [],
            "candidates_total": [],
            "response": [],
            "generator_id": state.get('generator_id')  # 상태에서 generator_id 유지
        }
    except Exception as e:
        print("[error]: node_rc_init")
        raise RuntimeError(f"[error]: node_rc_init: {str(e)}")

async def node_rc_keyword(state: SearchState) -> SearchState:
    """키워드 증강 노드 - LLM을 사용한 동적 키워드 생성"""
    print("[inform]: node_rc_keyword")
    
    
    # 단계 시작 상태 전송
    generator_id = state.get('generator_id')
    print(f"[NODE_KEYWORD] 🔍 generator_id: {generator_id}")
    
    if generator_id:
        print(f"[NODE_KEYWORD] 📤 B:started 메시지 전송 시작")
        await yield_node_status(
            generator_id,
            "B",
            "started",
            {
                "message": "키워드 증강 단계 시작",
                "step": "B. 키워드 증강",
                "question": state['question']
            }
        )
        print(f"[NODE_KEYWORD] ✅ B:started 메시지 전송 완료")
    else:
        print(f"[NODE_KEYWORD] ❌ generator_id가 없음")
    
    full_text_parts = []
    try:
        question = state['question']
        
        # OpenAI API 키 확인
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-api-key-here":
            print("[error]: OpenAI API 키가 설정되지 않았습니다.")
            # API 키가 없으면 기본 키워드만 반환
            base_keywords = [question]
            generator_id = state.get('generator_id')
            if generator_id:
                await yield_node_status(
                generator_id,
                "B",
                "completed",
                {
                    "message": "키워드 증강 단계 완료 (기본 모드)",
                    "step": "B. 키워드 증강 완료",
                    "keywords": base_keywords,
                    "keywords_count": len(base_keywords),
                    "reason": "OpenAI API 키 미설정"
                }
            )
            
            return {
                "question": state['question'],
                "keyword": base_keywords,
                "candidates_each": [],
                "candidates_total": [],
                "response": [],
                "generator_id": state.get('generator_id')  # 상태에서 generator_id 유지
            }
        
        try:
            # LLM을 사용하여 키워드 증강 - 새로운 LLM 방식
            messages = [
                {"role": "system", "content": "당신은 전문적인 키워드 분석가입니다. 주어진 질문을 분석하여 관련된 전문 키워드들을 생성해주세요. 각 키워드는 쉼표로 구분하고, 최대 15개까지 생성하세요."},
                {"role": "user", "content": f"다음 질문에 대한 관련 키워드들을 생성해주세요: {question}"}
            ]
            
            # httpx 클라이언트 설정
            httpx_client = httpx.AsyncClient(verify=False, timeout=None)

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
            # 스트림 청크 수신
            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if not content:
                    continue

                # 부분 응답 누적
                full_text_parts.append(content)

                # 너무 빡빡한 루프 방지
                await asyncio.sleep(0)

        except Exception as e:
            print(f"[error] streaming failed: {type(e).__name__}: {e}")
            full_text_parts = []

        # 스트리밍 종료 후 전체 응답 문자열 조립
        llm_response = "".join(full_text_parts).strip()

        # ⚙️ 키워드 변환 로직 (기존 동일)
        if not llm_response:
            augmented_keywords = [question]
        else:
            keywords_text = llm_response.strip()
            # 쉼표 기준 분리 및 정리
            augmented_keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
            # 원 질문 추가
            augmented_keywords.insert(0, question)
            # 중복 제거 및 20개 제한
            augmented_keywords = list(dict.fromkeys(augmented_keywords))[:20]

        print(f"[inform]: LLM을 통해 생성된 키워드: {len(augmented_keywords)}개")
        
        generator_id = state.get('generator_id')
        if generator_id:
            await yield_node_status(
                generator_id,
                "B",
                "completed",
                {
                    "message": "키워드 증강 단계 완료",
                    "step": "B. 키워드 증강 완료",
                    "keywords": augmented_keywords,
                    "keywords_count": len(augmented_keywords)
                }
            )
        
        return {
            "question": state['question'],
            "keyword": augmented_keywords,
            "candidates_each": [],
            "candidates_total": [],
            "response": [],
            "generator_id": state.get('generator_id')  # 상태에서 generator_id 유지
        }
    except Exception as e:
        print("[error]: node_rc_keyword")
        raise RuntimeError(f"[error]: node_rc_keyword: {str(e)}")

async def node_rc_rag(state: SearchState) -> SearchState:
    """RAG 검색 노드"""
    print("[inform]: node_rc_rag")
    
    
    # 단계 시작 상태 전송
    generator_id = state.get('generator_id')
    if generator_id:
        await yield_node_status(
            generator_id,
            "C",
            "started",
            {
                "message": "RAG 검색 단계 시작",
                "step": "C. RAG 검색",
                "keywords": state.get('keyword', [])
            }
        )
    
    try:
        # 벡터 DB 설정
        ip, port, collection = QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
        
        # 직접 검색 수행
        candidates_each = []
        
        # question으로 검색
        if state.get('question'):
            try:
                question_results = await direct_document_search('question', 5, [state['question']], ip, port, collection)
                candidates_each.extend(question_results)
            except Exception as e:
                print(f"Question 검색 오류: {e}")
        
        # keyword로 검색 (문자열 또는 리스트 처리)
        if state.get('keyword'):
            try:
                # keyword가 리스트인지 문자열인지 확인
                if isinstance(state['keyword'], list):
                    keywords = state['keyword']
                else:
                    keywords = [state['keyword']]
                
                # 빈 문자열이나 None 값 필터링
                keywords = [k for k in keywords if k and isinstance(k, str) and k.strip()]
                
                if keywords:
                    keyword_results = await direct_document_search('keyword', 3, keywords, ip, port, collection)
                    candidates_each.extend(keyword_results)
            except Exception as e:
                print(f"Keyword 검색 오류: {e}")
        
        # 검색 결과가 없는 경우 빈 리스트 반환 (하드코딩 제거)
        if not candidates_each:
            print("[RAG] 검색 결과가 없습니다.")

        # 동적 점수 집계 (하드코딩 제거)
        aggregated_scores = defaultdict(float)
        payloads = {}
        
        # candidates_each가 비어있지 않은 경우에만 처리
        if candidates_each:
            for item in candidates_each:
                try:
                    res_id = item.get('res_id')
                    score = item.get('res_score', 0.0)
                    
                    if res_id is not None and score > 0:
                        # 단순 점수 합산 (가중치 제거)
                        aggregated_scores[res_id] += score
                        if res_id not in payloads:
                            payloads[res_id] = item.get('res_payload', {})
                except Exception as e:
                    print(f"개별 결과 처리 오류: {e}")
                    continue
        
        # 유사도 순으로 정렬하여 상위 결과 선택 (고정 개수 제거)
        candidates_total = sorted(
            [{'res_id': res_id, 'res_score': aggregated_scores[res_id], 'res_payload': payloads[res_id]}
             for res_id in aggregated_scores],
            key=lambda x: x['res_score'],
            reverse=True
        )
        
        # 동적으로 결과 개수 결정 (최소 1개, 최대 10개)
        if candidates_total:
            max_results = min(len(candidates_total), max(1, min(10, len(candidates_total))))
            candidates_total = candidates_total[:max_results]
        
        print(f"[RAG] 최종 검색 결과 (상위 5건):")
        for i, candidate in enumerate(candidates_total):
            title = candidate.get('res_payload', {}).get('document_name', '제목 없음')
            vector_data = candidate.get("vector", {})
            # vector가 dict인지 확인 후 특정 키값만 추출
            summary = vector_data.get("summary_result") if isinstance(vector_data, dict) else None
            score = candidate.get('res_score', 0)
            print(f"  {i+1}. {title} - {summary} (유사도: {score:.4f})")
        
        generator_id = state.get('generator_id')
        if generator_id:
            await yield_node_status(
                generator_id,
                "C",
                "completed",
                {
                    "message": "RAG 검색 단계 완료",
                    "step": "C. RAG 검색 완료",
                    "documents_count": len(candidates_total),
                    "document_titles": [
                        candidate.get("res_payload", {}).get("document_name", "제목 없음")
                        for candidate in candidates_total
                    ],
                    "search_results": [
                        {
                            "title": candidate.get("res_payload", {}).get("document_name", "제목 없음"),
                            "text": candidate.get("res_payload", {}).get("vector", {}).get("text", "내용 없음"),
                            "summary": candidate.get("res_payload", {}).get("vector", {}).get("summary_result", "요약 없음"),
                            "image_url": candidate.get("res_payload", {}).get("vector", {}).get("image_url", ""),
                            "score": candidate.get("res_score", 0)
                        }
                        for candidate in candidates_total[:5]  # 상위 5개만
                    ]
                }
            )
        
        return {
            "question": state.get('question', ''),
            "keyword": state.get('keyword', ''),
            "candidates_total": candidates_total,
            "response": [],
            "generator_id": state.get('generator_id')
        }
    except Exception as e:
        print(f"[error]: node_rc_rag: {str(e)}")
        # 에러가 발생해도 기본 상태 반환하여 워크플로우 계속 진행
        return {
            "question": state.get('question', ''),
            "keyword": state.get('keyword', ''),
            "candidates_each": [],
            "candidates_total": [],
            "response": [],
            "generator_id": state.get('generator_id')
        }

async def node_rc_rerank(state: SearchState) -> SearchState:
    """동적 재순위 노드 (하드코딩 제거)"""
    print("[inform]: node_rc_rerank")
    
    
    # 단계 시작 상태 전송
    generator_id = state.get('generator_id')
    if generator_id:
        await yield_node_status(
            generator_id,
            "D",
            "started",
            {
                "message": "문서 재순위 단계 시작",
                "step": "D. 문서 재순위",
                "documents_count": len(state['candidates_total'])
            }
        )
    
    try:
        candidates_top = state['candidates_total']
        
        if not candidates_top:
            print("[RERANK] 재순위할 문서가 없습니다.")
            return {
                "question": state['question'],
                "keyword": state["keyword"],
                "candidates_total": state["candidates_total"],
                "response": [],
                "generator_id": state.get('generator_id')
            }
        
        # 유사도 기반 동적 재순위 (하드코딩된 0.1 감소 제거)
        similarity_calc = DirectSimilarityCalculator()
        question = state['question']
        
        for candidate in candidates_top:
            try:
                # 문서 텍스트 추출
                payload = candidate.get('res_payload', {})
                doc_title = payload.get('document_name', '')
                vector_data = payload.get("vector", {})
                # vector가 dict인지 확인 후 특정 키값만 추출
                doc_content = vector_data.get("text") if isinstance(vector_data, dict) else None

                doc_text = f"{doc_title} {doc_content}"
                
                # 질문과 문서 간 직접 유사도 계산
                relevance_score = similarity_calc.calculate_combined_similarity(question, doc_text)
                
                # 기존 검색 점수와 관련성 점수를 결합
                original_score = candidate.get('res_score', 0.0)
                combined_score = (original_score * 0.6) + (relevance_score * 0.4)
                
                candidate.update({
                    'res_relevance': relevance_score,
                    'combined_score': combined_score
                })
                
            except Exception as e:
                print(f"[RERANK] 개별 문서 재순위 오류: {e}")
                # 오류 시 기본값 설정
                candidate.update({
                    'res_relevance': candidate.get('res_score', 0.0),
                    'combined_score': candidate.get('res_score', 0.0)
                })
        
        # 결합 점수로 정렬 (하드코딩된 정렬 방식 제거)
        sorted_candidates_top = sorted(candidates_top, key=lambda x: x.get('combined_score', 0), reverse=True)
        
        print(f"[RERANK] 재순위 완료: {len(sorted_candidates_top)}개 문서")
        for i, candidate in enumerate(sorted_candidates_top[:3]):
            title = candidate.get('res_payload', {}).get('document_name', '제목없음')
            combined_score = candidate.get('combined_score', 0)
            relevance = candidate.get('res_relevance', 0)
            print(f"[RERANK]   {i+1}. {title} (결합점수: {combined_score:.4f}, 관련성: {relevance:.4f})")
        
        generator_id = state.get('generator_id')
        if generator_id:
            await yield_node_status(
                generator_id,
                "D",
                "completed",
                {
                    "message": "문서 재순위 단계 완료",
                    "step": "D. 문서 재순위 완료",
                    "documents_count": len(sorted_candidates_top),
                    "document_titles": [
                        candidate.get("res_payload", {}).get("document_name", "제목없음")
                        for candidate in sorted_candidates_top[:3]
                    ]
                }
            )
        
        return {
            "question": state['question'],
            "keyword": state["keyword"],
            "candidates_total": state["candidates_total"],
            "response": sorted_candidates_top,
            "generator_id": state.get('generator_id')
        }
    except Exception as e:
        print("[error]: node_rc_rerank")
        raise RuntimeError(f"[error]: node_rc_rerank: {str(e)}")

async def node_rc_answer(state: SearchState) -> SearchState:
    """답변 생성 노드 (랭그래프 전용) - 실시간 스트리밍 지원"""
    print("[inform]: node_rc_answer 실행")
    
    
    # 단계 시작 상태 전송
    generator_id = state.get('generator_id')
    if generator_id:
        await yield_node_status(
            generator_id,
            "E",
            "started",
            {
                "message": "답변 생성 단계 시작",
                "step": "E. 답변 생성",
                "search_results_count": len(state['response'])
            }
        )
    
    try:
        candidates_top = state['response']
        generator_id = state.get('generator_id')
        
        # 검색 결과가 있는 경우
        if candidates_top:
            print(f"[Answer] ✅ 검색 결과가 있습니다. LLM API 호출을 시작합니다.")
            
            # 상위 1건의 문서 정보 추출
            top_result = candidates_top[0]
            top_payload = top_result.get('res_payload', {})
            
            # 문서 제목과 내용 추출
            document_title = top_payload.get('document_name', '제목 없음')
            vector_data = top_payload.get("vector", {})
            document_content = vector_data.get("text") if isinstance(vector_data, dict) else None
            
            # LLM에 전송할 프롬프트 구성
            prompt = f"""
다음 문서를 참고하여 질문에 답변해주세요.

[참고 문서]
문서 제목: {document_title}
문서 내용: {str(document_content)[:1000]}...

[질문]
{state['question']}

위 문서를 바탕으로 질문에 대한 답변을 작성해주세요. 
답변은 다음과 같이 작성해주세요:
- 한국어로 구어체로 작성
- 형식적인 표현보다는 자연스럽고 이해하기 쉽게 설명
- 문서 내용을 바탕으로 구체적이고 유용한 답변 제공
- 답변만 작성하고 추가적인 헤더나 형식은 포함하지 마세요
            """.strip()
            
            # 실시간 스트리밍 답변 생성
            llm_answer = ""
            try:
                if IS_OPENAI_CONFIGURED:
                    print(f"[Answer] 🚀 실시간 스트리밍 LLM API 호출 시작...")
                    
                    messages = [{"role": "user", "content": prompt}]
                    
                    # httpx 클라이언트 설정 (타임아웃 추가)
                    httpx_client = httpx.AsyncClient(
                        verify=False, 
                        timeout=httpx.Timeout(30.0, connect=10.0)  # 연결 타임아웃 설정
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
                    
                    # 실시간 스트리밍 응답 처리
                    response = await client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        stream=True,
                    )
                    
                    # 스트리밍 청크를 실시간으로 SSE로 전송
                    async for chunk in response:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            llm_answer += content
                            
                            # 실시간으로 SSE를 통해 답변 청크 전송
                            if generator_id:
                                await yield_node_status(
                                    generator_id,
                                    "D",
                                    "streaming",
                                    {
                                        "message": "답변 생성 중...",
                                        "content": content,
                                        "accumulated_answer": llm_answer,
                                        "is_streaming": True
                                    }
                                )
                            
                            # 지연 제거 - 빠른 스트리밍을 위해
                    
                    print(f"[Answer] ✅ 실시간 스트리밍 완료")
                    
                else:
                    print(f"[Answer] ⚠️ OpenAI API 키가 설정되지 않음")
                    llm_answer = f"""입력하신 '{state['question']}'에 대한 답변입니다.

참고 문서: {document_title}

문서 내용을 바탕으로 분석한 결과, {str(document_content)[:200]}...에 대한 정보를 찾았습니다.

더 자세한 분석을 위해서는 OpenAI API 키가 필요합니다."""
                    
            except Exception as e:
                error_message = str(e)
                print(f"[Answer] ❌ LLM API 호출 실패: {error_message}")
                
                # 연결 오류 타입별 처리
                if "APIConnectionError" in error_message or "Connection error" in error_message:
                    error_desc = "AI 서비스에 연결할 수 없습니다. 네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요."
                elif "timeout" in error_message.lower():
                    error_desc = "AI 서비스 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
                elif "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
                    error_desc = "AI 서비스 인증에 문제가 있습니다. 관리자에게 문의해주세요."
                else:
                    error_desc = "AI 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                
                llm_answer = f"""입력하신 '{state['question']}'에 대한 답변입니다.

참고 문서: {document_title}

문서 내용을 바탕으로 분석한 결과, {str(document_content)[:200]}...에 대한 정보를 찾았습니다.

⚠️ {error_desc}"""
            
            # 이미지 URL 생성 (첫 번째 문서 기반)
            image_url = None
            if top_result and top_payload:
                doc_title = top_payload.get('document_name', '')
                doc_index = top_result.get('res_id', 0)
                
                if doc_title and doc_index:
                    import urllib.parse
                    import os
                    # .txt 확장자 제거하고 _whole.jpg로 대체
                    if doc_title.endswith('.txt'):
                        doc_title_without_ext = doc_title[:-4]  # .txt 제거
                        image_filename = f"{doc_title_without_ext}_whole.jpg"
                    else:
                        # 확장자가 없거나 다른 경우 그대로 사용
                        image_filename = doc_title
                    
                    safe_title = urllib.parse.quote(image_filename, safe='')
                    image_url = f"{IMAGE_BASE_URL}{IMAGE_PATH_PREFIX}/{safe_title}"
                    print(f"[Answer] 🖼️ 생성된 이미지 URL: {image_url}")

            # LangGraph 실행 결과를 위한 완전한 응답 구조
            response = {
                "res_id": [rest['res_id'] for rest in candidates_top],
                "answer": llm_answer,  # 실시간으로 생성된 전체 답변
                "q_mode": "search",
                "keyword": state["keyword"],
                "db_contents": [] ,
                "top_document": top_result,
                "analysis_image_url": image_url
            }
        else:
            print(f"[Answer] ⚠️ 검색 결과가 없습니다. 기본 답변을 생성합니다.")
            response = {
                "res_id": [],
                "answer": f"입력하신 '{state['question']}'에 대한 관련 문서를 찾을 수 없습니다.",
                "q_mode": "search",
                "keyword": state["keyword"],
            }
        
        # 최종 완료 상태 전송
        if generator_id:
            await yield_node_status(
                generator_id,
                "E",
                "completed",
                {
                    "message": "최종 답변 생성 완료",
                    "step": "E. 답변 생성 완료",
                    "answer": response.get("answer", ""),
                    "analysis_image_url": response.get("analysis_image_url"),
                    "keywords": response.get("keyword", state.get("keyword", [])),
                    "document_titles": [],  # 더 이상 사용하지 않음 (db_contents 사용)
                    "top_document": response.get("top_document"),
                    "is_streaming": False
                },
            )
        
        print(f"[Answer] ✅ node_rc_answer 함수 완료")
        
        return {
            "question": state['question'],
            "keyword": state["keyword"],
            "candidates_total": state["candidates_total"],
            "response": response,
            "generator_id": state.get('generator_id')
        }
        
    except Exception as e:
        print("[error]: node_rc_answer")
        import traceback
        print(f"[error] 상세 오류: {traceback.format_exc()}")
        raise RuntimeError(f"[error]: node_rc_answer: {str(e)}")

async def node_rc_plain_answer(state: SearchState) -> SearchState:
    """기본 답변 노드 (랭그래프 전용)"""
    print("[inform]: node_rc_plain_answer 실행")
    
    
    # 단계 시작 상태 전송
    generator_id = state.get('generator_id')
    if generator_id:
        await yield_node_status(
            generator_id,
            "E",
            "started",
            {
                "message": "기본 답변 생성 단계 시작",
                "step": "E. 기본 답변 생성",
                "reason": "검색 결과 없음"
            }
        )
    
    # 검색 결과가 없는 경우 더 구체적인 안내 메시지 생성
    question = state['question']
    keywords = state.get('keyword', [])
    
    if isinstance(keywords, list) and len(keywords) > 1:
        keyword_info = f"생성된 키워드: {', '.join(keywords[:5])}"
    else:
        keyword_info = f"생성된 키워드: {keywords}"
    
    detailed_answer = f"""🔍 **분석 결과 요약**

**입력 질문**: {question}

**키워드 증강**: {keyword_info}

**검색 결과**: 데이터베이스에서 관련 정보를 찾을 수 없습니다.

**개선 제안**:
1. **질문을 더 구체적으로 작성**해주세요
   - 예: "성과 개선" → "2024년 1분기 영업팀 성과 개선 방안"
   - 예: "전략 수립" → "신제품 출시를 위한 마케팅 전략 수립"

2. **관련 키워드를 추가**해주세요
   - 현재 키워드: {keywords[:3] if isinstance(keywords, list) else keywords}
   - 추가 키워드 예시: 구체적인 업무 영역, 기간, 부서명 등

3. **데이터베이스에 관련 문서가 있는지 확인**해주세요
   - 현재 설정된 벡터 DB: {QDRANT_HOST}:{QDRANT_PORT}
   - 컬렉션: {QDRANT_COLLECTION or '설정되지 않음'}

더 정확한 분석을 위해 구체적인 정보를 제공해주시면 도움이 됩니다."""
    
    # Redis를 통해 완료 상태 발행 (프론트엔드에서 DB 저장을 위해)
    complete_result = {
        "res_id": [], 
        "answer": detailed_answer,
        "q_mode": "search",  # 최초 질문은 항상 search 모드
        "keyword": state["keyword"],  # 키워드 증강 목록
    }
    
    # LangGraph 실행 결과는 프론트엔드에서 저장하도록 변경 (중복 저장 방지)
    # await save_langgraph_result_to_db(state['question'], complete_result, state["keyword"], state["candidates_total"])
    
    generator_id = state.get('generator_id')
    if generator_id:
        await yield_node_status(
                generator_id,
                "E",
                "completed",
                {
                    "message": "기본 답변 생성 단계 완료",
                    "step": "E. 기본 답변 생성 완료",
                    "answer": detailed_answer,
                    "keywords": state.get("keyword", []),
                    "reason": "검색 결과 없음"
                }
            )
    
    return {
        "question": state['question'],
        "keyword": state["keyword"],
        "candidates_total": state["candidates_total"],
        "response": {
            "res_id": [], 
            "answer": detailed_answer,
            "q_mode": "search",  # 최초 질문은 항상 search 모드
            "keyword": state["keyword"],  # 키워드 증강 목록
        },
        "generator_id": state.get('generator_id')
    }

def judge_rc_ragscore(state: SearchState) -> str:
    """벡터 기반 RAG 점수 판단"""
    candidates_total = state["candidates_total"]
    
    if not candidates_total:
        print(f"[JUDGE] 검색 결과 없음 -> N")
        return "N"
    
    # 벡터 유사도 점수 확인
    scores = [candidate.get("res_score", 0) for candidate in candidates_total]
    max_score = max(scores) if scores else 0
    avg_score = sum(scores) / len(scores) if scores else 0
    
    print(f"[JUDGE] 검색 결과 {len(candidates_total)}건")
    print(f"[JUDGE] 최고 벡터 점수: {max_score:.4f}, 평균: {avg_score:.4f}")
    
    # 벡터 유사도 기준 임계값 (일반적으로 0.7 이상이 높은 유사도)
    if max_score >= 0.7:
        print(f"[JUDGE] 높은 유사도 -> Y")
        return "Y"
    elif max_score >= 0.5:
        print(f"[JUDGE] 중간 유사도 -> Y")
        return "Y"
    elif max_score >= 0.3:
        print(f"[JUDGE] 낮은 유사도 -> Y")
        return "Y"
    else:
        print(f"[JUDGE] 매우 낮은 유사도 -> N")
        return "N"

async def save_langgraph_result_to_db_stream(question: str, result: dict, db: Session, user_id: int = 1):
    """LangGraph 스트리밍 결과를 DB에 저장"""
    try:
        print(f"[DB_SAVE_STREAM] 💾 LangGraph 스트리밍 결과 DB 저장 시작")
        print(f"[DB_SAVE_STREAM] - 질문: {question}")
        print(f"[DB_SAVE_STREAM] - 사용자 ID: {user_id}")
        
        # 결과에서 필요한 정보 추출
        response = result.get('response', {})
        keywords = result.get('keyword', [])
        candidates_total = result.get('candidates_total', [])
        
        if isinstance(response, dict):
            answer = response.get('answer', '')
            image_url = response.get('analysis_image_url')
        else:
            answer = str(response) if response else ''
            image_url = None
            
        print(f"[DB_SAVE_STREAM] - 답변 길이: {len(answer)}자")
        print(f"[DB_SAVE_STREAM] - 키워드: {len(keywords)}개")
        print(f"[DB_SAVE_STREAM] - 문서: {len(candidates_total)}건")
        
        # 검색 결과 전체 정보를 JSON 형식으로 저장
        db_contents_list = []
        if candidates_total:
            for idx, candidate in enumerate(candidates_total[:5]):  # 상위 5개만 저장
                payload = candidate.get('res_payload', {})
                vector_data = payload.get('vector', {})
                
                # image_url 처리 - Qdrant 구조에 맞게 수정
                image_url_value = ''
                if 'image_url' in payload:
                    # payload 최상위에 image_url이 있는 경우
                    img_url = payload.get('image_url', '')
                    if isinstance(img_url, list) and len(img_url) > 0:
                        image_url_value = img_url[0]  # 배열의 첫 번째 값 사용
                    elif isinstance(img_url, str):
                        image_url_value = img_url
                elif isinstance(vector_data, dict) and 'image_url' in vector_data:
                    # vector 내부에 image_url이 있는 경우
                    img_url = vector_data.get('image_url', '')
                    if isinstance(img_url, list) and len(img_url) > 0:
                        image_url_value = img_url[0]
                    elif isinstance(img_url, str):
                        image_url_value = img_url
                
                db_content = {
                    'rank': idx + 1,
                    'document_name': payload.get('document_name', ''),
                    'score': candidate.get('res_score', 0),
                    'combined_score': candidate.get('combined_score', candidate.get('res_score', 0)),
                    'relevance_score': candidate.get('res_relevance', 0),
                    'text': vector_data.get('text', '') if isinstance(vector_data, dict) else '',
                    'summary_purpose': vector_data.get('summary_purpose', '') if isinstance(vector_data, dict) else '',
                    'summary_result': vector_data.get('summary_result', '') if isinstance(vector_data, dict) else '',
                    'summary_fb': vector_data.get('summary_fb', '') if isinstance(vector_data, dict) else '',
                    'image_url': image_url_value,  # Qdrant 구조에 맞게 처리된 이미지 URL
                    'res_id': candidate.get('res_id', '')
                }
                db_contents_list.append(db_content)
        
        db_contents_json = json.dumps(db_contents_list, ensure_ascii=False)
        print(f"[DB_SAVE_STREAM] - 검색 결과 JSON 길이: {len(db_contents_json)}자")
        
        # 새 대화 생성
        from datetime import datetime
        title = question[:50] + "..." if len(question) > 50 else question
        conversation = Conversation(
            title=title,
            user_id=user_id,  # 실제 사용자 ID 사용
            last_updated=datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        # 사용자 정보 가져오기
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        user_name = user.loginid if user and user.loginid else (user.username if user else "system")
        
        print(f"[DB_SAVE_STREAM] - 사용자명: {user_name}")
        
        # 메시지 저장 (q_mode: 'search' - 랭그래프 전용)
        message = Message(
            conversation_id=conversation.id,
            role="user",
            question=question,
            ans=answer,
            q_mode='search',  # 랭그래프 전용 모드
            keyword=str(keywords) if keywords else None,
            db_contents=db_contents_json,  # 검색 결과 전체 정보 저장
            image=image_url,
            user_name=user_name  # 실제 사용자명
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        print(f"[DB_SAVE_STREAM] ✅ LangGraph 스트리밍 결과 DB 저장 완료")
        print(f"[DB_SAVE_STREAM] - 대화 ID: {conversation.id}")
        print(f"[DB_SAVE_STREAM] - 메시지 ID: {message.id}")
        
    except Exception as e:
        print(f"[DB_SAVE_STREAM] ❌ LangGraph 스트리밍 결과 DB 저장 실패: {str(e)}")
        import traceback
        print(f"[DB_SAVE_STREAM] 오류 상세: {traceback.format_exc()}")
        if db:
            db.rollback()

async def save_langgraph_result_to_db(question: str, response: dict, keywords: list, candidates_total: list, image_url: str = None):
    """LangGraph 실행 결과를 DB에 직접 저장 (랭그래프 전용)"""
    try:
        print(f"[DB_SAVE] LangGraph 결과 DB 저장 시작 (랭그래프 전용)")
        print(f"[DB_SAVE] 질문: {question}")
        print(f"[DB_SAVE] 응답: {response.get('answer', '')[:100]}...")
        print(f"[DB_SAVE] 키워드: {keywords}")
        print(f"[DB_SAVE] 문서: {len(candidates_total)}건")
        print(f"[DB_SAVE] 이미지 URL: {image_url}")
        
        # 검색 결과 전체 정보를 JSON 형식으로 저장
        db_contents_list = []
        if candidates_total:
            for idx, candidate in enumerate(candidates_total[:5]):  # 상위 5개만 저장
                payload = candidate.get('res_payload', {})
                vector_data = payload.get('vector', {})
                
                # image_url 처리 - Qdrant 구조에 맞게 수정
                image_url_value = ''
                if 'image_url' in payload:
                    # payload 최상위에 image_url이 있는 경우
                    img_url = payload.get('image_url', '')
                    if isinstance(img_url, list) and len(img_url) > 0:
                        image_url_value = img_url[0]  # 배열의 첫 번째 값 사용
                    elif isinstance(img_url, str):
                        image_url_value = img_url
                elif isinstance(vector_data, dict) and 'image_url' in vector_data:
                    # vector 내부에 image_url이 있는 경우
                    img_url = vector_data.get('image_url', '')
                    if isinstance(img_url, list) and len(img_url) > 0:
                        image_url_value = img_url[0]
                    elif isinstance(img_url, str):
                        image_url_value = img_url
                
                db_content = {
                    'rank': idx + 1,
                    'document_name': payload.get('document_name', ''),
                    'score': candidate.get('res_score', 0),
                    'combined_score': candidate.get('combined_score', candidate.get('res_score', 0)),
                    'relevance_score': candidate.get('res_relevance', 0),
                    'text': vector_data.get('text', '') if isinstance(vector_data, dict) else '',
                    'summary_purpose': vector_data.get('summary_purpose', '') if isinstance(vector_data, dict) else '',
                    'summary_result': vector_data.get('summary_result', '') if isinstance(vector_data, dict) else '',
                    'summary_fb': vector_data.get('summary_fb', '') if isinstance(vector_data, dict) else '',
                    'image_url': image_url_value,  # Qdrant 구조에 맞게 처리된 이미지 URL
                    'res_id': candidate.get('res_id', '')
                }
                db_contents_list.append(db_content)
        
        db_contents_json = json.dumps(db_contents_list, ensure_ascii=False)
        print(f"[DB_SAVE] - 검색 결과 JSON 길이: {len(db_contents_json)}자")
        
        # 새 대화 생성 또는 기존 대화 찾기
        db = next(get_db())
        
        # 새 대화 생성
        from datetime import datetime
        title = question[:50] + "..." if len(question) > 50 else question
        conversation = Conversation(
            title=title,
            user_id=1,  # 기본 사용자 ID (실제로는 인증된 사용자 ID 사용)
            last_updated=datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        # 메시지 저장 (q_mode: 'search' - 랭그래프 전용)
        message = Message(
            conversation_id=conversation.id,
            role="user",
            question=question,
            ans=response.get('answer', ''),
            q_mode='search',  # 랭그래프 전용 모드
            keyword=str(keywords) if keywords else None,
            db_contents=db_contents_json,  # 검색 결과 전체 정보 저장
            image=image_url,  # 이미지 URL 추가
            user_name="system"  # 기본 사용자명
        )
        
        db.add(message)
        db.commit()
        
        print(f"[DB_SAVE] ✅ LangGraph 결과 DB 저장 완료 (랭그래프 전용)")
        print(f"[DB_SAVE] 대화 ID: {conversation.id}")
        print(f"[DB_SAVE] 메시지 ID: {message.id}")
        print(f"[DB_SAVE] q_mode: {message.q_mode} (랭그래프 전용)")
        
    except Exception as e:
        print(f"[DB_SAVE] ❌ LangGraph 결과 DB 저장 실패: {str(e)}")
        import traceback
        print(f"[DB_SAVE] 오류 상세: {traceback.format_exc()}")


# LangGraph 구성
def create_langgraph():
    """LangGraph 생성"""
    workflow = StateGraph(SearchState)
    
    # 노드 추가
    workflow.add_node("node_rc_init", node_rc_init)
    workflow.add_node("node_rc_keyword", node_rc_keyword)
    workflow.add_node("node_rc_rag", node_rc_rag)
    workflow.add_node("node_rc_rerank", node_rc_rerank)
    workflow.add_node("node_rc_answer", node_rc_answer)
    workflow.add_node("node_rc_plain_answer", node_rc_plain_answer)
    
    # 엣지 정의
    workflow.set_entry_point("node_rc_init")
    workflow.add_edge("node_rc_init", "node_rc_keyword")
    workflow.add_edge("node_rc_keyword", "node_rc_rag")
    workflow.add_conditional_edges(
        "node_rc_rag",
        judge_rc_ragscore,
        {
            "Y": "node_rc_rerank",
            "N": "node_rc_plain_answer"
        }
    )
    workflow.add_edge("node_rc_rerank", "node_rc_answer")
    workflow.add_edge("node_rc_answer", END)
    workflow.add_edge("node_rc_plain_answer", END)
    
    return workflow.compile()

# LangGraph 인스턴스 생성
try:
    langgraph_instance = create_langgraph()
    print("[LangGraph] 워크플로우 생성 완료")
except Exception as e:
    print(f"[LangGraph] 워크플로우 생성 실패: {e}")
    langgraph_instance = None

# 간단한 LLM 응답 함수 (conversations.py에서 사용)
async def get_llm_response(question: str) -> str:
    """간단한 LLM 응답 생성 함수"""
    try:
        
        print(f"[LLM_RESPONSE] 질문: {question}")
        
        messages = [
            {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다."},
            {"role": "user", "content": question}
        ]
        
        # httpx 클라이언트 설정
        httpx_client = httpx.AsyncClient(verify=False, timeout=None)

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
        
        async for chunk in response:              # 이제 chunk는 OpenAIObject
                    delta = chunk.choices[0].delta
                    content = delta.content
                    # print(content)
                # for chunk in response:
                #     if chunk.choices[0].delta.get("content"):
                #         content = chunk.choices[0].delta.content
                    try:
                        # 비-ASCII 문자 허용, UTF-8 bytes 로 즉시 전송
                        payload = json.dumps({'content': content}, ensure_ascii=False)
                        yield (f"data: {payload}\n\n").encode("utf-8")

                        # 지연 제거 - 빠른 스트리밍을 위해
                    except (ConnectionResetError, BrokenPipeError, OSError, ConnectionAbortedError, ConnectionError) as e:
                        # 클라이언트 연결이 끊어진 경우 조용히 종료
                        print(f"Client disconnected during streaming lv2: {type(e).__name__}")
                        return
                    except Exception as e:
                        print(f"Unexpected error during streaming lv1: {str(e)}")
                        return
        
    except Exception as e:
        error_message = str(e)
        print(f"[LLM_RESPONSE] 오류: {error_message}")
        
        # 연결 오류 타입별 처리
        if "APIConnectionError" in error_message or "Connection error" in error_message:
            yield f"죄송합니다. AI 서비스에 연결할 수 없습니다. 네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요."
        elif "timeout" in error_message.lower():
            yield f"죄송합니다. AI 서비스 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        elif "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
            yield f"죄송합니다. AI 서비스 인증에 문제가 있습니다. 관리자에게 문의해주세요."
        else:
            yield f"죄송합니다. 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."




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



# 질문 유형 판별 함수
def is_first_question_in_conversation(conversation_id: int, db: Session) -> bool:
    """대화에서 첫 번째 질문인지 확인"""
    try:
        message_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
        print(f"[QUESTION_TYPE] 대화 ID {conversation_id}의 메시지 수: {message_count}")
        return message_count == 0
    except Exception as e:
        print(f"[QUESTION_TYPE] 메시지 수 확인 오류: {e}")
        return True  # 오류 시 첫 번째 질문으로 간주

def get_conversation_context(conversation_id: int, db: Session) -> dict:
    """대화의 컨텍스트와 히스토리 가져오기"""
    try:
        # 해당 대화의 모든 메시지 가져오기 (시간순 정렬)
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        print(f"[CONTEXT] 대화 ID {conversation_id}의 메시지 {len(messages)}개 로드")
        
        # 디버깅을 위한 메시지 상세 정보
        if len(messages) > 0:
            print(f"[CONTEXT] 메시지 상세:")
            for i, msg in enumerate(messages):
                print(f"[CONTEXT]   {i+1}. ID: {msg.id}, q_mode: {msg.q_mode}, role: {msg.role}, question: {msg.question[:50] if msg.question else 'None'}...")
        else:
            print(f"[CONTEXT] ⚠️ 메시지가 없습니다. 대화 ID {conversation_id} 확인 필요")
        
        # 첫 번째 질문 찾기 (q_mode가 "search"인 메시지)
        first_message = None
        for msg in messages:
            if msg.q_mode == "search":
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
            "message_count": len(messages)
        }
        
    except Exception as e:
        print(f"[CONTEXT] 대화 컨텍스트 로드 오류: {e}")
        return {
            "first_message": None,
            "conversation_history": [],
            "message_count": 0
        }

# SSE 스트리밍 엔드포인트 (첫 번째 질문용)
@router.post("/langgraph/stream")
async def execute_langgraph_stream(request: StreamRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """LangGraph SSE 스트리밍 실행 (첫 번째 질문 전용)"""
    
    async def generate_sse():
        generator_id = str(uuid.uuid4())
        print(f"[SSE] 🆔 새 제너레이터 생성: {generator_id}")
        generator = SSEGenerator(generator_id)
        sse_generators[generator_id] = generator
        print(f"[SSE] 📋 현재 활성 제너레이터 수: {len(sse_generators)}")
        
        try:
            # OpenAI API 키 확인
            if not OPENAI_API_KEY:
                yield f"data: {json.dumps({'error': 'OpenAI API 키가 설정되지 않았습니다.'})}\n\n"
                return
            
            print(f"[SSE] 🚀 LangGraph SSE 스트리밍 시작: {request.question}")
            
            # 대화 ID가 있는 경우 질문 유형 확인
            if request.conversation_id:
                is_first = is_first_question_in_conversation(request.conversation_id, db)
                if not is_first:
                    yield f"data: {json.dumps({'error': '추가 질문은 /langgraph/followup 엔드포인트를 사용하세요'})}\n\n"
                    return
            
            # 워크플로우 확인
            if langgraph_instance is None:
                yield f"data: {json.dumps({'error': 'LangGraph 워크플로우가 초기화되지 않았습니다.'})}\n\n"
                return
            
            # 초기 상태에 generator_id 추가
            initial_state = {
                "question": request.question,
                "keyword": "",
                "candidates_each": [],
                "candidates_total": [],
                "response": [],
                "generator_id": generator_id
            }
            print(f"[SSE] 📋 초기 상태 설정: generator_id={generator_id}")
            
            print(f"[SSE] LangGraph 실행 시작: {request.question}")
            
            # 테스트 메시지 먼저 전송
            test_message = {
                "stage": "TEST",
                "status": "started", 
                "result": {"message": "SSE 연결 테스트"}
            }
            print(f"[SSE] 🧪 테스트 메시지 전송")
            await generator.send_message(test_message)
            
            # LangGraph 실행을 별도 태스크로 실행
            async def run_langgraph():
                try:
                    print(f"[LANGGRAPH] 🚀 LangGraph 실행 시작 (generator_id: {generator_id})")
                    print(f"[LANGGRAPH] 📋 초기 상태: {initial_state}")
                    
                    # LangGraph 실행 전 제너레이터 상태 확인
                    print(f"[LANGGRAPH] 🔍 실행 전 제너레이터 상태: active={generator.is_active}, queue_size={generator.message_queue.qsize()}")
                    
                    result = await langgraph_instance.ainvoke(initial_state)
                    
                    print(f"[LANGGRAPH] ✅ LangGraph 실행 완료")
                    print(f"[LANGGRAPH] 📊 결과 요약: keyword={len(result.get('keyword', []))}개, candidates={len(result.get('candidates_total', []))}개")
                    print(f"[LANGGRAPH] 🔍 실행 후 제너레이터 상태: active={generator.is_active}, queue_size={generator.message_queue.qsize()}")
                    
                    # LangGraph 결과를 DB에 저장
                    try:
                        print(f"[LANGGRAPH] 💾 LangGraph 결과 DB 저장 시작")
                        await save_langgraph_result_to_db_stream(
                            initial_state["question"], 
                            result, 
                            db,
                            current_user.id  # 실제 사용자 ID 전달
                        )
                        print(f"[LANGGRAPH] ✅ LangGraph 결과 DB 저장 완료")
                    except Exception as e:
                        print(f"[LANGGRAPH] ❌ DB 저장 실패: {str(e)}")
                        # DB 저장 실패해도 계속 진행
                    
                    # DONE 메시지에 전체 LangGraph 결과 포함
                    done_message = {
                        "stage": "DONE", 
                        "result": result,  # 전체 LangGraph 결과 포함
                        "keyword": result.get('keyword', []),
                        "candidates_total": result.get('candidates_total', [])
                    }
                    print(f"[LANGGRAPH] 📤 DONE 메시지 전송 시도 (큐 크기: {generator.message_queue.qsize()})")
                    await generator.send_message(done_message)
                    print(f"[LANGGRAPH] ✅ DONE 메시지 전송 완료 (큐 크기: {generator.message_queue.qsize()})")
                    
                except Exception as e:
                    print(f"[LANGGRAPH] ❌ LangGraph 실행 오류: {e}")
                    import traceback
                    print(f"[LANGGRAPH] 오류 상세: {traceback.format_exc()}")
                    error_message = {"stage": "ERROR", "error": str(e)}
                    print(f"[LANGGRAPH] 📤 ERROR 메시지 전송 시도")
                    await generator.send_message(error_message)
                finally:
                    print(f"[LANGGRAPH] 🔚 제너레이터 종료 시작")
                    await generator.close()
                    print(f"[LANGGRAPH] ✅ 제너레이터 종료 완료")
            
            # LangGraph 실행 태스크 시작 (백그라운드에서 실행)
            langgraph_task = asyncio.create_task(run_langgraph())
            print(f"[SSE] 🚀 LangGraph 태스크 시작됨")
            
            # 짧은 지연 후 SSE 스트리밍 시작 (LangGraph가 시작할 시간을 줌)
            await asyncio.sleep(0.01)  # 0.1초 → 0.01초로 단축
            
            # SSE 메시지 스트리밍
            print(f"[SSE] 📡 SSE 스트리밍 루프 시작")
            message_count = 0
            heartbeat_count = 0
            
            # LangGraph 태스크가 실행 중이거나 제너레이터가 활성화된 동안 계속 실행
            while generator.is_active or not langgraph_task.done():
                try:
                    # 현재 상태 로깅
                    current_queue_size = generator.message_queue.qsize()
                    task_done = langgraph_task.done()
                    # print(f"[SSE] 🔄 루프 상태: generator_active={generator.is_active}, task_done={task_done}, queue_size={current_queue_size}")
                    
                    # 타임아웃을 늘려서 메시지를 놓치지 않도록 함
                    message = await asyncio.wait_for(generator.message_queue.get(), timeout=1.0)
                    
                    if message is None:  # 종료 신호
                        print(f"[SSE] 🔚 종료 신호 수신")
                        break
                    
                    message_count += 1
                    # print(f"[SSE] 📨 메시지 #{message_count} 수신: {message.get('stage', 'unknown')}:{message.get('status', 'unknown')}")
                    # print(f"[SSE] 📋 메시지 내용: {json.dumps(message, ensure_ascii=False)[:200]}...")
                    
                    # SSE 형식으로 메시지 전송
                    sse_data = f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                    # print(f"[SSE] 📤 클라이언트로 전송: {len(sse_data)} bytes")
                    yield sse_data
                    # print(f"[SSE] ✅ 클라이언트 전송 완료")
                    
                    # 메시지 전송 후 짧은 지연 제거 - 빠른 스트리밍을 위해
                    
                except asyncio.TimeoutError:
                    # 타임아웃 시 하트비트 전송 (10번마다 한 번씩만 로그)
                    heartbeat_count += 1
                    current_queue_size = generator.message_queue.qsize()
                    task_done = langgraph_task.done()
                    
                    if heartbeat_count % 10 == 0:
                        print(f"[SSE] 💓 하트비트 #{heartbeat_count} - 메시지:{message_count}, 큐:{current_queue_size}, 태스크완료:{task_done}")
                    
                    yield f"data: {json.dumps({'heartbeat': True, 'count': heartbeat_count, 'queue_size': current_queue_size, 'task_done': task_done})}\n\n"
                    continue
                except Exception as e:
                    print(f"[SSE] ❌ 메시지 처리 오류: {e}")
                    import traceback
                    print(f"[SSE] 오류 상세: {traceback.format_exc()}")
                    break
            
            print(f"[SSE] 📊 총 {message_count}개 메시지, {heartbeat_count}개 하트비트 처리 완료")
            
            # 최종 완료 메시지
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            print(f"[SSE] 스트리밍 오류: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # 정리
            if generator_id in sse_generators:
                del sse_generators[generator_id]
            print(f"[SSE] 스트리밍 종료: {generator_id}")
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# LangGraph 직접 실행 엔드포인트 (첫 번째 질문용) - 기존 유지
@router.post("/langgraph")
async def execute_langgraph(request: StreamRequest, db: Session = Depends(get_db)):
    """LangGraph를 직접 실행하여 결과 반환 (첫 번째 질문 전용)"""
    try:
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=400, detail="OpenAI API 키가 설정되지 않았습니다.")
        
        print(f"[LangGraph] 🚀 랭그래프 실행 시작: {request.question}")
        
        # 대화 ID가 있는 경우 질문 유형 확인
        if request.conversation_id:
            is_first = is_first_question_in_conversation(request.conversation_id, db)
            if not is_first:
                print(f"[LangGraph] ⚠️ 추가 질문 감지됨 - LangGraph 실행 차단")
                raise HTTPException(
                    status_code=400, 
                    detail="추가 질문은 /langgraph/followup 엔드포인트를 사용하세요"
                )
        
        # 워크플로우 확인
        if langgraph_instance is None:
            raise HTTPException(status_code=500, detail="LangGraph 워크플로우가 초기화되지 않았습니다.")
        
        initial_state = {"question": request.question}
        print(f"[LangGraph] 실행 시작: {request.question}")
        print(f"[LangGraph] 초기 상태: {initial_state}")
        
        result = await langgraph_instance.ainvoke(initial_state)
        
        print(f"[LangGraph] ✅ 실행 완료")
        
        # 결과에서 태그와 문서 타이틀 추출
        tags = None
        
        if isinstance(result, dict):
            # 키워드 정보에서 태그 추출
            if 'keyword' in result and result['keyword']:
                if isinstance(result['keyword'], list):
                    tags = ', '.join(result['keyword'])
                else:
                    tags = str(result['keyword'])
                print(f"[LangGraph] 키워드: {len(result['keyword'])}개")
            
            # RAG 검색 결과 확인
            if 'candidates_total' in result and result['candidates_total']:
                print(f"[LangGraph] 문서: {len(result['candidates_total'])}건")
            
            # 응답 정보 확인
            if 'response' in result and result['response']:
                response_text = result['response'].get('answer', '')[:50] if isinstance(result['response'], dict) else str(result['response'])[:50]
                print(f"[LangGraph] 응답: {response_text}...")
        
        print(f"[LangGraph] 요약: 키워드 {len(result.get('keyword', []))}개, 문서 {len(result.get('candidates_total', []))}건")
        
        return {
            "status": "success",
            "result": result,
            "tags": tags,
            "message": "LangGraph 실행 완료 (첫 번째 질문)"
        }
        
    except Exception as e:
        print(f"[LangGraph] 실행 오류: {str(e)}")
        import traceback
        print(f"[LangGraph] 오류 상세: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"LangGraph 실행 오류: {str(e)}")


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
        
        # 기존 대화 컨텍스트에서 RAG 정보 추출
        context = get_conversation_context(request.conversation_id, db)
        
        if not context["first_message"]:
            print(f"[FOLLOWUP_STREAM] ⚠️ 첫 번째 질문 없음")
            return Response(content="Error: 첫 번째 질문을 찾을 수 없습니다", media_type="text/plain")
        
        # 첫 번째 질문의 RAG 검색 결과 활용
        first_message = context["first_message"]
        
        # DB에서 첫 번째 질문과 관련된 RAG 검색 결과 재구성
        print(f"[FOLLOWUP_STREAM] 📄 첫 번째 질문 RAG 정보:")
        print(f"[FOLLOWUP_STREAM]   질문: {first_message.question}")
        print(f"[FOLLOWUP_STREAM]   키워드: {first_message.keyword}")
        print(f"[FOLLOWUP_STREAM]   검색 문서: {first_message.db_contents}")
        
        # 실제 RAG 문서 내용 구성 (DB에서 실제 검색 결과 재사용)
        document_title = "검색된 문서"
        
        # 첫 번째 질문의 키워드로 다시 검색하여 실제 문서 내용 가져오기
        try:
            # 첫 번째 질문의 키워드 파싱
            keywords_str = first_message.keyword or first_message.question
            if keywords_str and keywords_str != 'None':
                # 간단한 키워드 추출 (리스트 형태라면 파싱)
                if keywords_str.startswith('[') and keywords_str.endswith(']'):
                    import ast
                    keywords = ast.literal_eval(keywords_str)
                else:
                    keywords = [keywords_str]
                
                # 실제 RAG 검색 수행
                rag_results = await direct_document_search('followup', 1, keywords[:3], QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION)
                
                if rag_results and len(rag_results) > 0:
                    top_doc = rag_results[0]['res_payload']
                    actual_document_content = ""
                    
                    # 실제 문서 내용 추출
                    if 'vector' in top_doc and isinstance(top_doc['vector'], dict):
                        vector_data = top_doc['vector']
                        for field in ['text', 'summary_purpose', 'summary_result', 'summary_fb']:
                            if field in vector_data and vector_data[field]:
                                actual_document_content += f"{vector_data[field]} "
                    
                    actual_document_content = actual_document_content.strip() or "문서 내용 없음"
                else:
                    actual_document_content = "문서 내용을 찾을 수 없습니다"
            else:
                actual_document_content = "키워드 정보 없음"
                
        except Exception as e:
            print(f"[FOLLOWUP_STREAM] RAG 재검색 오류: {e}")
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
    """스트리밍 완료 후 메시지를 DB에 저장"""
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
        
        existing_message = db.query(Message).filter(
            Message.conversation_id == stream_request.conversation_id,
            Message.question == stream_request.question,
            Message.created_at >= recent_time
        ).first()
        
        if existing_message:
            print(f"[DB_SAVE] ⚠️ 중복 메시지 감지됨. 기존 메시지 ID: {existing_message.id}")
            return
        
        # 메시지 생성 및 저장
        # q_mode는 conversation_id가 있는 경우 'add', 없는 경우 None
        # conversation_id가 있으면 기존 대화에 추가 질문이므로 'add'
        # conversation_id가 없으면 새 대화이므로 None (첫 번째 질문)
        q_mode_value = "add" if stream_request.conversation_id else None
        
        print(f"[DB_SAVE] - q_mode: {q_mode_value} (conversation_id: {stream_request.conversation_id})")
        
        message = Message(
            conversation_id=stream_request.conversation_id,
            role="user",
            question=stream_request.question,
            ans=assistant_response,
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

async def generate_image(prompt: str) -> str:
    """Generate an image using OpenAI DALL-E API"""
    try:
        # 실제 구현에서는 이 부분에서 OpenAI DALL-E API 호출
        # 예시: 
        # client = OpenAI(api_key=OPENAI_API_KEY)
        # response = client.images.generate(prompt=prompt, n=1, size="1024x1024")
        # image_url = response.data[0].url
        
        # 이미지 URL 반환 (실제 이미지 생성 시스템에서 처리)
        return None
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None

async def get_streaming_response_with_db_save(messages: List[Dict], request: Request, stream_request: StreamRequest, db: Session, current_user: User = None):
    """Stream a response from LLM using AsyncOpenAI with custom headers and save to DB"""
    try:
        print(f"[LLM_STREAM_DB] 🚀 LLM 스트리밍 시작 (DB 저장 포함)")
        
        # 이미지 URL (이미지 생성이 요청된 경우)
        image_url = None
        if stream_request.generate_image:
            # 실제 이미지 생성 로직은 별도 구현 필요
            image_url = await generate_image(messages[-1]["content"] if messages else "")
        
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
        
        # 스트리밍 완료 후 DB에 저장
        try:
            print(f"[LLM_STREAM_DB] 💾 DB 저장 시작")
            await save_message_to_db(stream_request, text_response, image_url, db, current_user)
            print(f"[LLM_STREAM_DB] ✅ DB 저장 완료")
        except Exception as e:
            print(f"[LLM_STREAM_DB] ❌ DB 저장 실패: {str(e)}")
            # DB 저장 실패해도 스트리밍은 계속 진행
        
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
            # 실제 이미지 생성 로직은 별도 구현 필요
            image_url = await generate_image(messages[-1]["content"] if messages else "")
        
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
