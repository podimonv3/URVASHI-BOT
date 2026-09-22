import asyncio
lock = asyncio.Lock()
import re
import ast
import math
import ast  # eval-ന് പകരം സുരക്ഷിതമായി സ്ട്രിങ് ലിസ്റ്റ് ആക്കാൻ
import emoji  # ഇമോജികൾ നീക്കം ചെയ്യാൻ
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, REQ_CHANNEL1, REQ_CHANNEL2, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, \
    SINGLE_BUTTON, SPELL_CHECK_REPLY, LOG_CHANNEL
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, QueryIdInvalid
from utils import get_size, is_subscribed, temp, get_settings, save_group_settings, is_requested_one, is_requested_two
from database.users_chats_db import db
from database.ia_filterdb import Media, Mediaa, get_bad_files, get_file_details, get_search_results, db as clientDB, db1 as clientDB2, db2 as clientDB3
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
from database.gfilters_mdb import find_gfilter, get_gfilters
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# --- 🛠️ TELEGRAM ERROR FIXES START 🛠️ ---
_original_answer = CallbackQuery.answer
async def _patched_answer(self, *args, **kwargs):
    try:
        return await _original_answer(self, *args, **kwargs)
    except (QueryIdInvalid, FloodWait):  # 💡 FloodWait കൂടി ഇവിടെ ചേർത്തു
        pass
CallbackQuery.answer = _patched_answer
# --- 🛠️ TELEGRAM ERROR FIXES END 🛠️ ---

# --- 🛠️ ADVANCED MENUS CONFIGURATION (STYLISH FONTS) 🛠️ ---
LANGUAGES = [
    ("ᴍᴀʟᴀʏᴀʟᴀᴍ", "malayalam"),
    ("ᴛᴀᴍɪʟ", "tamil"),
    ("ᴇɴ🇬ʟɪsʜ", "english"),
    ("ʜɪɴᴅɪ", "hindi"),
    ("ᴛᴇʟᴜɢᴜ", "telugu"),
    ("ᴋᴀɴɴᴀᴅᴀ", "kannada"),
    ("🇵ᴘᴜɴᴊᴀʙɪ", "punjabi"),
    ("ʙᴇɴɢᴀʟɪ", "bengali"),
    ("ᴍᴀʀᴀᴛʜɪ", "marathi"),
    ("ʙʜᴏᴊᴘᴜʀɪ", "bhojpuri"),
    ("🔊 ᴅᴜᴀʟ ᴀᴜᴅɪᴏ", "dual"),
    ("🎵 ᴍᴜʟᴛɪ ᴀᴜᴅɪᴏ", "multi")
]

QUALITIES = ["360ᴘ", "480ᴘ", "720ᴘ", "1080ᴘ", "1440ᴘ", "2160ᴘ"]

# പ്രധാന ഫിൽട്ടർ മെനുവിന്റെ ഫോണ്ടും ഇമോജികളും (LANGUAGE, QUALITY, YEARS, SEASONS)
def get_filter_menu_buttons(req_id, key):
    return [
        [
            InlineKeyboardButton("ʟᴀɴɢᴜᴀɢе", callback_data=f"flm_langmenu_{req_id}_{key}"),
            InlineKeyboardButton("qᴜᴀʟɪᴛʏ", callback_data=f"flm_qualmenu_{req_id}_{key}")
        ],
        [
            InlineKeyboardButton("ʏᴇᴀʀꜱ", callback_data=f"flm_yearmenu_{req_id}_{key}"),
            InlineKeyboardButton("ꜱᴇᴀꜱᴏɴ‹›", callback_data=f"flm_seasonmenu_{req_id}_{key}")
        ]
    ]

def chunk_list(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]



BUTTONS = {}
SPELL_CHECK = {}


