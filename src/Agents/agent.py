import openai
import os
from datetime import datetime
from pathlib import Path
import sys
import re
from typing import List
import numpy as np
import time 
import random
import sqlite3


parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))
from Agents.Agent_memory import Memory
from Database.database_creator import Twitter_DB
from utils.functions import list_to_string, create_embedding_bytes, create_embedding_nparray, convert_bytes_to_nparray, profile, token_count, find_hashtags

class Agent:
    '''the twitter agent'''
    @profile
    def __init__(self, name, description, out_tokens, from_scratch= False):        
        self._name = name
        self._description = description
        self._use_openai = True # we use openai for now
        self._out_tokens = out_tokens
        self._temperature = 0.5
        self._db_path = self.create_agent_dir()       
        self._memory_db = Memory(self._name, self._db_path) 
        self._twitter_db = Twitter_DB(from_scratch)  #reset varaible also
        self._index = None # similarity index
        
        with open("src\Agents\instructions.txt", "r", encoding="utf-8", errors="ignore") as file:
            instruction = file.read() 
        self._prompt_template = f"""Agent: {self._name}\nDescription: {self._description} \n\n 
        Here are your instructions {instruction} \n\n"""
        
        self._context_size = 4000 # gpt 3.5 turbo has a max context size of 4000 tokens 
        instruction_tokens = token_count(self._prompt_template)
        print("tokens used for instructions", instruction_tokens)
        self._instruction_share = instruction_tokens / self._context_size  
        self._feed_share = (1-self._instruction_share) * 0.5 # 50% of whats left
        self._memory_share = 1-self._instruction_share-self._feed_share 
        
        print("instruction size", self._instruction_share, "feed size", self._feed_share, "memory size", self._memory_share)
        
        self.add_user_to_db()
    
    @profile
    def add_user_to_db(self):
        try:
            query = f"INSERT INTO Users (user_id) VALUES ('{self._name}')"
            self._twitter_db.query(query)
        except sqlite3.IntegrityError:
            print("user already exists")

    @profile
    def create_agent_dir(self):
        '''creates the directory for the agent if it does not exist'''
        # Check if the directory exists, if not, create it
        path = Path(__file__).parent.parent.resolve() / "Memory_bank" / self._name
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directory '{path}' created.")
                            
        return os.path.join(path, f"{self._name}.sqlite")
            
    @profile
    def prompt(self, text: str)->str:    
        '''prompts the agent with the text and returns the response'''        
        
        prompt = f"""{self._prompt_template} Now the task begins: {text}\n\n"""  
        #print("template size", token_count(self._prompt_template))
        #print("prompt size", token_count(prompt))
        print("HERE IS THE PROMPT: ", prompt, "\n\n")
        
        if self._use_openai is True:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "assistant", "content": prompt}
                ],
                temperature=0,
                max_tokens=self._out_tokens,
                top_p=1,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=["\n"],
            )
            text = response['choices'][0]['message']['content']
        else:
            print("not implemented yet")
            
        self.parser(text)
        return text      
        
    @profile
    def parser(self, text):
        '''gets in an output of the language model and converts it into actions'''
        pattern1 = r'api_call\[Tweet\("([^"]*)"\)\]'
        pattern2 = r"api_call\[Comment\('([^']*)',\s(\d+)\)]"
        pattern3 = r"api_call\[Like\((\d+)\)\]"
        pattern4 = r"api_call\[Retweet\((\d+)\)\]"
        pattern5 = r'api_call\[Reflection\("(.+)", \[(.+)\]\)\]'
        pattern6 = r'api_call\[Follow\((.*?)\)\]'      
        
        print("INPUT TEXT:",  self._name  , text , "\n\n")
        
        match1 = re.search(pattern1, text)
        match2 = re.search(pattern2, text)  
        match3 = re.search(pattern3, text)
        match4 = re.search(pattern4, text)
        match5 = re.search(pattern5, text)
        match6 = re.search(pattern6, text)

        # Get the current date and time
        now = datetime.now()

        # Format the date to YYYY-MM-DD
        date = now.strftime("%Y-%m-%d")

        if match1:      
            text = match1.group(1)
            text_embedding = create_embedding_bytes(text) 
            tuple = (text, text_embedding, self._name, 0, 0, date)
            self._twitter_db.insert_tweet(tuple)
            print(f"Tweet match found and succesfully inserted, {tuple} ")
        if match2:
            text = match2.group(1)
            text_embedding = create_embedding_bytes(text) 
            parent_tweet_id = match2.group(2)
            print(f"Comment match found: {text}, {parent_tweet_id}")
            self._twitter_db.insert_subtweet((text, text_embedding, self._name, 0, 0, date) , parent_tweet_id)
        if match3:
            tweet_id = match3.group(1)
            print(f"Like match found: {tweet_id}")
            self._twitter_db.increment_like_count(tweet_id)
        if match4:
            tweet_id = match4.group(1)
            print(f"Retweet match found: {tweet_id}")
            self._twitter_db.increment_retweet_count(tweet_id)
        if match5:
            reflection = match5.group(1)
            keywords = match5.group(2)
            reflection_embedding = create_embedding_bytes(reflection)
            print(f"Reflection match found: {reflection}, {keywords}")
            self._memory_db.insert_Reflection((reflection, keywords, reflection_embedding, token_count(reflection)))
        if match6:
            user = match6.group(1)
            print(f"Follow match found: {user}")
            self._twitter_db.insert_follow((user, self._name))    

    @profile
    def reflect(self, memory: List):
        '''reflects on the memory and returns a reflection, this is a way to synthesize and compress the memory'''
        print("reflecting on memory\n\n")
        if len(memory) == 0:
            "nothing reflect on input is empty"
        else:
            memory = list_to_string(memory)
            reflections = list_to_string(self._memory_db.get_reflections(10))
            
            text = f""""here are your 10 latest memories and reflections: {reflections} you have just viewed the following things on twitter: {memory} \n\n now you will reflect on what you have seen and experienced
            and make reflections in accordance with your description. You add a reflection to your memory like this: api_call[Reflection("text..”, [keywords, .,..])] \n\n"""
            if (1-self._instruction_share)*self._context_size  > token_count(text) : 
                self.prompt(text)
                    
    @profile
    def view_feed(self, lst_feed: List[tuple]):
        '''reacts to the feed and returns a reaction, this is a way to synthesize and compress the feed'''        
        feed = list_to_string(lst_feed)
        
        if token_count(feed)  > (1-self._instruction_share)*self._context_size :  # computing the number of tokens in the feed, if it is too long we return an error
            raise ValueError("Feed is too long, please shorten it")
        
        self.memory_manager()            
        memory_reflections = list_to_string(self._memory_db.get_memory_reflections_tweets())
        
        query = f"SELECT content FROM Tweet WHERE username = '{self._name}' ORDER BY id DESC LIMIT 5"        
        latest_tweets = self._twitter_db.query(query)
        latest_tweets = list_to_string([("Tweet", tweet) for tweet in latest_tweets])
        
        text = f"""here are short term memories and reflections: {memory_reflections} \n here are your previous tweets: {latest_tweets} \\
        now you view your feed and react to what you have seen and experienced based on a combination of previous memories, reflections in accordance with our description. Feed: {feed}. \n\n""" 
        
        # remove when safe
        #print("length of feed: ", token_count(feed))
        #print("length of memory: ", token_count(memory)) 
        #print(" length of prompt: ", token_count(text))
        
        out = [(label, (*tuple, token_count(tuple[0]))) for label, tuple in lst_feed]
        
        self.prompt(text)
           
        self._memory_db.dump_to_memory(out)        
        
    @profile
    def memory_manager(self):
        '''manages the memory, if it is full it removes the oldest tweets, subtweets, and reflections to make room for new ones and maintains the memory size at some number of tokens'''        
        
        print("managing memory\n\n")
        
        tweet_lengths = self._memory_db.query("SELECT length FROM Memory_Tweet ORDER BY id DESC")
        subtweet_lengths = self._memory_db.query("SELECT length FROM Memory_Subtweet ORDER BY id DESC")
        reflection_lengths = self._memory_db.query("SELECT length FROM Reflections ORDER BY id DESC")

        tweet_len = sum([length[0] for length in tweet_lengths])
        subtweet_len = sum([length[0] for length in subtweet_lengths])
        reflection_len = sum([length[0] for length in reflection_lengths])
        
        memory_tokens = tweet_len + subtweet_len + reflection_len + 150 # 500 buffere

        upper_bound = self._context_size * self._memory_share 

        print("tokens in memory", memory_tokens)
        print("upper bound", upper_bound)

        if memory_tokens > upper_bound:
            print("Memory is full, removing oldest tweets, subtweets, and reflections to make room for new ones")
            # manually set share of the 2000 token memory budget
            tweet_proportion = subtweet_proportion = reflection_proportion = 1 / 3

            # Calculate the desired number of rows for each table based on the specified proportions
            desired_tweet_len = int(upper_bound * tweet_proportion)
            desired_subtweet_len = int(upper_bound * subtweet_proportion)
            desired_reflection_len = int(upper_bound * reflection_proportion)

            # Determine how many rows to remove for each table, if any
            tweets_to_remove = int(max(0, tweet_len - desired_tweet_len))
            subtweets_to_remove = int(max(0, subtweet_len - desired_subtweet_len))
            reflections_to_remove = int(max(0, reflection_len - desired_reflection_len))

            # Take the oldest tweets, subtweets, and reflections to hit target size for each
            oldest_tweets = self._memory_db.calculate_rows_to_remove("Memory_Tweet", tweets_to_remove)
            oldest_subtweets = self._memory_db.calculate_rows_to_remove("Memory_Subtweet", subtweets_to_remove)
            oldest_reflections = self._memory_db.calculate_rows_to_remove("Reflections", reflections_to_remove)        

            # Process the reflections
            lst = self._memory_db.merge_memory_stream(oldest_tweets, oldest_subtweets, oldest_reflections)
                  
            bound = self._context_size * self._memory_share
            # reflecting on whats left     
            total_sum = 0
            for i in range(len(lst)):
                _ , _tuple = lst[i]
                total_sum += _tuple[-1]
                if total_sum > bound:            
                    self.reflect(lst[:i])   
                    lst = lst[i:]  
                    total_sum = 0
            
            # Remove the processed rows from the tables
            self._memory_db.remove_rows('Memory_Tweet', tweets_to_remove)
            self._memory_db.remove_rows('Memory_Subtweet', subtweets_to_remove)
            self._memory_db.remove_rows('Reflections', reflections_to_remove)
            
            print(f"Memory manager finished removed {tweets_to_remove} tweets, {subtweets_to_remove} subtweets, {reflections_to_remove} reflections, totaling {memory_tokens-upper_bound} tokens, should be below upper bound {upper_bound} ")
    
    
    @profile
    def inner_voice(self, inp:str):
        self.prompt(inp)
        
    
    @profile
    def recommend_feed(self): 
        '''creates customized feed for agent based on who they follow, similarity search, and time'''
        t0 = time.time()   
        k = 50 # number of tweets to search through
        prev_actions = self._twitter_db.query(f"SELECT content FROM Tweet WHERE username = '{self._name}'") 
        prev_reflections = list_to_string(self._memory_db.get_reflections(10))
        
        prompt = self._description + "".join(prev_actions) + prev_reflections
        
        #stupid check
        prompt_len = token_count(prompt)
        if prompt_len > 4000:
            prompt = " ".join(prompt.split()[:4000/2]) # 2 tokens per word
                
        query_emb = create_embedding_nparray(self._description + "".join(prev_actions) + prev_reflections) # might not be scalable
        xq = np.array(query_emb)
                
        tweets = self._twitter_db.similarity_search(xq, 30, False)
        upper = 100 #self._feed_share * self._context_size + 100 # 100 buffer
        total = 0     
        
        feed = self._twitter_db.get_feed(15)
        random.shuffle(feed)
        
        recommended_tweets = []      
        for x, y in zip(feed, tweets):
            if total >= upper:
                break
            total += token_count(x[1][0]) # tweet[0][0] is the content of the tweet
            total += token_count(y[0]) # tweet[0] is the content of the tweet
            recommended_tweets.append(x)
            recommended_tweets.append(("Tweet", (y)))
                    
        print("time to recommend:" ,time.time() - t0)   
        print("len of recommended tweets", len(recommended_tweets))
        print("total tokens in recommended tweets", sum([token_count(tweet[1][0]) for tweet in recommended_tweets]))
             
        return recommended_tweets
        
        
    
        
