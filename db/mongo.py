import os
import ssl
import certifi
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI")

# client = MongoClient(
#     MONGODB_URI,
#     server_api=ServerApi('1'),
#     tlsCAFile=certifi.where()
# )

# db = client["astranova_tasks"]

client = MongoClient(MONGODB_URI)
db = client["astranova_tasks"]

tasks_collection = db["task_logs"]
conversations_collection = db["conversations"]

def log_task_execution(task_type, tool_name, arguments, status, result, error=None):
    document = {
        "task_type": task_type,
        "tool_name": tool_name,
        "arguments": arguments,
        "status": status,
        "result": result,
        "error": error,
        "timestamp": datetime.utcnow()
    }
    inserted = tasks_collection.insert_one(document)
    return str(inserted.inserted_id)

def get_recent_task_logs(task_type=None, limit=20):
    query = {"task_type": task_type} if task_type else {}
    cursor = tasks_collection.find(query).sort("timestamp", -1).limit(limit)
    return [
        {
            "task_type": doc["task_type"],
            "tool_name": doc["tool_name"],
            "status": doc["status"],
            "result": doc["result"],
            "error": doc.get("error"),
            "timestamp": doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        }
        for doc in cursor
    ]

def get_failed_tasks(limit=20):
    cursor = tasks_collection.find({"status": "failure"}).sort("timestamp", -1).limit(limit)
    return [
        {
            "task_type": doc["task_type"],
            "tool_name": doc["tool_name"],
            "arguments": doc["arguments"],
            "error": doc.get("error"),
            "timestamp": doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        }
        for doc in cursor
    ]

def log_conversation_turn(role, content):
    conversations_collection.insert_one({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    })
