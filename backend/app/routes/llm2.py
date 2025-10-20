async def save_langgraph_result_to_db(question: str, response: dict, keywords: list, candidates_total: list, image_url: str = None):
    """LangGraph 실행 결과를 DB에 직접 저장 (랭그래프 전용)"""
    try:
        print(f"[DB_SAVE] LangGraph 결과 DB 저장 시작 (랭그래프 전용)")
        print(f"[DB_SAVE] 질문: {question}")
        print(f"[DB_SAVE] 응답: {response.get('answer', '')[:100]}...")
        print(f"[DB_SAVE] 키워드: {keywords}")
        print(f"[DB_SAVE] 문서: {len(candidates_total)}건")
        print(f"[DB_SAVE] 이미지 URL: {image_url}")
        
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
            db_search_title=str([item.get('res_payload', {}).get('document_name', '') for item in candidates_total[:5]]) if candidates_total else None,
            image=image_url  # 이미지 URL 추가
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
        
    except Exception as e:
        print(f"[LLM_RESPONSE] 오류: {str(e)}")
        yield  f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"




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
        
        # 스트리밍 방식 사용
        return StreamingResponse(
            get_streaming_response_async(messages, http_request, request.generate_image or False),
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
async def execute_langgraph_stream(request: StreamRequest, db: Session = Depends(get_db)):
    """LangGraph SSE 스트리밍 실행 (첫 번째 질문 전용)"""
    
    async def generate_sse():
        generator_id = str(uuid.uuid4())
        generator = SSEGenerator(generator_id)
        sse_generators[generator_id] = generator
        
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
                "generator_id": generator_id
            }
            
            print(f"[SSE] LangGraph 실행 시작: {request.question}")
            
            # LangGraph 실행을 별도 태스크로 실행
            async def run_langgraph():
                try:
                    result = await langgraph_instance.ainvoke(initial_state)
                    # DONE 메시지에 전체 LangGraph 결과 포함
                    done_message = {
                        "stage": "DONE", 
                        "result": result,  # 전체 LangGraph 결과 포함
                        "keyword": result.get('keyword', []),
                        "candidates_total": result.get('candidates_total', [])
                    }
                    await generator.send_message(done_message)
                except Exception as e:
                    await generator.send_message({"stage": "ERROR", "error": str(e)})
                finally:
                    await generator.close()
            
            # LangGraph 실행 태스크 시작
            langgraph_task = asyncio.create_task(run_langgraph())
            
            # SSE 메시지 스트리밍
            while generator.is_active:
                try:
                    # 타임아웃을 짧게 설정하여 응답성 향상
                    message = await asyncio.wait_for(generator.message_queue.get(), timeout=0.1)
                    
                    if message is None:  # 종료 신호
                        break
                    
                    # SSE 형식으로 메시지 전송
                    yield f"data: {json.dumps(message)}\n\n"
                    
                except asyncio.TimeoutError:
                    # 타임아웃 시 하트비트 전송
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"
                    continue
                except Exception as e:
                    print(f"[SSE] 메시지 처리 오류: {e}")
                    break
            
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


