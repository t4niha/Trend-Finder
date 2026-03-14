import re
import emoji

def clean_post(text):

    if not text:
        return None

    # lowercase
    text = text.lower()

    # remove urls
    text = re.sub(r'https?://\S+|www\.\S+', '[removed]', text)

    # remove mentions
    text = re.sub(r'@\w+', '', text)

    # remove hashtag symbol
    text = re.sub(r'#', '', text)

    # remove emojis
    text = emoji.replace_emoji(text, replace='')

    # normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text