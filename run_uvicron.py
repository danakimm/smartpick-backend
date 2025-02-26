# run_uvicorn.py
import sys, os
# 프로젝트 루트(여기 run_uvicorn.py가 있는 곳)를 sys.path의 최상단에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=os.path.abspath(os.path.dirname(__file__)))