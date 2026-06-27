import os, sys
import asyncio

_src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, _src_dir)

from api.design import generate_robot_design, DesignRequest
from retriever import Retriever

class MockState:
    def __init__(self):
        self.retriever = Retriever()

class MockApp:
    def __init__(self):
        self.state = MockState()

class MockRequest:
    def __init__(self):
        self.app = MockApp()

async def main():
    try:
        req = DesignRequest(query="scara robot")
        res = await generate_robot_design(MockRequest(), req)
        print("Subsystems:", res.subsystems)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