# 추가 질문 스트리밍 처리 엔드포인트
@router.post("/langgraph/followup/stream")
async def execute_followup_question_stream(request: StreamRequest, http_request: Request, db: Session = Depends(get_db)):
    """추가 질문 스트리밍 처리 - 기존 RAG 컨텍스트와 대화 히스토리 활용"""
    try:
        # OpenAI API 키 확인
        if not OPENAI_API_KEY:
            return Response(content="Error: OpenAI API 키가 설정되지 않았습니다.", media_type="text/plain")
        
        print(f"[FOLLOWUP_STREAM] 🔄 LLM 추가 질문 스트리밍 처리 시작: {request.question}")
        
        # 대화 ID 확인
        if not request.conversation_id:
            return Response(content="Error: 추가 질문은 conversation_id가 필요합니다", media_type="text/plain")
        
        # LangGraph 컨텍스트 처리 (프론트엔드에서 전송된 경우)
        langgraph_context = getattr(request, 'langgraph_context', None)
        include_langgraph_context = getattr(request, 'include_langgraph_context', False)
        
        if include_langgraph_context and langgraph_context:
            print(f"[FOLLOWUP_STREAM] 🔬 LangGraph 컨텍스트 사용")
            print(f"[FOLLOWUP_STREAM] 원본 질문: {langgraph_context.get('original_question', 'N/A')}")
            print(f"[FOLLOWUP_STREAM] 키워드: {langgraph_context.get('keywords', 'N/A')}")
            print(f"[FOLLOWUP_STREAM] 검색 결과 수: {len(langgraph_context.get('search_results', []))}")
            
            # LangGraph 컨텍스트로 문서 정보 구성
            document_title = "LangGraph 검색 결과"
            search_results = langgraph_context.get('search_results', [])
            keywords = langgraph_context.get('keywords', [])
            previous_answer = langgraph_context.get('previous_answer', '')
            original_question = langgraph_context.get('original_question', '')
            
            # 검색 결과를 문서 내용으로 구성
            search_content = ""
            for i, result in enumerate(search_results[:3], 1):
                if isinstance(result, dict) and 'res_payload' in result:
                    title = result['res_payload'].get('document_name', f'문서 {i}')
                    vector_data = top_payload.get("vector", {})
                    # vector가 dict인지 확인 후 특정 키값만 추출
                    content = vector_data.get("text") if isinstance(vector_data, dict) else None
                    search_content += f"\n[문서 {i}] {title}: {content}"
            
            document_content = f"""
[첫 번째 질문] {original_question}

[추출된 키워드] {', '.join(keywords) if isinstance(keywords, list) else keywords}

[검색된 문서들]{search_content}

[이전 답변] {previous_answer[:500]}...
"""
        else:
            # 기존 대화 컨텍스트 사용
            context = get_conversation_context(request.conversation_id, db)
            
            if not context["first_message"]:
                print(f"[FOLLOWUP_STREAM] ⚠️ 첫 번째 질문 없음 - 기본 컨텍스트로 처리")
                document_title = "일반 대화"
                document_content = "이전 대화 맥락을 참고하여 답변드리겠습니다."
            else:
                # 첫 번째 질문의 키워드와 문서 정보 활용
                first_message = context["first_message"]
                document_title = first_message.db_search_title or "관련 문서"
                document_content = f"키워드: {first_message.keyword}\n검색 결과: {first_message.db_search_title}\n첫 번째 질문: {first_message.question}\n첫 번째 답변: {first_message.ans[:500] if first_message.ans else '답변 없음'}..."
        
        print(f"[FOLLOWUP_STREAM] 📄 재사용할 RAG 문서:")
        print(f"[FOLLOWUP_STREAM] 제목: {document_title}")
        print(f"[FOLLOWUP_STREAM] 내용 길이: {len(document_content)} 문자")
        
        # 대화 히스토리 구성
        if include_langgraph_context and langgraph_context:
            # LangGraph 컨텍스트 사용 시 기본 대화 히스토리만 가져오기
            context = get_conversation_context(request.conversation_id, db)
            conversation_history = context["conversation_history"]
        else:
            # 기존 방식 사용
            conversation_history = context["conversation_history"]
        
        print(f"[FOLLOWUP_STREAM] 💬 대화 히스토리: {len(conversation_history)}개 메시지")
        
        # 시스템 프롬프트 구성
        system_prompt = f"""당신은 도움이 되는 AI 어시스턴트입니다. 
다음 문서를 참고하여 이전 대화의 맥락을 고려해서 답변해주세요.

[참고 문서]
문서 제목: {document_title}
문서 내용: {str(document_content)[:1500]}...

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
        
        print(f"[FOLLOWUP_STREAM] 📤 LLM에 전송할 메시지 수: {len(messages)}")
        print(f"[FOLLOWUP_STREAM] 📝 현재 질문: {request.question}")
        
        # 스트리밍 방식 사용
        return StreamingResponse(
            get_streaming_response_async(messages, http_request, request.generate_image or False),
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

async def get_streaming_response_async(messages: List[Dict], request: Request, generate_image: bool = False):
    """Stream a response from LLM using AsyncOpenAI with custom headers"""
    try:
        print(f"[LLM_STREAM] 🚀 LLM 스트리밍 시작")
        
        # 이미지 URL (이미지 생성이 요청된 경우)
        image_url = None
        if generate_image:
            # 실제 이미지 생성 로직은 별도 구현 필요
            image_url = await generate_image(messages[-1]["content"] if messages else "")
        
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
                    await asyncio.sleep(0.01)  # 청크 사이에 지연 추가하여 다른 API 처리 가능하도록 함
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
        print(f"[LLM_STREAM] Error in streaming response: {str(e)}")
        import traceback
        print(f"[LLM_STREAM] 오류 상세: {traceback.format_exc()}")
        try:
            error_payload = json.dumps({'error': str(e)}, ensure_ascii=False)
            yield (f"data: {error_payload}\n\n").encode("utf-8")
            yield "data: [DONE]\n\n".encode("utf-8")
        except Exception:
            # 에러 전송도 실패한 경우 조용히 종료
            return
