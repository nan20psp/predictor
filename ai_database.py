# ai_database.py

import pymongo
import os
from datetime import datetime

# --- MongoDB Connection ---
try:
    MONGO_URL = os.environ.get("MONGO_URL")
    if not MONGO_URL:
        print("Error: MONGO_URL environment variable မတွေ့ပါ။")
        exit()
        
    client = pymongo.MongoClient(MONGO_URL)
    db = client["ai_pattern_db"] 
    
    wingo_results_collection = db["wingo_results"] # Wingo Data တွေ သိမ်းရန်
    active_groups_collection = db["active_groups"] # Bot ရှိနေတဲ့ Group list
    bot_settings_collection = db["bot_settings"]   # "Pattern 1" / "Pattern 2" သိမ်းရန်

    print("✅ AI Pattern Bot Database နှင့် အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ။")
except Exception as e:
    print(f"❌ AI Pattern Bot Database ချိတ်ဆက်ရာတွင် Error ဖြစ်နေပါသည်: {e}")
    client = None

# --- Group Management ---
def add_group(chat_id, group_name):
    if not client: return
    active_groups_collection.update_one(
        {"_id": chat_id},
        {"$set": {"name": group_name, "joined_at": datetime.now().isoformat()}},
        upsert=True
    )

def remove_group(chat_id):
    if not client: return
    active_groups_collection.delete_one({"_id": chat_id})

def get_all_groups():
    if not client: return []
    return [doc["_id"] for doc in active_groups_collection.find({}, {"_id": 1})]

# --- Result & Pattern Functions ---
def add_result(issue_id, result_value, result_number):
    """Wingo Result အသစ် ထည့်ပါ။"""
    if not client: return
    check = wingo_results_collection.find_one({"_id": issue_id})
    if not check:
        wingo_results_collection.insert_one({
            "_id": issue_id,
            "result_val": result_value.lower(), # "small"
            "result_num": result_number, # "5"
            "timestamp": datetime.now()
        })
        print(f"New Result Added: {issue_id} -> {result_value} ({result_number})")
        return True
    return False

def get_last_results(count=10):
    """ခန့်မှန်း ချက် တွက်ရန် နောက်ဆုံး Result (10) ခုကို ယူပါ။"""
    if not client: return []
    # (ပြင်ဆင်ပြီး) "small" or "big" ကိုပဲ ယူပါ
    cursor = wingo_results_collection.find({}, {"result_val": 1, "_id": 0}).sort("_id", -1).limit(count)
    results = [doc["result_val"] for doc in cursor]
    return results[::-1] # Reverse the list [oldest...newest]

def set_active_pattern(pattern_number):
    if not client: return
    bot_settings_collection.update_one(
        {"_id": "main_config"},
        {"$set": {"active_pattern": pattern_number}},
        upsert=True
    )

def get_active_pattern():
    if not client: return 1 
    config = bot_settings_collection.find_one({"_id": "main_config"})
    if config:
        return config.get("active_pattern", 1)
    return 1
