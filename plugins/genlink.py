import re
import os
import json
import base64
import logging
import time  # ടൈംഔട്ട് ട്രാക്ക് ചെയ്യാൻ
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from database.ia_filterdb import unpack_new_file_id
from utils import temp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# അഡ്മിൻമാരുടെ സ്റ്റേറ്റ് ട്രാക്ക് ചെയ്യാനുള്ള താത്കാലിക ഡിക്ഷണറി
ADMIN_BATCH_STATE = {}

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')
    
    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("Reply to a supported media")
        
    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")
        
    file_id, ref = unpack_new_file_id((getattr(replied, file_type.value)).file_id)
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    await message.reply(f"Here is your Link:\nhttps://t.me{temp.U_NAME}?start={outstr}")


# കമാൻഡ് ഇല്ലാതെ ഫോർവേഡ് മെസ്സേജുകൾ കൈകാര്യം ചെയ്യുന്നു
@Client.on_message(filters.private & filters.forwarded & filters.create(allowed))
async def handle_forward_batch(bot, message):
    user_id = message.from_user.id
    f_chat_id = message.forward_from_chat.id if message.forward_from_chat else None
    f_msg_id = message.forward_from_message_id
    current_time = time.time()

    if not f_chat_id:
        return await message.reply("ദയവായി ഒരു ചാനലിൽ നിന്നും ഫയൽ ഫോർവേഡ് ചെയ്യുക.")

    # 10 മിനിറ്റിൽ കൂടുതൽ പഴയ ഡാറ്റ മെമ്മറിയിൽ ഉണ്ടെങ്കിൽ അത് ക്ലിയർ ചെയ്യുന്നു (Memory Protection)
    if user_id in ADMIN_BATCH_STATE:
        if current_time - ADMIN_BATCH_STATE[user_id]["timestamp"] > 600:
            del ADMIN_BATCH_STATE[user_id]

    # ഘട്ടം 1: ആദ്യത്തെ ഫയൽ ഫോർവേഡ് ചെയ്യുമ്പോൾ
    if user_id not in ADMIN_BATCH_STATE:
        ADMIN_BATCH_STATE[user_id] = {
            "chat_id": f_chat_id,
            "first_msg_id": f_msg_id,
            "timestamp": current_time
        }
        return await message.reply(
            "📥 **ആദ്യത്തെ ഫയൽ ലഭിച്ചു!**\n\nഇനി ബാച്ചിന്റെ **അവസാനത്തെ ഫയൽ** കൂടി ഇങ്ങോട്ട് ഫോർവേഡ് ചെയ്യുക. ഞാൻ **Protected Link** ജനറേറ്റ് ചെയ്ത് തരാം.\n\n_ഒഴിവാക്കാൻ /cancel എന്ന് ടൈപ്പ് ചെയ്യുക._"
        )

    # ഘട്ടം 2: രണ്ടാമത്തെ ഫയൽ ഫോർവേഡ് ചെയ്യുമ്പോൾ
    state = ADMIN_BATCH_STATE[user_id]
    
    if state["chat_id"] != f_chat_id:
        ADMIN_BATCH_STATE[user_id] = {
            "chat_id": f_chat_id,
            "first_msg_id": f_msg_id,
            "timestamp": current_time
        }
        return await message.reply("⚠️ വ്യത്യസ്തമായ ചാനൽ! ഇത് പുതിയ ബാച്ചിന്റെ ആദ്യ ഫയലായി സേവ് ചെയ്തു. ഇനി അവസാന ഫയൽ അയക്കുക.")

    first_msg_id = state["first_msg_id"]
    last_msg_id = f_msg_id

    # ബാച്ച് തുടങ്ങിയതിനാൽ ഡാറ്റ മെമ്മറിയിൽ നിന്നും നീക്കുന്നു
    del ADMIN_BATCH_STATE[user_id]

    sts = await message.reply("⏳ ബാച്ച് ഫയലുകൾ പ്രോസസ്സ് ചെയ്യുന്നു... ദയവായി കാത്തിരിക്കുക.")

    # ഫയൽ സ്റ്റോർ ചാനൽ ലിസ്റ്റിൽ ഉള്ളതാണെങ്കിൽ ഡയറക്ട് പ്രൊട്ടക്റ്റഡ് ലിങ്ക് നൽകുന്നു
    if f_chat_id in FILE_STORE_CHANNEL:
        string = f"{first_msg_id}_{last_msg_id}_{f_chat_id}_/pbatch"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        return await sts.edit(f"🔒 Here is your Protected Batch link:\nhttps://t.me{temp.U_NAME}?start=DSTORE-{b_64}")

    start_id = min(first_msg_id, last_msg_id)
    end_id = max(first_msg_id, last_msg_id)
    total_messages = (end_id - start_id) + 1

    FRMT = "Generating Link...\nTotal Messages: `{total}`\nDone: `{current}`\nRemaining: `{rem}`\nStatus: `{sts}`"
    outlist = []
    og_msg = 0
    tot = 0

    try:
        async for msg in bot.get_chat_history(chat_id=f_chat_id, offset_id=end_id + 1):
            if msg.id < start_id:
                break
                
            tot += 1
            if msg.empty or msg.service:
                continue
            if not msg.media:
                continue
                
            try:
                file_type = msg.media
                file = getattr(msg, file_type.value)
                caption = getattr(msg, 'caption', '')
                if caption:
                    caption = caption.html
                if file:
                    file = {
                        "file_id": file.file_id,
                        "caption": caption,
                        "title": getattr(file, "file_name", ""),
                        "size": file.file_size,
                        "protect": True,  # Protect Content എനേബിൾഡ്
                    }
                    og_msg += 1
                    outlist.append(file)
            except Exception:
                pass
                
            if not tot % 20:
                try:
                    await sts.edit(FRMT.format(total=total_messages, current=tot, rem=max(0, total_messages - tot), sts="Saving Messages"))
                except Exception:
                    pass

        if not outlist:
            return await sts.edit("ഈ പരിധിയിൽ സപ്പോർട്ട് ചെയ്യുന്ന മീഡിയ ഫയലുകൾ ഒന്നും കണ്ടെത്താൻ കഴിഞ്ഞില്ല.")

        json_path = f"batchmode_{user_id}.json"
        with open(json_path, "w+") as out:
            json.dump(outlist, out)
            
        # ഫയൽ ലോഗ് ചാനലിലേക്ക് അയക്കുന്നു
        post = await bot.send_document(LOG_CHANNEL, json_path, file_name="Batch.json", caption="⚠️ Protected Batch Generated via forward.")
        
        if os.path.exists(json_path):
            os.remove(json_path)
            
        file_id, ref = unpack_new_file_id(post.document.file_id)
        await sts.edit(f"🔒 Here is your Protected Link\nContains `{og_msg}` files.\n https://t.me/{temp.U_NAME}?start=BATCH-{file_id}")

    except Exception as e:
        await sts.edit(f"Error സംഭവിച്ചു: {e}")

# ക്യാൻസൽ ചെയ്യാനുള്ള കമാൻഡ്
@Client.on_message(filters.command('cancel') & filters.create(allowed))
async def cancel_batch(bot, message):
    user_id = message.from_user.id
    if user_id in ADMIN_BATCH_STATE:
        del ADMIN_BATCH_STATE[user_id]
        await message.reply("❌ നിലവിലുള്ള ബാച്ച് പ്രോസസ്സ് റദ്ദാക്കിയിരിക്കുന്നു.")
    else:
        await message.reply("നിങ്ങൾ നിലവിൽ ബാച്ച് ഒന്നും ചെയ്യുന്നില്ല.")

