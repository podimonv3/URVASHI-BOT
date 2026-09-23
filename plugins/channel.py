from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import save_file, save_filea, check_file

# 🛠️ ഫിൽറ്ററിൽ നിന്നും audio ഒഴിവാക്കി (document, video എന്നിവ മാത്രം)
media_filter = filters.document | filters.video


@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    # 🛠️ ലൂപ്പിൽ നിന്നും "audio" ഒഴിവാക്കി
    for file_type in ("document", "video"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption
    
    if message.id % 2 == 0:
        tru = await check_file(media)
        if tru == "okda":
            await save_file(media)
    else:
        try_a = await check_file(media)
        if try_a == "okda":
            await save_filea(media)
