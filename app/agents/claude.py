from langchain.chat_models import ChatAnthropic
from .base import BaseAgent

class QuestionDecompositionAgent(BaseAgent):
    def __init__(self):
        super().__init__("question_decomposition")
        self.llm = ChatAnthropic()
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        question = state["question"]
        
        # 질문을 세부 질문으로 분해하는 프롬프트
        prompt = f"""
        다음 질문을 유튜브 리뷰 분석용, 스펙 분석용, 사용자 리뷰 분석용 
        세 가지 세부 질문으로 분해해주세요:
        
        질문: {question}
        """
        
        response = await self.llm.apredict(prompt)
        
        # 응답 파싱 및 상태 업데이트
        sub_questions = self._parse_response(response)
        return {
            "sub_questions": sub_questions,
            "original_question": question
        } 