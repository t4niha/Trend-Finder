"""
translation.py

Function for detecting language and translating non-English posts
in the final_trendingtopics table using Google Cloud Translation API:

- translate_posts(conn): Translates all posts with NULL text_en to English
  and updates the database

Requires Google Cloud credentials JSON in `service_account.json`

"""

import os
from google.cloud import translate_v2 as translate
from langdetect import detect, DetectorFactory
from tqdm import tqdm

DetectorFactory.seed = 0

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

def translate_posts(conn):
    translate_client = translate.Client()
    cursor = conn.cursor()
    
    cursor.execute("SELECT post_id, full_text FROM final_trendingtopics WHERE text_translated IS NULL;")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} rows to check for translation")
    
    translated_count = 0
    english_count = 0
    unknown_count = 0
    
    for post_id, text in tqdm(rows, desc="Translating posts", unit="post"):
        if not text:
            unknown_count += 1
            continue
        try:
            lang = detect(text)
        except:
            lang = 'unknown'
        
        if lang != 'en' and lang != 'unknown':
            try:
                result = translate_client.translate(text, target_language='en')
                translated_text = result['translatedText']
                translated_count += 1
            except:
                translated_text = text
                unknown_count += 1
        else:
            translated_text = text
            if lang == 'en':
                english_count += 1
            else:
                unknown_count += 1
        
        cursor.execute(
            "UPDATE final_trendingtopics SET text_translated = %s WHERE post_id = %s;",
            (translated_text, post_id)
        )
    
    conn.commit()
    cursor.close()
    
    print(f"Translated to English: {translated_count}")
    print(f"Already in English: {english_count}")
    print(f"Unknown: {unknown_count}")