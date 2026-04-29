import json
import requests
import time
from datetime import datetime, timedelta, timezone

# ============================================================
#  CONFIG
# ============================================================
SCRAPER_API_KEY = 'YOUR_SCRAPERAPI_KEY_HERE'  # Get a free key at https://www.scraperapi.com/
DAYS_BACK       = 30
OUTPUT_FILE     = 'reddit_trends_last_30_days.json'

SUBREDDITS = [
    "technology",
    "worldnews",
    "science",
    "gaming",
    "movies",
    "smartphones"
]

# Each endpoint gives a different pool of up to 1,000 posts
# Combined and deduplicated = much better 30-day coverage
ENDPOINTS = [
    ("new",             None),    # most recent posts chronologically
    ("top",             "month"), # highest scored posts this month
    ("top",             "week"),  # highest scored posts this week
    ("controversial",   "month"), # most controversial this month
    ("controversial",   "week"),  # most controversial this week
]
# ============================================================


def fetch_endpoint(subreddit, sort, time_filter, cutoff):
    """
    Paginate a single endpoint (new/top/controversial) fully
    and return all posts within the cutoff date.
    """
    all_posts = []
    after     = None
    page      = 1

    label = f"{sort}?t={time_filter}" if time_filter else sort
    print(f"    📡 Fetching /{label}...")

    while True:
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit=100"
        if time_filter:
            url += f"&t={time_filter}"
        if after:
            url += f"&after={after}"

        payload = {'api_key': SCRAPER_API_KEY, 'url': url}

        try:
            r    = requests.get('https://api.scraperapi.com/', params=payload, timeout=30)
            data = r.json()
        except Exception as e:
            print(f"      ❌ Page {page} failed: {e}")
            break

        posts = data.get('data', {}).get('children', [])
        if not posts:
            break

        stop = False
        for post in posts:
            p           = post['data']
            created_utc = datetime.fromtimestamp(p['created_utc'], tz=timezone.utc)

            # For /new we stop at cutoff since posts are chronological
            # For /top and /controversial we collect everything since
            # posts aren't in chronological order — filter after
            if sort == "new" and created_utc < cutoff:
                stop = True
                break

            # Only keep posts within 30-day window
            if created_utc >= cutoff:
                all_posts.append({
                    'post_id'      : p['id'],
                    'niche'        : subreddit,
                    'title'        : p['title'],
                    'author'       : p.get('author', '[deleted]'),
                    'subreddit'    : p['subreddit_name_prefixed'],
                    'score'        : p['score'],
                    'upvote_ratio' : p.get('upvote_ratio', None),
                    'num_comments' : p['num_comments'],
                    'timestamp_utc': created_utc.strftime('%Y-%m-%d %H:%M:%S'),
                    'permalink'    : f"https://reddit.com{p['permalink']}",
                    'url'          : p.get('url', ''),
                    'selftext'     : p.get('selftext', ''),
                    'flair'        : p.get('link_flair_text', None),
                    'is_video'     : p.get('is_video', False),
                })

        if stop:
            break

        after = data['data'].get('after')
        if not after:
            break

        page += 1
        time.sleep(1)

    print(f"      ✅ {len(all_posts)} posts from /{label}")
    return all_posts


def fetch_subreddit_posts(subreddit, days=DAYS_BACK):
    """
    Fetch from all endpoints and merge — each endpoint contributes
    a different pool of posts, deduplication keeps unique ones only.
    """
    cutoff    = datetime.now(timezone.utc) - timedelta(days=days)
    seen_ids  = set()
    all_posts = []

    print(f"\n📌 Scraping r/{subreddit}")
    print(f"   Cutoff : {cutoff.strftime('%Y-%m-%d')} UTC")
    print(f"   Sources: {len(ENDPOINTS)} endpoints\n")

    for sort, time_filter in ENDPOINTS:
        posts = fetch_endpoint(subreddit, sort, time_filter, cutoff)

        # Deduplicate across endpoints
        new_posts = [p for p in posts if p['post_id'] not in seen_ids]
        seen_ids.update(p['post_id'] for p in new_posts)
        all_posts.extend(new_posts)

        time.sleep(2)

    print(f"\n  ✅ r/{subreddit} done")
    print(f"     Total unique posts : {len(all_posts):,}")
    print(f"     Duplicates dropped : {sum(len(fetch_endpoint.__code__.co_consts)) - len(all_posts) if False else 'N/A (deduped across endpoints)'}")
    return all_posts


def fetch_all_subreddits():
    combined = []
    total    = len(SUBREDDITS)

    for i, subreddit in enumerate(SUBREDDITS, 1):
        print(f"\n{'='*55}")
        print(f"[{i}/{total}] Starting r/{subreddit}...")
        posts = fetch_subreddit_posts(subreddit)
        combined.extend(posts)

        if i < total:
            print(f"\n  ⏳ Waiting 3 seconds before next subreddit...")
            time.sleep(3)

    return combined


# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    print("🚀 Starting Reddit trend scraper (30-day, multi-endpoint)")
    print(f"📋 Subreddits : {', '.join(['r/' + s for s in SUBREDDITS])}")
    print(f"📅 Days back  : {DAYS_BACK}")
    print(f"📡 Endpoints  : {len(ENDPOINTS)} per subreddit\n")

    all_posts = fetch_all_subreddits()

    all_posts.sort(key=lambda x: x['timestamp_utc'], reverse=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"✅ Scraping complete!")
    print(f"📊 Total posts collected : {len(all_posts):,}")
    print(f"📋 Breakdown by niche:")
    for subreddit in SUBREDDITS:
        count = sum(1 for p in all_posts if p['niche'] == subreddit)
        print(f"   {subreddit:<20} → {count:,} posts")
    print(f"💾 Saved to '{OUTPUT_FILE}'")
    print(f"{'='*55}")