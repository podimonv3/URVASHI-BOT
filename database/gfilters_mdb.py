import pymongo
from info import DATABASE_URI, DATABASE_NAME
from pyrogram import enums
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]



async def add_gfilter(gfilters, text, reply_text, btn, file, alert):
    mycol = mydb[str(gfilters)]

    data = {
        'text': str(text),
        'reply': str(reply_text),
        'btn': str(btn),
        'file': str(file),
        'alert': str(alert)
    }

    try:
        mycol.update_one({'text': str(text)}, {"$set": data}, upsert=True)
    except:
        logger.exception('Some error occured!', exc_info=True)
             
     
async def find_gfilter(gfilters, name):
    mycol = mydb[str(gfilters)]
    
    query = mycol.find({"text": name})
    try:
        reply_text, btn, alert, fileid = None, None, None, None
        for file in query:
            reply_text = file['reply']
            btn = file['btn']
            fileid = file['file']
            # .get() ഉപയോഗിച്ചാൽ അഥവാ ഡാറ്റ ഇല്ലെങ്കിലും എറർ അടിക്കാതെ None എന്ന് കിട്ടും
            alert = file.get('alert', None)
        return reply_text, btn, alert, fileid
    except:
        return None, None, None, None


async def get_gfilters(gfilters):
    mycol = mydb[str(gfilters)]

    texts = []
    query = mycol.find()
    try:
        for file in query:
            text = file['text']
            texts.append(text)
    except:
        pass
    return texts


async def delete_gfilter(message, text, gfilters):
    mycol = mydb[str(gfilters)]
    
    myquery = {'text': text}
    count = mycol.count_documents(myquery)
    if count > 0:  # ഇവിടെ 1-ന് പകരം > 0 ആക്കി സുരക്ഷിതമാക്കി
        mycol.delete_many(myquery) # ഡിലീറ്റ് ഓൾ അല്ലെങ്കിൽ ഡിലീറ്റ് വൺ
        await message.reply_text(
            f"'`{text}`' deleted. I'll not respond to that gfilter anymore.",
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN
        )
    else:
        await message.reply_text("Couldn't find that gfilter!", quote=True)


async def del_allg(message, gfilters):
    if str(gfilters) not in mydb.list_collection_names():
        await message.edit_text("Nothing to remove !")
        return

    mycol = mydb[str(gfilters)]
    try:
        mycol.drop()
        await message.edit_text("All gfilters have been removed !") # Text Grammar ശരിയാക്കി
    except:
        await message.edit_text("Couldn't remove all gfilters !")
        return


async def count_gfilters(gfilters):
    mycol = mydb[str(gfilters)]
    count = mycol.count_documents({})
    return False if count == 0 else count


async def gfilter_stats():
    collections = mydb.list_collection_names()

    if "CONNECTION" in collections:
        collections.remove("CONNECTION")

    totalcount = 0
    for collection in collections:
        mycol = mydb[collection]      
        count = mycol.count_documents({})
        totalcount += count

    totalcollections = len(collections)

    return totalcollections, totalcount
