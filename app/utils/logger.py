import logging
import os

def setup_logger(log_dir: str = "logs"):
    # 로그 디렉토리 생성
    os.makedirs(log_dir, exist_ok=True)
    
    # Logger 설정
    logger = logging.getLogger("smartpick")
    logger.setLevel(logging.DEBUG)

    # 이미 핸들러가 있다면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(os.path.join(log_dir, 'smartpick.log'))
    file_handler.setLevel(logging.DEBUG)
    
    # 포맷터 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 핸들러를 로거에 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# 기본 로거 설정
logger = setup_logger()