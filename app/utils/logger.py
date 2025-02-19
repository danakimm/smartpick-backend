import logging

# Logger 설정
logger = logging.getLogger("smartpick")
logger.setLevel(logging.DEBUG)

# 콘솔 핸들러 생성 및 설정
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# 핸들러를 로거에 추가
logger.addHandler(console_handler)