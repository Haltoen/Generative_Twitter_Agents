import openai
import os
from pathlib import Path
import sys
import re
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List,Tuple

parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))
from Database.database_creator import DB, Twitter_DB
from utils.functions import list_to_string
openai.api_key = os.getenv("OPENAI_API_KEY")

class Agent_memory(DB):
    def __init__(self, name, db_path):
        super().__init__(name, db_path)
        self.build_db()
        self.init_agent_memory()

    def init_agent_memory(self):
        if not self.table_exists("Memory_Tweet"):
            query1 = """
            CREATE TABLE Memory_Tweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                username TEXT,
                like_count INTEGER,
                retweet_count INTEGER
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
                tweet_id INTEGER,
                FOREIGN KEY (tweet_id) REFERENCES Tweet (id)
            );
            """
            self.query(query2)
            
            
        if not self.table_exists("Reflections"):
            
            query2 = """
            CREATE TABLE Reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Reflection TEXT,
                Keywords TEXT
            );            
            """
            self.query(query2)

    def insert_Reflection(self, tuple):
        query = """
        INSERT INTO Reflections (Reflection, Keywords)
        VALUES (?, ?);
        """
        self.query(query, tuple)
        
    def insert_tweet_memory(self, tuple):
        query = """
        INSERT INTO Memory_Tweet (content, username, like_count, retweet_count)
        VALUES (?, ?, ?, ?)
        """
        self.query(query, tuple)

        
    def insert_subtweet_memory(self, tuple):
        query = """
        Insert INTO Memory_Subtweet (content, username, like_count, retweet_count, tweet_id)
        VALUES (?, ?, ?, ?, ?)
        """
        self.query(query, tuple)
        
    def dump_to_memory(self, feed: List[Tuple]) -> None:
        for table_name, tuple in feed:
            if table_name == "Tweet":
                self.insert_tweet_memory(tuple[1:]) #id is autoincremented
                print("inserted tweet successfully")
            elif table_name == "Subtweet":
                self.insert_subtweet_memory(tuple[1:]) # id is autoincremented
                print("inserted subtweet successfully")
            elif table_name == "Reflection":
                print("inserting in reflection:", tuple)
                self.insert_Reflection(tuple)
            else:
                raise Exception("Invalid table name")
         
                
    def get_memory(self) -> str:    
        reflections = self.query("SELECT * FROM Reflections")
        subtweet = self.query("SELECT * FROM Memory_Subtweet")
        tweet = self.query("SELECT * FROM Memory_Tweet")
        text =  list_to_string(self.merge_memory_stream(subtweet,tweet, reflections))
        return text
    
    def merge_memory_stream(self, oldest_tweets, oldest_subtweets, oldest_reflections) -> List:
        return [("Tweet_memory", tweet) for tweet in oldest_tweets] + [("Subtweet_memory", subtweet) for subtweet in oldest_subtweets] + [("Reflection", reflection) for reflection in oldest_reflections]
        
    
