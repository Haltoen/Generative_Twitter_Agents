from typing import List, Tuple
from agent import Agent
from utils.functions import embed
class Twitter:
    def __init__(self, agents: List[Tuple[str,str, bool]]) -> None:
        self.agents = [Agent(name, description, 150, use_openai, 100) for name, description, use_openai in agents]
        print(agents)
        
    def run(self):
        for i in range(2):
            for agent in self.agents:
                feed = agent.recommend_feed()
                embed(['hello bitch'])
                agent.react(feed)
                
twitter =  Twitter([("yoga_lover", 'you love yoga, you tweet about your free yoga classes, you are a yoga instructor', True), ("yoga_hater", 'you hate yoga, you tweet about how yoga is a cult, you are a yoga instructor', True)])
twitter.run()
 
agent = Agent("yoga_lover", 'you love yoga, you tweet about your free yoga classes, you are a yoga instructor', 150, True, 100)
agent.recommend_feed()
