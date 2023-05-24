from typing import List, Tuple
from agent import Agent
from utils.functions import embed, create_embedding_bytes, profile
import time 
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))

print(parent_dir)


import time
class Twitter:
    def __init__(self) -> None:
        self.agents = []
        self.current_agent_index = 0    


    def run(self):
        while not self.paused:
            current_agent = self.agents[self.current_agent_index]
            feed = current_agent.recommend_feed()
            current_agent.view_feed(feed)
            self.current_agent_index = (self.current_agent_index + 1) % len(self.agents)
        time.sleep(1)  # Wait for 1 second before the next iteration

    def pause(self):
        self.paused = True

    def unpause(self):
        if self.agents:
            self.paused = False
            self.run()

    def add_agent(agent:Agent):
        self.agents += [agent]
        

game = Twitter([("DOnald Trump", "you are the former president of the us, you want to build a wall and hates nancy polosi, every tweet you make is a rhyme", True),
               ])

game.run()
                
                
        
