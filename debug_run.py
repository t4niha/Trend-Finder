from xpoz_scraper import make_client, fetch_topic
client = make_client()
res = fetch_topic(client, "Winter Olympics 2026 Milano")
print("collected", len(res))
