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
    IMAGE_BASE_URL, IMAGE_PATH_PREFIX
)
from app.database import get_db
from app.models import Conversation, Message
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
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text.lower())
        # 토큰화
        tokens = text.split()
        # 불용어 제거 및 길이 2 이상 토큰만 유지
        tokens = [token for token in tokens if token not in self.stopwords and len(token) >= 2]
        return tokens
    
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
            # 문서 텍스트 추출 (제목 + 내용)document_name
            doc_title = doc.get('document_name', '')
            vector_data = doc.get("vector", {})
            # vector가 dict인지 확인 후 특정 키값만 추출
            doc_content = vector_data.get("text") if isinstance(vector_data, dict) else None
            doc_text = f"{doc_title} {doc_content}"
            
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

# 직접 구현한 문서 검색 함수
async def direct_document_search(question_type: str, limit: int, queries: List[str], 
                               ip: str, port: int, collection: str) -> List[dict]:
    """직접 구현한 문서 검색 (유사도 기반)"""
    try:
        print(f"[DIRECT_SEARCH] 직접 검색 시작: {len(queries)}개 쿼리")
        
        # Qdrant에서 모든 문서 가져오기
        client = QdrantClient(host=ip, port=port)
        
        # 컬렉션 존재 확인
        try:
            collections = client.get_collections()
            print(f"[DIRECT_SEARCH] 사용 가능한 컬렉션: {[col.name for col in collections.collections]}")
            
            if not collection or collection not in [col.name for col in collections.collections]:
                print(f"[DIRECT_SEARCH] 컬렉션 '{collection}' 사용 불가")
                return []
                
        except Exception as e:
            print(f"[DIRECT_SEARCH] Qdrant 연결 오류: {e}")
            return []
        
        # 모든 문서 가져오기 (스크롤 방식)
        all_documents = []
        try:
            scroll_result = client.scroll(
                collection_name=collection,
                limit=1000,  # 한 번에 가져올 문서 수
                with_payload=True
            )
            
            for point in scroll_result[0]:
                if point.payload:
                    all_documents.append({
                        'id': point.id,
                        'payload': point.payload
                    })
            
            print(f"[DIRECT_SEARCH] 총 {len(all_documents)}개 문서 로드")
            
        except Exception as e:
            print(f"[DIRECT_SEARCH] 문서 로드 오류: {e}")
            return []
        
        if not all_documents:
            print(f"[DIRECT_SEARCH] 검색할 문서가 없습니다")
            return []
        
        # 유사도 계산기 초기화
        similarity_calc = DirectSimilarityCalculator()
        
        # 각 쿼리에 대해 유사도 계산
        all_results = []
        for query in queries:
            print(f"[DIRECT_SEARCH] 쿼리 처리: {query}")
            
            # 문서들과 유사도 계산
            query_results = similarity_calc.find_similar_documents(
                query=query,
                documents=[doc['payload'] for doc in all_documents],
                top_k=limit
            )
            
            # 결과 변환
            for i, result in enumerate(query_results):
                all_results.append({
                    'res_id': all_documents[i]['id'] if i < len(all_documents) else f"doc_{i}",
                    'res_score': result['similarity'],
                    'type_question': question_type,
                    'type_vector': 'direct_similarity',
                    'res_payload': result['document']
                })
        
        # 유사도 순으로 정렬하여 상위 결과만 반환
        all_results.sort(key=lambda x: x['res_score'], reverse=True)
        final_results = all_results[:limit]
        
        print(f"[DIRECT_SEARCH] 최종 검색 결과: {len(final_results)}건")
        for i, result in enumerate(final_results[:3]):
            title = result['res_payload'].get('document_name', '제목없음')
            score = result['res_score']
            print(f"[DIRECT_SEARCH]   {i+1}. {title} (유사도: {score:.4f})")
        
        return final_results
        
    except Exception as e:
        print(f"[DIRECT_SEARCH] 검색 오류: {e}")
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

# SSE 스트리밍을 위한 제너레이터 클래스
class SSEGenerator:
    def __init__(self, generator_id: str):
        self.generator_id = generator_id
        self.message_queue = asyncio.Queue()
        self.is_active = True
        
    async def send_message(self, message: dict):
        """메시지를 큐에 추가"""
        if self.is_active:
            await self.message_queue.put(message)
    
    async def close(self):
        """제너레이터 종료"""
        self.is_active = False
        await self.message_queue.put(None)  # 종료 신호

