import openai
import os
from datetime import datetime
from pathlib import Path
import sys
import re
from typing import List,Tuple
import pathlib as pl
import faiss
import numpy as np
import time 

parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))
from Database.database_creator import DB, Twitter_DB
from utils.functions import list_to_string, create_embedding_bytes, create_embedding_nparray, convert_bytes_to_nparray
openai.api_key = os.getenv("OPENAI_API_KEY")

class Agent_memory(DB):
    '''the memory database for each agent'''
    def __init__(self, name, db_path):
        super().__init__(name, db_path)
        self.build_db()
        self.init_agent_memory()

    def init_agent_memory(self):
        '''initializes the agent memory database, should not be called by user'''
        if not self.table_exists("Memory_Tweet"):
            query1 = """
            CREATE TABLE Memory_Tweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                username TEXT,
                like_count INTEGER,
                retweet_count INTEGER,
                date TEXT
            );            
            """
            self.query(query1)
            
        if not self.table_exists("Memory_Subtweet"):
            query2 = """
            CREATE TABLE Memory_Subtweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                username TEXT,
                like_count INTEGER,
                retweet_count INTEGER,
                date TEXT
            );
            """
            self.query(query2)
             
        if not self.table_exists("Reflections"):
            
            query2 = """
            CREATE TABLE Reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Reflection TEXT,
                Keywords TEXT,
                Reflection_embedding BLOB
            );            
            """ # possibly both reflection and embedding
            self.query(query2)
        
    def insert_Reflection(self, tuple):
        '''inserts a reflection into the database'''
        query = """
        INSERT INTO Reflections (Reflection, Keywords, Reflection_embedding)
        VALUES (?, ?, ?);
        """
        self.query(query, tuple)
        
    def insert_tweet_memory(self, tuple):
        '''inserts a tweet into the database'''
        query = """
        INSERT INTO Memory_Tweet (content, username, like_count, retweet_count, date) 
        VALUES (?, ?, ?, ?, ?)
        """ # important changem content_embedding not in memory
        self.query(query, tuple)

        
    def insert_subtweet_memory(self, tuple):
        '''inserts a subtweet into the database'''
        query = """
        Insert INTO Memory_Subtweet (content, username, like_count, retweet_count, date)
        VALUES (?, ?, ?, ?, ?)
        """
        self.query(query, tuple)
    
    
    def dump_to_memory(self, feed: List[Tuple]) -> None:
        '''dumps the feed into the memory database'''
        for table_name, tuple in feed:
            if table_name == "Tweet":               
                self.insert_tweet_memory(tuple) #id is autoincremented
                print("inserted tweet successfully")
            elif table_name == "Subtweet":                
                self.insert_subtweet_memory(tuple) # id is autoincremented
                print("inserted subtweet successfully")
            elif table_name == "Reflection":
                print("inserting in reflection:", tuple)
                text, keywords = tuple
                embed = create_embedding_bytes([text+keywords])
                self.insert_Reflection((text, keywords, embed))
            else:
                raise Exception("Invalid table name")
         
                
    def get_memory(self) -> str:    
        '''returns the memory of the agent as a string everything except the embedding'''
        reflections = self.query("SELECT Reflection, Keywords FROM Reflections")
        subtweet = self.query("SELECT * FROM Memory_Subtweet") # every column in agent memory
        tweet = self.query("SELECT * FROM Memory_Tweet") # every column in agent memory
        
        text = list_to_string(self.merge_memory_stream(subtweet, tweet, reflections))
        return text

    
    def merge_memory_stream(self, oldest_tweets, oldest_subtweets, oldest_reflections) -> List:
        '''merges the oldest tweets, subtweets and reflections into a single list'''
        return [("Tweet_memory", tweet) for tweet in oldest_tweets] + [("Subtweet_memory", subtweet) for subtweet in oldest_subtweets] + [("Reflection", reflection) for reflection in oldest_reflections]
        
    
