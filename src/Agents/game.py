from typing import List, Tuple
import time 
import asyncio
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))
print(parent_dir)

from Agents.agent import Agent
from utils.functions import embed, create_embedding_bytes, profile

import time
class Agent_Manager:
    def __init__(self, twitter_db) -> None:
        print("initialize agent manager")
        self.agents = []
        self.current_agent_index = 0
        self._paused = True
        self._twitter_db = twitter_db
        
    async def run(self):
        while not self._paused and self.agents:
            current_agent = self.agents[self.current_agent_index]
            feed = current_agent.recommend_feed()
            current_agent.view_feed(feed)
            self.current_agent_index = (self.current_agent_index + 1) % len(self.agents)
            time.sleep(1)  # Wait for 1 second before the next iteration

    def pause(self):
        self._paused = True

    def unpause(self):
        self._paused = False
        self.run()

    def pause_unpause(self):
        if self._paused is True:
            self.unpause()
        else:
            self.pause()

    def add_agent(self, name, description) -> None:
        agent = Agent(name, description, 100, self._twitter_db)
        self.agents.append(agent)

    def collect_agents(self):
        return [agent.to_dict() for agent in self.agents]


        