class Agent:
    def __init__(self, name, description, out_tokens, use_openai, temperature = 100):        
        self._name = name
        self._description = description
        self._use_openai = use_openai
        self._out_tokens = out_tokens
        self._temperature = temperature
        self._db_path = self.create_agent_dir()       
        self._memory_db = Agent_memory(self._name, self._db_path) 
        self._twitter_db = Twitter_DB("Twitter_db")
        
    def create_agent_dir(self):
        # Check if the directory exists, if not, create it
        path = Path(__file__).parent.parent.resolve() / "Agent" / self._name
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directory '{path}' created.")
        else:
            print(f"Directory '{path}' already exists.")
                            
        return os.path.join(path, f"{self._name}.sqlite")
            
    def prompt(self, text: str)->str:    
        # instructions are 1000 tokens long so 3000 tokens left for the prompt
        with open("src\Agent\instructions.txt", "r", encoding="utf-8", errors="ignore") as file:
            instruction = file.read() 
        prompt_template = f"""Agent: {self._name}\nDescription: {self._description} \n\n 
        Here are your instructions {instruction} \n\n"""
        
        prompt = f"""{prompt_template} Now the task begins: {text}\n\n"""               
        if self._use_openai is True:
            print("using openai")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "assistant", "content": prompt},
                    #{"role": "assistant", "content": text},
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
            print("using local model")
            tokenizer = AutoTokenizer.from_pretrained("OpenAssistant/stablelm-7b-sft-v7-epoch-3")
            model = AutoModelForCausalLM.from_pretrained("OpenAssistant/stablelm-7b-sft-v7-epoch-3")
            prompt = f"<|prompter|>{prompt}<|endoftext|><|assistant|>"
            input_tokens = tokenizer.encode(prompt, return_tensors="pt")

            output_tokens = model.generate(input_tokens)
            text = tokenizer.decode(output_tokens[0]) # Decode the output tokens to text
            print("local model Bitch!!!!" , text)
            
            
            # models we could use, Vicuna 13b, allpaca 13b, openassistant 13b, all on huggingface
        self.parser(text)
        return text      
        
    def parser(self, text):
        pattern1 = r'api_call\[Tweet\("([^"]*)"\)\]'
        pattern2 = r'Comment\("(.*?)",\s(\d+)\)'
        pattern3 = r"api_call\[Like\((\d+)\)\]"
        pattern4 = r"api_call\[Retweet\((\d+)\)\]"
        pattern5 = r'api_call\[Reflection\("(.+)", \[(.+)\]\)\]'

        match1 = re.search(pattern1, text)
        match2 = re.search(pattern2, text)
        match3 = re.search(pattern3, text)
        match4 = re.search(pattern4, text)
        match5 = re.search(pattern5, text)

        if match1:
            text = match1.group(1)
            tuple = (text, self._name, 0, 0)
            self._twitter_db.insert_tweet(tuple)
            print(f"Tweet match found and succesfully inserted, {tuple} ")
        elif match2:
            text = match2.group(1)
            tweet_id = match2.group(2)
            print(f"Comment match found: {text}, {tweet_id}")
            self._twitter_db.insert_subtweet((text, self._name, 0, 0, tweet_id))
        elif match3:
            tweet_id = match3.group(1)
            print(f"Like match found: {tweet_id}")
            self._twitter_db.increment_like_count(tweet_id)
        elif match4:
            tweet_id = match4.group(1)
            print(f"Retweet match found: {tweet_id}")
            self._twitter_db.increment_retweet_count(tweet_id)
        elif match5:
            reflection_text = match5.group(1)
            keywords = match5.group(2)
            print(f"Reflection match found: {reflection_text}, {keywords}")
            self._memory_db.insert_Reflection((reflection_text, keywords))
        else:
            print("No match found")

    def retriever(inp) -> str: # possibly not needed
        pass
    
    def reflect(self, memory: List):
        print("reflecting on memory\n\n")
        if len(memory) == 0:
            "nothing reflect on input is empty"
        else:
            memory = list_to_string(memory)
            text = f""""you have the following things in memory: {memory} \n\n now you need to reflect on what you have seen and experienced, what were the most interesting takeaways from the your memories, given your description?
            You can reflect on Tweet_memory, Subtweet_memory and Reflection. Remember you add a reflection to your memory like this: api_call[Reflection("text..”, [keywords, .,..])] \n\n"""
            self.prompt(text)
                    
    def react(self, feed: List[Tuple]):
        # think about whether feed is correct or not. remember we want to add the entire feed to memory, so perhaps it should be a different format from list.
        # feed on form either tweet: ['id', 'content', 'username', 'like_count', 'retweet_count')]
        # or subtweet: ['id', 'content', 'username', 'like_count', 'retweet_count', 'tweet_id')]
        if len(feed) *45 > 1000:
            return print("the feed is too long, please shorten it")
        
        self.memory_manager()            
        memory = self._memory_db.get_memory()
                
        text = f"""here are short term memories of twitter interaction: {memory} \n\n now you view your feed and react to what you have seen and experienced. Feed: {list_to_string(feed)}. \n\n"""
        print(text)      
        self.prompt(text)
        self._memory_db.dump_to_memory(feed)
        #save to memory
        
        
    def memory_manager(self):
        tweet_len = self._memory_db.query("SELECT COUNT(*) FROM Memory_Tweet")[0][0]
        subtweet_len = self._memory_db.query("SELECT COUNT(*) FROM Memory_Subtweet")[0][0]
        reflection_len = self._memory_db.query("SELECT COUNT(*) FROM Reflections")[0][0]
        total_len = tweet_len + subtweet_len + reflection_len
        memory_tokens = total_len * 45  # average tweet token length = 45
        print(memory_tokens)

        if memory_tokens > 1500:
            print("Memory is full, removing oldest tweets, subtweets, and reflections to make room for new ones")
            # manually set share of the 2000 token memory budget
            tweet_proportion = 1 / 3
            subtweet_proportion = 1 / 3
            reflection_proportion = 1 / 3

            # Calculate the desired number of rows for each table based on the specified proportions
            total_desired_len = int(2000 / 45)
            desired_tweet_len = int(total_desired_len * tweet_proportion)
            desired_subtweet_len = int(total_desired_len * subtweet_proportion)
            desired_reflection_len = int(total_desired_len * reflection_proportion)

            # Determine how many rows to remove for each table, if any
            tweets_to_remove = max(0, tweet_len - desired_tweet_len)
            subtweets_to_remove = max(0, subtweet_len - desired_subtweet_len)
            reflections_to_remove = max(0, reflection_len - desired_reflection_len)

            # Take the oldest tweets, subtweets, and reflections to hit target size for each
            oldest_tweets = self._memory_db.query(f"SELECT * FROM Memory_Tweet ORDER BY id LIMIT {tweets_to_remove}")
            oldest_subtweets = self._memory_db.query(f"SELECT * FROM Memory_Subtweet ORDER BY id LIMIT {subtweets_to_remove}")
            oldest_reflections = self._memory_db.query(f"SELECT * FROM Reflections ORDER BY id LIMIT {reflections_to_remove}")

            # Process the reflections
            lst = self._memory_db.merge_memory_stream(oldest_tweets, oldest_subtweets, oldest_reflections)
            
            while len(lst) * 45 > 2800: # 2800 tokens left to prompt the model
                target_len = int(2800 // 45)
                self.reflect(lst[:target_len])
                lst = lst[target_len:]
                
            self.reflect(lst) # reflecting on whats left
            
            # Remove the processed rows from the tables
            self._memory_db.query(f"DELETE FROM Memory_Tweet WHERE id IN (SELECT id FROM Memory_Tweet ORDER BY id LIMIT {tweets_to_remove})")
            self._memory_db.query(f"DELETE FROM Memory_Subtweet WHERE id IN (SELECT id FROM Memory_Subtweet ORDER BY id LIMIT {subtweets_to_remove})")
            self._memory_db.query(f"DELETE FROM Reflections WHERE id IN (SELECT id FROM Reflections ORDER BY id LIMIT {reflections_to_remove})")
            print(f"Memory manager finished removed {tweets_to_remove} tweets, {subtweets_to_remove} subtweets, {reflections_to_remove} reflections", memory_tokens)
        
    
    def inner_voice(self):
        pass

class Game:
    def __init__(self, agents: List[Tuple[str,str, bool]]) -> None:
        self.agents = [Agent(name, description, 150, use_openai) for name, description, use_openai in agents]
        print(agents)
        
    def run(self):
        for i in range(10):
            for agent in self.agents:
                feed = agent._twitter_db.get_feed()
                agent.react(feed)

 
agent = Agent("crypto_sceptic_69", "Loves to hate on crypto, loves ai and machine learning", False, 50)
agent.memory_manager()
agent.prompt("hello")
#game = Game([("crypto_sceptic_69", "Loves to hate on crypto, loves ai and machine learning", False)])

#game.run()