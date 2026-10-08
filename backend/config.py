import os
from dotenv import load_dotenv

load_dotenv()

COMPANY_NAME = os.getenv("COMPANY_NAME", "Home Credit")
AGENT_NAME = os.getenv("AGENT_NAME", "Priya")
AGENT_GENDER = os.getenv("AGENT_GENDER", "Female")
LANGUAGE_TO_SPEAK = os.getenv("LANGUAGE_TO_SPEAK", "English")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
