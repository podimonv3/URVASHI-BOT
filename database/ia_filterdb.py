import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_URI2, DATABASE_URI3, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER
import unicodedata

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

client1 = AsyncIOMotorClient(DATABASE_URI2)
db1 = client1[DATABASE_NAME]
instance1 = Instance.from_db(db1)

client2 = AsyncIOMotorClient(DATABASE_URI3)
db2 = client2[DATABASE_NAME]
instance2 = Instance.from_db(db2)

@instance1.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    
    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

@instance2.register
class Mediaa(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    
    class Metaa:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

async def check_file(media):
    """Check if file is present in the database"""

    # TODO: Find better way to get same file_id for same media to avoid duplicates
    file_id, file_ref = unpack_new_file_id(media.file_id)
    
    existing_file = await Media.collection.find_one({"_id": file_id})
    existing_filea = await Mediaa.collection.find_one({"_id": file_id})
    
    if existing_file:
        pass
    elif existing_filea:
        pass
    else:
        okda = "okda"
        return okda
        

def clean_file_name(raw_name):
    """ഫയൽ നെയിം ക്ലീൻ ചെയ്യാനും ഇമോജികൾ/ചിഹ്നങ്ങൾ മാറ്റാനും ഉള്ള ഹെൽപ്പർ ഫങ്ഷൻ"""
    if not raw_name:
        return "NO_FILE"
        
    cleaned_name = str(raw_name)
    
    # 1. വീഡിയോ ഫയൽ എക്സ്റ്റൻഷൻ (mkv, mp4...) ഒഴിവാക്കുന്നു
    if '.' in cleaned_name:
        name_parts = cleaned_name.split('.')
        if len(name_parts) > 1 and name_parts[-1].lower() in ['mkv', 'mp4', 'avi', 'mov', 'webm', 'ts']:
            cleaned_name = '.'.join(name_parts[:-1])

    # 2. ചിഹ്നങ്ങൾ ഒഴിവാക്കി പകരം സ്പേസ് നൽകുന്നു
    cleaned_name = re.sub(r"['‘’]", "", cleaned_name)
    cleaned_name = re.sub(r"[-–—_,#&?/( )\[\]\\\":\.¡%“”]", " ", cleaned_name)
    
    # 3. ഇംഗ്ലീഷ്, മലയാളം അക്ഷരങ്ങളും അക്കങ്ങളും മാത്രം നിലനിർത്തുന്നു (ഇമോജികൾ മാറും)
    cleaned_symbols = re.sub(r'[^a-zA-Z0-9\u0D00-\u0D7F\s]', '', cleaned_name)
    
    # 4. അനാവശ്യ ഇരട്ട സ്പേസുകൾ ഒഴിവാക്കുന്നു
    return re.sub(r'\s+', ' ', cleaned_symbols).strip()


async def save_file(media):
    """Save file in Media database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    
    # നിങ്ങളുടെ അഡ്വാൻസ്ഡ് ക്ലീനിംഗ് ലോജിക് ഇവിടെ പ്രവർത്തിക്കും
    file_name = clean_file_name(media.file_name)
    
    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
         )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
            )
            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            return True, 1


async def save_filea(media):
    """Save file in Mediaa database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    
    # നിങ്ങളുടെ അഡ്വാൻസ്ഡ് ക്ലീനിംഗ് ലോജിക് ഇവിടെയും പ്രവർത്തിക്കും
    file_name = clean_file_name(media.file_name)
    
    try:
        file = Mediaa(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
       )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
            )
            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            return True, 1

            

