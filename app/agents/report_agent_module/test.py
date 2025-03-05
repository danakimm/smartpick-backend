from app.agents.report_agent import ReportAgent
from .dummy import get_dummy
import asyncio
import time


def main():
    start=time.time()
    data=get_dummy()
    agent=ReportAgent()
    result=asyncio.run(agent.run(data))
    import pprint
    pprint.pprint(result, width=150)
    print(f"실행 시간 : {time.time()-start}")
    return result

if __name__ == "__main__":
    main()
    
