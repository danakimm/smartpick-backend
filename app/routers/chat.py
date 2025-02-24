from fastapi import APIRouter, WebSocket
from typing import Dict
from .agents.graph import define_workflow, AgentState
from .agents.question_agent import QuestionAgent

router = APIRouter()
active_connections: Dict[str, WebSocket] = {}  # client_id로 연결 관리

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    
    try:
        question_agent = QuestionAgent()
        state = {}
        
        # 초기 메시지 전송
        initial_response = await question_agent.run(state)
        await websocket.send_json({
            "type": "message",
            "client_id": client_id,
            "data": {
                "response": initial_response["response"],
                "status": initial_response["status"]
            }
        })
        
        while True:
            message = await websocket.receive_json()
            content = message.get("content", "")
            
            # QuestionAgent 상태 업데이트
            state = {
                "user_input": content,
                "conversation_history": initial_response.get('conversation_history', []),
                "requirements": initial_response.get('requirements'),
                "collected_info": initial_response.get('collected_info', {}),
                "missing_info": initial_response.get('missing_info', []),
                "current_question": initial_response.get('current_question'),
                "status": initial_response.get('status'),
                "additional_requirements": initial_response.get('additional_requirements')
            }
            
            # QuestionAgent 실행
            response = await question_agent.run(state)
            
            # 클라이언트에 응답 전송
            await websocket.send_json({
                "type": "message",
                "client_id": client_id,
                "data": {
                    "response": response["response"],
                    "status": response["status"]
                }
            })
            
            # completed 상태인 경우 워크플로우 실행
            if response.get('status') == "completed":
                workflow = define_workflow()
                agent_states = await question_agent._prepare_agent_states(response['requirements'])
                
                initial_state: AgentState = {
                    "question": response["requirements"],
                    "sub_questions": [],
                    "youtube_agent_state": agent_states["youtube_agent_state"],
                    "review_agent_state": agent_states["review_agent_state"],
                    "spec_agent_state": agent_states["spec_agent_state"],
                    "youtube_results": {},
                    "review_results": {},
                    "spec_results": {},
                    "middleware_results": {},
                    "final_report": ""
                }
                
                final_state = await workflow.invoke(initial_state)
                await websocket.send_json({
                    "type": "complete",
                    "client_id": client_id,
                    "data": final_state
                })
    except Exception as e:
        print(f"WebSocket error for client {client_id}: {e}")
    finally:
        del active_connections[client_id] 