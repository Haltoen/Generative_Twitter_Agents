import sqlite3 
import pandas as pd
import os
from typing import List, Tuple
from utils.functions import convert_to_BLOB, get_date, list_to_string
import csv
import base64
import ast
class DB:
    def __init__(self, name, db_path):
        self._name = name
        self._db_path = db_path

    def csv_to_db(self, csv_path, table_name):
        if os.path.exists(self._db_path):
            print(f"Database '{self._name}' already exists.")
        else:
            print(f"Building Database from csv")
            df = pd.read_csv(csv_path)
            print("type df fromk csv", type(df["content_embedding"][0]))
            
            df['content_embedding'] = df['content_embedding'].apply(lambda x: ast.literal_eval(x)) ## not ideal but csv files when opened have bytes as strings, this is fucking slow
            df['date'] = df['date'].apply(lambda x: get_date(x))  
            print("type df fromk csv after intervention", type(df["content_embedding"][0]))  
            conn = sqlite3.connect(self._db_path)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            conn.close()
            print(f"CSV data has been imported into the '{table_name}' table in '{self._db_path}'.")
            
    def build_db(self):
        if os.path.exists(self._db_path):
            print(f"Database '{self._name}' already exists.")
        else:
            conn = sqlite3.connect(self._db_path)
            conn.close()

    
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
    
    def table_exists(self, table_name):
        result = self.query(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        return len(result) > 0
    
    def insert_subtweet(self, tuple):
        query = """
        INSERT INTO Subtweet (content,content_embedding, username, like_count, retweet_count, tweet_id, date)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        self.query(query, tuple)
        
    def insert_tweet(self, tuple):
        query = """
        INSERT INTO Tweet (content,content_embedding, username, like_count, retweet_count, date)
        VALUES (?, ?,?, ?, ?, ?);
        """
        self.query(query, tuple)
        
    def increment_like_count(self, table_name, id):
        query = f"""
        UPDATE {table_name}
        SET like_count = like_count + 1
        WHERE id = {id};
        """
        self.query(query)
    
    def increment_retweet_count(self, table_name, id):
        query = f"""
        UPDATE {table_name}
        SET retweet_count = retweet_count + 1
        WHERE id = {id};
        """
        self.query(query)
    
    def insert_follow(self, tuple):
        query = """
        INSERT INTO Follow (follower, followee)
        VALUES (?, ?);
        """
        self.query(query, tuple)    
    
    def drop_row(self, table_name, row_id):
        query = f"""
        DELETE FROM {table_name}
        WHERE id = {row_id};
        """
        self.query(query)
        
class Twitter_DB(DB):
    def __init__(self, name, csv_path = 'src\Database\embedded_dataset_small.csv' ):
        self._db_path = f"src\Database\{name}.sqlite"
        super().__init__(name, self._db_path)
        self.csv_to_db(csv_path, "initial_data")
        self.init_twitter_db()
    #should not be called by user
    def init_twitter_db(self):
        
        # modifying the csv file data and making id self incrementing        
        if not self.table_exists("Tweet"):
                
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
            self.query(query)

            query1 = """
            INSERT INTO Tweet (content, content_embedding, username, like_count, retweet_count, date)
            SELECT content, content_embedding, username, like_count, retweet_count, date
            FROM initial_data;
            """
            self.query(query1)

        if not self.table_exists("Subtweet"):
            query2 = """
            CREATE TABLE Subtweet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                content_embedding BLOB,
                username TEXT,
                like_count INTEGER,
                retweet_count INTEGER,
                date TEXT,
                tweet_id INTEGER,
                FOREIGN KEY (tweet_id) REFERENCES Tweet (id)
            );
            """
            self.query(query2)
            self.query("DROP TABLE initial_data")
        
        if not self.table_exists("Follow"):
            query3 = """
            CREATE TABLE Follow (
                follower TEXT,
                followee TEXT,
                FOREIGN KEY (follower) REFERENCES Tweet (username),
                FOREIGN KEY (followee) REFERENCES Tweet (username)
            );
            """
            self.query(query3)   
        
    def get_feed(self)-> List[Tuple] : # not finished
                
        tweet_query = f"""
        SELECT content, username, like_count, retweet_count, date FROM Tweet
        ORDER BY id DESC
        LIMIT {10};        
        """
        subtweet_query = f"""
        SELECT content, username, like_count, retweet_count, date FROM Subtweet
        ORDER BY id DESC
        LIMIT {10};
        """        
        lst = [("Tweet", tweet) for tweet in self.query(tweet_query)] + [("Subtweet", subtweet) for subtweet in self.query(subtweet_query)]
        return lst