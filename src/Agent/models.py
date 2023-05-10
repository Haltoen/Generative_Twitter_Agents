from cerebrium import Conduit, model_type, hardware
import requests
import json
import os


class model:
    def __init__(self, model_name, max_tokens):
        self._model_name = model_name    
        self._max_tokens = max_tokens
        self._api_key_private = os.environ.get("CEREBRIUM_API_KEY_Private")
        self._api_key_public = os.environ.get("CEREBRIUM_API_KEY_PUBLIC")
        
        print(self._api_key_private)
        print(self._api_key_public)
    def deploy_llm(self):
        c = Conduit(
            'hf-gpt',
            self._api_key_private,
            [
                (model_type.HUGGINGFACE_PIPELINE, {"task": "text-generation", "model": "EleutherAI/gpt-neo-125M", "max_new_tokens": 100}),
            ],
        )
        c.deploy()

    def generate(self, prompt):            
        url = "<ENDPOINT>"
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
            print(response.text)
            

gpt = model("gpt", 100)
gpt.deploy.llm()

