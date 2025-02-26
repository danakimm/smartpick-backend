import queue
from typing import List, Dict, Any
import threading
import time
# 글로벌 변수로 큐 선언
_global_queue = None

def get_queue():
    global _global_queue
    if _global_queue is None:
        _global_queue = queue.Queue()
    return _global_queue

def add_log(message):
    get_queue().put(message)
    
    
class LogConsumer:
    """
    상시 구동형 로그 소비자 클래스
    로그 큐에서 메시지를 꺼내 처리하고 최근 로그를 유지합니다.
    """
    def __init__(self, max_logs=100):
        # 최근 로그 저장용 리스트
        self.recent_logs: List[str] = []
        # 최대 로그 개수
        self.max_logs = max_logs
        self.thread=threading.Thread(target=self.Que_main_loop)
        # 에이전트 상태 정보
        self.state: Dict[str, Any] = {
            "status": "idle",
            "last_update": time.time(),
            "error_count": 0,
            "processed_logs": 0
        }
        # 스레드 관련 변수
        self._stop_event = threading.Event()
        self.consumer_thread = None
        # 싱글톤 인스턴스 등록
        LogConsumer._instance = self
    def process_state_info(self, log_message: str) -> None:
        """
        로그 메시지에서 <<::STATE::문자열>> 형태의 상태 정보를 추출하고 
        상태를 직접 업데이트합니다.
        
        Args:
            log_message: 로그 메시지 문자열
        """
        import re
        # 정규식 패턴을 사용하여 <<::STATE::문자열>> 형식 찾기
        pattern = r'<<::STATE::(.*?)>>'
        match = re.search(pattern, log_message)
        if match:
            # 그룹 1(첫 번째 괄호 안의 내용)이 실제 상태 정보
            state_info = match.group(1)
            # 상태 정보 업데이트
            self.state["status"] = state_info
            self.state["last_update"] = time.time()
    def log_processing(self, log_message: str) -> None:
                # 상태 정보 처리
        self.process_state_info(log_message)
        
        # 최근 로그 목록에 추가
        self.recent_logs.append(log_message)
        
        # 최대 개수 유지
        if len(self.recent_logs) > self.max_logs:
            self.recent_logs.pop(0)  # 가장 오래된 로그 제거
        
        # 처리 완료 표시
        get_queue().task_done()
        
        # 처리된 로그 카운트 증가
        self.state["processed_logs"] += 1
    def run(self):
        if not self.thread.is_alive():
            self.FLAG = True
            self.thread.start()
            return True
        return False
        

    def Que_main_loop(self):
        """
        로그 소비자의 메인 루프. 
        큐에서 로그를 꺼내 처리하고, 큐가 비었을 경우 일정 시간 대기합니다.
        """
        self.FLAG = True
        
        while self.FLAG:
            messages_processed = 0
            
            # 큐에 메시지가 있는 동안 계속 처리
            while not get_queue().empty():
                try:
                    # 큐에서 로그 메시지 가져오기
                    log_message = get_queue().get(block=False)
                    self.log_processing(log_message)
                    messages_processed += 1
                except queue.Empty:
                    # 큐가 비었을 경우 루프 종료
                    break
                except Exception as e:
                    # 오류 발생 시 카운트 증가
                    self.state["error_count"] += 1
                    print(f"로그 처리 중 오류 발생: {e}")
                    self.log_processing(f"로그 처리 중 오류 발생: {e}")
            # 메시지가 처리되지 않았을 경우에만 대기
            if messages_processed == 0:
                time.sleep(2)  # 2초 대기
    def stop(self):
        """
        로그 소비자를 안전하게 종료합니다.
        FLAG 변수를 변경하여 run 메서드의 루프가 종료되도록 합니다.
        """
        if self.thread.is_alive():
            self.FLAG = False
            self.state["status"] = "shutdown"
            self.log_processing("로그 소비자 종료 요청됨. 다음 사이클에서 종료됩니다.")
            self.thread.join()
            return True
        return False