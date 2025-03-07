from fastapi import APIRouter, WebSocket
from typing import Dict
from app.agents.graph import define_initial_workflow, define_feedback_workflow, AgentState
from app.agents.question_agent import QuestionAgent
import json
from app.utils.logger import logger

router = APIRouter()
active_connections: Dict[str, WebSocket] = {}  # client_id로 연결 관리
<<<<<<< HEAD
def remove_none(data):
    if not data:
        data={"key":"None"}
        return data
    return data
=======


>>>>>>> origin/main
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    
    try:
        question_agent = QuestionAgent()
        state = {}
        # 두 개의 워크플로우 초기화
        initial_workflow = define_initial_workflow()
        feedback_workflow = define_feedback_workflow()
        initial_app = initial_workflow.compile()
        feedback_app = feedback_workflow.compile()

        # 초기 메시지 전송
        initial_response = await question_agent.run(state)
        await websocket.send_json({
            "type": "message",
            "client_id": client_id,
            "data": {
<<<<<<< HEAD
                "response": remove_none(initial_response).get("response", ""),
                "status": remove_none(initial_response).get("status", "")
=======
                "response": initial_response.get("response", ""),
                "status": initial_response.get("status", "")
>>>>>>> origin/main
            }
        })

        while True:
            message = await websocket.receive_json()
<<<<<<< HEAD
            #if remove_none(message).get("message"):
                
            # 연결 종료 메시지 처리 추가
            if remove_none(message).get("type") == "close":
=======
            
            # 연결 종료 메시지 처리 추가
            if message.get("type") == "close":
>>>>>>> origin/main
                # 진행 중인 워크플로우가 있다면 정리
                if initial_app:
                    await initial_app.aclose()
                if feedback_app:
                    await feedback_app.aclose()
                
                # QuestionAgent 정리
                if question_agent:
                    await question_agent.close()  # QuestionAgent에 close 메서드가 있다면
                
                logger.info(f"Closing connection for client {client_id}")
                await websocket.close()
                break

<<<<<<< HEAD
            if remove_none(message).get("type") != "feedback":
                # 일반 메시지 처리 (요구사항 수집)
                content = remove_none(message).get("content", "")
=======
            if message.get("type") != "feedback":
                # 일반 메시지 처리 (요구사항 수집)
                content = message.get("content", "")
>>>>>>> origin/main
                
                # QuestionAgent 상태 업데이트
                state = {
                    "user_input": content,
<<<<<<< HEAD
                    "conversation_history": remove_none(initial_response).get('conversation_history', []),
                    "requirements": remove_none(initial_response).get('requirements', ""),
                    "collected_info": remove_none(initial_response).get('collected_info', {}),
                    "missing_info": remove_none(initial_response).get('missing_info', []),
                    "current_question": remove_none(initial_response).get('current_question', ""),
                    "status": remove_none(initial_response).get('status', ""),
                    "additional_requirements": remove_none(initial_response).get('additional_requirements', "")
=======
                    "conversation_history": initial_response.get('conversation_history', []),
                    "requirements": initial_response.get('requirements', ""),
                    "collected_info": initial_response.get('collected_info', {}),
                    "missing_info": initial_response.get('missing_info', []),
                    "current_question": initial_response.get('current_question', ""),
                    "status": initial_response.get('status', ""),
                    "additional_requirements": initial_response.get('additional_requirements', "")
>>>>>>> origin/main
                }

                try:
                    response = await question_agent.run(state)
                    initial_response = response

                    await websocket.send_json({
                        "type": "message",
                        "client_id": client_id,
                        "data": {
<<<<<<< HEAD
                            "response": remove_none(response).get("response", ""),
                            "status": remove_none(response).get("status", "")
=======
                            "response": response.get("response", ""),
                            "status": response.get("status", "")
>>>>>>> origin/main
                        }
                    })

                    # requirements_collected 상태인 경우 초기 워크플로우 실행