# =====================================================================
# 1. USER SIDE: HANDLES INCOMING PM MESSAGES (TEXT, PHOTO, VIDEO, STICKER)
# =====================================================================
@Client.on_message(filters.private & (filters.text | filters.photo | filters.video | filters.sticker) & filters.incoming)
async def pm_text(bot: Client, message):
    user_id = message.from_user.id
    user = message.from_user.first_name or "User"
    
    # കമാൻഡുകളും അഡ്മിൻ മെസ്സേജുകളും ഇഗ്നോർ ചെയ്യുന്നു
    if message.text and (message.text.startswith("/") or message.text.startswith("#")): return  
    if user_id in ADMINS: return 
    
    # 🔍 TEXT ONLY VALIDATION (ടെക്സ്റ്റ് മെസ്സേജുകൾക്ക് മാത്രം ഫോർമാറ്റ് പരിശോധിക്കുന്നു)
    if message.text:
        text_to_check = message.text.strip()
        # മെസ്സേജിന്റെ അവസാനം 1900-2029 വരെയുള്ള 4 അക്ക വർഷമുണ്ടോ എന്ന് നോക്കുന്നു
        if not re.search(r'\b(19\d{2}|20[0-2]\d)\b$', text_to_check):
            await bot.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
            await asyncio.sleep(0.5)
            
            # തെറ്റായ ഫോർമാറ്റിന് നൽകുന്ന മറുപടി അലെർട്ട്
            alert_msg = await message.reply_text(
                text=f"<b>❌ Wrong Format / തെറ്റായ ഫോർമാറ്റ്!\n\n"
                     f"Please send your request in this format:\n"
                     f"<code>Movie Name + Year</code>\n\n"
                     f"Example:\n"
                     f"<code>Kuruthi 2019</code>\n\n"
                     f"💡 സിനിമയുടെ പേരിനൊപ്പം വർഷം കൂടി ടൈപ്പ് ചെയ്ത് അയക്കുക.</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚸 MUST READ 🚸", url="http://telegra.ph/Request-%E0%B4%85%E0%B4%AF%E0%B4%95%E0%B4%95-%E0%B4%AE%E0%B4%A8%E0%B4%A8-%E0%B4%B5%E0%B4%AF%E0%B4%95%E0%B4%95%E0%B4%A3%E0%B4%9F%E0%B4%A8%E0%B4%A8%E0%B4%A4-08-19")] 
                ])
            )
            
            # 30 സെക്കൻഡിന് ശേഷം അലെർട്ട് മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുന്നു
            await asyncio.sleep(30)
            try:
                await bot.delete_messages(chat_id=message.chat.id, message_ids=[alert_msg.id])
            except Exception as e:
                logger.error(f"Error deleting alert message: {e}")
            return # കോഡ് ഇവിടെ അവസാനിക്കുന്നു, ലോഗ് ചാനലിലേക്ക് പോകില്ല.

    # ----------------------------------------------------
    # ശരിയായ ഫോർമാറ്റ് / മീഡിയ ഫയൽ ആണെങ്കിൽ മാത്രം താഴോട്ടുള്ള കോഡ് വർക്ക് ചെയ്യും
    # ----------------------------------------------------

    # മെസ്സേജിന്റെ ടൈപ്പ് അനുസരിച്ച് ഉള്ളടക്കം വേർതിരിക്കുന്നു (Text/Caption/Sticker)
    content = message.text or message.caption or (f"Sent a Sticker [{message.sticker.emoji}]" if message.sticker else "Media File")
    
    # 🔍 DATABASE SEARCH (ടെക്സ്റ്റ് മെസ്സേജ് ആണെങ്കിൽ ഡാറ്റാബേസിൽ ഉണ്ടോ എന്ന് പരിശോധിക്കുന്നു)
    files_found = False
    if message.text:
        search_query = message.text.strip()
        files, offset, total_results = await get_search_results(search_query.lower(), offset=0, filter=True)
        
        # ഡാറ്റാബേസിൽ ഫയലുകൾ കണ്ടെത്തുകയാണെങ്കിൽ
        if files:
            files_found = True
            await bot.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
            
            settings = await get_settings(message.chat.id)
            pre = 'filep' if settings['file_secure'] else 'file'
            
            # PM-ലെ മെസ്സേജുകൾക്കും തനതായ ഒരു ഐഡന്റിഫിക്കേഷൻ കീ നിർമ്മിക്കുന്നു
            key = f"{message.chat.id}-{message.id}"
            BUTTONS[key] = search_query
            
            # 🛠️ ഗ്രൂപ്പിലെ പോലെ തന്നെ PM-ലും മുകളിൽ അഡ്വാൻസ്‌ഡ് ഫിൽട്ടർ ബട്ടണുകൾ ആഡ് ചെയ്യുന്നു
            btn = get_filter_menu_buttons(user_id, key)
            
            if settings["button"]:
                for file in files[:10]: # ആദ്യത്തെ 10 ഫയലുകൾ ലിസ്റ്റ് ചെയ്യുന്നു
                    btn.append([InlineKeyboardButton(text=f"{get_size(file.file_size)}➪{file.file_name}", callback_data=f'{pre}#{file.file_id}')])
            else:
                for file in files[:10]:
                    btn.append([
                        InlineKeyboardButton(text=f"{file.file_name}", callback_data=f'{pre}#{file.file_id}'),
                        InlineKeyboardButton(text=f"{get_size(file.file_size)}", callback_data=f'{pre}#{file.file_id}')
                    ])
            
            # കൂടുതൽ ഫയലുകൾ ഉണ്ടെങ്കിൽ നെക്സ്റ്റ് പേജ് ബട്ടൺ അടിയിൽ ചേർക്കുന്നു
            if total_results > 10:
                btn.append([
                    InlineKeyboardButton(text=f"   𝟷 / {math.ceil(int(total_results) / 10)}", callback_data="pages"),
                    InlineKeyboardButton(text="ɴᴇxᴛ", callback_data=f"next_{user_id}_{key}_10")
                ])
                
            cap = f"<b><i><u>© can_Urvashi Theaters™️</u></i></b>"
            await message.reply_text(text=cap, reply_markup=InlineKeyboardMarkup(btn))


    # സിനിമ ഡാറ്റാബേസിൽ നിന്ന് കിട്ടിയിട്ടില്ലെങ്കിലോ അല്ലെങ്കിൽ ഇതൊരു മീഡിയ ഫയൽ ആണെങ്കിലോ പഴയ റിപ്ലൈ നൽകും
    if not files_found:
        await bot.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        await asyncio.sleep(0.5)
        
        reply_msg = await message.reply_text(
             text=f"<b>Your Request Has Been Submitted✅\n\nOTT Available Add Files With In 24Hrs.. Please Wait\n\nനിങ്ങളുടെ request അഡ്മിൻ അയച്ചിട്ടുണ്ട് ഫയൽസ് ഉണ്ടെങ്കിൽ 24മണിക്കൂറിനുള്ളിൽ ആഡ് ചെയ്യുന്നതാണ്</b>",   
             reply_markup=InlineKeyboardMarkup([
                 [InlineKeyboardButton("🚫 ANY ERROR REPORT 🚫 ", url="https://t.me/Adhityan_edavattom")],
                 [InlineKeyboardButton("🚸 MUST READ 🚸", url="http://telegra.ph/Request-%E0%B4%85%E0%B4%AF%E0%B4%95%E0%B4%95-%E0%B4%AE%E0%B4%A8%E0%B4%A8-%E0%B4%B5%E0%B4%AF%E0%B4%95%E0%B4%95%E0%B4%A3%E0%B4%9F%E0%B4%A8%E0%B4%A8%E0%B4%A4-08-19")] 
             ])
        )    
        
        # താത്കാലിക കൺഫർമേഷൻ മെസ്സേജ് 30 സെക്കൻഡിന് ശേഷം ഡിലീറ്റ് ചെയ്യാനുള്ള ടാസ്ക്
        async def auto_delete():
            await asyncio.sleep(30)
            try: await bot.delete_messages(chat_id=message.chat.id, message_ids=[reply_msg.id])
            except: pass
        asyncio.create_task(auto_delete())

    # ----------------------------------------------------
    # 📢 LOG CHANNEL SECTION (എല്ലാ ശരിയായ റിക്വസ്റ്റുകളും ലോഗ് ചെയ്യുന്നു)
    # ----------------------------------------------------
    log_reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 MESSAGE USER (DIRECT)", url=f"tg://user?id={user_id}")]
    ])
    
    # സിനിമ ഡാറ്റാബേസിൽ ഉണ്ടോ ഇല്ലയോ എന്ന സ്റ്റാറ്റസ് കൂടി ലോഗ് ടെക്സ്റ്റിൽ കാണിക്കുന്നു
    status_tag = " [FOUND IN DB 📁]" if files_found else " [NOT FOUND IN DB ❌]"
    log_text = f"<b>#PM_MSG{status_tag}\n\nNᴀᴍᴇ : <a href='tg://user?id={user_id}'>{user}</a>\n\nID : <code>{user_id}</code>\n\nMᴇssᴀɢᴇ :</b> <code>{content}</code>\n\n#id{user_id}"
    
    try:
        if message.photo:
            await bot.send_chat_action(chat_id=LOG_CHANNEL, action=enums.ChatAction.UPLOAD_PHOTO)
            await bot.send_photo(chat_id=LOG_CHANNEL, photo=message.photo.file_id, caption=log_text, reply_markup=log_reply_markup)
        elif message.video:
            await bot.send_chat_action(chat_id=LOG_CHANNEL, action=enums.ChatAction.UPLOAD_VIDEO)
            await bot.send_video(chat_id=LOG_CHANNEL, video=message.video.file_id, caption=log_text, reply_markup=log_reply_markup)
        elif message.sticker:
            await bot.send_message(chat_id=LOG_CHANNEL, text=log_text, reply_markup=log_reply_markup, disable_web_page_preview=True)
            await bot.send_sticker(chat_id=LOG_CHANNEL, sticker=message.sticker.file_id)
        else:
            await bot.send_chat_action(chat_id=LOG_CHANNEL, action=enums.ChatAction.TYPING)
            await bot.send_message(chat_id=LOG_CHANNEL, text=log_text, reply_markup=log_reply_markup, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error sending log to LOG_CHANNEL: {e}")



@Client.on_message(filters.chat(LOG_CHANNEL) & filters.reply)
async def admin_reply_to_user(bot: Client, message):
    parent_message = message.reply_to_message
    parent_text = parent_message.text or parent_message.caption
    
    if not parent_text:
        return
        
    pattern = r"#id(\d+)"
    match = re.search(pattern, parent_text)
    
    if match:
        user_id = int(match.group(1))
        # ക്യാപ്ഷൻ ഉണ്ടെങ്കിൽ അത് HTML ബോൾഡ് ഫോർമാറ്റിൽ എടുക്കുന്നു
        reply_caption = f"<b>{message.caption}</b>" if message.caption else ""
        
        try:
            if message.photo:
                await bot.send_chat_action(chat_id=user_id, action=enums.ChatAction.UPLOAD_PHOTO)
                await bot.send_photo(chat_id=user_id, photo=message.photo.file_id, caption=reply_caption)
            elif message.video:
                await bot.send_chat_action(chat_id=user_id, action=enums.ChatAction.UPLOAD_VIDEO)
                await bot.send_video(chat_id=user_id, video=message.video.file_id, caption=reply_caption)
            elif message.sticker:
                await bot.send_sticker(chat_id=user_id, sticker=message.sticker.file_id)
            elif message.text:
                await bot.send_chat_action(chat_id=user_id, action=enums.ChatAction.TYPING)
                await bot.send_message(
                    chat_id=user_id,
                    text=f"<b>💬 Message From Admin:\n\n{message.text}</b>"
                )
            else:
                return
                
            await message.reply_text("<b>✅ മറുപടി യൂസർക്ക് വിജയകരമായി അയച്ചു!</b>")
            
        except UserIsBlocked:
            await message.reply_text("<b>❌ മറുപടി അയക്കാൻ കഴിഞ്ഞില്ല! ഈ യൂസർ ബോട്ടിനെ ബ്ലോക്ക് ചെയ്തിരിക്കുകയാണ്.</b>")
        except PeerIdInvalid:
            await message.reply_text("<b>❌ ഈ യൂസറുമായി ബോട്ട് ഇതുവരെ ചാറ്റ് തുടങ്ങിയിട്ടില്ല (Peer ID Invalid).</b>")
        except Exception as e:
            logger.error(f"Admin reply forward error: {e}")
            await message.reply_text(f"<b>❌ മെസ്സേജ് അയക്കാൻ കഴിഞ്ഞില്ല!\nError: {e}</b>")


@Client.on_message(filters.text & filters.incoming)
async def give_filters(client, message):
    # രണ്ട് ഫങ്ക്ഷനുകളും ഒരേ സമയം ബാക്ക്ഗ്രൗണ്ടിൽ റൺ ചെയ്യാൻ ടാസ്കുകൾ ഉണ്ടാക്കുന്നു
    task1 = asyncio.create_task(global_filters(client, message))
    task2 = asyncio.create_task(auto_filter(client, message))
    
    # രണ്ട് ടാസ്കുകളും ഒരുമിച്ച് (Parallel ആയി) എക്സിക്യൂട്ട് ചെയ്യുന്നു
    # return_exceptions=True നൽകിയാൽ ഒരെണ്ണത്തിൽ എറർ വന്നാലും മറ്റേത് കൃത്യമായി വർക്ക് ചെയ്യും
    await asyncio.gather(task1, task2, return_exceptions=True)

        
@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer("Search for Yourself", show_alert=True)

    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    search = BUTTONS.get(key)
    if not search:
        await query.answer("You are using one of my old messages, please send the request again.", show_alert=True)
        return

    # മൾട്ടി ഫിൽട്ടർ ടാഗുകൾ ഉണ്ടെങ്കിൽ അവ ക്ലീൻ ചെയ്ത് ഡാറ്റാബേസ് സെർച്ചിന് പാകത്തിലാക്കുന്നു
    db_search = search
    if " [" in search:
        base = search.split(" [")[0]
        tags = search.split(" [")[1].replace("]", "").split(" + ")
        db_search = f"{base} {' '.join(tags)}"

    files, n_offset, total = await get_search_results(db_search.lower(), offset=offset, filter=True)

    if not files:
        await query.answer("no files", show_alert=True)
        return

    settings = await get_settings(query.message.chat.id)
    
    # 🛠️ ഫിക്സ്: അടുത്ത പേജുകളിലും മുകളിലെ അഡ്വാൻസ്ഡ് ഫിൽട്ടർ മെനു ബട്ടണുകൾ നിലനിർത്തുന്നു
    btn = get_filter_menu_buttons(req, key)

    pre = 'filep' if settings['file_secure'] else 'file'
    for file in files:
        btn.append([InlineKeyboardButton(text=f"{get_size(file.file_size)}➪{file.file_name}", callback_data=f'{pre}#{file.file_id}')])

    if 0 < offset < 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10

    if n_offset == '':
        btn.append([
            InlineKeyboardButton("Bᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
            InlineKeyboardButton(f"{math.ceil(offset / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages")
        ])
    elif off_set is None:
        btn.append([
            InlineKeyboardButton(f"{math.ceil(offset / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
            InlineKeyboardButton("Nᴇxᴛ", callback_data=f"next_{req}_{key}_{n_offset}")
        ])
    else:
        btn.append([
            InlineKeyboardButton("Bᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
            InlineKeyboardButton(f"{math.ceil(offset / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
            InlineKeyboardButton("Nᴇxᴛ", callback_data=f"next_{req}_{key}_{n_offset}")
        ])
        
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass
    except FloodWait as e:
        await query.answer(f"വളരെ വേഗത്തിലാണ്! ദയവായി {e.value} സെക്കൻഡ് കാത്തിരിക്കൂ.", show_alert=True)
        return
        
    await query.answer()
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    # =====================================================================
    # ADVANCED INLINE MENUS HANDLERS (ALL LIST ERRORS FULLY FIXED)
    # =====================================================================
    if query.data.startswith("flm_"):
        parts = query.data.split("_")
        action = parts[1]         # 💡 FIXED: Index 1 for action string
        req_user = int(parts[2])  # 💡 FIXED: Index 2 for user ID integer
        key = parts[3]            # 💡 FIXED: Index 3 for message unique key
        
        if req_user not in [query.from_user.id, 0]:
            return await query.answer("ഇത് നിങ്ങളുടെ സെർച്ച് റിസൾട്ട് അല്ല!", show_alert=True)
            
        search_query = BUTTONS.get(key)
        if not search_query:
            return await query.answer("സെർച്ച് എക്സ്പെയർ ആയി, ദയവായി വീണ്ടും സെർച്ച് ചെയ്യുക.", show_alert=True)
            
        # 1. QUALITY MENU
        if action == "qualmenu":
            buttons_list = []
            for q in QUALITIES:
                # 💡 FIXED: callback_data modified to pass single filter action cleanly
                buttons_list.append(InlineKeyboardButton(q, callback_data=f"flm_filter_{req_user}_{key}_{q.split()[-1].lower()}"))
            grid = chunk_list(buttons_list, 2)
            grid.append([InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data=f"flm_home_{req_user}_{key}")])
            try:
                await query.message.edit_text("ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ qᴜᴀʟɪᴛʏ", reply_markup=InlineKeyboardMarkup(grid), parse_mode=enums.ParseMode.HTML)
            except FloodWait as e:
                await query.answer(f"വേഗത കൂടുതലാണ്! ദയവായി {e.value} സെക്കൻഡ് കാത്തിരിക്കൂ.", show_alert=True)
                return
            except Exception: pass
            return await query.answer()
            
        # 2. LANGUAGES MENU
        elif action == "langmenu":
            buttons_list = []
            for name, code in LANGUAGES:
                buttons_list.append(InlineKeyboardButton(name, callback_data=f"flm_filter_{req_user}_{key}_{code}"))
            grid = chunk_list(buttons_list, 2)
            grid.append([InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data=f"flm_home_{req_user}_{key}")])
            try:
                await query.message.edit_text("ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ʟᴀɴɢᴜᴀɢеs", reply_markup=InlineKeyboardMarkup(grid), parse_mode=enums.ParseMode.HTML)
            except FloodWait as e:
                await query.answer(f"വേഗത കൂടുതലാണ്! ദയവായി {e.value} സെക്കൻഡ് കാത്തിരിക്കൂ.", show_alert=True)
                return
            except Exception: pass
            return await query.answer()

        # 3. YEARS MENU
        elif action == "yearmenu":
            buttons_list = []
            for year in range(1990, 2027):
                buttons_list.append(InlineKeyboardButton(f"{year}", callback_data=f"flm_filter_{req_user}_{key}_{year}"))
            grid = chunk_list(buttons_list, 4)
            grid.append([InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data=f"flm_home_{req_user}_{key}")])
            try:
                await query.message.edit_text("ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ʏᴇᴀʀ", reply_markup=InlineKeyboardMarkup(grid), parse_mode=enums.ParseMode.HTML)
            except FloodWait as e:
                await query.answer(f"വേഗത കൂടുതലാണ്! ദയവായി {e.value} സെക്കൻഡ് കാത്തിരിക്കൂ.", show_alert=True)
                return
            except Exception: pass
            return await query.answer()

        # 4. SEASONS MENU
        elif action == "seasonmenu":
            buttons_list = []
            for s in range(1, 11):
                buttons_list.append(InlineKeyboardButton(f"SEASON {s}", callback_data=f"flm_filter_{req_user}_{key}_s{s:02d}"))
            grid = chunk_list(buttons_list, 2)
            grid.append([InlineKeyboardButton("ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data=f"flm_home_{req_user}_{key}")])
            try:
                await query.message.edit_text("ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ꜱᴇᴀꜱᴏɴ", reply_markup=InlineKeyboardMarkup(grid), parse_mode=enums.ParseMode.HTML)
            except FloodWait as e:
                await query.answer(f"വേഗത കൂടുതലാണ്! ദയവായി {e.value} സെക്കൻഡ് കാത്തിരിക്കൂ.", show_alert=True)
                return
            except Exception: pass
            return await query.answer()

        # 5. HOME BUTTON
        elif action == "home":
            db_search = search_query
            if " [" in search_query:
                base = search_query.split(" [")[0]
                tags = search_query.split(" [")[1].replace("]", "").split(" + ")
                db_search = f"{base} {' '.join(tags)}"

            files, offset, total_results = await get_search_results(db_search.lower(), offset=0, filter=True)
            chat_id = query.message.chat.id if (query.message and query.message.chat) else query.from_user.id
            settings = await get_settings(chat_id)
            
            pre = 'filep' if settings['file_secure'] else 'file'
            btn = get_filter_menu_buttons(req_user, key)
            for file in files[:10]:
                btn.append([InlineKeyboardButton(text=f"{get_size(file.file_size)}➪{file.file_name}", callback_data=f'{pre}#{file.file_id}')])
            if total_results > 10:
                btn.append([
                    InlineKeyboardButton(text=f"𝟷 / {math.ceil(int(total_results) / 10)}", callback_data="pages"),
                    InlineKeyboardButton(text="ɴᴇxᴛ", callback_data=f"next_{req_user}_{key}_10")
                ])
            
            if " [" in search_query:
                btn.append([InlineKeyboardButton("🔄 RESET FILTERS", callback_data=f"flm_reset_{req_user}_{key}")])

            cap = f"<b><i>Here is What I Found For: {search_query}</i></b>"
            try:
                await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn))
            except FloodWait as e:
                await query.answer(f"വേഗത കൂടുതലാണ്! ദയവായി {e.value} സെക്കൻഡ് കാത്തിരിക്കൂ.", show_alert=True)
                return
            except Exception: pass
            return await query.answer()
            
        # 6. MULTI-FILTER SUB-BUTTON CLICKED (FIXED INDEX ENGINE)
        elif action == "filter":
            filter_tag = parts[4].lower() if len(parts) > 4 else ""  # 💡 FIXED: Index 4 for target filter word
            if not filter_tag:
                return await query.answer("❌ തെറ്റായ ഫിൽട്ടർ ടാഗ്!", show_alert=True)
            
            current_search = BUTTONS.get(key, "")
            
            if " [" in current_search:
                base_query = current_search.split(" [")[0]
                existing_tags = current_search.split(" [")[1].replace("]", "").split(" + ")
                
                if filter_tag not in existing_tags:
                    existing_tags.append(filter_tag)
                
                new_search_entry = f"{base_query} [{" + ".join(existing_tags)}]"
                db_search_query = f"{base_query} {" ".join(existing_tags)}"
            else:
                new_search_entry = f"{current_search} [{filter_tag}]"
                db_search_query = f"{current_search} {filter_tag}"
            
            BUTTONS[key] = new_search_entry
            files = []
            total_results = 0
            
            # സീസൺ വേരിയന്റുകൾ പരിശോധിക്കുന്നു (eg: season 1, s01)
            if re.match(r'^s\d{2}$', filter_tag):
                s_num = int(filter_tag[1:])
                search_variants = [
                    db_search_query,
                    f"{db_search_query.replace(filter_tag, '')} season {s_num}",
                    f"{db_search_query.replace(filter_tag, '')} season {s_num:02d}"
                ]
                for variant in search_variants:
                    res_files, _, res_total = await get_search_results(variant.lower(), offset=0, filter=True)
                    if res_files:
                        files.extend(res_files)
                        total_results += res_total
                        break
                        
            # ലാംഗ്വേജ് വേരിയന്റുകൾ പരിശോധിക്കുന്നു
            else:
                lang_variants = {
                    "malayalam": ["malayalam", "mal"],
                    "tamil": ["tamil", "tam"],
                    "english": ["english", "eng"],
                    "hindi": ["hindi", "hin"],
                    "telugu": ["telugu", "tel"],
                    "kannada": ["kannada", "kan"]
                }
                
                if filter_tag in lang_variants:
                    for variant in lang_variants[filter_tag]:
                        v_search = db_search_query.replace(filter_tag, variant)
                        res_files, _, res_total = await get_search_results(v_search.lower(), offset=0, filter=True)
                        if res_files:
                            files.extend(res_files)
                            total_results += res_total
                            break
                else:
                    res_files, _, res_total = await get_search_results(db_search_query.lower(), offset=0, filter=True)
                    if res_files:
                        files.extend(res_files)
                        total_results += res_total

            seen_ids = set()
            unique_files = []
            for f in files:
                if f.file_id not in seen_ids:
                    seen_ids.add(f.file_id)
                    unique_files.append(f)

            if not unique_files:
                BUTTONS[key] = current_search
                return await query.answer(f"❌ ഈ കോമ്പിനേഷനിൽ ഫയലുകൾ ഒന്നും കണ്ടെത്താനായില്ല!", show_alert=True)
                
            chat_id = query.message.chat.id if (query.message and query.message.chat) else query.from_user.id
            settings = await get_settings(chat_id)
            pre = 'filep' if settings['file_secure'] else 'file'
            
            btn = get_filter_menu_buttons(req_user, key)
            for file in unique_files[:10]:
                btn.append([InlineKeyboardButton(text=f"{get_size(file.file_size)}➪{file.file_name}", callback_data=f'{pre}#{file.file_id}')])
            
            btn.append([InlineKeyboardButton("🔄 RESET FILTERS", callback_data=f"flm_reset_{req_user}_{key}")])
            
            cap = f"<b><i>Filtered Results for: {new_search_entry.upper()}</i></b>"
            try:
                await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn))
            except FloodWait as e:
                await query.answer(f"വേഗത കൂടുതലാണ്! ദയവായി {e.value} സെക്കൻഡ് കാത്തിരിക്കൂ.", show_alert=True)
                return
            except Exception: pass
            return await query.answer()

        # 7. RESET BUTTON CLICKED
        elif action == "reset":
            current_search = BUTTONS.get(key, "")
            if " [" in current_search:
                current_search = current_search.split(" [")[0]
                BUTTONS[key] = current_search
                
            files, offset, total_results = await get_search_results(current_search.lower(), offset=0, filter=True)
            chat_id = query.message.chat.id if (query.message and query.message.chat) else query.from_user.id
            settings = await get_settings(chat_id)
            
            pre = 'filep' if settings['file_secure'] else 'file'
            btn = get_filter_menu_buttons(req_user, key)
            for file in files[:10]:
                btn.append([InlineKeyboardButton(text=f"{get_size(file.file_size)}➪{file.file_name}", callback_data=f'{pre}#{file.file_id}')])
            
            if total_results > 10:
                btn.append([
                    InlineKeyboardButton(text=f"𝟷 / {math.ceil(int(total_results) / 10)}", callback_data="pages"),
                    InlineKeyboardButton(text="ɴᴇxᴛ", callback_data=f"next_{req_user}_{key}_10")
                ])
                
            cap = f"<b><i>Here is What I Found In My Database For Your Query: {current_search}</i></b>"
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn))
            return await query.answer("Filters Cleared! 🔄", show_alert=True)    
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer('Piracy Is Crime')
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer('Piracy Is Crime')

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer('Piracy Is Crime')

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("That's not for you!!", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return await query.answer('Piracy Is Crime')
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer('Piracy Is Crime')
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('Piracy Is Crime')
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('Piracy Is Crime')
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer('Piracy Is Crime')
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True) 
            
    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.file_name
        
        # ⬇️ എറർ വരാതിരിക്കാൻ ഈ 2 വരികൾ പകരം ചേർക്കുക ⬇️
        chat_id = query.message.chat.id if (query.message and query.message.chat) else query.from_user.id
        settings = await get_settings(chat_id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption, mention=query.from_user.mention)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
            
        # ബട്ടണുകൾ ഉണ്ടായിരുന്ന ഭാഗം ഒഴിവാക്കി നേരിട്ട് PM-ലേക്ക് റീഡയറക്ട് ചെയ്യുന്നു
        try:
            if settings['botpm']:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
        except QueryIdInvalid:
            await query.answer("This query is no longer valid.", show_alert=True)
        except UserIsBlocked:
            await query.answer('Unblock the bot mahn !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
            
    elif query.data.startswith("checksub"):
        if REQ_CHANNEL1 and not await is_requested_one(client, query):
            await query.answer("CLICK  «➳ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺»", show_alert=True)
            return
        if REQ_CHANNEL2 and not await is_requested_two(client, query):
            await query.answer("Update Channel ജോയിൻ ആവുക", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
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

        await query.answer()
        
        # ഇവിടെ നിന്നും reply_markup (ബട്ടണുകൾ) ഒഴിവാക്കി
        xd = await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == "checksubp" else False
        )
        
        if title and any(keyword in title.lower() for keyword in ['predvd', 'predvdrip']):
            f_caption += "\n⚠️<b><i>ഈ മൂവിയുടെ ഫയൽ എവിടെയെങ്കിലും ഫോർവേഡ് ചെയ്തു വെക്കുക എന്നിട്ട് ഡൗൺലോഡ് ചെയ്യുക\n\n3 മിനിറ്റിൽ ഇവിടുന്ന് ഡിലീറ്റ് ആവും🗑\n\n⚠️Forward the file of this Movie somewhere and download it\n\nWill be deleted from here in 3 minutes🗑</i></b>"
            
            # എഡിറ്റ് ചെയ്യുമ്പോഴും ബട്ടണുകൾ വരാതിരിക്കാൻ reply_markup ഒഴിവാക്കി
            await xd.edit_caption(caption=f_caption)
            await asyncio.sleep(180)                   
            await xd.delete()


    elif query.data.startswith("killfilesdq"):
        ident, keyword = query.data.split("#")
        await query.message.edit_text(f"<b>Fᴇᴛᴄʜɪɴɢ Fɪʟᴇs ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} ᴏɴ DB... Pʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
        files_media1, files_media2, total_media = await get_bad_files(keyword)        
        await query.message.edit_text(f"<b>Fᴏᴜɴᴅ {total_media} Fɪʟᴇs ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} !\n\nFɪʟᴇ ᴅᴇʟᴇᴛɪᴏɴ ᴘʀᴏᴄᴇss ᴡɪʟʟ sᴛᴀʀᴛ ɪɴ 5 sᴇᴄᴏɴᴅs!</b>")
        await asyncio.sleep(5)
        deleted = 0
        async with lock:
            try:
                # Delete files from Media collection
                for file in files_media1:
                    file_ids = file.file_id
                    file_name = file.file_name
                    result = await Media.collection.delete_one({
                        '_id': file_ids,
                    })
                    if result.deleted_count:
                        logger.info(f'Fɪʟᴇ Fᴏᴜɴᴅ ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword}! Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {file_name} ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ.')
                    deleted += 1
                    if deleted % 100 == 0:
                        await query.message.edit_text(f"<b>Pʀᴏᴄᴇss sᴛᴀʀᴛᴇᴅ ғᴏʀ ᴅᴇʟᴇᴛɪɴɢ ғɪʟᴇs ғʀᴏᴍ DB. Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {str(deleted)} ғɪʟᴇs ғʀᴏᴍ DB ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} !\n\nPʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
                # Delete files from Mediaa collection
                for file in files_media2:
                    file_ids = file.file_id
                    file_name = file.file_name
                    result = await Mediaa.collection.delete_one({
                        '_id': file_ids,
                    })
                    if result.deleted_count:
                        logger.info(f'Fɪʟᴇ Fᴏᴜɴᴅ ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword}! Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {file_name} ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ.')
                    deleted += 1
                    if deleted % 100 == 0:
                        await query.message.edit_text(f"<b>Pʀᴏᴄᴇss sᴛᴀʀᴛᴇᴅ ғᴏʀ ᴅᴇʟᴇᴛɪɴɢ ғɪʟᴇs ғʀᴏᴍ DB. Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {str(deleted)} ғɪʟᴇs ғʀᴏᴍ DB ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} !\n\nPʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
            except Exception as e:
                logger.exception
                await query.message.edit_text(f'Eʀʀᴏʀ: {e}')
            else:
                await query.message.edit_text(f"<b>Pʀᴏᴄᴇss Cᴏᴍᴘʟᴇᴛᴇᴅ ғᴏʀ ғɪʟᴇ ᴅᴇʟᴇᴛɪᴏɴ !\n\nSᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {str(deleted)} ғɪʟᴇs ғʀᴏᴍ DB ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword}.</b>")
            
    elif query.data == "pages":
        await query.answer()
    
    elif query.data == "start":
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
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('ʙᴀᴄᴋ', callback_data='start')           
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)        
        
        tot = await Media.count_documents()
        tota = await Mediaa.count_documents()
        total = tot + tota
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        
        stats = await clientDB.command('dbStats')
        used_dbSize = (stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))        
        free_dbSize = 512-used_dbSize
        
        stats2 = await clientDB2.command('dbStats')
        used_dbSize2 = (stats2['dataSize']/(1024*1024))+(stats2['indexSize']/(1024*1024))
        free_dbSize2 = 512-used_dbSize2
        
        stats3 = await clientDB3.command('dbStats')
        used_dbSize3 = (stats3['dataSize']/(1024*1024))+(stats3['indexSize']/(1024*1024))
        free_dbSize3 = 512-used_dbSize3        
        
        stats_text = (
            "📊 <b>Bot Statistics</b>\n\n"
            f"▪️ Total Files: {total}\n"
            f"▪️ Main DB Files (Media): {tot}\n"
            f"▪️ DB 2 Files (Mediaa): {tota}\n\n"
            f"▪️ Total Users: {users}\n"
            f"▪️ Total Chats: {chats}\n\n"
            f"🗄 Database 1 Size: {round(used_dbSize2, 2)} MB / Free: {round(free_dbSize2, 2)} MB\n"
            f"🗄 Database 2 Size: {round(used_dbSize3, 2)} MB / Free: {round(free_dbSize3, 2)} MB\n"
            f"🗄 Database 3 Size: {round(used_dbSize, 2)} MB / Free: {round(free_dbSize, 2)} MB"
        )
        
        # 🛠️ എറർ ഒഴിവാക്കാനായി വരുത്തിയ മാറ്റം:
        try:
            # മീഡിയ മെസ്സേജ് ആണെങ്കിൽ അതിന്റെ ക്യാപ്ഷൻ എഡിറ്റ് ചെയ്യുന്നു
            await query.message.edit_caption(
                caption=stats_text,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            # അതല്ലെങ്കിൽ സാധാരണ പോലെ ടെക്സ്റ്റ് എഡിറ്റ് ചെയ്യുന്നു
            await query.message.edit_text(
                text=stats_text,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )

    
async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text): return
        if 0 < len(message.text) < 100:
            
            search = message.text
            search = re.sub(r'[\u200b\u200c\u200d\ufeff\u200e\u200f]', '', search)
            search = re.sub(r'[\s\u00a0\u2000-\u200a\u202f\u205f\u3000]+', ' ', search)
            search = re.sub(r"['‘’]", "", search)
            search = re.sub(r"[-–—_,#&?/( )\[\]\\\":\.¡%“”]", " ", search)
            search = re.sub(r"\b(hd|full|print|file)\b", "", search, flags=re.IGNORECASE)                       
                                
            find = search.lower().split(" ")
            removes = {
                "pls", "plz", "plzz", "please", "send", "snd", "snt",
                "gib", "veno", "venam", "venum",
                "undo", "ayakkumo", "ayakkamo", "und", "move", 
                "multi", "dubb", "dub", "bro", "bruh", "broh", "dubbed", "link", "lnk",
                "iruka", "pannunga", "pannungga", "anuppunga", "anupunga", "anuppungga", 
                "anupungga", "subtile", "kitti", "kitty", "tharu", "kittumo", "kittum",
                "da", "mwonse", "bhai", "share", "malayalm", "malylm", "subtitle"
            }
            search = " ".join([w for w in find if w not in removes])
            search = re.sub(r"\s+", " ", search).strip()
            
            if not search: return

            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            
            if not files:
                reqst_gle = search.replace(" ", "+")
                btn_google = InlineKeyboardButton("🔎 𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝗦𝗽𝗲𝗹𝗹𝗶𝗻𝗴 (𝖦𝗈𝗈𝗀𝗅𝖾) 🔍", url=f"https://www.google.com/search?q={reqst_gle}")
                btn_rules = InlineKeyboardButton("📜 Rᴜʟᴇs", url="http://telegra.ph/Request-%E0%B4%85%E0%B4%AF%E0%B4%95%E0%B4%95-%E0%B4%AE%E0%B4%A8%E0%B4%A8-%E0%B4%B5%E0%B4%AF%E0%B4%95%E0%B4%95%E0%B4%A3%E0%B4%9F%E0%B4%A8%E0%B4%A8%E0%B4%A4-08-19")
                btn_request = InlineKeyboardButton("📥 Rᴇqᴜᴇsᴛ", url="http://t.me/Promoviesearcher_bot")

                keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn_google], [btn_rules, btn_request]])                
                try:
                    await msg.reply_photo(
                        photo="https://files.catbox.moe/yt159d.jpg",
                        caption=script.SPELL_TEXT.format(msg.from_user.mention),
                        reply_markup=keyboard,
                        parse_mode=enums.ParseMode.HTML
                    )
                    return       
                except Exception:
                    try:
                        await msg.reply_text(
                            text=script.SPELL_TEXT.format(msg.from_user.mention), 
                            reply_markup=keyboard,
                            parse_mode=enums.ParseMode.HTML
                        )
                        return
                    except Exception: return
        else: return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  
        search, files, offset, total_results = spoll
        
    pre = 'filep' if settings['file_secure'] else 'file'
    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    BUTTONS[key] = search

    # മെനു ബട്ടണുകൾ മുകളിൽ ആഡ് ചെയ്യുന്നു
    btn = get_filter_menu_buttons(req, key)

    if settings["button"]:
        for file in files:
            btn.append([InlineKeyboardButton(text=f"{get_size(file.file_size)}➪{file.file_name}", callback_data=f'{pre}#{file.file_id}')])
    else:
        for file in files:
            btn.append([
                InlineKeyboardButton(text=f"{file.file_name}", callback_data=f'{pre}#{file.file_id}'),
                InlineKeyboardButton(text=f"{get_size(file.file_size)}", callback_data=f'{pre}#{file.file_id}')
            ])

    if offset != "":
        try: offset = int(offset)
        except ValueError: offset = 0
    else: offset = 0
    
    if offset > 0:
        btn.append(
            [InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / 10)}", callback_data="pages"),
            InlineKeyboardButton(text="Nᴇxᴛ", callback_data=f"next_{req}_{key}_{offset}")]
        )     
    cap = f"<b><i>Found Results For Your Query {search}</i></b>\n\n<b><i><u>For better result:</u></i></b>\n<i>↪bhramam      ❌\n↪bhramam 2021 ✅</i>"
    fmsg = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))

           


