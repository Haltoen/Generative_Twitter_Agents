from typing import List, Tuple
import time 
import sys
from pathlib import Path


parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))
print(parent_dir)

from Agents.agent import Agent
from Database.database_creator import DB, Twitter_DB
from utils.functions import find_hashtags
import sqlite3

import time
class Agent_Manager:
    def __init__(self) -> None:
        self.agents = []
        self.current_agent_index = 0
        self.paused = True

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

    def pause_unpause(self):
        if self.paused is True:
            self.paused = False
        else:
            self.paused = True
        
    def status(self)-> bool:
        return self.paused

    
    def add_agent(self, agent:Agent):
        self.agents.append(agent)
        

agent = Agent("agent1", "twitter.db", 100)

for i in range(1):
    feed = agent.recommend_feed()
    agent.view_feed(feed)
    