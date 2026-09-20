import logging
from pymongo import MongoClient
from info import DATABASE_URI

logger = logging.getLogger(__name__)

try:
    client = MongoClient(DATABASE_URI)
    db = client['telegram_advanced_bot']
    settings_collection = db['settings']
    logger.info("✅ MongoDB-യുമായി വിജയകരമായി കണക്ട് ചെയ്തിരിക്കുന്നു!")
except Exception as e:
    logger.error(f"❌ MongoDB കണക്ഷൻ പരാജയപ്പെട്ടു: {e}")


def get_group_locks(chat_id: int):
    """ഗ്രൂപ്പിലെ നിലവിലെ എല്ലാ ലോക്ക് സെറ്റിങ്സും എടുക്കുന്നു"""
    config = settings_collection.find_one({'_id': f'locks_{int(chat_id)}'})
    if config:
        return config.get('locks', {})
    
    # ഡിഫോൾട്ട് ആയി ആദ്യ തവണ എല്ലാ മീഡിയകളും അനുവദിച്ചിരിക്കുന്നു (Allow = False)
    return {
        "photos": False, "videos": False, "stickers": False, "voice": False, 
        "audio": False, "document": False, "animation": False, "poll": False,
        "video_note": False, "contact": False, "location": False, "inline": False,
        "story": False, "game": False, "channel": False,
        "new_members": False, "left_members": False, "title_changed": False,
        "photo_changed": False, "pinned": False, "video_chat": False,
        "fwd_channel": False, "usernames": False, "hashtags": False, 
        "commands": False, "emails": False, "links": False, 
        "text_styles": False, "edited": False
    }


def set_group_lock(chat_id: int, media_type: str, status: bool):
    """ഒരു പ്രത്യേക മീഡിയ ലോക്ക്/അൺലോക്ക് ചെയ്യാൻ"""
    current_locks = get_group_locks(chat_id)
    current_locks[media_type] = status
    settings_collection.update_one(
        {'_id': f'locks_{int(chat_id)}'}, 
        {'$set': {'locks': current_locks}}, 
        upsert=True
    )
