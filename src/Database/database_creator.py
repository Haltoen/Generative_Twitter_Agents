import sqlite3 
import pandas as pd
import os
from typing import List, Tuple
from utils.functions import convert_to_BLOB, get_date, list_to_string, profile
import ast


class DB:
    def __init__(self, name, db_path):
        self._name = name
        self._db_path = db_path

    @profile
    def csv_to_db(self, csv_path, table_name):
        if os.path.exists(self._db_path):
            print(f"Database '{self._name}' already exists.")
        else:
            print(f"Building Database from csv")
            df = pd.read_csv(csv_path)
            print(df.head())
            print("content_embedding col type" , type(df["content_embedding"][0]))
            
            
            df['content_embedding'] = df['content_embedding'].apply(lambda x: ast.literal_eval(x)) ## not ideal but csv files when opened have bytes as strings, this is fucking slow
            df['date'] = df['date'].apply(lambda x: get_date(x))  
            print("type df fromk csv after intervention", type(df["content_embedding"][0]))  
            conn = sqlite3.connect(self._db_path)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            conn.close()
            print(f"CSV data has been imported into the '{table_name}' table in '{self._db_path}'.")
    
    @profile        
    def build_db(self):
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
    
    @profile    
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
    def __init__(self, name, csv_path = 'src\Database\large_embedded_dataset.csv' ):
        self._db_path = f"src\Database\{name}.sqlite"
        super().__init__(name, self._db_path)
        self.csv_to_db(csv_path, "initial_data") # possibly not good, bc if an erroneous db is created we wont know
        self.init_twitter_db()
    
    @profile#should not be called by user
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
                id_child INTEGER PRIMARY KEY,
                id_parent INTEGER,
                FOREIGN KEY (id_parent) REFERENCES Tweet(tweet_id),
                FOREIGN KEY (id_child) REFERENCES Tweet(tweet_id)
            );
            """
            self.query(query2)
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
                user_id INTEGER PRIMARY KEY,
            );
            """
    
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
    def get_feed(self)-> List[Tuple] : # delete soon
                
        tweet_query = f"""
        SELECT content, username, like_count, retweet_count, date FROM Tweet
        ORDER BY id DESC
        LIMIT {10};        
        """
        lst = [("Tweet", tweet) for tweet in self.query(tweet_query)]
        return lst
    