# SSE 스트리밍을 위한 전역 변수
sse_generators = {}

# SSE 상태 발행 함수
async def yield_node_status(generator_id: str, node_name: str, status: str, data: dict):
    """SSE를 통해 노드 상태를 발행"""
    if generator_id not in sse_generators:
        print(f"[SSE] ❌ 제너레이터 ID가 없음 - {node_name}: {status}")
        return
        
    try:
        message = {
            "stage": node_name,
            "status": status,
            "result": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # SSE 제너레이터에 메시지 전송
        generator = sse_generators.get(generator_id)
        if generator and generator.is_active:
            await generator.send_message(message)
            print(f"[SSE] ✅ 메시지 전송: {node_name}:{status}")
        else:
            print(f"[SSE] ❌ 제너레이터가 유효하지 않음: {generator_id}")
    except Exception as e:
        print(f"[SSE] ❌ 메시지 전송 실패: {node_name}:{status} - 오류: {e}")
        import traceback
        print(f"[SSE] 오류 상세: {traceback.format_exc()}")
        pass

# LangGraph 노드 함수들
async def node_rc_init(state: SearchState) -> SearchState:
    """초기화 노드"""
    print("[inform]: node_rc_init")
    try: 
        question = state['question']
        generator_id = state.get('generator_id')
        
        if generator_id:
            await yield_node_status(
                generator_id,
                "A",
                "completed",
                {
                    "message": "RAG 검색 완료",
                    "documents_count": len(candidates_total),
                    "documents": candidates_total,
                    "document_titles": [
                        candidate.get("res_payload", {}).get("document_name", "제목 없음3")
                        for candidate in candidates_total
                    ],
                },
            )
        
        return {
            "question": question,
            "keyword": "",
            "candidates_each": [],
            "candidates_total": [],
            "response": [],
            "generator_id": generator_id
        }
    except Exception as e:
        print("[error]: node_rc_init")
        raise RuntimeError(f"[error]: node_rc_init: {str(e)}")

async def node_rc_keyword(state: SearchState) -> SearchState:
    """키워드 증강 노드 - LLM을 사용한 동적 키워드 생성"""
    print("[inform]: node_rc_keyword")
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
                    "message": "RAG 검색 완료",
                    "documents_count": len(candidates_total),
                    "documents": candidates_total,
                    "document_titles": [
                        candidate.get("res_payload", {}).get("document_name", "제목 없음3")
                        for candidate in candidates_total
                    ],
                },
            )
            
            yield {
                "question": state['question'],
                "keyword": base_keywords,
                "candidates_each": [],
                "candidates_total": [],
                "response": [],
                "generator_id": generator_id
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
                model="openai/gpt-oss-120b",
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
                    "message": "RAG 검색 완료",
                    "documents_count": len(candidates_total),
                    "documents": candidates_total,
                    "document_titles": [
                        candidate.get("res_payload", {}).get("document_name", "제목 없음3")
                        for candidate in candidates_total
                    ],
                },
            )
        
        yield {
            "question": state['question'],
            "keyword": augmented_keywords,
            "candidates_each": [],
            "candidates_total": [],
            "response": [],
            "generator_id": generator_id
        }
    except Exception as e:
        print("[error]: node_rc_keyword")
        raise RuntimeError(f"[error]: node_rc_keyword: {str(e)}")

