import os
import logging
import random
import sys
import asyncio
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait, MessageDeleteForbidden
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from asyncio import sleep
from pyrogram.enums import ChatType
from database.ia_filterdb import Media, Mediaa, get_file_details, unpack_new_file_id, delete_files_below_threshold
from database.users_chats_db import db
from info import CHANNELS, ADMINS, REQ_CHANNEL1, REQ_CHANNEL2, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, DATABASE_URI, DATABASE_NAME
from utils import get_settings, get_size, is_subscribed, is_requested_one, is_requested_two, save_group_settings, temp, check_loop_sub, check_loop_sub1, check_loop_sub2
from database.connections_mdb import active_connection
from plugins.pm_filter import auto_filter
import re
import json
import base64
import pymongo
logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv("./dynamic.env", override=True, encoding="utf-8")

BATCH_FILES = {}
DS_REACT = ["⚡"]

should_run_check_loop_sub = False
should_run_check_loop_sub1 = False

inclient = pymongo.MongoClient(DATABASE_URI)
indb = inclient[DATABASE_NAME]
incol = indb['auto_del']
infile = indb['file_reply_text']
restarti = indb['restart']


# ⏱️ Auto delete time in seconds (e.g., 600 seconds = 10 minutes)
AUTO_DELETE_TIME = 180

# 📝 Short Warning Message Template in Blockquote
AUTO_DEL_TEXT = (
    "<blockquote>⚠️ <b>This file will be deleted in 3 mins. Forward to Saved Messages now!</b>\n\n"
    "<i>കോപ്പിറൈറ്റ് ഒഴിവാക്കാൻ ഈ ഫയൽ 3 മിനിറ്റിനുള്ളിൽ ഡിലീറ്റ് ആകും. ഉടൻ തന്നെ Saved Messages-ലേക്ക് Forward ചെയ്യുക!</i></blockquote>"
)