async def delete_files_below_threshold(db, threshold_size_mb: int = 50, batch_size: int = 20, chat_id: int = None, message_id: int = None):
    cursor_media = Media.find({"file_size": {"$lt": threshold_size_mb * 1024 * 1024}}).limit(batch_size // 2)
    cursor_mediaa = Mediaa.find({"file_size": {"$lt": threshold_size_mb * 1024 * 1024}}).limit(batch_size // 2)
    deleted_count_media = 0
    deleted_count_mediaa = 0
    
    async for document in cursor_media:
        try:
            await Media.collection.delete_one({"_id": document["file_id"]})
            deleted_count_media += 1
            print(f'Deleted file from Media: {document["file_name"]}')
        except Exception as e:
            print(f'Error deleting file from Media: {document["file_name"]}, {e}')

    async for document in cursor_mediaa:
        try:
            await Mediaa.collection.delete_one({"_id": document["file_id"]})
            deleted_count_mediaa += 1
            print(f'Deleted file from Mediaa: {document["file_name"]}')
        except Exception as e:
            print(f'Error deleting file from Mediaa: {document["file_name"]}, {e}')
            
    deleted_count = deleted_count_media + deleted_count_mediaa
    return deleted_count

async def get_bad_files(query, file_type=None, filter=False):
    """For given query return (results, next_offset)"""
    query = query.strip()

    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []

    if USE_CAPTION_FILTER:
        filter = {'file_name': regex}
    else:
        filter = {'file_name': regex}

    if file_type:
        filter['file_type'] = file_type

    total_results_media1 = await Media.count_documents(filter)
    total_results_media2 = await Mediaa.count_documents(filter)
    total_results = total_results_media1 + total_results_media2

    cursor_media1 = Media.find(filter)
    cursor_media1.sort('$natural', -1)
    files_media1 = await cursor_media1.to_list(length=total_results_media1)

    cursor_media2 = Mediaa.find(filter)
    cursor_media2.sort('$natural', -1)
    files_media2 = await cursor_media2.to_list(length=total_results_media2)

    return files_media1, files_media2, total_results
        


async def get_search_results(query, file_type=None, max_results=10, offset=0, filter_param=False):
    """For given query return (results, next_offset, total_results) 
    with Super Smart Exact Match & Natural Sorting"""
    
    query = query.strip()    
    query = ''.join(c for c in unicodedata.normalize('NFD', query) if unicodedata.category(c) != 'Mn')
    query = re.sub(r"['‘’]", "", query)
    query = re.sub(r"[-–—_,#&?/( )\[\]\\\":\.¡%“”]", " ", query)  
    query = re.sub(r'[^a-zA-Z0-9\s]', '', query)
    query = re.sub(r'\s+', ' ', query).strip()    
    
    if not query:
        return [], '', 0

    # 1. Exact Match Pattern (കൃത്യമായ വാക്ക് ഉള്ളവ)
    exact_pattern = r'\b' + re.escape(query) + r'\b'
    # 2. Smart Fuzzy/Partial Match Pattern (വാക്കുകൾക്കിടയിൽ മറ്റ് ചിഹ്നങ്ങൾ ഉള്ളവ)
    fuzzy_pattern = query.replace(' ', r'.*[\s\.\+\-_()]')

    try:
        regex_exact = re.compile(exact_pattern, flags=re.IGNORECASE)
        regex_fuzzy = re.compile(fuzzy_pattern, flags=re.IGNORECASE)
    except:
        return [], '', 0

    # Base Filter നിർമ്മിക്കുന്നു
    def make_filter(regex_obj):
        if USE_CAPTION_FILTER:
            f = {'$or': [{'file_name': regex_obj}, {'caption': regex_obj}]}
        else:
            f = {'file_name': regex_obj}
        if file_type:
            f['file_type'] = file_type
        return f

    # രണ്ട് തരം ഫിൽട്ടറുകൾ തയാറാക്കുന്നു
    exact_filter = make_filter(regex_exact)
    fuzzy_filter = make_filter(regex_fuzzy)

    # എക്സാക്റ്റ് മാച്ചിൽ വരാത്തവ മാത്രം ഫസി ഫിൽട്ടറിൽ വരാൻ (ഡ്യൂപ്ലിക്കേഷൻ ഒഴിവാക്കാൻ)
    if USE_CAPTION_FILTER:
        fuzzy_filter['$and'] = [
            {'file_name': {'$not': regex_exact}},
            {'caption': {'$not': regex_exact}}
        ]
    else:
        fuzzy_filter['file_name'] = {'$regex': fuzzy_pattern, '$options': 'i', '$not': regex_exact}

    # ഫലങ്ങൾ ശേഖരിക്കാനുള്ള ഫങ്ഷൻ (Natural Sorting -$natural: -1 നിലനിർത്തിക്കൊണ്ട്)
    async def fetch_combined(current_filter):
        cursor_media = Media.find(current_filter).sort('$natural', -1)
        cursor_mediaa = Mediaa.find(current_filter).sort('$natural', -1)
        
        # വലിയ കളക്ഷനുകളിൽ മെമ്മറി പ്രശ്നം ഒഴിവാക്കാൻ ആവശ്യത്തിന് മാത്രം (ലിമിറ്റ് 200) എടുക്കുന്നു
        list_m = await cursor_media.to_list(length=200)
        list_ma = await cursor_mediaa.to_list(length=200)
        
        # Interleave (ഒന്നിടവിട്ട് ചേർക്കുക) വഴി Natural Sorting മിക്സ് ചെയ്യുന്നു
        interleaved = []
        i = j = 0
        while i < len(list_m) or j < len(list_ma):
            if i < len(list_m):
                interleaved.append(list_m[i])
                i += 1
            if j < len(list_ma):
                interleaved.append(list_ma[j])
                j += 1
        return interleaved

    # Exact Match ഉള്ളവ ആദ്യം എടുക്കുന്നു, അതിനു ശേഷം Fuzzy Match ഉള്ളവയും
    exact_results = await fetch_combined(exact_filter)
    fuzzy_results = await fetch_combined(fuzzy_filter)

    # സൂപ്പർ സ്മാർട്ട് ഓർഡറിൽ ഫയലുകൾ ഒന്നിപ്പിക്കുന്നു
    all_files = exact_results + fuzzy_results
    total_results = len(all_files)

    # Offset ക്രമീകരണം
    if offset < 0:
        offset = 0

    # ഫലങ്ങൾ മുറിച്ചെടുക്കുന്നു (Pagination)
    files = all_files[offset:offset + max_results]
    next_offset = offset + len(files)

    if next_offset < total_results:
        return files, next_offset, total_results
    else:
        return files, '', total_results


async def get_file_details(query):
    filter = {'file_id': query}
    cursor_media = Media.find(filter)
    filedetails_media = await cursor_media.to_list(length=1)
    if filedetails_media:
        return filedetails_media
    # Query details from Mediaa collection
    cursor_mediaa = Mediaa.find(filter)
    filedetails_mediaa = await cursor_mediaa.to_list(length=1)
    if filedetails_mediaa:
        return filedetails_mediaa

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
