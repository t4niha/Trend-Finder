import os
import json
import requests
import time
import urllib3
from io import StringIO

# Suppress the SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SAFE CONFIGURATION ---
API_KEY = "K3AMAkSORO6SZwcS1Q85PvBnsJb1wmkBbNJc9xyIiSEFYLe7d69IkCCa3qwI7AadfEAnRCG"
MCP_URL = "https://mcp.xpoz.ai/mcp"
OUTPUT_FILE = "data/bd_election.json"
TOPIC = "Bangladesh Election 2026"
TARGET_LIMIT = 5000

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

def call_mcp_stream(query, cursor=None):
    """Calls the API requesting a live stream instead of a bulk dump."""
    arguments = {"query": query, "count": 100} # Pull in small, cheap batches
    if cursor:
        arguments["cursor"] = cursor
        
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "getTwitterPostsByKeywords", "arguments": arguments}
    }
    return requests.post(MCP_URL, headers=HEADERS, json=payload, stream=True, verify=False)

def main():
    print(f"--- Starting Safe Streaming Extraction for: '{TOPIC}' ---")
    print(f"Target: {TARGET_LIMIT} tweets. Credits are protected.")
    
    collected_tweets = {}
    next_cursor = None
    api_calls = 0
    
    # Keep looping until we safely hit our 5,000 limit
    while len(collected_tweets) < TARGET_LIMIT:
        api_calls += 1
        print(f"Initiating stream request #{api_calls}... (Current tweets: {len(collected_tweets)})")
        
        try:
            resp = call_mcp_stream(TOPIC, next_cursor)
            if resp.status_code != 200:
                print(f"API Error: {resp.status_code}. Retrying in 5s...")
                time.sleep(5)
                continue
                
            chunk_count = 0
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    
                    # Look for the data payloads in the stream
                    if decoded.startswith("data: "):
                        try:
                            json_data = json.loads(decoded[6:]) # strip 'data: '
                            
                            # Extract the cursor for the next page if it exists
                            if "next_cursor" in json_data:
                                next_cursor = json_data["next_cursor"]
                                
                            # Extract tweets if they exist in this chunk
                            if "results" in json_data:
                                for item in json_data["results"]:
                                    tweet_id = item.get("id", str(time.time()))
                                    
                                    # Deduplicate and format
                                    if tweet_id not in collected_tweets:
                                        collected_tweets[tweet_id] = {
                                            "id": tweet_id,
                                            "text": item.get('text', ''),
                                            "created_at": item.get('created_at', ''),
                                            "username": item.get('author', item.get('username', '')),
                                            "likes": item.get('like_count', item.get('likes', 0)),
                                            "retweets": item.get('retweet_count', item.get('retweets', 0))
                                        }
                                        chunk_count += 1
                                        
                                        # Emergency Stop: Break the second we hit 5,000
                                        if len(collected_tweets) >= TARGET_LIMIT:
                                            break
                        except json.JSONDecodeError:
                            continue
                            
            print(f"   -> Added {chunk_count} new tweets from stream.")
            
            # If no cursor was returned, we've exhausted all available tweets
            if not next_cursor or chunk_count == 0:
                print("No more pages available. Stopping early.")
                break
                
            # Sleep to respect rate limits
            time.sleep(2)
            
        except Exception as e:
            print(f"Connection dropped: {e}. Reconnecting in 5s...")
            time.sleep(5)

    # Save everything safely to the new file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(collected_tweets.values()), f, indent=4)
        
    print(f"\n🎉 SUCCESS! Saved exactly {len(collected_tweets)} tweets to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()