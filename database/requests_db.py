from motor.motor_asyncio import AsyncIOMotorClient
from info import DATABASE_URI  # നിങ്ങളുടെ പ്രധാന കൺഫിഗറേഷൻ ഫയലിൽ നിന്നുള്ള URI

# ഇവിടെ DATABASE_URI അല്ലെങ്കിൽ നിങ്ങളുടെ കറക്റ്റ് ലിങ്ക് നൽകുക
client = AsyncIOMotorClient(DATABASE_URI)
db = client["MissingRequestsDB"]
collection = db["missing_movies"]

async def init_db():
    """24 മണിക്കൂർ കഴിയുമ്പോൾ ഡാറ്റ തനിയെ ഡിലീറ്റ് ആകാനുള്ള TTL ഇൻഡക്സ് സെറ്റ് ചെയ്യുന്നു"""
    # 86400 സെക്കൻഡ് = 24 മണിക്കൂർ
    await collection.create_index("createdAt", expireAfterSeconds=86400)
    # ഡ്യൂപ്ലിക്കേഷൻ വരാതിരിക്കാൻ സിനിമയുടെ പേര് unique ആക്കുന്നു
    await collection.create_index("movie_name", unique=True)

async def save_missing_movie(movie_name):
    """സിനിമയുടെ പേര് ആവർത്തനം ഇല്ലാതെ ഡാറ്റാബേസിൽ സേവ് ചെയ്യുന്നു"""
    from datetime import datetime
    try:
        # unique ഇൻഡക്സ് ഉള്ളതിനാൽ ഒരേ പേര് വീണ്ടും വന്നാൽ ഇത് skip ചെയ്യും
        await collection.insert_one({
            "movie_name": movie_name.strip().lower(),
            "createdAt": datetime.utcnow()
        })
        return True
    except Exception:
        # Duplicate key error വന്നാൽ ഇവിടെ ഹാൻഡിൽ ചെയ്യും
        return False

async def get_all_missing_movies():
    """ഡാറ്റാബേസിലുള്ള എല്ലാ സിനിമകളും alphabetical order-ൽ എടുക്കുന്നു"""
    cursor = collection.find({}).sort("movie_name", 1)
    results = await cursor.to_list(length=None)
    return [doc["movie_name"].title() for doc in results]

