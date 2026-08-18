import os
from pathlib import Path
from dotenv import load_dotenv
import requests

env_path = Path('d:/users/OMNIROUTE-TEST/memorygraph/.env')
load_dotenv(env_path)

api_key = os.environ.get("GROQ_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
models = response.json()

for model in models.get("data", []):
    print(model["id"])
