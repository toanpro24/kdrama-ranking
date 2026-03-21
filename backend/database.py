import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "kdrama_ranking")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
actresses_collection = db["actresses"]

# Index for fast drama lookups (used by /api/dramas/:title and drama field updates)
actresses_collection.create_index("dramas.title")
