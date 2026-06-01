import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JSEARCH_API_KEY:str=os.getenv("JSEARCH_API_KEY")
    JSEARCH_API_HOST:str=os.getenv("JSEARCH_API_HOST")
    jsearch_URL:str=os.getenv("jsearch_URL")
    jsearch_detail_URL:str=os.getenv("jsearch_detail_URL")

settings=Settings()