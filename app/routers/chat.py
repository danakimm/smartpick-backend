from fastapi import APIRouter, WebSocket
from typing import Dict
from app.agents.graph import define_workflow, AgentState
from app.agents.question_agent import QuestionAgent
import json
from app.utils.logger import logger

router = APIRouter()
active_connections: Dict[str, WebSocket] = {}  # client_id로 연결 관리


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    
    # WebSocket timeout 설정
    websocket.client.timeout = 60.0  # 60초 timeout 설정

    try:
        question_agent = QuestionAgent()
        state = {}
        workflow = define_workflow()
        app = workflow.compile()

        # 초기 메시지 전송
        initial_response = await question_agent.run(state)
        await websocket.send_json({
            "type": "message",
            "client_id": client_id,
            "data": {
                "response": initial_response.get("response", ""),
                "status": initial_response.get("status", "")
            }
        })

        while True:
            message = await websocket.receive_json()

            if message.get("type") == "feedback":
                # 피드백 처리
                try:
                    feedback_content = message.get("content", "")
                    requirements = initial_response.get("requirements", "")

                    # 필요한 AgentState 필드가 모두 있는지 확인하고 추가
                    feedback_state = {
                        "question": requirements,
                        "sub_questions": [],
                        "youtube_agent_state": {},
                        "review_agent_state": {},
                        "spec_agent_state": {},
                        "youtube_results": {},
                        "review_results": {},
                        "spec_results": {},
                        "middleware_results": {},
                        "final_report": "",
                        "feedback": feedback_content,
                        "feedback_type": "",
                        "refined_requirements": {},
                        "feedback_response": ""
                    }

                    logger.debug(f"Processing feedback with state: {feedback_state}")

                    final_state = await app.ainvoke(feedback_state)

                    await websocket.send_json({
                        "type": "feedback_response",
                        "client_id": client_id,
                        "data": {
                            "response": final_state.get("feedback_response") or final_state.get("final_report", ""),
                            "analysis": final_state.get("middleware_results", {}).get("analysis", {})
                        }
                    })
                except Exception as e:
                    logger.error(f"Error processing feedback: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "client_id": client_id,
                        "data": {
                            "message": f"피드백 처리 중 오류가 발생했습니다: {str(e)}"
                        }
                    })
            else:
                content = message.get("content", "")

                # QuestionAgent 상태 안전하게 업데이트
                state = {
                    "user_input": content,
                    "conversation_history": initial_response.get('conversation_history', []),
                    "requirements": initial_response.get('requirements', ""),
                    "collected_info": initial_response.get('collected_info', {}),
                    "missing_info": initial_response.get('missing_info', []),
                    "current_question": initial_response.get('current_question', ""),
                    "status": initial_response.get('status', ""),
                    "additional_requirements": initial_response.get('additional_requirements', "")
                }

                # QuestionAgent 실행
                try:
                    response = await question_agent.run(state)

                    # 응답 업데이트 - 후속 요청에서 사용할 수 있도록 initial_response를 업데이트
                    initial_response = response

                    # 클라이언트에 응답 전송
                    await websocket.send_json({
                        "type": "message",
                        "client_id": client_id,
                        "data": {
                            "response": response.get("response", ""),
                            "status": response.get("status", "")
                        }
                    })

                    # completed 상태인 경우 워크플로우 실행
                    if response.get('status') == "completed":
                        try:
                            agent_states = await question_agent._prepare_agent_states(response.get('requirements', ""))

                            # AgentState 형식에 맞는 초기 상태 생성
                            initial_state = {
                                "question": response.get("requirements", ""),
                                "sub_questions": [],
                                "youtube_agent_state": agent_states.get("youtube_agent_state", {}),
                                "review_agent_state": agent_states.get("review_agent_state", {}),
                                "spec_agent_state": agent_states.get("spec_agent_state", {}),
                                "youtube_results": {},
                                "review_results": {},
                                "spec_results": {},
                                "middleware_results": {},
                                "final_report": "",
                                "feedback": "",
                                "feedback_type": "",
                                "refined_requirements": {},
                                "feedback_response": "",
                            }

                            logger.debug(f"Starting workflow with initial state: {initial_state}")

                            final_state = await app.ainvoke(initial_state)
                            await websocket.send_json({
                                "type": "complete",
                                "client_id": client_id,
                                "data": final_state
                            })
                        except Exception as e:
                            logger.error(f"Error running workflow: {str(e)}")
                            logger.debug(f"Error details: {type(e).__name__}")  # 오류 타입 추가
                            await websocket.send_json({
                                "type": "error",
                                "client_id": client_id,
                                "data": {
                                    "message": "워크플로우 실행 중 오류가 발생했습니다",
                                    "error": str(e)
                                }
                            })
                except Exception as e:
                    logger.error(f"Error running QuestionAgent: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "client_id": client_id,
                        "data": {
                            "message": f"질문 처리 중 오류가 발생했습니다: {str(e)}"
                        }
                    })
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        if client_id in active_connections:
            del active_connections[client_id]