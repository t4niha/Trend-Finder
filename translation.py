import os
import psycopg2
from google.cloud import translate_v2 as translate
from langdetect import detect, DetectorFactory
from tqdm import tqdm

DetectorFactory.seed = 0

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

# Connect to local PostgreSQL
conn = psycopg2.connect(
    dbname="trend_finder",
    user="postgres",
    password="taniha",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

translate_client = translate.Client()

cursor.execute("SELECT id, text FROM trending_topics WHERE text_en IS NULL;")
rows = cursor.fetchall()

print(f"Found {len(rows)} rows to check for translation.")

# Detect language and translate non-English posts
translated_count = 0
english_count = 0
unknown_count = 0

for id_, text in tqdm(rows, desc="Translating posts", unit="post"):
    if not text:
        unknown_count += 1
        continue
    try:
        lang = detect(text)
    except Exception as e:
        lang = 'unknown'

    if lang != 'en' and lang != 'unknown':
        try:
            result = translate_client.translate(text, target_language='en')
            translated_text = result['translatedText']
            translated_count += 1
        except Exception as e:
            translated_text = text
            unknown_count += 1
    else:
        translated_text = text
        if lang == 'en':
            english_count += 1
        else:
            unknown_count += 1

    cursor.execute(
        "UPDATE trending_topics SET text_en = %s WHERE id = %s;",
        (translated_text, id_)
    )

conn.commit()
cursor.close()
conn.close()

print(f"Translated to English: {translated_count}")
print(f"Already English: {english_count}")
print(f"Unknown: {unknown_count}")