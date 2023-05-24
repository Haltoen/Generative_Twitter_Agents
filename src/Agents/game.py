from typing import List, Tuple
from agent import Agent
from utils.functions import embed, create_embedding_bytes, profile
import time 
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))

print(parent_dir)


class Twitter:
    def __init__(self, agents: List[Tuple[str,str, bool]]) -> None:
        self.agents = [Agent(name, description, 150, use_openai, 0) for name, description, use_openai in agents]
        
    def run(self):
        for _ in range(10):
            for agent in self.agents:
                feed = agent.recommend_feed()
                agent.view_feed(feed) 



agent = Agent("kanye", "you are kanye west but in a counterfactual universe where you and pete davidson are in love, you love jews. you tweet a lot about you and petes sex life", 150, True, 100)
#agent._memory_db.get_reflections()
b = agent._twitter_db.view_columns("Users")
