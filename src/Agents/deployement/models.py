from cerebrium import Conduit, model_type, hardware
import requests
import json
import os
import subprocess
import io
import contextlib
import pathlib as pl
import time 

class model:
    def __init__(self, model_name, huggingface_name,  max_tokens):
        self._model_name = model_name    
        self._max_tokens = max_tokens
        self._api_key_private = os.environ.get("CEREBRIUM_API_KEY_Private")
        self._api_key_public = os.environ.get("CEREBRIUM_API_KEY_PUBLIC")
        self._end_point = None
        path = pl.Path(__file__).parent
        self._json_path = f"{path}\models_deployed.json" # hardcoded
        self._huggingface_name = huggingface_name
        
        self.deploy_llm()
        
    def check_endpoint(self) -> bool:

        with open(self._json_path, 'r') as json_file:
            data = json.load(json_file)

        if self._huggingface_name in data['models_deployed']:
            print(f"{self._huggingface_name} already deployed")
            self._end_point = data['models_deployed'][self._huggingface_name]           
            print("model already deployed, ready to generate")
            
            return True
        else: 
            return False    

    
    def deploy_llm(self):  # not ideal, instance deployed each time the function is called, expensive!!!  
        
        exists = self.check_endpoint()
        if exists == False:       
            c = Conduit(
                'hf-gpt',
                self._api_key_private,
                [
                    (model_type.HUGGINGFACE_PIPELINE, {"task": "text-generation", "model": f"{self._huggingface_name}", "max_new_tokens": 100}),
                ],
            )
            
            c.deploy()
            # Redirect standard output to a custom stream
            custom_stdout = io.StringIO()
            with contextlib.redirect_stdout(custom_stdout):
                c.deploy()

            # Get the output as a string
            output = custom_stdout.getvalue()

            # Parse the output as before
            for line in output.split('\n'):
                if line.startswith('🌍 Endpoint:'):
                    self._end_point = line.split(': ')[1]  # this will return the URL after '🌍 Endpoint: '
                    
            print("end point set:", self._end_point)
            with open(self._json_path, 'r') as json_file:
                data = json.load(json_file)
            data['models_deployed'][self._huggingface_name] = self._end_point
            
            with open(self._json_path, 'w') as json_file:
                json.dump(data, json_file, indent=4)
        
                    
        else:
            print( f"model {self._model_name} which is a {self._huggingface_name} deployed at {self._end_point}")     
        
    def generate(self, prompt):   
        t0 = time.time()
                 
        url = f"{self._end_point}"
        headers = {
            "Authorization": self._api_key_public,
            "Content-Type": "application/json",
        }

        data = {
            "data": f"{prompt}",
            "parameters": {
                "max_new_tokens": self._max_tokens,
            }
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            print("Request successful")
            print(response.json())
        else:
            print(f"Request failed with status code {response.status_code}")
            out = response.text
            print(out)
            
        print(f"Time taken: {time.time() - t0} seconds")
        return out


path = pl.Path(__file__).parent.parent

with open(f"{path}\instructions.txt", "r", encoding="utf-8", errors="ignore") as file:
    instruction = file.read() 

gpt = model("mosaic_instruction_tune", "mosaicml/mpt-7b-instruct", 100)


gpt.generate("make a tweet call to the api. you make an api call that creates a tweet like this: api.create_tweet('hello world')")