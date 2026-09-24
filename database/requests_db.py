from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from info import DATABASE_URI

client = AsyncIOMotorClient(DATABASE_URI)
db = client["MissingRequestsDB"]
collection = db["missing_movies"]

async def init_db():
    """24 മണിക്കൂർ കഴിയുമ്പോൾ ഡാറ്റ തനിയെ ഡിലീറ്റ് ആകാനുള്ള TTL ഇൻഡക്സ് സെറ്റ് ചെയ്യുന്നു"""
    # ശ്രദ്ധിക്കുക: അവസാനമായി തിരഞ്ഞ സമയത്തിന് (lastSearchedAt) ശേഷമുള്ള 24 മണിക്കൂറാണ് ഇവിടെ കണക്കാക്കുക.
    await collection.create_index("lastSearchedAt", expireAfterSeconds=86400)
    await collection.create_index("movie_name", unique=True)

async def save_missing_movie(movie_name):
    """സിനിമ പുതിയതാണെങ്കിൽ സേവ് ചെയ്യും, ഉള്ളതാണെങ്കിൽ കൗണ്ട് 1 വർദ്ധിപ്പിക്കും"""
    movie_clean = movie_name.strip().lower()
    
    # ഡാറ്റാബേസിൽ ഉണ്ടോ എന്ന് നോക്കി കൗണ്ട് കൂട്ടുന്നു, ഇല്ലെങ്കിൽ പുതിയത് ക്രിയേറ്റ് ചെയ്യുന്നു
    await collection.update_one(
        {"movie_name": movie_clean},
        {
            "$inc": {"search_count": 1},
            "$set": {"lastSearchedAt": datetime.utcnow()}
        },
        upsert=True
    )
    return True

async def get_all_missing_movies():
    """ഡാറ്റാബേസിലുള്ള എല്ലാ സിനിമകളും alphabetical order-ൽ എടുക്കുന്നു"""
    cursor = collection.find({}).sort("movie_name", 1)
    results = await cursor.to_list(length=None)
    
    # സിനിമയുടെ പേരും അതിന്റെ കൗണ്ടും ഒന്നിച്ച് റിട്ടേൺ ചെയ്യുന്നു
    return [{"name": doc["movie_name"].title(), "count": doc.get("search_count", 1)} for doc in results]
