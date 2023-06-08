
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.resolve() # src\Agent
sys.path.append(str(parent_dir))

import shutil
import sqlite3 
import pandas as pd
import os
from typing import List, Tuple
from utils.functions import  profile, convert_bytes_to_nparray, embed, process_dataframe, find_hashtags
import faiss
import numpy as np

class DB:
    def __init__(self, name, db_path):
        self._name = name
        self._db_path = db_path
    
    @profile        
    def build_db(self):
        if not os.path.exists(self._db_path):
            conn = sqlite3.connect(self._db_path)
            conn.close()
    
    @profile
    def build_from_csv(self, csv_path):
        if not os.path.exists(self._db_path):
            df = pd.read_csv(csv_path)          
            df = process_dataframe(df)
            conn = sqlite3.connect(self._db_path)
            df.to_sql('initial_data', conn, if_exists='replace', index=False)
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
    
    def executemany(self, query, params_list):
        '''Used for executing many queries at once'''
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.executemany(query, params_list)

        conn.commit()
        conn.close()
    
    @profile
    def table_exists(self, table_name) -> bool:
        result = self.query(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        return len(result) > 0 
    
        
class Twitter_DB(DB):
    def __init__(self, from_scratch: bool, reset: bool = False): # default is to not to reset the db        
        if from_scratch is True:
            name = "empty_twitter_db"
        else:
            name = "twitter_db"
        self._db_path = f"src\Database\{name}.sqlite"
        self._base_path = 'src\Database\Base_Twitter_db.sqlite'
        self._from_scratch = from_scratch
        self._reset = reset
        self._index = None
        super().__init__(name, self._db_path) 

        if self._reset is True:
            try:
                os.remove(self._db_path)
                print("Old database deleted successfully.")
            except FileNotFoundError:
                print("File not found. Unable to delete.")
            except OSError as e:
                print(f"Error deleting the file: {e}")

        if not os.path.exists(self._base_path):
            print("building base twitter db")
            self._csv_path = 'src\Database\mini_embedded_dataset.csv'
            self.twitter_csv_to_db() 
        
        if self._from_scratch is False:
            if not os.path.exists(self._db_path):
                print("copying base db")
                self.build_db()
                shutil.copy2(self._base_path, self._db_path) 
        else: 
            print("building empty db from scratch")
            self._csv_path = 'src\Database\empty.csv'
            self.build_db()
            db = DB("empty_twitter_db", self._db_path)
            db.build_from_csv(self._csv_path)
            self.build_tables(db)   
        
    @profile
    def twitter_csv_to_db(self):        
        print(f"Building Database from {self._csv_path}")
        db = DB("base_twitter_db", self._base_path)
        db.build_from_csv(self._csv_path)        
        self.build_tables(db)
        print(f"CSV data has been imported into in to '{self._db_path}'.")      

                    
    @profile #should not be called by user
    def build_tables(self, db: DB):
        '''building tables for twitter db'''
        if not db.table_exists("Tweet"):     
            query = """
            CREATE TABLE Tweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                content_embedding BLOB,
                username TEXT,
                like_count INTEGER,
                retweet_count INTEGER,
                date TEXT
            );
            """
            db.query(query)
            
            if not self._from_scratch: 
                query = """
                INSERT INTO Tweet (content, content_embedding, username, like_count, retweet_count, date)
                SELECT content, content_embedding, username, like_count, retweet_count, date
                FROM initial_data;
                """
                db.query(query)

        if not db.table_exists("Subtweet"):
            query = """
            CREATE TABLE Subtweet (
                id_child INTEGER PRIMARY KEY,
                id_parent INTEGER,
                FOREIGN KEY (id_parent) REFERENCES Tweet(tweet_id),
                FOREIGN KEY (id_child) REFERENCES Tweet(tweet_id)
            );
            """
            db.query(query)
        
        if not db.table_exists("Hashtag"):
            
            query = """
            CREATE TABLE Hashtag (
                tweet_id INTEGER,
                hashtag TEXT,
                PRIMARY KEY (tweet_id, hashtag),
                FOREIGN KEY (tweet_id) REFERENCES Tweet(id)
            );"""    
            db.query(query)
                        
            query = """
            SELECT id, content FROM Tweet;
            """
            
            out = db.query(query)
            
            params_lst = []
            for id, content in out:
                hashtags = find_hashtags(content)
                for hashtag in hashtags:
                    params_lst.append((id, hashtag))
            
            params_lst = list(set(params_lst)) # remove duplicates
                        
            db.executemany("INSERT INTO Hashtag (tweet_id, hashtag) VALUES (?, ?)", params_lst)
                    
        if not db.table_exists("Follow"):
            query = """
            CREATE TABLE Follow (
                follower INTEGER,
                followee INTEGER,
                PRIMARY KEY (follower, followee)
                FOREIGN KEY (follower) REFERENCES Tweet (username),
                FOREIGN KEY (followee) REFERENCES Tweet (username)
            );
            """
            db.query(query) 
            
        if not db.table_exists("Users"): # Users = username
            query = """
            CREATE TABLE Users (
                user_id TEXT PRIMARY KEY
            );
            """
            db.query(query)
            
            query = """
            INSERT INTO Users (user_id)
            SELECT DISTINCT username
            FROM Tweet;
            """
            db.query(query)
        
        if not self._from_scratch:
            db.query("DROP TABLE initial_data")
            

    @profile
    def insert_hashtag(self, tuple):
        try:
            query = """
            INSERT INTO Hashtag (tweet_id, hashtag)
            VALUES (?, ?);
            """
            self.query(query, tuple)
        except sqlite3.IntegrityError:
            pass
    
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
        query = """
        INSERT INTO Tweet (content,content_embedding, username, like_count, retweet_count, date)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        self.query(query, tuple)
 
        query = """
        SELECT MAX(id) AS max_id FROM Tweet
        """
 
        hashtags = find_hashtags(tuple[0]) # content is first elm of tuple
        latest_tweet_id = self.query(query)[0][0]  # returns a list of tuples, we want the first element of the first tuple            
        for hashtag in hashtags:
            self.insert_hashtag((latest_tweet_id, hashtag)) # latesttweet_id is the id of the tweet we just inserted

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
        try:
            self.query(query, tuple)   
        except sqlite3.IntegrityError:
            print("already following the user")
            
    @profile    
    def get_feed(self, n_samples:int, with_ids:bool, username )-> List[Tuple] : # returns a list of tuples, used by frontend
        if with_ids:
            tweet_id = "id,"
        else:
            tweet_id = ""
        
        if username is None:
            user = ""
        else:
            user = f"AND username <> '{username}'"   
        
        tweet_query = f""" 
        SELECT {tweet_id} content, username, like_count, retweet_count, date FROM Tweet 
        WHERE 1=1 {user}
        ORDER BY id DESC
        LIMIT {n_samples};        
        """
        lst = [("Tweet", tweet) for tweet in self.query(tweet_query)] # change to also include hashtags from hashtag table
        return lst
    
    @profile
    def similarity_search(self, xq: np.array, n_samples: int, with_dist : bool , with_ids: bool, username,  retrain = False) -> list:        
        k = n_samples # number of tweets to search through
        d = 1024 # dimnesion of embeddings
        nlist = 128 # number of clusters
        if username is None:
            user = ""
        else:
            user = f"AND username <> '{username}'"   
            
        tweets = self.query("SELECT id, content_embedding FROM Tweet")
        tweet_embeddings = [convert_bytes_to_nparray(embedding) for _ , embedding in tweets]   
        tweet_ids = [id for id, _ in tweets]
        embeddings = np.array(tweet_embeddings)
        try:
            wb = np.stack(embeddings)
        except ValueError as e:
            print('database is empty not search can be performed:', e)
            return []
            
        d = 1024 # dimnesion of embeddings
        nlist = 128 # number of clusters
       
        if retrain or not os.path.exists('src\Database\Trained.index'): # if model already trained
            quantizer = faiss.IndexFlatIP(d)
            self._index = faiss.IndexIVFFlat(quantizer, d, nlist)
            self._index.train(wb)         
            faiss.write_index(self._index, 'src\Database\Trained.index')
        else:
            self._index = faiss.read_index('src\Database\Trained.index')  

        self._index.add(wb)
        self._index.nprobe = 4
        
        D, I = self._index.search(xq, k) # distance, index
        recommended_tweet_ids = [tweet_ids[i] for i in I[0]]
        if with_ids: 
            tweet_id = "id,"
        else:
            tweet_id = ""
        tweets = self.query(f"SELECT {tweet_id} content, username, like_count, retweet_count, date FROM Tweet WHERE id IN ({','.join(map(str, recommended_tweet_ids))}) {user}")
         
        if with_dist:
            distances = [dist for dist in D[0]]
            return list(zip(distances, tweets))
        else:                
            return tweets        
    
    @profile 
    def search_db(self, search: str, n_samples: int) -> List[Tuple]: # CHNAGE FUNCTION SEARCH IN HASHTAG TABLE INSTEAD!!
        '''searches the database for tweets, returns a list of tuples of format (content, username, like_count, retweet_count, date)'''
        if search.startswith("#"): # change this 
            
            term = search.lstrip('#')
            
            query = f"""
            SELECT tweet_id FROM Hashtag WHERE hashtag LIKE '{term}%' 
            LIMIT {n_samples}
            """
            
            tweet_ids = self.query(query)        
            tweets = []
                      
            for id in tweet_ids:
                query = f"""
                SELECT content, username, like_count, retweet_count, date FROM Tweet 
                WHERE id IN ({id[0]})
                """
                tweet = self.query(query)
                
                tweets.append(('Tweet', tweet[0]))
                
            return tweets
           
        if search.startswith("@"):
            username_to_search = search.lstrip('@')
            query = f"""
            SELECT content, username, like_count, retweet_count, date FROM Tweet 
            WHERE username LIKE '{username_to_search}%'
            LIMIT {n_samples}
            """
            out = self.query(query)
            return [('Tweet', tweet) for tweet in out]
                    
        else:   
            xq = embed([search])# this is the latency bottleneck
            xq = np.array([xq.embeddings[0]])  
            out = self.similarity_search(xq, n_samples, False, False, None)
            return [('Tweet', tweet) for tweet in out]
            
            

        



