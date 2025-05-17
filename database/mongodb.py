import os

from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(MONGO_URL)

def mongo_client(database: str, collection: str):
    """function
    parameter:
        database: str (require)
        collection: str (require)"""
    try:
        client.admin.command("ping")
        print(f"[{collection}]: [Pinged your deployment. You successfully connected to MongoDB!]")
        
        database_name = client[database]
        collection_name = database_name[collection]
        
        return collection_name
    except Exception as e:
        return f"An error occurred: {e}"