async def global_filters(client, message, text=False):
    group_id = message.chat.id
    raw_name = text or message.text
    
    # ---- ക്ലീനിങ് ലോജിക് ----
    search = emoji.replace_emoji(raw_name, replace='')
    search = re.sub(r'[\u200b\u200c\u200d\ufeff\u200e\u200f]', '', search)
    search = re.sub(r'[\s\u00a0\u2000-\u200a\u202f\u205f\u3000]+', ' ', search)
    search = re.sub(r"['‘’]", "", search)
    search = re.sub(r"[-–—_,#&?/( )\[\]\\\":\.¡%“”]", " ", search)
    search = re.sub(r"\b(hd|full|print|file)\b", "", search, flags=re.IGNORECASE)                       
                        
    find = search.lower().split(" ")
    removes = {
        "pls", "plz", "plzz", "please", "send", "snd", "snt",
        "gib", "veno", "venam", "venum",
        "undo", "ayakkumo", "ayakkamo", "und", "move", 
        "multi", "dubb", "dub", "bro", "bruh", "broh", "dubbed", "link", "lnk",
        "iruka", "pannunga", "pannungga", "anuppunga", "anupunga", "anuppungga", 
        "anupungga", "subtile", "kitti", "kitty", "tharu", "kittumo", "kittum",
        "da", "mwonse", "bhai", "share", "malayalm", "malylm", "subtitle"
    }
    search = " ".join([w for w in find if w not in removes])
    clean_name = re.sub(r"\s+", " ", search).strip()
    # -----------------------

    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_gfilters('gfilters')
    
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"^" + re.escape(keyword.strip().lower()) + r"$"
        
        if re.match(pattern, clean_name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_gfilter('gfilters', keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    # Safely parse buttons using json instead of eval
                    if btn != "[]":
                        try:
                            button = json.loads(btn)
                        except Exception:
                            button = eval(btn) # Fallback if stored in non-standard JSON format
                    else:
                        button = []

                    if fileid == "None":
                        if btn == "[]":
                            while True:
                                try:
                                    await client.send_message(
                                        group_id, 
                                        reply_text, 
                                        disable_web_page_preview=True,
                                        reply_to_message_id=reply_id
                                    )
                                    break
                                except FloodWait as e:
                                    logger.warning(f"FloodWait triggered! Sleeping for {e.value} seconds.")
                                    await asyncio.sleep(e.value)
                        else:
                            while True:
                                try:
                                    await client.send_message(
                                        group_id,
                                        reply_text,
                                        disable_web_page_preview=True,
                                        reply_markup=InlineKeyboardMarkup(button),
                                        reply_to_message_id=reply_id
                                    )
                                    break
                                except FloodWait as e:
                                    logger.warning(f"FloodWait triggered! Sleeping for {e.value} seconds.")
                                    await asyncio.sleep(e.value)

                    elif btn == "[]":
                        while True:
                            try:
                                await client.send_cached_media(
                                    group_id,
                                    fileid,
                                    caption=reply_text or "",
                                    reply_to_message_id=reply_id
                                )
                                break
                            except FloodWait as e:
                                logger.warning(f"FloodWait triggered! Sleeping for {e.value} seconds.")
                                await asyncio.sleep(e.value)
                    else:
                        while True:
                            try:
                                # Replaced message.reply_cached_media with client.send_cached_media 
                                # to remain structurally uniform and reliable across channels/groups
                                await client.send_cached_media(
                                    group_id,
                                    fileid,
                                    caption=reply_text or "",
                                    reply_markup=InlineKeyboardMarkup(button),
                                    reply_to_message_id=reply_id
                                )
                                break
                            except FloodWait as e:
                                logger.warning(f"FloodWait triggered! Sleeping for {e.value} seconds.")
                                await asyncio.sleep(e.value)
                        
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