<<<<<<< HEAD
                    if remove_none(response).get('status') == "requirements_collected":
                        try:
                            agent_states = await question_agent._prepare_agent_states(remove_none(response).get('requirements', ""))

                            initial_state = {
                                "question": remove_none(response).get("requirements", ""),
=======
                    if response.get('status') == "requirements_collected":
                        try:
                            agent_states = await question_agent._prepare_agent_states(response.get('requirements', ""))

                            initial_state = {
                                "question": response.get("requirements", ""),
>>>>>>> origin/main
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

                            logger.debug(f"Starting initial workflow with state: {initial_state}")

                            final_state = await initial_app.ainvoke(initial_state)
                            initial_response.update(final_state)  # 상태 저장
                            
                            await websocket.send_json({
                                "type": "complete",
                                "client_id": client_id,
                                "data": final_state
                            })
                        except Exception as e:
                            logger.error(f"Error running initial workflow: {str(e)}")
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

            else:
                # 피드백 처리
                try:
<<<<<<< HEAD
                    feedback_content = remove_none(message).get("content", "")
                    requirements = remove_none(initial_response).get("requirements", "")
=======
                    feedback_content = message.get("content", "")
                    requirements = initial_response.get("requirements", "")
>>>>>>> origin/main

                    # 피드백 워크플로우용 상태 준비
                    feedback_state = {
                        "question": requirements,
<<<<<<< HEAD
                        "youtube_agent_state": remove_none(initial_response).get("youtube_agent_state", {}),
                        "review_agent_state": remove_none(initial_response).get("review_agent_state", {}),
                        "spec_agent_state": remove_none(initial_response).get("spec_agent_state", {}),
                        "youtube_results": remove_none(initial_response).get("youtube_results", {}),
                        "review_results": remove_none(initial_response).get("review_results", {}),
                        "spec_results": remove_none(initial_response).get("spec_results", {}),
                        "middleware_results": remove_none(initial_response).get("middleware_results", {}),
                        "final_report": remove_none(initial_response).get("final_report", ""),
=======
                        "youtube_agent_state": initial_response.get("youtube_agent_state", {}),
                        "review_agent_state": initial_response.get("review_agent_state", {}),
                        "spec_agent_state": initial_response.get("spec_agent_state", {}),
                        "youtube_results": initial_response.get("youtube_results", {}),
                        "review_results": initial_response.get("review_results", {}),
                        "spec_results": initial_response.get("spec_results", {}),
                        "middleware_results": initial_response.get("middleware_results", {}),
                        "final_report": initial_response.get("final_report", ""),
>>>>>>> origin/main
                        "feedback": feedback_content,
                        "feedback_type": "",
                        "refined_requirements": {},
                        "feedback_response": ""
                    }

                    logger.debug(f"Processing feedback with state: {feedback_state}")

                    # 피드백 워크플로우 실행
                    final_state = await feedback_app.ainvoke(feedback_state)

                    # 응답 전송 (피드백 타입에 따라 다른 응답)
                    if final_state.get("feedback_type") == "refinement":
                        await websocket.send_json({
                            "type": "feedback_response",
                            "client_id": client_id,
                            "data": {
                                "response": final_state.get("final_report", ""),
                                "analysis": final_state.get("middleware_results", {}).get("analysis", {})
                            }
                        })
                    else:  # 단순 질문
                        await websocket.send_json({
                            "type": "feedback_response",
                            "client_id": client_id,
                            "data": {
                                "response": final_state.get("feedback_response", "")
                            }
                        })

                    # 상태 업데이트
                    initial_response.update(final_state)

                except Exception as e:
                    logger.error(f"Error processing feedback: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "client_id": client_id,
                        "data": {
                            "message": f"피드백 처리 중 오류가 발생했습니다: {str(e)}"
                        }
                    })


    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        if client_id in active_connections:
            del active_connections[client_id]