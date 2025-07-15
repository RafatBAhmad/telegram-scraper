from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import requests
import re
from datetime import datetime
import time
import os
import asyncio

# Telegram credentials
api_id = 24446133
api_hash = '6c11abd16230bf4dc23cb57266391857'
channel_username = 'ahwalaltreq'

# Spring Boot API endpoint
api_url = 'https://ahwal-checkpoints-api.onrender.com/api/v1/checkpoints/update'

# Telegram session
client = TelegramClient('ahwal_session', api_id, api_hash)

# ربط كل نقطة تفتيش بمدينة
CHECKPOINT_TO_CITY = {
    "قلنديا": "القدس",
    "الكونتينر": "بيت لحم",
    "حوارة": "نابلس",
    "بيت إيل": "رام الله",
    "الزعيم": "القدس",
    "شعفاط": "القدس",
    "دير شرف": "نابلس",
    "ديرشرف": "نابلس",
    "الولجة": "بيت لحم",
    "ترقوميا": "الخليل",
    "النبي يونس": "الخليل",
    "زعترة": "نابلس",
    "صرة": "نابلس",
    "صره": "نابلس",
    "العزرية": "القدس",
    "جسر حلحول": "الخليل",
    "سدة قراوة": "سلفيت",
    "جماعين": "سلفيت",
    "شقبا": "رام الله",
    "كرملو": "رام الله",
    "ترمسعيا": "رام الله",
    "دير دبوان": "رام الله",
    "ديردبوان": "رام الله",
    "بوابة اللبن": "نابلس",
    "بوابة سلفيت": "سلفيت",
    "بوابة بروقين الغربية": "سلفيت",
    "سدة قراوة": "سلفيت",
     "بديا": "سلفيت",
    "بوابة بروقين الشرقية": "سلفيت"
}


# Keywords to detect messages about checkpoints
checkpoint_keywords = ["حاجز", "بوابة", "مفتوح", "مغلق", "مغلقه", "مغلقة", "ازدحام", "سالك", "سالكة", "سالكه"]

# Known checkpoint names for better name extraction
KNOWN_CHECKPOINTS = [
    "قلنديا", "الكونتينر", "حوارة", "بيت إيل", "الزعيم", "شعفاط", "دير شرف",
    "الولجة", "ترقوميا", "النبي يونس", "زعترة", "صرة", "صره","العزرية", "جسر حلحول",
    "سدة قراوة", "بوابة اللبن", "بوابة سلفيت", "بوابة بروقين الغربية", "بوابة بروقين الشرقية"
]


# File to store last fetched message ID
LAST_ID_FILE = "last_id.txt"

def load_last_message_id():
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, 'r', encoding='utf-8') as f:
            try:
                return int(f.read().strip())
            except:
                return 0
    return 0

def save_last_message_id(message_id):
    with open(LAST_ID_FILE, 'w', encoding='utf-8') as f:
        f.write(str(message_id))

def normalize_arabic(text):
    return text.replace("ى", "ي").replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").lower()

def extract_status(text):
    if "مفتوح" in text:
        return "مفتوح"
    if "مغلق" in text or "مغلقه" in text:
        return "مغلق"
    if "ازدحام" in text:
        return "ازدحام"
    if "سالكة" in text or "سالكه" in text or "سالك" in text:
        return "سالكة"
    return "غير معروف"

def extract_name(text):
    for cp in KNOWN_CHECKPOINTS:
        if cp in text:
            return cp
    match = re.search(r"(?:حاجز|بوابة)\s+([^\n،:]+)", text)
    return match.group(1).strip() if match else "غير معروف"

def extract_city_from_checkpoint(checkpoint_name):
    return CHECKPOINT_TO_CITY.get(checkpoint_name, "غير معروف")


def extract_checkpoint_data(text, message_id, message_date):
    norm_text = normalize_arabic(text)
    if any(keyword in norm_text for keyword in checkpoint_keywords):
        checkpoint_name = extract_name(text)
        checkpoint_city = extract_city_from_checkpoint(checkpoint_name)
        return {
            "name": checkpoint_name,
            "city": checkpoint_city,
            "status": extract_status(norm_text),
            "sourceText": text,
            "sourceMessageId": message_id,
            "latitude": 0.0,
            "longitude": 0.0,
            "effectiveAt": message_date.isoformat()
        }
    return None

async def fetch_and_process():
    last_seen_id = load_last_message_id()
    await client.start()
    entity = await client.get_entity(channel_username)
    messages = await client(GetHistoryRequest(
        peer=entity,
        limit=100,
        offset_id=0,
        max_id=0,
        min_id=last_seen_id + 1,
        offset_date=None,
        add_offset=0,
        hash=0
    ))

    for message in reversed(messages.messages):
        if hasattr(message, 'message') and message.id > last_seen_id:
            data = extract_checkpoint_data(message.message, message.id, message.date)
            if data:
                print(f"\n✅ نقطة جديدة ({message.id}): {data['name']} | {data['status']}")
                try:
                    res = requests.post(api_url, json=data)
                    if res.status_code == 200:
                        print("➡️ تم الإرسال بنجاح")
                    else:
                        print(f"⚠️ فشل - كود: {res.status_code}")
                except Exception as e:
                    print(f"❌ خطأ أثناء الإرسال: {e}")
            last_seen_id = max(last_seen_id, message.id)
            save_last_message_id(last_seen_id)

# Loop every 5 minutes
async def main_loop():
    while True:
        try:
            await fetch_and_process()
        except Exception as e:
            print(f"⚠️ حصل خطأ أثناء التنفيذ: {e}")
        print("⏳ ننتظر 300 ثانية...")
        await asyncio.sleep(300)

with client:
    client.loop.run_until_complete(main_loop())