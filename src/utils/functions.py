from typing import List, Tuple
import openai
import numpy as np
import re
import cohere
import time 
import os
import functools
import cProfile
import pathlib as pl
import sys

parent = pl.Path(__file__).parent  

while parent.name != 'Generative_Twitter_Agents':
    if parent.parent == parent: # We've reached the root directory
        break
    parent = parent.parent

sys.path.append(str(parent))

def profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        path = f"{parent}/profiling/"
        if not os.path.exists(path):
            os.makedirs(path)
        profiler.dump_stats(path + f"{func.__name__}.prof")
        return result

    return wrapper

def token_count(text: str) -> int:
    return len(text.split())*2    

def list_to_string(inp: List[Tuple[str,str]]) -> str:
    return "\n".join([f"{pred}{elm}" for pred,elm in inp])
    
def convert_to_BLOB(embedding):
    out = np.array(embedding) # np array to bytes for blob data in sqlite, float 64 is the default
    return out.tobytes()

def embed(text: List[str]):
    co = cohere.Client(os.getenv("COHERE_API_KEY"))
    time.sleep((100/60) + 0.01)
    response = co.embed(
    texts=text,
    model='small',
    )
    return response

def create_embedding_bytes(text: str) -> bytes:
    if type(text) is list:
        raise Exception("text is a list of strings, please pass a string")
    
    response = embed([text])    
    out_lst = convert_to_BLOB(response.embeddings[0])
    return out_lst

def create_embedding_nparray(text: str) -> np.array:
    if type(text) is list:
        raise Exception("text is a list of strings, please pass a string")
    response = embed([text])    
    out_lst = [np.array(embedding) for embedding in response.embeddings]
    return out_lst

# After retrieving from SQLite

def convert_bytes_to_nparray(embedding_bytes:bytes) -> np.array:
    '''Converts a byte stream to a numpy array'''
    embedding_np = np.frombuffer(embedding_bytes, dtype=np.float64)    
    return embedding_np

def get_date(data):
    pattern = r'\d{4}-\d{2}-\d{2}'
    if data is not None:
        match = re.search(pattern, data)
        if match:
            return match.group(0)
    else: 
        return None

