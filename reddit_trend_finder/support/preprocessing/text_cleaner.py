"""
text_cleaner.py — Preprocessing helpers for Reddit post text.

Used by the embedding generator and the clustering pipeline.
"""

import re


def clean_text(text: str) -> str:
    """
    Clean raw Reddit text for embedding / clustering.

    Steps:
      1. Remove URLs
      2. Remove Reddit-specific markdown (e.g. >quotes, **bold**)
      3. Remove excessive whitespace
      4. Strip leading/trailing whitespace
    """
    if not text or not isinstance(text, str):
        return ""

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)

    # Remove Reddit markdown artifacts
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#x200B;", "", text)  # zero-width space

    # Remove markdown formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)       # italic
    text = re.sub(r"~~(.+?)~~", r"\1", text)        # strikethrough
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)  # blockquotes
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)   # [text](url)

    # Remove [removed] / [deleted]
    text = re.sub(r"\[removed\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[deleted\]", "", text, flags=re.IGNORECASE)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def combine_title_body(title: str, selftext: str) -> str:
    """Combine title and selftext into a single text field."""
    title = (title or "").strip()
    body = (selftext or "").strip()

    if body and body.lower() not in ("[removed]", "[deleted]", ""):
        return f"{title} {body}"
    return title
