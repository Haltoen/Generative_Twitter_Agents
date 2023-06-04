import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))
print("path", str(parent_dir))


import shutil
import sqlite3 
import pandas as pd
import os
from typing import List, Tuple
from utils.functions import  profile, convert_bytes_to_nparray, embed, process_dataframe, parallelize_dataframe
import faiss
import numpy as np
import random 
class DB:
    def __init__(self, name, db_path):
        self._name = name
        self._db_path = db_path
    
    @profile        
    def build_db(self)-> bool:
        if os.path.exists(self._db_path):
            print(f"Database '{self._name}' already exists.")
        else:
            conn = sqlite3.connect(self._db_path)
            conn.close()

    
    @profile
    def view_columns(self, table_name):
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
    
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        conn.close()

        column_names = [column[1] for column in columns]
        column_count = len(column_names)

        return column_names, column_count
 
    def query(self, query, params=None):
        '''Used for general queries'''
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        conn.commit()
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    @profile
    def table_exists(self, table_name):
        result = self.query(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        return len(result) > 0 
    
    @profile
    def drop_row(self, table_name, row_id):
        query = f"""
        DELETE FROM {table_name}
        WHERE id = {row_id};
        """
        self.query(query)
        
class Twitter_DB(DB):
    def __init__(self, name, from_scratch):
        self._db_path = f"src\Database\{name}.sqlite"
        self._base_path = 'src\Database\Base_Twitter_db.sqlite'
        self._from_scratch = from_scratch
        self._index = None
        super().__init__(name, self._db_path)
       
        if not os.path.exists(self._base_path):
            "building base twitter db"
            self._csv_path = 'src\Database\large_embedded_dataset.csv'
            self.twitter_csv_to_db(self._csv_path) # possibly not good, bc if an erroneous db is created we wont know
        
        if not self._from_scratch:
            if not os.path.exists(self._db_path):
                print("copying base db")
                shutil.copy2(self._base_path, self._db_path)
        else: 
            print("building db from scratch")
            self._csv_path = 'src\Database\empty.csv'
            self.build_db() # db has to be deleted if path already exists
            self.build_tables()        
        
    @profile
    def twitter_csv_to_db(self, csv_path):
        
        if os.path.exists(self._base_path):
            print(f"Database '{self._name}' already exists.")
        else:
            print(f"Building Database from csv")
            df = pd.read_csv(csv_path)          
            df = process_dataframe(df)

            #print("type df fromk csv after intervention", type(df["content_embedding"][0]))  
            conn = sqlite3.connect(self._base_path)
            df.to_sql('initial_data', conn, if_exists='replace', index=False)
            self.build_tables()
            conn.close()
            
            print(f"CSV data has been imported into in to '{self._db_path}'.")      

                    
    @profile#should not be called by user
    def build_tables(self):
        '''building tables from twitter db'''
        # modifying the csv file data and making id self incrementing        
        if not self.table_exists("Tweet"):
                
            query = """
            CREATE TABLE Tweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                content_embedding BLOB,
                username TEXT,
                hashtags TEXT,
                like_count INTEGER,
                retweet_count INTEGER,
                date TEXT
            );
            """
            self.query(query)
            
            if not self._from_scratch: 
                query1 = """
                INSERT INTO Tweet (content, content_embedding, username, hashtags, like_count, retweet_count, date)
                SELECT content, content_embedding, username, hashtags, like_count, retweet_count, date
                FROM initial_data;
                """
                self.query(query1)

        if not self.table_exists("Subtweet"):
            query2 = """
            CREATE TABLE Subtweet (
                id_child INTEGER PRIMARY KEY,
                id_parent INTEGER,
                FOREIGN KEY (id_parent) REFERENCES Tweet(tweet_id),
                FOREIGN KEY (id_child) REFERENCES Tweet(tweet_id)
            );
            """
            self.query(query2)
            
        if not self._from_scratch:
            self.query("DROP TABLE initial_data")
        
        if not self.table_exists("Follow"):
            query3 = """
            CREATE TABLE Follow (
                follower INTEGER,
                followee INTEGER,
                PRIMARY KEY (follower, followee)
                FOREIGN KEY (follower) REFERENCES Tweet (username),
                FOREIGN KEY (followee) REFERENCES Tweet (username)
            );
            """
            self.query(query3) 

        if not self.table_exists("Users"): # Users = username
            query3 = """
            CREATE TABLE Users (
                user_id TEXT PRIMARY KEY
            );
            """
            self.query(query3)
            
            query4 = """
            INSERT INTO Users (user_id)
            SELECT DISTINCT username
            FROM Tweet;
            """
            self.query(query4)


    @profile        
    def insert_subtweet(self, tuple, parent_id):
        self.insert_tweet(tuple)
        
        query1 = """
        SELECT MAX(id) AS max_id
        FROM Tweet
        """
        
        out = self.query(query1)
        child_id = out[0][0]  # retunrs a list of tuples, we want the first element of the first tuple
        
        query2 = """
        INSERT INTO Subtweet (id_child, id_parent)
        VALUES (?, ?);
        """
        tuple_subtweet = (child_id ,parent_id)
        
        self.query(query2, tuple_subtweet)
        print('subtweet inserted')
    
    @profile    
    def insert_tweet(self, tuple):
        query1 = """
        INSERT INTO Tweet (content,content_embedding, username, hashtags, like_count, retweet_count, date)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        self.query(query1, tuple)        
    
    @profile    
    def increment_like_count(self, id):
        query = f"""
        UPDATE 'Tweet'
        SET like_count = like_count + 1
        WHERE id = {id};
        """
        self.query(query)
    
    @profile
    def increment_retweet_count(self, id):
        query = f"""
        UPDATE 'Tweet'
        SET retweet_count = retweet_count + 1
        WHERE id = {id};
        """
        self.query(query)
    
    @profile
    def insert_follow(self, tuple): # how do you select for some users having the same username?
        query = """
        INSERT INTO Follow (follower, followee)
        VALUES (?, ?);
        """
        if tuple[0] == tuple[1]:
            raise ValueError("cannot follow yourself, the tuples ellements must be different")
        self.query(query, tuple)   
    
    @profile    
    def get_feed(self, n_samples)-> List[Tuple] : # returns a list of tuples, used by frontend
        tweet_query = f"""
        SELECT content, username, hashtags, like_count, retweet_count, date FROM Tweet
        ORDER BY id DESC
        LIMIT {n_samples};        
        """
        lst = [("Tweet", tweet) for tweet in self.query(tweet_query)]
        return lst
    
    @profile
    def similarity_search(self, xq, n_samples, retrain = False):        
        k = n_samples # number of tweets to search through
        d = 1024 # dimnesion of embeddings
        nlist = 128 # number of clusters

        
        tweets = self.query("SELECT id, content_embedding FROM Tweet")
        tweet_embeddings = [convert_bytes_to_nparray(embedding) for _ , embedding in tweets]   
        tweet_ids = [id for id, _ in tweets]
        embeddings = np.array(tweet_embeddings)
        wb = np.stack(embeddings)
        
        d = 1024 # dimnesion of embeddings
        nlist = 128 # number of clusters
        
       
        if retrain or not os.path.exists('src\Database\Trained.index'): # if model already trained
            print("training indexer")
            quantizer = faiss.IndexFlatIP(d)
            self._index = faiss.IndexIVFFlat(quantizer, d, nlist)
            self._index.train(wb)         
            faiss.write_index(self._index, 'src\Database\Trained.index')
        else:
            print("loading indexer")
            self._index = faiss.read_index('src\Database\Trained.index')  

        self._index.add(wb)
        self._index.nprobe = 4
        D, I = self._index.search(xq, k)
        
        recommended_tweet_ids = [tweet_ids[i] for i in I[0]] 
        tweets = self.query(f"SELECT content, username, like_count, retweet_count, date FROM Tweet WHERE id IN ({','.join(map(str, recommended_tweet_ids))})")
        return tweets
        
    
    @profile 
    def search_db(self, search: str, n_samples: int) -> List[Tuple]:
        '''searches the database for tweets, returns a list of tuples of format (content, username, like_count, retweet_count, date)'''
        if search.startswith("#"):
            print(search)
        
            query = f"""
            SELECT content, username, like_count, retweet_count, date FROM Tweet 
            WHERE (hashtags LIKE '% {search} %' OR hashtags LIKE '{search} %' OR hashtags LIKE '% {search}')
            LIMIT {n_samples}
            """

            out = self.query(query)
            return [('Tweet', tweet) for tweet in out]
        
        if search.startswith("@"):
            username_to_search = search.lstrip('@')
            query = f"""
            SELECT content, username, like_count, retweet_count, date FROM Tweet 
            WHERE username LIKE '{username_to_search}%'
            LIMIT {n_samples}
            """
            out = self.query(query)
            return [('Tweet', tweet) for tweet in out]
                    
        if search.startswith("similar_to:"): # 
            search = search.lstrip("similar_to:")
            xq = embed([search])
            xq = np.array([xq.embeddings[0]])  # this is the latency bottleneck
            out = self.similarity_search(xq, n_samples)
            return [('Tweet', tweet) for tweet in out]
            
            

        