async def node_rc_rag(state: SearchState) -> SearchState:
    """RAG 검색 노드"""
    print("[inform]: node_rc_rag")
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
                    "message": "RAG 검색 완료",
                    "documents_count": len(candidates_total),
                    "documents": candidates_total,
                    "document_titles": [
                        candidate.get("res_payload", {}).get("document_name", "제목 없음3")
                        for candidate in candidates_total
                    ],
                },
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
                "C",
                "completed",
                {
                    "message": "RAG 검색 완료",
                    "documents_count": len(candidates_total),
                    "documents": candidates_total,
                    "document_titles": [
                        candidate.get("res_payload", {}).get("document_name", "제목 없음3")
                        for candidate in candidates_total
                    ],
                },
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
    """답변 생성 노드 (랭그래프 전용)"""
    print("[inform]: node_rc_answer 실행")
    
    try:
        candidates_top = state['response']
        
        # 검색 결과가 있는 경우
        if candidates_top:
            print(f"[Answer] ✅ 검색 결과가 있습니다. LLM API 호출을 시작합니다.")
            
            # 상위 1건의 문서 정보 추출
            top_result = candidates_top[0]
            top_payload = top_result.get('res_payload', {})
            
            # 문서 제목과 내용 추출
            document_title = top_payload.get('document_name', '제목 없음')
            vector_data = top_payload.get("vector", {})

            # vector가 dict인지 확인 후 특정 키값만 추출
            document_content = vector_data.get("text") if isinstance(vector_data, dict) else None
            
            print(f"[Answer] 📄 RAG 문서 정보:")
            print(f"[Answer] 제목: {document_title}")
            print(f"[Answer] 내용 길이: {len(document_content)} 문자")
            print(f"[Answer] 내용 미리보기: {str(document_content)[:200]}...")
            
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
            
            print(f"[Answer] 📝 LLM에 전송할 프롬프트:")
            print(f"[Answer] {prompt}")
            print(f"[Answer] 📊 프롬프트 길이: {len(prompt)} 문자")
            
            # OpenAI API 호출하여 답변 생성 - 새로운 LLM 방식
            llm_answer = ""
            try:
                if OPENAI_API_KEY:
                    print(f"[Answer] 🚀 LLM API 호출 시작...")
                    
                    messages = [{"role": "user", "content": prompt}]
                    
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
                        model="openai/gpt-oss-120b",
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

                            await asyncio.sleep(0.01)
                            # 청크 사이에 지연 추가하여 다른 API 처리 가능하도록 함
                            await asyncio.sleep(0.01)
                        except (ConnectionResetError, BrokenPipeError, OSError, ConnectionAbortedError, ConnectionError) as e:
                            # 클라이언트 연결이 끊어진 경우 조용히 종료
                            print(f"Client disconnected during streaming lv2: {type(e).__name__}")
                            return
                        except Exception as e:
                            print(f"Unexpected error during streaming lv1: {str(e)}")
                            return
                else:
                    print(f"[Answer] ⚠️ OpenAI API 키가 설정되지 않음")
                    llm_answer = f"""입력하신 '{state['question']}'에 대한 답변입니다.

참고 문서: {document_title}

문서 내용을 바탕으로 분석한 결과, {str(document_content)[:200]}...에 대한 정보를 찾았습니다.

더 자세한 분석을 위해서는 OpenAI API 키가 필요합니다."""
                    
            except Exception as e:
                print(f"[Answer] ❌ LLM API 호출 실패: {e}")
                import traceback
                print(f"[Answer] 오류 상세: {traceback.format_exc()}")
                # API 호출 실패 시 기본 답변 생성
                llm_answer = f"""입력하신 '{state['question']}'에 대한 답변입니다.

참고 문서: {document_title}

문서 내용을 바탕으로 분석한 결과, {str(document_content)[:200]}...에 대한 정보를 찾았습니다.

API 호출 중 오류가 발생했습니다: {str(e)}"""
            
            print(f"[Answer] 🎯 최종 생성된 답변:")
            print(f"[Answer] {llm_answer}")
            
            # 이미지 URL 생성 (첫 번째 문서 기반)
            image_url = None
            if top_result and top_payload:
                # 문서 제목과 인덱스를 기반으로 이미지 URL 생성
                doc_title = top_payload.get('document_name', '')
                doc_index = top_result.get('res_id', 0)
                
                if doc_title and doc_index:
                    # 설정 가능한 기본 URL에 RAG 문서 정보를 추가한 형식
                    # URL 안전한 문자열로 변환
                    import urllib.parse
                    safe_title = urllib.parse.quote(doc_title, safe='')
                    base = os.path.splitext(safe_title)[0]
                    # 새 확장자 추가
                    new_filename = f"{base}_whole.jpg"
                    image_url = f"{IMAGE_BASE_URL}{IMAGE_PATH_PREFIX}/{safe_title}"
                    print(f"[Answer] 🖼️ 생성된 이미지 URL: {image_url}")
                    print(f"[Answer] 🔧 이미지 URL 구성 - 기본URL: {IMAGE_BASE_URL}, 경로: {IMAGE_PATH_PREFIX}, 제목: {safe_title}, 인덱스: {doc_index}")
                else:
                    print(f"[Answer] ⚠️ 이미지 URL 생성 실패 - doc_title: {doc_title}, doc_index: {doc_index}")

            # LangGraph 실행 결과를 위한 완전한 응답 구조
            response = {
                "res_id": [rest['res_id'] for rest in candidates_top],
                "answer": llm_answer,  # LLM으로 생성된 실제 답변
                "q_mode": "search",  # 랭그래프는 항상 search 모드
                "keyword": state["keyword"],  # 키워드 증강 목록
                "db_search_title": [item.get('res_payload', {}).get('document_name', '제목 없음') for item in candidates_top],  # 검색된 문서 제목들
                "top_document": top_result,
                "analysis_image_url": image_url  # 랭그래프 4단계 분석 결과 이미지 URL
            }
        else:
            print(f"[Answer] ⚠️ 검색 결과가 없습니다. 기본 답변을 생성합니다.")
            response = {
                "res_id": [],
                "answer": f"입력하신 '{state['question']}'에 대한 관련 문서를 찾을 수 없습니다.",
                "q_mode": "search",
                "keyword": state["keyword"],
                "db_search_title": []
            }
        
        print(f"[Answer] 📤 최종 응답 구조:")
        print(f"[Answer] {response}")
        
        # LangGraph 실행 결과는 프론트엔드에서 저장하도록 변경 (중복 저장 방지)
        # await save_langgraph_result_to_db(state['question'], response, state["keyword"], state["candidates_total"])
        
        generator_id = state.get('generator_id')
        if generator_id:
            await yield_node_status(
                generator_id,
                "D",
                "completed",
                {
                    "message": "최종 답변 생성 완료",
                    "answer": response.get("answer", ""),
                    "analysis_image_url": response.get("analysis_image_url"),
                    "keywords": response.get("keyword", state.get("keyword", [])),
                    "document_titles": response.get("db_search_title", []),
                    "search_results": candidates_top,
                    "top_document": response.get("top_document"),
                },
            )
        
        print(f"[Answer] ✅ node_rc_answer 함수 완료")
        
        yield  {
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
        "db_search_title": []  # 검색 결과가 없는 경우
    }
    
    # LangGraph 실행 결과는 프론트엔드에서 저장하도록 변경 (중복 저장 방지)
    # await save_langgraph_result_to_db(state['question'], complete_result, state["keyword"], state["candidates_total"])
    
    generator_id = state.get('generator_id')
    if generator_id:
        await yield_node_status(
                generator_id,
                "D",
                "completed",
                {
                    "message": "최종 답변 생성 완료",
                    "answer": response.get("answer", ""),
                    "analysis_image_url": response.get("analysis_image_url"),
                    "keywords": response.get("keyword", state.get("keyword", [])),
                    "document_titles": response.get("db_search_title", []),
                    "search_results": candidates_top,
                    "top_document": response.get("top_document"),
                },
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
            "db_search_title": []
        },
        "generator_id": state.get('generator_id')
    }

def judge_rc_ragscore(state: SearchState) -> str:
    """동적 RAG 점수 판단 (하드코딩된 임계값 제거)"""
    candidates_total = state["candidates_total"]
    
    if not candidates_total:
        return "N"
    
    # 동적 임계값 계산: 평균 점수의 70%를 임계값으로 사용
    scores = [candidate.get("res_score", 0) for candidate in candidates_total]
    valid_scores = [score for score in scores if score > 0]
    
    if not valid_scores:
        return "N"
    
    avg_score = sum(valid_scores) / len(valid_scores)
    dynamic_threshold = avg_score * 0.7
    
    # 최소 임계값 설정 (너무 낮은 점수는 제외)
    min_threshold = 0.1
    threshold = max(dynamic_threshold, min_threshold)
    
    has_good_results = any(candidate.get("res_score", 0) >= threshold for candidate in candidates_total)
    
    print(f"[JUDGE] 동적 임계값: {threshold:.4f} (평균: {avg_score:.4f})")
    print(f"[JUDGE] 판단 결과: {'Y' if has_good_results else 'N'}")
    
    return "Y" if has_good_results else "N"
