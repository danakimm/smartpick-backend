from fastapi import APIRouter, WebSocket
from typing import List, Dict
from .agents.graph import define_workflow, AgentState
from enum import Enum

class ChatState(Enum):
    CLARIFYING = "clarifying"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"

router = APIRouter()
active_connections: Dict[str, WebSocket] = {}  # client_id로 연결 관리

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    
    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type", "")
            content = message.get("content", "")
            
            if message_type == "initial_question":
                workflow = define_workflow()
                clarification_state = {
                    "question": content,
                    "state": ChatState.CLARIFYING,
                    "client_id": client_id 
                }
                
                clarified_result = await workflow.run_clarification_agent(clarification_state)
                
                await websocket.send_json({
                    "type": "clarification_check",
                    "client_id": client_id,
                    "data": {
                        "original_question": content,
                        "clarified_question": clarified_result["clarified_question"],
                        "sub_questions": clarified_result["sub_questions"],
                        "needs_confirmation": True
                    }
                })
                
            elif message_type == "clarification_response":
                if content.get("confirmed"):
                    workflow = define_workflow()
                    initial_state: AgentState = {
                        "question": content["clarified_question"],
                        "sub_questions": content["sub_questions"],
                        "state": ChatState.PROCESSING,
                        "client_id": client_id, 
                        "youtube_results": {},
                        "review_results": {},
                        "spec_results": {},
                        "middleware_results": {},
                        "final_report": ""
                    }
                    
                    async def progress_callback(state: dict):
                        await websocket.send_json({
                            "type": "progress",
                            "client_id": client_id,
                            "data": state
                        })
                    
                    try:
                        workflow.add_progress_callback(progress_callback)
                        final_state = await workflow.invoke(initial_state)
                        await websocket.send_json({
                            "type": "complete",
                            "client_id": client_id,
                            "data": final_state
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "client_id": client_id,
                            "message": str(e)
                        })
                else:
                    await websocket.send_json({
                        "type": "request_clarification",
                        "client_id": client_id,
                        "data": {
                            "message": "질문을 다시 작성해주세요."
                        }
                    })
                    
    except Exception as e:
        print(f"WebSocket error for client {client_id}: {e}")
    finally:
        del active_connections[client_id]

@router.post("/analyze")
async def start_analysis_flow(question: str):
    # 워크플로우 초기화
    workflow = define_workflow()
    
    # 초기 상태 설정
    initial_state: AgentState = {
        "question": question,
        "sub_questions": [],
        "youtube_results": {},
        "review_results": {},
        "spec_results": {},
        "middleware_results": {},
        "final_report": ""
    }
    
    # 워크플로우 실행
    try:
        final_state = await workflow.invoke(initial_state)
        return {
            "status": "success",
            "report": final_state["final_report"]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/status/{task_id}")
async def get_analysis_status(task_id: str):
    # 워크플로우 상태 조회
    return await workflow.get_status(task_id) 