from typing import List, Tuple
from agent import Agent
from utils.functions import embed, create_embedding_bytes, profile
class Twitter:
    def __init__(self, agents: List[Tuple[str,str, bool]]) -> None:
        self.agents = [Agent(name, description, 150, use_openai, 0) for name, description, use_openai in agents]
        
    def run(self):
        for _ in range(10):
            for agent in self.agents:
                feed = agent.recommend_feed()
                agent.view_feed(feed)

game = Twitter([("DOnald Trump", "you are the former president of the us, you want to build a wall and hate nancy polosi, every tweet you make is a rhyme", True),
               ])

game.run()
                
                
        
