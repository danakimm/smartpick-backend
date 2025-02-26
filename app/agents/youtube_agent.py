from search import print_with_output, Keyword_filter
from typing import Dict, Any
import asyncio
from base import BaseAgent
from queue_manager import add_log, LogConsumer
globalist=[]

def log_wrapper(log_message):
    globalist.append(log_message)
    add_log(log_message)
    
class YouTube_agent(BaseAgent):
    def __init__(self, name="youtube_agent"):
        self.name = name
        self.filtter= Keyword_filter()
        self.input= {}
        self.query= ""
        self.output= {}
        self.flag= False    
        self.log_manager = LogConsumer(max_logs=200)
        self.log_manager.run()

        
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 입력 처리...
        self.input = state
        if "query" not in self.input.keys():
            log_wrapper( "<<::STATE::ail error: query key is not in input>>")
            return {"fail error": "query key is not in input"}
        
        
        self.query = self.input["query"]
        try:
            log_wrapper(f"<<::STATE::inference_thread_started>>")
            # 서브스레드에서 실행하고 결과를 직접 받음
            result = await asyncio.to_thread(self.run_inference)
            
            log_wrapper(f"<<::STATE::inference_thread_completed>>")
            return result
            
        except Exception as e:
            log_wrapper(f"<<::STATE::error>>")
            return {"fail error": str(e)}

    def run_inference(self):
        """결과를 직접 반환하는 서브스레드 메서드"""
        try:
            # 플래그 설정 (모니터링용)
            self.flag = True
            # 실제 추론 실행
            result = self.extract_from_query()
            # 최종 출력 구성

            # 플래그 해제
            self.flag = False
            
            # 결과 직접 반환
            return result
        except Exception as e:
            self.flag = False
            log_wrapper(f"서브스레드 오류: {str(e)}")
            raise  # 예외를 메인스레드로 전파
        
    def extract_from_query(self):
        a,b,c =print_with_output(self.filtter,self.query)
        self.output['recent result']= a
        self.output['key_name']= b
        self.output['RAGOUT_class']= c
        self.flag= False        
        return a
    def clean(self):
        self.log_manager.stop()



if __name__ == "__main__":
    
    youtube_agent = YouTube_agent()
    input_data = {"query": "애플 태블릿 추천해줘 "}
    result=asyncio.run(youtube_agent.run(input_data))
    youtube_agent.clean()