async def admin_check(message: Message) -> bool:
    if not message.from_user: return False
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]: return False
    if message.from_user.id in [777000, 1087968824]: return True
    client = message._client
    chat_id = message.chat.id
    user_id = message.from_user.id
    check_status = await client.get_chat_member(chat_id=chat_id, user_id=user_id)
    admin_strings = [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
    if check_status.status not in admin_strings: return False
    else: return True      
    
def convert_time_to_seconds(time_str):
    if time_str.endswith("s"):
        return int(time_str[:-1])
    elif time_str.endswith("m"):
        return int(time_str[:-1]) * 60
    elif time_str.endswith("h"):
        return int(time_str[:-1]) * 3600
    else:
        return 0



# 🗑️ Function to delete messages safely after delay
async def auto_delete_messages(client, chat_id, message_ids, delay):
    await asyncio.sleep(delay)
    for msg_id in message_ids:
        try:
            await client.delete_messages(chat_id=chat_id, message_ids=msg_id)
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                await client.delete_messages(chat_id=chat_id, message_ids=msg_id)
            except Exception: pass
        except Exception: pass



async def send_file(client, query, ident, file_id):
    from pyrogram.errors import UserIsBlocked
    files_ = await get_file_details(file_id)
    if not files_:
        return
    files = files_[0]
    title = files.file_name
    size = get_size(files.file_size)
    f_caption = files.file_name
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption, mention=query.from_user.mention)
        except Exception as e:
            logger.exception(e)
            f_caption = f_caption
    if f_caption is None:
        f_caption = f"{title}"

    # 🛠️ കാപ്ഷന്റെ കൂടെ ഓട്ടോ ഡിലീറ്റ് ടെക്സ്റ്റ് Quote ആയി ചേർക്കുന്നു
    final_caption = f"{f_caption}\n\n{AUTO_DEL_TEXT}"

    try:
        # 1. Send File with quote caption
        ok = await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=final_caption,
            parse_mode=enums.ParseMode.HTML,
            protect_content=True if ident == 'checksubp' else False
        )
        
        # 2. Trigger Auto Delete Task (ഫയൽ മെസ്സേജ് ഐഡി മാത്രം പാസ്സ് ചെയ്യുന്നു)
        asyncio.create_task(auto_delete_messages(client, query.from_user.id, [ok.id], AUTO_DELETE_TIME))
        
    except UserIsBlocked:
        logger.warning(f"യൂസർ ({query.from_user.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. ഫയൽ അയക്കാൻ കഴിഞ്ഞില്ല.")
    except Exception as e:
        logger.error(f"ഫയൽ അയക്കുന്നതിൽ പരാജയപ്പെട്ടു: {e}")

    
   
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):   
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        # ഗ്രൂപ്പിൽ റീപ്ലേ നൽകുന്നതും ലോഗ് ചാനലിലേക്ക് അയക്കുന്നതും ഒഴിവാക്കി
        await asyncio.sleep(2) 
        if not await db.get_chat(message.chat.id):
            await db.add_chat(message.chat.id, message.chat.title)
        return 
        
    # ബോട്ടിന്റെ PM (Private)-ൽ മാത്രം താഴെയുള്ള ഭാഗം പ്രവർത്തിക്കും
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        # ഇവിടെയുണ്ടായിരുന്ന ലോഗ് ചാനൽ മെസ്സേജ് ഒഴിവാക്കി
        
    if len(message.command) != 2:
        buttons = [
            [
                InlineKeyboardButton('👥 Jᴏɪɴ Oᴜʀ Gʀᴏᴜᴘ 👥', url='https://t.me/+eb__Eg3RS2IyZWQ1')
            ],
            [
                InlineKeyboardButton('📊 Sᴛᴀᴛs 📊', callback_data='stats'),
                InlineKeyboardButton('✖️ Cʟᴏsᴇ ✖️', callback_data='close_data')
            ]
        ]       
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(            
            text=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return       
    if REQ_CHANNEL1 and not await is_requested_one(client, message):
        btn = [[
            InlineKeyboardButton(
                "✦ 𝑱𝑶𝑰𝑵 𝑼𝑷𝑫𝑨𝑻𝑬 𝑪𝑯𝑨𝑵𝑵𝑬𝑳 I✦", url=client.req_link1)
        ]]
        global should_run_check_loop_sub1, should_run_check_loop_sub
        should_run_check_loop_sub1 = True
        should_run_check_loop_sub = False
        
        pre = 'checksub'
        file_id = None
        
        try:
            if REQ_CHANNEL2 and not await is_requested_two(client, message):
                btn.append([
                    InlineKeyboardButton(
                        "✦ 𝑱𝑶𝑰𝑵 𝑼𝑷𝑫𝑨𝑻𝑬 𝑪𝑯𝑨𝑵𝑵𝑬𝑳 II✦", url=client.req_link2)
                ])
                should_run_check_loop_sub = True                      
        except Exception as e:
            print(e)
            
        if len(message.command) > 1 and message.command[1] != "subscribe": 
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("⟲ 𝘛𝘳𝘺 𝘈𝘨𝘢𝘪𝘯 ⟳", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("⟲ 𝘛𝘳𝘺 𝘈𝘨𝘢𝘪𝘯 ⟳", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        
        sh = await client.send_message(
            chat_id=message.from_user.id,
            text=script.JOIN_TXT,
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        
        check = False
        if should_run_check_loop_sub:
            check = await check_loop_sub(client, message)
        elif should_run_check_loop_sub1:
            check = await check_loop_sub1(client, message)
            
        if check and file_id:     
            await send_file(client, message, pre, file_id)
            await sh.delete()        
            return
        else:
            return False           
            
    if REQ_CHANNEL2 and not await is_requested_two(client, message):
        btn = [[
            InlineKeyboardButton(
                "Update Channel 2", url=client.req_link2)
        ]]
        
        pre = 'checksub'
        file_id = None
        
        if len(message.command) > 1 and message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("⟲ 𝘛𝘳𝘺 𝘈𝘨𝘢𝘪𝘯 ⟳", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("⟲ 𝘛𝘳𝘺 𝘈𝘨𝘢𝘪𝘯 ⟳", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        
        sh = await client.send_message(
            chat_id=message.from_user.id,
            text=script.JOIN_TXT,
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        check = await check_loop_sub2(client, message)
        if check and file_id:
            await send_file(client, message, pre, file_id)
            await sh.delete()     
            return 
        else:
            return False
    if len(message.command) == 2 and message.command[1].startswith('getfile'):
        searches = message.command[1].split("-", 1)[1] 
        search = searches.replace('-',' ')
        message.text = search 
        await auto_filter(client, message) 
        return
         
    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [
            [
                InlineKeyboardButton('👥 Jᴏɪɴ Oᴜʀ Gʀᴏᴜᴘ 👥', url='https://t.me/+eb__Eg3RS2IyZWQ1')
            ],
            [
                InlineKeyboardButton('📊 Sᴛᴀᴛs 📊', callback_data='stats'),
                InlineKeyboardButton('✖️ Cʟᴏsᴇ ✖️', callback_data='close_data')
            ]
        ]       
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(            
            text=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return
    data = message.command[1]
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
        
    from pyrogram.errors import UserIsBlocked

    
    if data.split("-", 1)[0] == "BATCH":
        try:
            sts = await message.reply("Please wait")
        except UserIsBlocked:
            logger.warning(f"യൂസർ ({message.from_user.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. ബാച്ച് പ്രോസസ്സ് തുടങ്ങാൻ കഴിഞ്ഞില്ല.")
            return
            
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                try: await sts.edit("FAILED")
                except: pass
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
            
        # 📂 ബാച്ചായി അയക്കുന്ന ഫയലുകളുടെ മെസ്സേജ് ഐഡികൾ സൂക്ഷിക്കാൻ ലിസ്റ്റ്
        batch_msg_ids = []
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            
            # 🛠️ ഫയൽ കാപ്ഷന്റെ കൂടെ ഓട്ടോ ഡിലീറ്റ് ടെക്സ്റ്റ് Quote ആയി ചേർക്കുന്നു
            final_caption = f"{f_caption}\n\n{AUTO_DEL_TEXT}"
            
            try:
                b_msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=final_caption,
                    parse_mode=enums.ParseMode.HTML, # HTML എങ്കിൽ മാത്രമേ blockquote വർക്ക് ചെയ്യൂ
                    protect_content=msg.get('protect', False),
                    )
                if b_msg:
                    batch_msg_ids.append(b_msg.id) # ഐഡി ലിസ്റ്റിലേക്ക് ചേർക്കുന്നു
            except FloodWait as e:
                await asyncio.sleep(e.x)
                logger.warning(f"Floodwait of {e.x} sec.")
                try:
                    b_msg = await client.send_cached_media(
                        chat_id=message.from_user.id,
                        file_id=msg.get("file_id"),
                        caption=final_caption,
                        parse_mode=enums.ParseMode.HTML,
                        protect_content=msg.get('protect', False),
                        )
                    if b_msg:
                        batch_msg_ids.append(b_msg.id)
                except UserIsBlocked:
                    logger.warning(f"യൂസർ ({message.from_user.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. ഫ്ലഡ്‌വൈറ്റിന് ശേഷം ബാച്ച് മീഡിയ അയക്കാൻ കഴിഞ്ഞില്ല.")
                    break
                except Exception: continue
            except UserIsBlocked:
                logger.warning(f"യൂസർ ({message.from_user.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. ബാച്ച് മീഡിയ അയക്കാൻ കഴിഞ്ഞില്ല.")
                break 
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
            
        # ⏳ ബാച്ച് ഫയലുകൾ ഒന്നിച്ച് ഡിലീറ്റ് ചെയ്യാൻ നൽകുന്നു (സെപ്പറേറ്റ് വാർണിംഗ് മെസ്സേജ് ഒഴിവാക്കി)
        if batch_msg_ids:
            try:
                # 🗑️ സുരക്ഷിതമായ ബാക്ക്ഗ്രൗണ്ട് ടാസ്ക് വഴി എല്ലാ ഫയലുകളും ഒന്നിച്ച് ഡിലീറ്റ് ചെയ്യാൻ നൽകുന്നു
                asyncio.create_task(auto_delete_messages(client, message.from_user.id, batch_msg_ids, AUTO_DELETE_TIME))
            except Exception as e:
                logger.error(f"Error in BATCH auto-delete task: {e}")
                
        try: await sts.delete()
        except: pass
        return


        
    elif data.split("-", 1)[0] == "DSTORE":
        try:
            sts = await message.reply("Please wait")
        except UserIsBlocked:
            logger.warning(f"യൂസർ ({message.from_user.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. DSTORE പ്രോസസ്സ് തുടങ്ങാൻ കഴിഞ്ഞില്ല.")
            return
            
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        diff = int(l_msg_id) - int(f_msg_id)
        
        # 📂 അയക്കുന്ന ഫയലുകളുടെ മെസ്സേജ് ഐഡികൾ ശേഖരിക്കാൻ ഒരു ലിസ്റ്റ്
        dstore_msg_ids = []
        
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            copied_msg = None
            if msg.media:
                # 🛠️ ഫിക്സ്: Enum/None മൂലമുണ്ടാകുന്നTypeError ഒഴിവാക്കാൻ സ്ട്രിങ് വാല്യൂ കൃത്യമായി എടുക്കുന്നു
                media_type = msg.media.value if hasattr(msg.media, "value") else str(msg.media)
                media = getattr(msg, media_type, None) if media_type else None
                
                if media:
                    if BATCH_FILE_CAPTION:
                        try:
                            f_caption=BATCH_FILE_CAPTION.format(file_name=getattr(media, 'file_name', ''), file_size=getattr(media, 'file_size', ''), file_caption=getattr(msg, 'caption', ''))
                        except Exception as e:
                            logger.exception(e)
                            f_caption = getattr(msg, 'caption', '')
                    else:
                        file_name = getattr(media, 'file_name', '')
                        f_caption = getattr(msg, 'caption', file_name)
                    
                    # 🛠️ ഫയൽ കാപ്ഷന്റെ കൂടെ ഓട്ടോ ഡിലീറ്റ് ടെക്സ്റ്റ് Quote ആയി ചേർക്കുന്നു
                    final_caption = f"{f_caption}\n\n{AUTO_DEL_TEXT}"
                        
                    try:
                        copied_msg = await msg.copy(message.chat.id, caption=final_caption, parse_mode=enums.ParseMode.HTML, protect_content=True if protect == "/pbatch" else False)
                        if copied_msg:
                            dstore_msg_ids.append(copied_msg.id)
                    except FloodWait as e:
                        await asyncio.sleep(e.x)
                        copied_msg = await msg.copy(message.chat.id, caption=final_caption, parse_mode=enums.ParseMode.HTML, protect_content=True if protect == "/pbatch" else False)
                        if copied_msg:
                            dstore_msg_ids.append(copied_msg.id)
                    except UserIsBlocked:
                        logger.warning(f"യൂസർ ({message.chat.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. ബാച്ച് ഫയൽ കോപ്പി ചെയ്യാൻ കഴിഞ്ഞില്ല.")
                        break
                    except Exception as e:
                        logger.exception(e)
                        continue
            elif msg.empty:
                continue
            else:
                # മീഡിയ അല്ലാത്ത സാധാ ടെക്സ്റ്റ് മെസ്സേജുകൾക്ക് ഇവിടെ ഫോട്ടോ കാപ്ഷൻ പോലെ ചെയ്യാൻ പറ്റാത്തതിനാൽ പഴയ രീതിയിൽ കോപ്പി ചെയ്യുന്നു
                try:
                    copied_msg = await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                    if copied_msg:
                        dstore_msg_ids.append(copied_msg.id)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    copied_msg = await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                    if copied_msg:
                        dstore_msg_ids.append(copied_msg.id)
                except UserIsBlocked:
                    logger.warning(f"യൂസർ ({message.chat.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. ബാച്ച് മെസ്സേജ് കോപ്പി ചെയ്യാൻ കഴിഞ്ഞില്ല.")
                    break
                except Exception as e:
                    logger.exception(e)
                    continue
            await asyncio.sleep(1) 
            
        # ⏳ ഫയലുകൾ കോപ്പി ചെയ്ത് കഴിഞ്ഞാൽ ഒന്നിച്ച് ഡിലീറ്റ് ചെയ്യാൻ നൽകുന്നു (സെപ്പറേറ്റ് വാർണിംഗ് മെസ്സേജ് ഒഴിവാക്കി)
        if dstore_msg_ids:
            try:
                # 🗑️ ബാക്ക്ഗ്രൗണ്ട് ടാസ്ക് വഴി എല്ലാ ഫയലുകളും ഒന്നിച്ച് ഡിലീറ്റ് ചെയ്യാൻ നൽകുന്നു
                asyncio.create_task(auto_delete_messages(client, message.chat.id, dstore_msg_ids, AUTO_DELETE_TIME))
            except Exception as e:
                logger.error(f"Error in DSTORE auto-delete task: {e}")
                
        return await sts.delete()



        
    files_ = await get_file_details(file_id)           
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        try:
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=True if pre == 'filep' else False,
                )
            
            # 🛠️ ഫിക്സ്: Enum/None എറർ വരാതിരിക്കാൻ സ്ട്രിങ് വാല്യൂവിലേക്ക് മാറ്റുന്നു
            if msg.media:
                filetype = msg.media.value if hasattr(msg.media, "value") else str(msg.media)
                file = getattr(msg, filetype, None)
            else:
                file = None

            if not file:
                return await message.reply('No such file exist.')

            title = file.file_name
            size=get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption, mention=message.from_user.mention)    
                except:
                    return
            
            # 🛠️ സിംഗിൾ കാഷെ ഫയൽ കാപ്ഷൻ എഡിറ്റ് ചെയ്യുമ്പോൾ വാർണിങ് Quote ആയി ചേർക്കുന്നു
            final_caption = f"{f_caption}\n\n{AUTO_DEL_TEXT}"
            await msg.edit_caption(final_caption, parse_mode=enums.ParseMode.HTML)            
            
            # ഫയൽ മാത്രം ഡിലീറ്റ് ചെയ്യാൻ നൽകുന്നു (സെപ്പറേറ്റ് വാർണിങ് മെസ്സേജ് ഒഴിവാക്കി)
            asyncio.create_task(auto_delete_messages(client, message.from_user.id, [msg.id], AUTO_DELETE_TIME))
            return
        except UserIsBlocked:
            logger.warning(f"യൂസർ ({message.from_user.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു. കാഷെഡ് മീഡിയ അയക്കാൻ കഴിഞ്ഞില്ല.")
            return
        except Exception:
            pass
        return await message.reply('No such file exist.')
        
    files = files_[0]
    title = files.file_name
    size=get_size(files.file_size)
    f_caption=files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption, mention=message.from_user.mention)
        except Exception as e:
            logger.exception(e)
            f_caption = f_caption

    if f_caption is None:
        f_caption = f"{title}"

    # 🛠️ സാധാരണ ഫയൽ അയക്കുമ്പോഴും കാപ്ഷന്റെ കൂടെ ഓട്ടോ ഡിലീറ്റ് ടെക്സ്റ്റ് Quote ആയി ചേർക്കുന്നു
    final_caption = f"{f_caption}\n\n{AUTO_DEL_TEXT}"

    try:
        xd = await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=file_id,
            caption=final_caption,
            parse_mode=enums.ParseMode.HTML,
            protect_content=True if pre == 'filep' else False
        )
        
        # ഫയൽ മാത്രം ഡിലീറ്റ് ചെയ്യാൻ നൽകുന്നു
        asyncio.create_task(auto_delete_messages(client, message.from_user.id, [xd.id], AUTO_DELETE_TIME))
    except UserIsBlocked:
        logger.warning(f"യൂസർ ({message.from_user.id}) ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുന്നു.")
    except Exception as e:
        logger.error(f"മെസ്സേജ് അയക്കുന്നതിൽ പരാജയപ്പെട്ടു: {e}")


    
    
@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
           
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('TelegramBot.log')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Reply to the file with /delete that you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not a supported file format')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    # Check if the file exists in Media collection
    result_media = await Media.collection.find_one({'_id': file_id})

    # Check if the file exists in Mediaa collection
    result_mediaa = await Mediaa.collection.find_one({'_id': file_id})   

    if result_media and result_mediaa:
        await Media.collection.delete_one({'_id': file_id})
        await Mediaa.collection.delete_one({'_id': file_id})
        
    if result_media:
        # Delete from Media collection
        await Media.collection.delete_one({'_id': file_id})
    elif result_mediaa:
        # Delete from Mediaa collection
        await Mediaa.collection.delete_one({'_id': file_id})
    else:
        # File not found in both collections
        await msg.edit('File not found in the database')
        return

    await msg.edit('File is successfully deleted from the database')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue??',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="YES", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CANCEL", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await Mediaa.collection.drop()
    await message.answer('Piracy Is Crime')
    await message.message.edit('Succesfully Deleted All The Indexed Files.')



@Client.on_message(filters.command('restart') & filters.user(ADMINS))
async def restart(b, m):
    if os.path.exists(".git"):
        os.system("git pull")

    oo = await m.reply_text("Restarting...")
    await oo.delete()
    try:
        os.remove("TelegramBot.txt")
    except:
        pass
    os.execl(sys.executable, sys.executable, "bot.py")


            

@Client.on_message(filters.command("setchat1") & filters.user(ADMINS))
async def add_fsub_chats(bot: Client, update: Message):
    await update.react("🌭")
    chat = update.command[1] if len(update.command) > 1 else None
    if not chat:
        await update.reply_text("Invalid chat id.", quote=True)
        return
    else:
        chat = int(chat)
    await db.add_fsub_chat(chat)

    text = f"Added chat <code>{chat}</code> to the database."
    await update.reply_text(text=text, quote=True, parse_mode=enums.ParseMode.HTML)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL1={chat}\n")
    restarti.update_one(
        {"_id": "frestart"},
        {"$set": {"restart": "on"}},
        upsert=True
    )
    os.execl(sys.executable, sys.executable, "bot.py")


@Client.on_message(filters.command("delchat1") & filters.user(ADMINS))
async def clear_fsub_chats(bot: Client, update: Message):
    await update.react("👍")
    await db.delete_fsub_chat(chat_id=(await db.get_fsub_chat())['chat_id'])
    await update.reply_text(text="Deleted fsub chat from the database.", quote=True)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL1=False\n")

    logger.info("Restarting to update REQ_CHANNEL from database...")
    os.execl(sys.executable, sys.executable, "bot.py")
    
@Client.on_message(filters.command("viewchat1") & filters.user(ADMINS))
async def get_fsub_chat(bot: Client, update: Message):
    await update.react("👍")
    chat = await db.get_fsub_chat()
    if not chat:
        await update.reply_text("No fsub chat found in the database.", quote=True)
        return
    else:
        await update.reply_text(f"Fsub chat: <code>{chat['chat_id']}</code>", quote=True, parse_mode=enums.ParseMode.HTML)
        
@Client.on_message(filters.command("setchat2") & filters.user(ADMINS))
async def add_fsub_chats2(bot: Client, update: Message):
    await update.react("🍌")
    chat = update.command[1] if len(update.command) > 1 else None
    if not chat:
        await update.reply_text("Invalid chat id.", quote=True)
        return
    else:
        chat = int(chat)
    await db.add_fsub_chat2(chat)

    text = f"Added chat <code>{chat}</code> to the database."
    await update.reply_text(text=text, quote=True, parse_mode=enums.ParseMode.HTML)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL2={chat}\n")
    restarti.update_one(
        {"_id": "frestart"},
        {"$set": {"restart": "on"}},
        upsert=True
    )
    os.execl(sys.executable, sys.executable, "bot.py")


@Client.on_message(filters.command("delchat2") & filters.user(ADMINS))
async def clear_fsub_chats2(bot: Client, update: Message):
    await update.react("👍")
    await db.delete_fsub_chat2(chat_id=(await db.get_fsub_chat2())['chat_id'])
    await update.reply_text(text="Deleted fsub chat from the database.", quote=True)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL2=False\n")

    logger.info("Restarting to update REQ_CHANNEL from database...")
    os.execl(sys.executable, sys.executable, "bot.py")
    
@Client.on_message(filters.command("viewchat2") & filters.user(ADMINS))
async def get_fsub_chat2(bot: Client, update: Message):
    await update.react("👍")
    chat = await db.get_fsub_chat2()
    if not chat:
        await update.reply_text("No fsub chat found in the database.", quote=True)
        return
    else:
        await update.reply_text(f"Fsub chat: <code>{chat['chat_id']}</code>", quote=True, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS))
async def deletemultiplefiles(bot, message):
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, Tʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴡᴏɴ'ᴛ ᴡᴏʀᴋ ɪɴ ɢʀᴏᴜᴘs. Iᴛ ᴏɴʟʏ ᴡᴏʀᴋs ᴏɴ ᴍʏ PM!</b>")
    else:
        pass
    try:
        keyword = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, Gɪᴠᴇ ᴍᴇ ᴀ ᴋᴇʏᴡᴏʀᴅ ᴀʟᴏɴɢ ᴡɪᴛʜ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ғɪʟᴇs.</b>")
    btn = [[
       InlineKeyboardButton("Yᴇs, Cᴏɴᴛɪɴᴜᴇ !", callback_data=f"killfilesdq#{keyword}")
       ],[
       InlineKeyboardButton("Nᴏ, Aʙᴏʀᴛ ᴏᴘᴇʀᴀᴛɪᴏɴ !", callback_data="close_data")
    ]]
    await message.reply_text(
        text="<b>Aʀᴇ ʏᴏᴜ sᴜʀᴇ? Dᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ?\n\nNᴏᴛᴇ:- Tʜɪs ᴄᴏᴜʟᴅ ʙᴇ ᴀ ᴅᴇsᴛʀᴜᴄᴛɪᴠᴇ ᴀᴄᴛɪᴏɴ!</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )
    
@Client.on_message(filters.command("deletesmallfiles") & filters.user(ADMINS))
async def process_command(client, message):
    chat_id = message.chat.id
    processing_message = await message.reply_text("<b>Processing: Deleting files...</b>")
    
    total_files_deleted = 0
    batch_size = 250

    while True:
        deleted_files = await delete_files_below_threshold(db, threshold_size_mb=50, batch_size=batch_size)
        
        if deleted_files == 0:
            break

        total_files_deleted += deleted_files

        # Update the message to show progress
        progress_message = f'<b>Processing: Deleted {total_files_deleted} files in {total_files_deleted // batch_size} batches.</b>'
        await processing_message.edit_text(progress_message)
        await asyncio.sleep(3)

    print(f'Total files deleted: {total_files_deleted}')
    await processing_message.edit_text(f'<b>Deletion complete: Deleted {total_files_deleted} files.</b>')

@Client.on_message(filters.command("delete_duplicate") & filters.user(ADMINS))
async def delete_duplicate_files(client, message):
    ok = await message.reply("prosessing...")
    deleted_count = 0
    batch_size = 0
    async def remove_duplicates(collection1, unique_files, ok, deleted_count, batch_size):                        
        async for duplicate_file in collection1.find():
            file_size = duplicate_file["file_size"]
            file_id = duplicate_file["file_id"]
            if file_size in unique_files and unique_files[file_size] != file_id:
                result_media1 = await collection1.find_one({'_id': file_id})                
                if result_media1:
                    await collection1.collection.delete_one({'_id': file_id})               
                    deleted_count += 1                
                    if deleted_count % 100 == 0:
                        batch_size += 1
                        await ok.edit(f'<b>Processing: Deleted {deleted_count} files in {batch_size} batches.</b>')
        return deleted_count, batch_size
    # Get all four collections
    media1_collection = Media
    media2_collection = Mediaa
    
    # Get all files from each collection
    all_files_media1 = await media1_collection.find({}, {"file_id": 1, "file_size": 1}).to_list(length=None)
    all_files_media2 = await media2_collection.find({}, {"file_id": 1, "file_size": 1}).to_list(length=None)
    
    # Combine files from all collections
    all_files = all_files_media1 + all_files_media2

    # Remove duplicate files while keeping one copy
    unique_files = {}
    for file_info in all_files:
        file_id = file_info["file_id"]
        file_size = file_info["file_size"]
        if file_size not in unique_files:
            unique_files[file_size] = file_id

    # Delete duplicate files from each collection
    deleted_count, batch_size = await remove_duplicates(media1_collection, unique_files, ok, deleted_count, batch_size)
    deleted_count = deleted_count
    batch_size = batch_size
    deleted_count, batch_size = await remove_duplicates(media2_collection, unique_files, ok, deleted_count, batch_size)
    deleted_count = deleted_count
    batch_size = batch_size
    
    # Send a final message indicating the total number of duplicates deleted
    await message.reply(f"Deleted {deleted_count} duplicate files. in {batch_size} batches")
