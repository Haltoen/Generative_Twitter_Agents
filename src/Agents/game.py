from typing import List, Tuple
from agent import Agent
from utils.functions import embed, create_embedding_bytes, profile
class Twitter:
    def __init__(self, agents: List[Tuple[str,str, bool]]) -> None:
        self.agents = [Agent(name, description, 150, use_openai, 100) for name, description, use_openai in agents]
        
    def run(self):
        for _ in range(2):
            for agent in self.agents:
                feed = agent.recommend_feed()
                agent.view_feed(feed)

game = Twitter([("haiku master", "you are a mysterious but insightful man that writes everything as a haiku poem", True),
                ("rhyming anon", "everything you wrtie starts with a and rhymes you love sports and are interested in ai", False)])

game.run()
                
                
        
