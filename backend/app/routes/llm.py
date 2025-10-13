import openai
import asyncio
import json
import base64
import random
import requests
from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
import redis.asyncio as aioredis
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph
from collections import defaultdict
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, SearchRequest, Filter
from app.utils.config import (
    OPENAI_API_KEY, CUSTOM_LLAMA_API_KEY, CUSTOM_LLAMA_API_ENDPOINT, CUSTOM_LLAMA_API_BASE,
    REDIS_HOST, REDIS_PORT, REDIS_CHANNEL,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
)
from app.database import get_db
from app.models import Conversation, Message
from sqlalchemy.orm import Session

from datetime import datetime

# Create router 
router = APIRouter()

# Redis 비동기 클라이언트 초기화
try:
    redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    print(f"[Redis] Redis 클라이언트 초기화 완료: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"[Redis] Redis 클라이언트 초기화 실패: {e}")
    redis_client = None

# 환경 변수 로딩 확인
print(f"[Config] OpenAI API Key: {'설정됨' if OPENAI_API_KEY else '설정되지 않음'}")
print(f"[Config] Qdrant: {QDRANT_HOST}:{QDRANT_PORT} (컬렉션: {QDRANT_COLLECTION or '설정되지 않음'})")

# 임베딩 모델 (10차원 벡터 생성)
class SimpleEmbeddings:
    def __init__(self):
        self.dimension = 10  # Qdrant 컬렉션 차원에 맞춤
        self.api_key = OPENAI_API_KEY
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """10차원 벡터 생성 (Qdrant 컬렉션에 맞춤)"""
        try:
            embeddings = []
            for text in texts:
                # 간단한 해시 기반 10차원 벡터 생성
                import hashlib
                import struct
                
                # 텍스트를 해시로 변환
                text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
                
                # 해시를 10개의 float로 변환
                vector = []
                for i in range(0, 40, 4):  # MD5는 32바이트, 4바이트씩 8개 그룹
                    if i + 4 <= len(text_hash):
                        hex_group = text_hash[i:i+4]
                        # 16진수를 float로 변환 (0-1 범위로 정규화)
                        float_val = float(int(hex_group, 16)) / 65535.0
                        vector.append(float_val)
                
                # 10차원이 되도록 패딩 또는 자르기
                while len(vector) < 10:
                    vector.append(0.0)
                vector = vector[:10]
                
                embeddings.append(vector)
                
            print(f"[Embeddings] {len(texts)}개 텍스트에 대해 {self.dimension}차원 벡터 생성 완료")
            return embeddings
            
        except Exception as e:
            print(f"[Embeddings] 벡터 생성 오류: {e}")
            # 오류 시 기본 10차원 벡터 반환
            return [[0.0] * self.dimension for _ in texts]

# 벡터 DB 검색 함수들
async def rag_multivector(question_type: str, limit: int, queries: List[str], query_vectors: List[List[float]], 
                          ip: str, port: int, collection: str) -> List[dict]:
    """멀티벡터 검색 (Qdrant)"""
    try:
        print(f"[RAG] Qdrant 연결 시도: {ip}:{port}, 컬렉션: {collection}")
        
        # 벡터 DB 연결 시도
        client = QdrantClient(host=ip, port=port)
        
        # 컬렉션 존재 확인
        try:
            collections = client.get_collections()
            print(f"[RAG] 사용 가능한 컬렉션: {[col.name for col in collections.collections]}")
            
            if not collection:
                print(f"[RAG] 컬렉션이 설정되지 않았습니다.")
                return []
                
            if collection not in [col.name for col in collections.collections]:
                print(f"[RAG] 컬렉션 '{collection}'이 존재하지 않습니다.")
                return []
                
            print(f"[RAG] 컬렉션 '{collection}' 연결 성공")
            
        except Exception as e:
            print(f"[RAG] Qdrant 컬렉션 확인 오류: {e}")
            return []
        
        results = []
        for i, (query, vector) in enumerate(zip(queries, query_vectors)):
            try:
                print(f"[RAG] 벡터 검색 시작: query {i+1}/{len(queries)}")
                
                # 벡터 검색
                search_result = client.search(
                    collection_name=collection,
                    query_vector=vector,
                    limit=limit,
                    with_payload=True
                )
                
                print(f"[RAG] 검색 결과: {len(search_result)}건")
                
                for item in search_result:
                    results.append({
                        'res_id': item.id,
                        'res_score': item.score,
                        'type_question': question_type,
                        'type_vector': '',  # 벡터 타입
                        'res_payload': item.payload
                    })
            except Exception as e:
                print(f"[RAG] 개별 벡터 검색 오류 (query {i}): {e}")
                continue
        
        print(f"[RAG] 총 검색 결과: {len(results)}건")
        return results
        
    except Exception as e:
        print(f"[RAG] Qdrant 검색 오류: {e}")
        return []

async def rag_vector_qdrant(question_type: str, limit: int, queries: List[str], query_vectors: List[List[float]], 
                           ip: str, port: int, collection: str) -> List[dict]:
    """Qdrant 벡터 검색"""
    return await rag_multivector(question_type, limit, queries, query_vectors, ip, port, collection)

async def rag_payload_qdrant(question_type: str, limit: int, queries: List[str], query_vectors: List[List[float]], 
                             ip: str, port: int, collection: str) -> List[dict]:
    """Qdrant 페이로드 검색"""
    return await rag_multivector(question_type, limit, queries, query_vectors, ip, port, collection)



# Available models with added custom Llama models
AVAILABLE_MODELS = [
    {"name": "GPT-3.5 Turbo", "value": "gpt-3.5-turbo"},
    {"name": "GPT-4", "value": "gpt-4"},
    {"name": "Claude 3 Opus", "value": "claude-3-opus"},
    {"name": "Claude 3 Sonnet", "value": "claude-3-sonnet"},
    {"name": "Llama 4 Maverick", "value": "llama-4-maverick"}
]

# 구버전 OpenAI SDK 강제 사용
USING_NEW_SDK = False

# Custom API key update for Llama models only
class CustomApiKeyUpdate(BaseModel):
    api_key: str
    api_base: Optional[str] = None
    api_endpoint: Optional[str] = None

class Model(BaseModel):
    name: str
    value: str

# 스트리밍 요청을 위한 클래스
class StreamRequest(BaseModel):
    question: str
    conversation_id: Optional[int] = None
    generate_image: Optional[bool] = False  # 이미지 생성 플래그 추가

# 이미지 URL (실제 이미지 생성 시스템에서 처리)
# SAMPLE_IMAGE_URLS = []

# LangGraph 상태 정의
class SearchState(dict):
    question: str       # 사용자 입력 질의
    keyword: str       # 사용자 입력 질의
    candidates_each: List[dict] 
    candidates_total: List[dict] 
    response: List[dict]     # LLM이 생성한 응답

# Redis 상태 발행 함수
async def publish_node_status(node_name: str, status: str, data: dict):
    """Redis를 통해 노드 상태를 발행"""
    if redis_client is None:
        print(f"[Redis] Redis 클라이언트가 초기화되지 않음 - {node_name}: {status}")
        return
        
    try:
        message = {
            "node": node_name,
            "status": status,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await redis_client.publish(REDIS_CHANNEL, json.dumps(message))
        print(f"[Redis] Published {node_name}: {status}")
    except Exception as e:
        print(f"[Redis] Error publishing status: {e}")
        # Redis 오류가 발생해도 워크플로우는 계속 진행
        pass

# LangGraph 노드 함수들
async def node_rc_init(state: SearchState) -> SearchState:
    """초기화 노드"""
    print("[inform]: node_rc_init")
    try: 
        question = state['question']
        await publish_node_status("node_init", "completed", {"result": question})
        return {
            "question": question,
            "keyword": "",
            "candidates_each": [],
            "candidates_total": [],
            "response": []
        }
    except Exception as e:
        print("[error]: node_rc_init")
        raise RuntimeError(f"[error]: node_rc_init: {str(e)}")

async def node_rc_keyword(state: SearchState) -> SearchState:
    """키워드 증강 노드 - LLM을 사용한 동적 키워드 생성"""
    print("[inform]: node_rc_keyword")
    try:
        question = state['question']
        
        # OpenAI API 키 확인
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-api-key-here":
            print("[error]: OpenAI API 키가 설정되지 않았습니다.")
            # API 키가 없으면 기본 키워드만 반환
            base_keywords = [question]
            await publish_node_status("node_rc_keyword", "completed", {"result": base_keywords})
            return {
                "question": state['question'],
                "keyword": base_keywords,
                "candidates_each": [],
                "candidates_total": [],
                "response": []
            }
        
        try:
            # LLM을 사용하여 키워드 증강
            # 구버전 OpenAI 라이브러리 사용
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 전문적인 키워드 분석가입니다. 주어진 질문을 분석하여 관련된 전문 키워드들을 생성해주세요. 각 키워드는 쉼표로 구분하고, 최대 15개까지 생성하세요."},
                    {"role": "user", "content": f"다음 질문에 대한 관련 키워드들을 생성해주세요: {question}"}
                ],
                max_tokens=200,
                temperature=0.7
            )
            llm_response = response.choices[0].message.content
            
            # LLM 응답을 키워드 리스트로 변환
            keywords_text = llm_response.strip()
            # 쉼표로 구분하고 각 키워드 정리
            augmented_keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            # 원본 질문도 포함
            augmented_keywords.insert(0, question)
            # 중복 제거 및 최대 20개로 제한
            augmented_keywords = list(dict.fromkeys(augmented_keywords))[:20]
            
            print(f"[inform]: LLM을 통해 생성된 키워드: {len(augmented_keywords)}개")
            
        except Exception as llm_error:
            print(f"[error]: LLM 키워드 생성 실패: {llm_error}")
            # LLM 실패 시 기본 키워드 사용
            augmented_keywords = [question]
        
        await publish_node_status("node_rc_keyword", "completed", {"result": augmented_keywords})
        
        return {
            "question": state['question'],
            "keyword": augmented_keywords,
            "candidates_each": [],
            "candidates_total": [],
            "response": []
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
        
        # 임베딩 모델 초기화
        try:
            embeddings = SimpleEmbeddings()
        except Exception as e:
            print(f"임베딩 모델 초기화 오류: {e}")
            # 임베딩 모델 초기화 실패 시 더미 벡터 사용
            embeddings = None
        
        # question으로 검색
        candidates_each = []
        if state.get('question') and embeddings:
            try:
                query_vectors = embeddings.embed_documents([state['question']])
                candidates_each.extend(await rag_multivector('question', 5, [state['question']], query_vectors, ip, port, collection))
            except Exception as e:
                print(f"Question 검색 오류: {e}")
        
        # keyword로 검색 (문자열 또는 리스트 처리)
        if state.get('keyword') and embeddings:
            try:
                # keyword가 리스트인지 문자열인지 확인
                if isinstance(state['keyword'], list):
                    keywords = state['keyword']
                else:
                    keywords = [state['keyword']]
                
                # 빈 문자열이나 None 값 필터링
                keywords = [k for k in keywords if k and isinstance(k, str) and k.strip()]
                
                if keywords:
                    query_vectors = embeddings.embed_documents(keywords)
                    candidates_each.extend(await rag_multivector('keyword', 2, keywords, query_vectors, ip, port, collection))
            except Exception as e:
                print(f"Keyword 검색 오류: {e}")
        
        # 벡터 검색이 실패한 경우 기본 응답 생성
        if not candidates_each:
            print("[RAG] 벡터 검색 결과가 없어 기본 응답을 생성합니다.")
            # 검색 결과가 없을 때 기본 데이터 생성
            candidates_each = [{
                'res_id': 'no_results',
                'res_score': 0.0,
                'res_payload': {
                    'title': '검색 결과 없음',
                    'content': '데이터베이스에서 관련 정보를 찾을 수 없습니다. 질문을 더 구체적으로 작성하거나 다른 키워드로 시도해보세요.',
                    'type': 'no_results'
                }
            }]
            print(f"[RAG] 기본 응답 생성 완료: {len(candidates_each)}건")

        # 가중 평균 summation (기존 랭그래프 코드와 동일)
        w_question = {
            'question': 1,
            'keyword': 1
        }
        w_vector = {
            'text': 1,
            'summary_purpose': 0.5,
            'summary_result': 0.5,
            'summary_fb': 0.5,
        }
        
        aggregated_scores = defaultdict(float)
        payloads = {}
        
        # candidates_each가 비어있지 않은 경우에만 처리
        if candidates_each:
            for item in candidates_each:
                try:
                    res_id = item.get('res_id')
                    score = item.get('res_score', 0.0)
                    type_question = item.get('type_question', '')
                    type_vector = item.get('type_vector', '')
                    
                    if res_id is not None:
                        aggregated_scores[res_id] += score * w_question.get(type_question, 1.0) * w_vector.get(type_vector, 1.0)
                        if res_id not in payloads:
                            payloads[res_id] = item.get('res_payload', {})
                except Exception as e:
                    print(f"개별 결과 처리 오류: {e}")
                    continue
        
        # 정렬된 결과 생성 (list of dicts 형태) - 상위 5건만
        candidates_total = sorted(
            [{'res_id': res_id, 'res_score': aggregated_scores[res_id], 'res_payload': payloads[res_id]}
             for res_id in aggregated_scores],
            key=lambda x: x['res_score'],
            reverse=True
        )[:5]  # 상위 5건만 선택
        
        print(f"[RAG] 최종 검색 결과 (상위 5건):")
        for i, candidate in enumerate(candidates_total):
            title = candidate.get('res_payload', {}).get('ppt_title', '제목 없음')
            summary = candidate.get('res_payload', {}).get('ppt_summary', '요약 없음')
            score = candidate.get('res_score', 0)
            print(f"  {i+1}. {title} - {summary} (유사도: {score:.4f})")
        
        await publish_node_status("node_rc_rag", "completed", {"result": candidates_total})
        
        return {
            "question": state.get('question', ''),
            "keyword": state.get('keyword', ''),
            "candidates_total": candidates_total,
            "response": []
        }
    except Exception as e:
        print(f"[error]: node_rc_rag: {str(e)}")
        # 에러가 발생해도 기본 상태 반환하여 워크플로우 계속 진행
        return {
            "question": state.get('question', ''),
            "keyword": state.get('keyword', ''),
            "candidates_each": [],
            "candidates_total": [],
            "response": []
        }

async def node_rc_rerank(state: SearchState) -> SearchState:
    """재순위 노드"""
    print("[inform]: node_rc_rerank")
    try:
        cnt_result = 5
        candidates_top = state['candidates_total'][:cnt_result]
        
        # 재순위 처리 (실제로는 LLM을 사용한 재순위)
        for idx in range(len(candidates_top)):
            candidates_top[idx].update({'res_relevance': 1.0 - (idx * 0.1)})
        
        # 점수와 관련성으로 정렬
        sorted_candidates_top = sorted(candidates_top, key=lambda x: (-x['res_relevance'], -x['res_score']))
        
        await publish_node_status("node_rc_rerank", "completed", {"result": sorted_candidates_top})
        
        return {
            "question": state['question'],
            "keyword": state["keyword"],
            "candidates_total": state["candidates_total"],
            "response": sorted_candidates_top
        }
    except Exception as e:
        print("[error]: node_rc_rerank")
        raise RuntimeError(f"[error]: node_rc_rerank: {str(e)}")

async def node_rc_answer(state: SearchState) -> SearchState:
    """답변 생성 노드 (랭그래프 전용)"""
    print("[inform]: node_rc_answer 실행")
    
    try:
        cnt_result = 5
        candidates_top = state['response'][:cnt_result]
        
        # 검색 결과가 있는 경우
        if candidates_top:
            print(f"[Answer] ✅ 검색 결과가 있습니다. LLM API 호출을 시작합니다.")
            
            # 상위 1건의 문서 정보 추출
            top_result = candidates_top[0]
            top_payload = top_result.get('res_payload', {})
            
            # 문서 제목과 내용 추출
            document_title = top_payload.get('ppt_title', '제목 없음')
            document_content = top_payload.get('ppt_content', top_payload.get('ppt_summary', '내용 없음'))
            
            print(f"[Answer] 📄 RAG 문서 정보:")
            print(f"[Answer] 제목: {document_title}")
            print(f"[Answer] 내용 길이: {len(document_content)} 문자")
            print(f"[Answer] 내용 미리보기: {document_content[:200]}...")
            
            # LLM에 전송할 프롬프트 구성
            prompt = f"""
다음 문서를 참고하여 질문에 답변해주세요.

[참고 문서]
문서 제목: {document_title}
문서 내용: {document_content[:1000]}...

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
            
            # OpenAI API 호출하여 답변 생성
            llm_answer = ""
            try:
                if OPENAI_API_KEY:
                    print(f"[Answer] 🚀 OpenAI API 호출 시작...")
                    openai.api_key = OPENAI_API_KEY
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=1000,
                        temperature=0.7
                    )
                    raw_llm_answer = response['choices'][0]['message']['content']
                    print(f"[Answer] ✅ OpenAI 응답 생성 완료")
                    print(f"[Answer] 📥 OpenAI 원시 응답:")
                    print(f"[Answer] {raw_llm_answer}")
                    print(f"[Answer] 📊 응답 길이: {len(raw_llm_answer)} 문자")
                    print(f"[Answer] 사용된 토큰: {response['usage']['total_tokens'] if response.get('usage') else 'N/A'}")
                    
                    # LLM에서 받은 깔끔한 답변을 바로 사용
                    llm_answer = raw_llm_answer.strip()
                else:
                    print(f"[Answer] ⚠️ OpenAI API 키가 설정되지 않음")
                    llm_answer = f"""입력하신 '{state['question']}'에 대한 답변입니다.

참고 문서: {document_title}

문서 내용을 바탕으로 분석한 결과, {document_content[:200]}...에 대한 정보를 찾았습니다.

더 자세한 분석을 위해서는 OpenAI API 키가 필요합니다."""
                    
            except Exception as e:
                print(f"[Answer] ❌ OpenAI API 호출 실패: {e}")
                import traceback
                print(f"[Answer] 오류 상세: {traceback.format_exc()}")
                # API 호출 실패 시 기본 답변 생성
                llm_answer = f"""입력하신 '{state['question']}'에 대한 답변입니다.

참고 문서: {document_title}

문서 내용을 바탕으로 분석한 결과, {document_content[:200]}...에 대한 정보를 찾았습니다.

API 호출 중 오류가 발생했습니다: {str(e)}"""
            
            print(f"[Answer] 🎯 최종 생성된 답변:")
            print(f"[Answer] {llm_answer}")
            
            # LangGraph 실행 결과를 위한 완전한 응답 구조
            response = {
                "res_id": [rest['res_id'] for rest in candidates_top],
                "answer": llm_answer,  # LLM으로 생성된 실제 답변
                "q_mode": "search",  # 랭그래프는 항상 search 모드
                "keyword": state["keyword"],  # 키워드 증강 목록
                "db_search_title": [item.get('res_payload', {}).get('ppt_title', '제목 없음') for item in candidates_top],  # 검색된 문서 제목들
                "top_document": top_result
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
        
        await publish_node_status("node_rc_answer", "completed", {"result": response})
        
        print(f"[Answer] ✅ node_rc_answer 함수 완료")
        
        return {
            "question": state['question'],
            "keyword": state["keyword"],
            "candidates_total": state["candidates_total"],
            "response": response
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
    
    await publish_node_status("node_rc_plain_answer", "completed", {"result": complete_result})
    
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
        }
    }

def judge_rc_ragscore(state: SearchState) -> str:
    """RAG 점수 판단"""
    candidates_total = state["candidates_total"]
    return "Y" if any(candidate.get("res_score", 0) >= 0.5 for candidate in candidates_total) else "N"

async def save_langgraph_result_to_db(question: str, response: dict, keywords: list, candidates_total: list):
    """LangGraph 실행 결과를 DB에 직접 저장 (랭그래프 전용)"""
    try:
        print(f"[DB_SAVE] LangGraph 결과 DB 저장 시작 (랭그래프 전용)")
        print(f"[DB_SAVE] 질문: {question}")
        print(f"[DB_SAVE] 응답: {response.get('answer', '')[:100]}...")
        print(f"[DB_SAVE] 키워드: {keywords}")
        print(f"[DB_SAVE] 문서: {len(candidates_total)}건")
        
        # 새 대화 생성 또는 기존 대화 찾기
        db = next(get_db())
        
        # 새 대화 생성
        conversation = Conversation(
            title=question[:50] + "..." if len(question) > 50 else question,
            user_id=1  # 기본 사용자 ID (실제로는 인증된 사용자 ID 사용)
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
            db_search_title=str([item.get('res_payload', {}).get('ppt_title', '') for item in candidates_total[:5]]) if candidates_total else None
            # user_name 필드 제거 - 하드코딩 방지
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

async def generate_detailed_analysis(question: str, top_result: dict) -> str:
    """상위 검색 결과에 대해 LLM을 사용하여 상세 분석 생성"""
    try:
        # 검색 결과 정보 추출
        doc_title = top_result.get('res_payload', {}).get('ppt_title', '제목 없음')
        doc_summary = top_result.get('res_payload', {}).get('ppt_summary', '요약 없음')
        doc_content = top_result.get('res_payload', {}).get('ppt_content', '내용 없음')
        doc_score = top_result.get('res_score', 0)
        
        # LLM 프롬프트 구성
        prompt = f"""다음 문서를 기반으로 사용자의 질문에 대해 상세하고 유용한 답변을 제공해주세요.

**사용자 질문**: {question}

**검색된 문서 정보**:
- 제목: {doc_title}
- 요약: {doc_summary}
- 내용: {doc_content}
- 유사도 점수: {doc_score:.4f}

**답변 요구사항**:
1. 문서 내용을 바탕으로 질문에 직접적으로 답변
2. 구체적인 정보와 예시 포함
3. 실무에 적용 가능한 인사이트 제공
4. 추가 질문이나 고려사항 제시

**답변 형식**:
- 핵심 요약 (2-3줄)
- 상세 분석 (5-7줄)
- 실무 적용 방안 (2-3줄)
- 추가 고려사항 (1-2줄)

문서 내용을 충실히 반영하여 답변해주세요."""

        # OpenAI API 호출
        if OPENAI_API_KEY:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 전문적인 비즈니스 분석가입니다. 문서 내용을 바탕으로 명확하고 실용적인 답변을 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            detailed_answer = response.choices[0].message.content
            print(f"[LLM] 상세 분석 생성 완료: {len(detailed_answer)}자")
            return detailed_answer
        else:
            # OpenAI API 키가 없는 경우 기본 답변 생성
            basic_answer = f"""🔍 **분석 결과 요약**

**입력 질문**: {question}

**검색된 문서**: {doc_title}
**유사도 점수**: {doc_score:.4f}

**문서 요약**: {doc_summary}

**상세 내용**: {doc_content}

**핵심 인사이트**:
- 이 문서는 {doc_title}에 대한 정보를 제공합니다
- {doc_summary}와 관련된 내용을 담고 있습니다
- {doc_content}에 대한 구체적인 정보를 포함하고 있습니다

**실무 적용 방안**:
- 문서의 내용을 바탕으로 {question}에 대한 해결책을 모색할 수 있습니다
- {doc_title} 영역에서의 모범 사례를 참고할 수 있습니다

**추가 고려사항**:
- 더 구체적인 정보가 필요하다면 추가 질문을 해주세요
- 관련된 다른 문서나 자료도 함께 검토하는 것을 권장합니다"""
            
            print(f"[LLM] 기본 답변 생성 완료: {len(basic_answer)}자")
            return basic_answer
            
    except Exception as e:
        print(f"[LLM] 상세 분석 생성 중 오류: {str(e)}")
        # 오류 발생 시 기본 답변 반환
        return f"""🔍 **분석 결과 요약**

**입력 질문**: {question}

**검색된 문서**: {top_result.get('res_payload', {}).get('ppt_title', '제목 없음')}
**유사도 점수**: {top_result.get('res_score', 0):.4f}

**문서 내용**: {top_result.get('res_payload', {}).get('ppt_content', '내용을 불러올 수 없습니다')}

**상세 분석**: 
문서 내용을 바탕으로 한 상세 분석을 생성하는 중 오류가 발생했습니다. 
기본 정보는 위와 같으며, 추가 질문을 통해 더 구체적인 답변을 받으실 수 있습니다."""

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

@router.get("/models", response_model=List[Model])
def get_models():
    """Get list of available models"""
    return AVAILABLE_MODELS

@router.get("/test-embeddings")
async def test_embeddings():
    """임베딩 모델 테스트"""
    try:
        if not OPENAI_API_KEY:
            return {"status": "error", "message": "OpenAI API 키가 설정되지 않았습니다."}
        
        embeddings = SimpleEmbeddings()
        test_texts = ["테스트 텍스트"]
        vectors = embeddings.embed_documents(test_texts)
        
        return {
            "status": "success", 
            "message": "임베딩 모델 테스트 성공",
            "vector_dimension": len(vectors[0]) if vectors else 0
        }
    except Exception as e:
        return {"status": "error", "message": f"임베딩 모델 테스트 실패: {str(e)}"}

@router.get("/test-vector-db")
async def test_vector_db():
    """벡터 데이터베이스 연결 테스트"""
    try:
        # Qdrant 연결 테스트
        qdrant_status = "연결 안됨"
        try:
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            collections = client.get_collections()
            qdrant_status = f"연결됨 (컬렉션 수: {len(collections.collections)})"
        except Exception as e:
            qdrant_status = f"연결 실패: {str(e)}"
        
        
        return {
            "status": "success",
            "qdrant": {
                "host": QDRANT_HOST,
                "port": QDRANT_PORT,
                "collection": QDRANT_COLLECTION,
                "status": qdrant_status
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"벡터 DB 테스트 실패: {str(e)}"}

@router.get("/test-langgraph")
async def test_langgraph():
    """LangGraph 워크플로우 테스트"""
    try:
        # 워크플로우 상태 확인
        workflow_info = {
            "nodes": ["node_rc_init", "node_rc_keyword", "node_rc_rag", "node_rc_rerank", "node_rc_answer", "node_rc_plain_answer"],
            "entry_point": "node_rc_init",
            "end_points": ["END"]
        }
        
        # 워크플로우 확인
        if langgraph_instance is None:
            return {
                "status": "error",
                "workflow_info": workflow_info,
                "workflow_status": "워크플로우가 초기화되지 않음",
                "result_summary": {}
            }
        
        # 간단한 테스트 실행
        test_state = {"question": "테스트 질문"}
        try:
            result = await langgraph_instance.ainvoke(test_state)
            workflow_status = "실행 성공"
            result_summary = {
                "question": result.get("question", ""),
                "keyword_count": len(result.get("keyword", [])) if isinstance(result.get("keyword"), list) else 1,
                "candidates_count": len(result.get("candidates_total", [])),
                "response_count": len(result.get("response", []))
            }
        except Exception as e:
            workflow_status = f"실행 실패: {str(e)}"
            result_summary = {}
        
        return {
            "status": "success",
            "workflow_info": workflow_info,
            "workflow_status": workflow_status,
            "result_summary": result_summary
        }
    except Exception as e:
        return {"status": "error", "message": f"LangGraph 테스트 실패: {str(e)}"}

# OpenAI API 키는 config.py에서 고정으로 설정됨 - 런타임 변경 불가

@router.post("/set-custom-api-key")
def set_custom_api_key(key_data: CustomApiKeyUpdate):
    """Set the custom LLM API key and endpoints at runtime (Llama models only)"""
    global CUSTOM_LLAMA_API_KEY, CUSTOM_LLAMA_API_BASE, CUSTOM_LLAMA_API_ENDPOINT
    try:
        # Set the new API key for custom Llama models only
        CUSTOM_LLAMA_API_KEY = key_data.api_key
        
        # Optionally update API base and endpoint
        if key_data.api_base:
            CUSTOM_LLAMA_API_BASE = key_data.api_base
        if key_data.api_endpoint:
            CUSTOM_LLAMA_API_ENDPOINT = key_data.api_endpoint
        
        # We don't test the API key here as it might require special headers
        # that we don't know about in advance
        
        return {
            "status": "success", 
            "message": "Custom API key updated successfully (Llama models only)",
            "api_base": CUSTOM_LLAMA_API_BASE,
            "api_endpoint": CUSTOM_LLAMA_API_ENDPOINT
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error setting custom API key: {str(e)}")

def get_llm_response(prompt: str) -> str:
    """Get a response from the selected LLM model"""
    model = "gpt-3.5-turbo"  # 기본 모델 설정
    
    # Check if API key is set
    if model.startswith("gpt") and not OPENAI_API_KEY:
        return "Error: OpenAI API key not set. Please set your API key in the settings."
    
    # Handle different model providers
    if model.startswith("gpt"):
        return get_openai_response(prompt, model)
    elif model.startswith("claude"):
        # Claude API 통합이 필요합니다
        return f"Error: Claude API integration not implemented yet. Model: {model}"
    elif model.startswith("llama"):
        return get_custom_llama_response(prompt, model)
    else:
        return f"Unknown model: {model}. Please select a supported model."

def get_custom_llama_response(prompt: str, model: str = "llama-4-maverick") -> str:
    """Get a response from custom Llama API"""
    try:
        # Construct the full API URL
        api_url = f"{CUSTOM_LLAMA_API_BASE}{CUSTOM_LLAMA_API_ENDPOINT}"
        
        # Prepare the headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CUSTOM_LLAMA_API_KEY}"
        }
        
        # Prepare the request body
        # Note: Adjust this format according to your API's requirements
        data = {
            "prompt": prompt,
            "max_tokens": 500,
            "temperature": 0.7,
            "model": model,  # This might need adjustment based on your API
            "stream": False
        }
        
        # Make the API call
        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        
        # Check for successful response
        if response.status_code == 200:
            result = response.json()
            # Extract the generated text (adjust key names based on your API response structure)
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0].get("text", "No response text found")
            return "No valid response from Llama API"
        else:
            return f"Error from Llama API: HTTP {response.status_code}"
            
    except Exception as e:
        print(f"Error calling Llama API: {str(e)}")
        return f"Error: {str(e)}"

def get_openai_response(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """Get a response from OpenAI API"""
    try:
        if USING_NEW_SDK:
            # New SDK style (>1.0)
            try:
                client = OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"New SDK error: {e}, trying old SDK...")
                # New SDK 실패 시 old SDK 시도
                openai.api_key = OPENAI_API_KEY
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000
                )
                return response.choices[0].message.content
        else:
            # Old SDK style (<1.0)
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return f"Error: {str(e)}"

# 스트리밍 응답을 위한 새로운 엔드포인트
@router.post("/stream")
async def stream_response(request: StreamRequest):
    """Stream a response from the LLM model using LangGraph"""
    try:
        # 워크플로우 확인
        if langgraph_instance is None:
            return Response(content="Error: LangGraph 워크플로우가 초기화되지 않았습니다.", media_type="text/plain")
        
        # LangGraph 실행
        initial_state = {"question": request.question}
        
        # 비동기로 LangGraph 실행
        result = await langgraph_instance.ainvoke(initial_state)
        
        # 스트리밍 응답 생성
        async def stream_generator():
            # 각 노드의 진행 상황을 스트리밍
            yield f"data: {json.dumps({'type': 'start', 'message': 'LangGraph 실행 시작'})}\n\n"
            
            # 최종 결과 스트리밍
            if 'response' in result and 'answer' in result['response']:
                answer = result['response']['answer']
                # 답변을 단어 단위로 스트리밍
                words = answer.split()
                for word in words:
                    yield f"data: {word} \n\n"
                    await asyncio.sleep(0.1)  # 자연스러운 타이핑 효과
            
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        print(f"Error in LangGraph streaming: {str(e)}")
        return Response(content=f"Error: {str(e)}", media_type="text/plain")

# 일반 LLM 채팅 엔드포인트 (streaming 지원)
@router.post("/chat/stream")
async def stream_chat_with_llm(request: StreamRequest, db: Session = Depends(get_db)):
    """Stream a response from general LLM chat (without LangGraph)"""
    try:
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            return Response(content="Error: OpenAI API 키가 설정되지 않았습니다.", media_type="text/plain")
        
        print(f"[Chat Stream] ========== 일반 LLM 스트리밍 채팅 시작 ==========")
        print(f"[Chat Stream] 요청 정보:")
        print(f"[Chat Stream] - 질문: {request.question}")
        print(f"[Chat Stream] - 대화 ID: {request.conversation_id}")
        print(f"[Chat Stream] - conversation_id 타입: {type(request.conversation_id)}")
        print(f"[Chat Stream] - conversation_id가 None인가?: {request.conversation_id is None}")
        
        # 대화 히스토리 구성
        messages = [{"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다. 이전 대화의 맥락을 고려하여 답변해주세요."}]
        
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
        
        # 스트리밍 응답 생성
        async def stream_generator():
            try:
                print(f"[Chat Stream] OpenAI API 스트림 생성 시작...")
                # Old SDK style (<1.0) 강제 사용
                openai.api_key = OPENAI_API_KEY
                stream = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7,
                    stream=True
                )
                print(f"[Chat Stream] OpenAI API 스트림 생성 완료, 스트리밍 시작...")
                
                chunk_count = 0
                for chunk in stream:
                    chunk_count += 1
                    # print(f"[Chat Stream] 청크 {chunk_count} 수신: {chunk}")
                    if chunk['choices'][0].get('delta', {}).get('content'):
                        content = chunk['choices'][0]['delta']['content']
                        # print(f"[Chat Stream] 청크 {chunk_count} 내용: '{content}'")
                        yield f"data: {content}\n\n"
                    await asyncio.sleep(0.01)  # 부드러운 스트리밍을 위한 짧은 지연
                
                # print(f"[Chat Stream] 스트리밍 완료, 총 {chunk_count}개 청크 처리")
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                print(f"[Chat Stream] 스트리밍 중 오류: {str(e)}")
                import traceback
                print(f"[Chat Stream] 오류 상세: {traceback.format_exc()}")
                yield f"data: Error: {str(e)}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            stream_generator(),
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
        print(f"[Chat Stream] 일반 LLM 스트리밍 채팅 오류: {str(e)}")
        import traceback
        print(f"[Chat Stream] 오류 상세: {traceback.format_exc()}")
        return Response(content=f"Error: {str(e)}", media_type="text/plain")

# 스트리밍 테스트 엔드포인트
@router.get("/chat/stream/test")
async def test_streaming():
    """스트리밍 기능 테스트"""
    async def test_stream_generator():
        try:
            print("[Test Stream] 테스트 스트리밍 시작")
            for i in range(5):
                message = f"테스트 메시지 {i+1}"
                print(f"[Test Stream] 전송: {message}")
                yield f"data: {message}\n\n"
                await asyncio.sleep(1)  # 1초 간격으로 전송
            
            print("[Test Stream] 테스트 스트리밍 완료")
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"[Test Stream] 오류: {str(e)}")
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        test_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

# 기존 비-스트리밍 채팅 엔드포인트 (하위 호환성을 위해 유지)
@router.post("/chat")
async def chat_with_llm(request: StreamRequest, db: Session = Depends(get_db)):
    """일반 LLM을 사용한 채팅 응답 (랭그래프 없이)"""
    try:
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=400, detail="OpenAI API 키가 설정되지 않았습니다.")
        
        print(f"[Chat] ========== 일반 LLM 채팅 시작 (비-스트리밍) ==========")
        print(f"[Chat] 요청 정보:")
        print(f"[Chat] - 질문: {request.question}")
        print(f"[Chat] - 대화 ID: {request.conversation_id}")
        print(f"[Chat] - conversation_id 타입: {type(request.conversation_id)}")
        print(f"[Chat] - conversation_id가 None인가?: {request.conversation_id is None}")
        
        # 대화 히스토리 구성
        messages = [{"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다. 이전 대화의 맥락을 고려하여 답변해주세요."}]
        
        if request.conversation_id:
            try:
                # 해당 대화의 이전 메시지들 가져오기 (최근 10개만)
                conversation_messages = db.query(Message).filter(
                    Message.conversation_id == request.conversation_id
                ).order_by(Message.created_at.asc()).limit(10).all()
                
                print(f"[Chat] 이전 대화 메시지 {len(conversation_messages)}개 로드")
                print(f"[Chat] ========== 이전 대화 히스토리 상세 정보 ==========")
                
                # 이전 대화를 messages에 추가
                for i, msg in enumerate(conversation_messages):
                    print(f"[Chat] DB 메시지 {i+1}: ID={msg.id}, role={msg.role}, created_at={msg.created_at}")
                    if msg.question:
                        print(f"[Chat] 질문: {msg.question}")
                        messages.append({"role": "user", "content": msg.question})
                    if msg.ans:
                        print(f"[Chat] 답변: {msg.ans}")
                        messages.append({"role": "assistant", "content": msg.ans})
                    print(f"[Chat] ----------------------------------------")
                
                print(f"[Chat] ========== 이전 대화 히스토리 로드 완료 ==========")
                        
            except Exception as e:
                print(f"[Chat] 대화 히스토리 로드 실패: {e}")
                # 히스토리 로드 실패해도 계속 진행
        
        # 현재 질문 추가
        messages.append({"role": "user", "content": request.question})
        
        print(f"[Chat] 전송할 메시지 개수: {len(messages)}")
        print(f"[Chat] ========== OpenAI API에 전송할 전체 메시지 내용 ==========")
        for i, msg in enumerate(messages):
            print(f"[Chat] 메시지 {i+1}/{len(messages)}: role={msg['role']}")
            print(f"[Chat] 내용: {msg['content']}")
            print(f"[Chat] ----------------------------------------")
        print(f"[Chat] ========== 전체 메시지 내용 끝 ==========")
        
        # OpenAI API 호출 (구버전 사용)
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        answer = response.choices[0].message.content
        print(f"[Chat] ✅ 구버전 OpenAI 응답 생성 완료")
        
        return {
            "status": "success",
            "response": answer,
            "message": "일반 LLM 채팅 완료"
        }
        
    except Exception as e:
        print(f"[Chat] 일반 LLM 채팅 오류: {str(e)}")
        import traceback
        print(f"[Chat] 오류 상세: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"일반 LLM 채팅 오류: {str(e)}")

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

# LangGraph 직접 실행 엔드포인트 (첫 번째 질문용)
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
        db_search_title = None
        
        if isinstance(result, dict):
            # 키워드 정보에서 태그 추출
            if 'keyword' in result and result['keyword']:
                if isinstance(result['keyword'], list):
                    tags = ', '.join(result['keyword'])
                else:
                    tags = str(result['keyword'])
                print(f"[LangGraph] 키워드: {len(result['keyword'])}개")
            
            # RAG 검색 결과에서 문서 타이틀 추출
            if 'candidates_total' in result and result['candidates_total']:
                db_search_title = f"{len(result['candidates_total'])}건"
                print(f"[LangGraph] 문서: {db_search_title}")
            
            # 응답 정보 확인
            if 'response' in result and result['response']:
                response_text = result['response'].get('answer', '')[:50] if isinstance(result['response'], dict) else str(result['response'])[:50]
                print(f"[LangGraph] 응답: {response_text}...")
        
        print(f"[LangGraph] 요약: 키워드 {len(result.get('keyword', []))}개, 문서 {len(result.get('candidates_total', []))}건")
        
        return {
            "status": "success",
            "result": result,
            "tags": tags,
            "db_search_title": db_search_title,
            "message": "LangGraph 실행 완료 (첫 번째 질문)"
        }
        
    except Exception as e:
        print(f"[LangGraph] 실행 오류: {str(e)}")
        import traceback
        print(f"[LangGraph] 오류 상세: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"LangGraph 실행 오류: {str(e)}")

# 추가 질문 처리 엔드포인트 (RAG 컨텍스트 재사용)
@router.post("/langgraph/followup")
async def execute_followup_question(request: StreamRequest, db: Session = Depends(get_db)):
    """추가 질문 처리 - 기존 RAG 컨텍스트와 대화 히스토리 활용"""
    try:
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=400, detail="OpenAI API 키가 설정되지 않았습니다.")
        
        print(f"[FOLLOWUP] 🔄 추가 질문 처리 시작: {request.question}")
        
        # 대화 ID 확인
        if not request.conversation_id:
            raise HTTPException(status_code=400, detail="추가 질문은 conversation_id가 필요합니다")
        
        # 첫 번째 질문 검증 제거 (프론트엔드에서 세션 기반으로 관리)
        print(f"[FOLLOWUP] 📝 추가 질문 처리 (세션 기반 관리로 인해 백엔드 검증 생략)")
        
        # 대화 컨텍스트 가져오기
        context = get_conversation_context(request.conversation_id, db)
        
        if not context["first_message"]:
            print(f"[FOLLOWUP] ⚠️ 첫 번째 질문 없음 - 기본 컨텍스트로 처리")
            # 첫 번째 질문이 없어도 일반적인 답변 제공
            document_title = "일반 대화"
            document_content = "이전 대화 맥락을 참고하여 답변드리겠습니다."
        else:
            # 첫 번째 질문의 키워드와 문서 정보 활용
            first_message = context["first_message"]
            
            # 기본 문서 정보 (실제 RAG 결과가 없으므로 키워드 기반으로 구성)
            document_title = first_message.db_search_title or "관련 문서"
            document_content = f"키워드: {first_message.keyword}\n검색 결과: {first_message.db_search_title}\n첫 번째 질문: {first_message.question}\n첫 번째 답변: {first_message.ans[:500] if first_message.ans else '답변 없음'}..."
        
        print(f"[FOLLOWUP] 📄 재사용할 RAG 문서:")
        print(f"[FOLLOWUP] 제목: {document_title}")
        print(f"[FOLLOWUP] 내용 길이: {len(document_content)} 문자")
        
        # 대화 히스토리 구성
        conversation_history = context["conversation_history"]
        print(f"[FOLLOWUP] 💬 대화 히스토리: {len(conversation_history)}개 메시지")
        
        # 시스템 프롬프트 구성
        system_prompt = f"""당신은 도움이 되는 AI 어시스턴트입니다. 
다음 문서를 참고하여 이전 대화의 맥락을 고려해서 답변해주세요.

[참고 문서]
문서 제목: {document_title}
문서 내용: {document_content[:1500]}...

위 문서 내용과 이전 대화를 바탕으로 추가 질문에 답변해주세요.
답변은 다음과 같이 작성해주세요:
- 한국어로 구어체로 작성
- 이전 대화의 맥락을 고려하여 자연스럽게 연결
- 문서 내용을 바탕으로 구체적이고 유용한 답변 제공
- 답변만 작성하고 추가적인 헤더나 형식은 포함하지 마세요"""
        
        # LLM API 호출을 위한 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]
        
        # 대화 히스토리 추가 (최근 10개 메시지만)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        messages.extend(recent_history)
        
        # 현재 질문 추가
        messages.append({"role": "user", "content": request.question})
        
        print(f"[FOLLOWUP] 📤 LLM에 전송할 메시지 수: {len(messages)}")
        print(f"[FOLLOWUP] 📝 현재 질문: {request.question}")
        
        # OpenAI API 호출
        try:
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            print(f"[FOLLOWUP] ✅ LLM 응답 생성 완료: {len(answer)} 문자")
            
        except Exception as e:
            print(f"[FOLLOWUP] ❌ LLM API 호출 실패: {e}")
            answer = f"죄송합니다. 추가 질문 처리 중 오류가 발생했습니다: {str(e)}"
        
        # 응답 구성 (추가 질문 모드)
        result = {
            "res_id": [],
            "answer": answer,
            "q_mode": "add",  # 추가 질문 모드
            "keyword": context["first_message"].keyword if context["first_message"] else None,
            "db_search_title": context["first_message"].db_search_title if context["first_message"] else None,
            "conversation_context": {
                "message_count": context["message_count"],
                "reused_context": True
            }
        }
        
        print(f"[FOLLOWUP] 📤 최종 응답 구조:")
        print(f"[FOLLOWUP] - q_mode: {result['q_mode']}")
        print(f"[FOLLOWUP] - 답변 길이: {len(result['answer'])} 문자")
        print(f"[FOLLOWUP] - 재사용된 문서: {document_title}")
        
        return {
            "status": "success",
            "result": result,
            "tags": context["first_message"].keyword if context["first_message"] else None,
            "db_search_title": context["first_message"].db_search_title if context["first_message"] else None,
            "message": "추가 질문 처리 완료 (컨텍스트 재사용)"
        }
        
    except Exception as e:
        print(f"[FOLLOWUP] 추가 질문 처리 오류: {str(e)}")
        import traceback
        print(f"[FOLLOWUP] 오류 상세: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"추가 질문 처리 오류: {str(e)}")

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

async def get_streaming_response(prompt: str, model: str = "gpt-3.5-turbo", generate_image: bool = False):
    """Stream a response from OpenAI API, optionally with an image"""
    try:
        # 이미지 URL (이미지 생성이 요청된 경우)
        image_url = None
        if generate_image or "이미지" in prompt or "그림" in prompt or "image" in prompt.lower() or "picture" in prompt.lower():
            image_url = await generate_image(prompt)
        
        if USING_NEW_SDK:
            # New SDK style (>1.0)
            client = OpenAI(api_key=OPENAI_API_KEY)
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                stream=True
            )
            
            text_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    text_response += content
                    
                    # 일반 텍스트만 스트리밍
                    yield f"data: {content}\n\n"
                await asyncio.sleep(0.01)  # 부드러운 스트리밍을 위한 짧은 지연
            
            # 텍스트 응답이 완료된 후 이미지 URL이 있으면 전송
            if image_url:
                response_data = {
                    "text": text_response,
                    "image_url": image_url
                }
                yield f"data: {json.dumps(response_data)}\n\n"
            
            yield "data: [DONE]\n\n"
        else:
            # Old SDK style (<1.0)
            openai.api_key = OPENAI_API_KEY
            stream = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                stream=True
            )
            
            text_response = ""
            for chunk in stream:
                if chunk['choices'][0].get('delta', {}).get('content'):
                    content = chunk['choices'][0]['delta']['content']
                    text_response += content
                    
                    # 일반 텍스트만 스트리밍
                    yield f"data: {content}\n\n"
                await asyncio.sleep(0.01)  # 부드러운 스트리밍을 위한 짧은 지연
            
            # 텍스트 응답이 완료된 후 이미지 URL이 있으면 전송
            if image_url:
                response_data = {
                    "text": text_response,
                    "image_url": image_url
                }
                yield f"data: {json.dumps(response_data)}\n\n"
            
            yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"Error in streaming response: {str(e)}")
        yield f"data: Error: {str(e)}\n\n"
        yield "data: [DONE]\n\n" 