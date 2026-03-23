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

# Per-user collections
user_rankings_collection = db["user_rankings"]
user_rankings_collection.create_index([("userId", 1), ("actressId", 1)], unique=True)

user_drama_status_collection = db["user_drama_status"]
user_drama_status_collection.create_index([("userId", 1), ("actressId", 1), ("dramaTitle", 1)], unique=True)

# Per-user actress list (which actresses each user has in their pool)
user_actresses_collection = db["user_actresses"]
user_actresses_collection.create_index([("userId", 1), ("actressId", 1)], unique=True)
user_actresses_collection.create_index("userId")