class Agent:
    '''the twitter agent'''
    def __init__(self, name, description, out_tokens, use_openai , temperature):        
        self._name = name
        self._description = description
        self._use_openai = use_openai
        self._out_tokens = out_tokens
        self._temperature = temperature
        self._db_path = self.create_agent_dir()       
        self._memory_db = Agent_memory(self._name, self._db_path) 
        self._twitter_db = Twitter_DB("Twitter_db")
        self._context_size = 4000 # gpt 3.5 turbo has a max context size of 4000 tokens 
        self._index = None # similarity index
        
        with open("src\Agents\instructions.txt", "r", encoding="utf-8", errors="ignore") as file:
            instruction = file.read() 
        self._prompt_template = f"""Agent: {self._name}\nDescription: {self._description} \n\n 
        Here are your instructions {instruction} \n\n"""
        
        self._instruction_size = (len(self._prompt_template) / 4) / self._context_size
        self._feed_size = (1-self._instruction_size) * 0.5 # 50% of whats left
        self._memory_size = 1-self._instruction_size-self._feed_size 
       
    def create_agent_dir(self):
        '''creates the directory for the agent if it does not exist'''
        # Check if the directory exists, if not, create it
        path = Path(__file__).parent.parent.resolve() / "Memory_bank" / self._name
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directory '{path}' created.")
        else:
            print(f"Directory '{path}' already exists.")
                            
        return os.path.join(path, f"{self._name}.sqlite")
            
    def prompt(self, text: str)->str:    
        '''prompts the agent with the text and returns the response'''
        # instructions are 1000 tokens long so 3000 tokens left for the prompt
        
        
        prompt = f"""{self._prompt_template} Now the task begins: {text}\n\n"""               
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
            print("agent :", text)
        else:
            print("not implemented yet")
            
        self.parser(text)
        return text      
        
    def parser(self, text):
        '''gets in an output of the language model and converts it into actions'''
        pattern1 = r'api_call\[Tweet\("([^"]*)"\)\]'
        pattern2 = r'Comment\("(.*?)",\s(\d+)\)'
        pattern3 = r"api_call\[Like\((\d+)\)\]"
        pattern4 = r"api_call\[Retweet\((\d+)\)\]"
        pattern5 = r'api_call\[Reflection\("(.+)", \[(.+)\]\)\]'
        pattern6 = r'api_call\[Follow\((.*?)\)\]'   
        
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
            tweet_id = match2.group(2)
            print(f"Comment match found: {text}, {tweet_id}")
            self._twitter_db.insert_subtweet((text, text_embedding, self._name, 0, 0, tweet_id, date))
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
            relfection_embedding = create_embedding_bytes(reflection)
            print(f"Reflection match found: {reflection}, {keywords}")
            self._memory_db.insert_Reflection((reflection, keywords, relfection_embedding))
        if match6:
            user = match6.group(1)
            print(f"Follow match found: {user}")
            self._twitter_db.insert_follow((user, self._name))    
        
        else:
            print("No match found")

    def reflect(self, memory: List):
        '''reflects on the memory and returns a reflection, this is a way to synthesize and compress the memory'''
        print("reflecting on memory\n\n")
        if len(memory) == 0:
            "nothing reflect on input is empty"
        else:
            memory = list_to_string(memory)
            
            text = f""""you have the following things in memory: {memory} \n\n now you need to reflect on what you have seen and experienced, what were the most interesting takeaways from the your memories, given your description?
            You can reflect on Tweet_memory, Subtweet_memory and Reflection. Remember you add a reflection to your memory like this: api_call[Reflection("text..”, [keywords, .,..])] \n\n"""
            if (1-self._instruction_size)*self._context_size  > len(text) / 4: # 1 token per prompt
                "agent reflecting"
                self.prompt(text)
                    
    def react(self, lst_feed: List[tuple]):
        '''reacts to the feed and returns a reaction, this is a way to synthesize and compress the feed'''
        # think about whether feed is correct or not. remember we want to add the entire feed to memory, so perhaps it should be a different format from list.
        # feed on form either tweet: ['id', 'content', 'username', 'like_count', 'retweet_count')]
        # or subtweet: ['id', 'content', 'username', 'like_count', 'retweet_count', 'tweet_id')]
        
        feed = list_to_string(lst_feed)
        
        if len(feed) / 4 > (1-self._instruction_size)*self._context_size :  # computing the number of tokens in the feed, if it is too long we return an error
            raise ValueError("Feed is too long, please shorten it")
        
        self.memory_manager()            
        memory = self._memory_db.get_memory()
        print("memory: ", memory)
        print("feed: ", feed)
                
        text = f"""here are short term memories of twitter interaction: {memory} \n\n now you view your feed and react to what you have seen and experienced. Feed: {feed}. \n\n""" 
        self.prompt(text)
        self._memory_db.dump_to_memory(lst_feed)        
        
    def memory_manager(self):
        '''manages the memory, if it is full it removes the oldest tweets, subtweets, and reflections to make room for new ones and maintains the memory size at some number of tokens'''        
        tweet_len = self._memory_db.query("SELECT COUNT(*) FROM Memory_Tweet")[0][0]
        subtweet_len = self._memory_db.query("SELECT COUNT(*) FROM Memory_Subtweet")[0][0]
        reflection_len = self._memory_db.query("SELECT COUNT(*) FROM Reflections")[0][0]
        total_len = tweet_len + subtweet_len + reflection_len
        memory_tokens = total_len * 80  # average tweet token length = 80               

        if memory_tokens > self._context_size * self._memory_size:
            print("Memory is full, removing oldest tweets, subtweets, and reflections to make room for new ones")
            # manually set share of the 2000 token memory budget
            tweet_proportion = 1 / 3
            subtweet_proportion = 1 / 3
            reflection_proportion = 1 / 3

            # Calculate the desired number of rows for each table based on the specified proportions
            total_desired_len = int(2000 / 80)
            desired_tweet_len = int(total_desired_len * tweet_proportion)
            desired_subtweet_len = int(total_desired_len * subtweet_proportion)
            desired_reflection_len = int(total_desired_len * reflection_proportion)

            # Determine how many rows to remove for each table, if any
            tweets_to_remove = max(0, tweet_len - desired_tweet_len)
            subtweets_to_remove = max(0, subtweet_len - desired_subtweet_len)
            reflections_to_remove = max(0, reflection_len - desired_reflection_len)

            # Take the oldest tweets, subtweets, and reflections to hit target size for each
            oldest_tweets = self._memory_db.query(f"SELECT content, username, like_count, retweet_count FROM Memory_Tweet ORDER BY id LIMIT {tweets_to_remove}")
            oldest_subtweets = self._memory_db.query(f"SELECT content, username, like_count, retweet_count, tweet_id  FROM Memory_Subtweet ORDER BY id LIMIT {subtweets_to_remove}")
            oldest_reflections = self._memory_db.query(f"SELECT Reflection, Keywords FROM Reflections ORDER BY id LIMIT {reflections_to_remove}")

            # Process the reflections
            lst = self._memory_db.merge_memory_stream(oldest_tweets, oldest_subtweets, oldest_reflections)
            
            tokens_bound = self._context_size * (1-self._instruction_size)
            
            while len(lst) * 80 > tokens_bound: # no feed so we can use the tokens left after instruction size
                target_len = int(2800 // 80)
                try:
                    self.reflect(lst[:target_len])
                except openai.InvalidRequestError: # too many tokens
                    self.reflect(lst[:target_len-10])               
                lst = lst[target_len:]
                
            self.reflect(lst) # reflecting on whats left
            
            # Remove the processed rows from the tables
            self._memory_db.query(f"DELETE FROM Memory_Tweet WHERE id IN (SELECT id FROM Memory_Tweet ORDER BY id LIMIT {tweets_to_remove})")
            self._memory_db.query(f"DELETE FROM Memory_Subtweet WHERE id IN (SELECT id FROM Memory_Subtweet ORDER BY id LIMIT {subtweets_to_remove})")
            self._memory_db.query(f"DELETE FROM Reflections WHERE id IN (SELECT id FROM Reflections ORDER BY id LIMIT {reflections_to_remove})")
            print(f"Memory manager finished removed {tweets_to_remove} tweets, {subtweets_to_remove} subtweets, {reflections_to_remove} reflections", memory_tokens)
    
    
    def inner_voice(self, inp:str):
        self.prompt(inp)
        
    
    def recommend_feed(self): # not finished
        '''creates customized feed for agent based on who they follow, similarity search, and time'''
        t0 = time.time()
        max_tokens = (self._feed_size * self._context_size) # number of recommended tweets        
        k = int(max_tokens // 80) # number of tweets to search for
        print(k)
        print(max_tokens)
        prev_actions = self._twitter_db.query(f"SELECT content FROM Tweet WHERE username = '{self._name}'")                  
        query_emb = create_embedding_nparray(self._description + "".join(prev_actions)) # might not be scalable
        xq = np.array(query_emb)
        
        
        tweets = self._twitter_db.query("SELECT id, content_embedding FROM Tweet")
        tweet_embeddings = [convert_bytes_to_nparray(embedding) for id, embedding in tweets]   
        tweet_ids = [id for id, _ in tweets]
        embeddings = np.array(tweet_embeddings)
        wb = np.stack(embeddings)
        
        
        d = 1024 # dimnesion of embeddings
        
        nlist = 128 # number of clusters
        
        #if self._index is None:     
        quantizer = faiss.IndexFlatIP(d)
        index = faiss.IndexIVFFlat(quantizer, d, nlist)
        index.train(wb)
        index.add(wb)
        
        index.nprobe = 4
        D, I = index.search(xq, k)
        
        
        recommended_tweet_ids = [tweet_ids[i] for i in I[0]]  # Assuming you are querying with only one vector
        recommended_tweets = self._twitter_db.query(f"SELECT content, username, like_count, retweet_count, date FROM Tweet WHERE id IN ({','.join(map(str, recommended_tweet_ids))})")
    
        print("time to recommend:" ,time.time() - t0)        
        return [("Tweet", tweet) for tweet in recommended_tweets]
        
        
    
        
