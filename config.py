import os 
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_TRACING_V2= os.getenv("LANGSMITH_TRACING_V2")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")
DATABASE_URL = "sqlite+aiosqlite:///inventory.db"
CHECKPOINT_DB = "checkpoints.sqlite"
CHROMA_DIR = "./store_inventory"

#validation of OPENAI Key
if not OPENAI_API_KEY:
    raise ValueError("OPEN AI API key is missing.")
