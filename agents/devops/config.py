import os
from brain.config import API_KEY, BASE_URL, MODEL

MAX_TOKENS  = 4096
TEMPERATURE = 0.1

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompt.md")
