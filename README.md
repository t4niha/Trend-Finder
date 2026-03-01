# Twitter Data Collection via Xpoz API

## Requirements
- httpx
- python-dotenv

## Setup
1. Create .env with your key:
   `
   XPOZ_API_KEY=your_key_here
   `
2. Install deps in venv:
   `
   pip install httpx python-dotenv
   `

## Run
`
python xpoz_scraper.py
`
Data is saved to data/twitter.json with fields: id, text, timestamp, username, likes, retweets, topic.

