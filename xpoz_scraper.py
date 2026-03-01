import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import httpx

# --- Configuration ---------------------------------------------------------
API_KEY = (
    os.getenv("XPOZ_API_KEY")
    or "K3AMGsRKLAfh4cwqoqPfmR04nWJHkJpMpcfJkwDPFoUvyTdJK9qF04Gev57QAYilvlN0UGK"
)
MCP_URL = "https://mcp.xpoz.ai/mcp"
TOPICS = ["Bangladesh Election 2026"]
TARGET_PER_TOPIC = 4000  # strict cap
PAGE_LIMIT = 200  # per-request limit the API accepts
OUTPUT_PATH = Path("data/bd_election.json")
REQUEST_TIMEOUT = 60
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Host": "mcp.xpoz.ai",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "User-Agent": "Mozilla/5.0 (Codex)",
}


# --- Helpers ---------------------------------------------------------------
def parse_records_from_block(block: str) -> Tuple[List[Dict], Optional[str]]:
    """
    Parse the textual block returned in the SSE 'text' content.
    Expected format resembles:
        results[300]{id,text,authorUsername,impressionCount,lang,createdAtDate}:
          "id","text","user","123","en","2026-03-01T00:00:00.000Z"
    Returns list of dicts and optional nextPageCursor if present.
    """
    rows: List[Dict] = []
    next_cursor: Optional[str] = None

    # Cursor extraction (lines like "nextPageCursor: abc")
    for line in block.splitlines():
        if "nextPageCursor" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                maybe = parts[1].strip().strip('"')
                if maybe:
                    next_cursor = maybe

    # Extract CSV-like rows after the header marker
    # Find the section after the colon of results[...] marker
    m = re.search(r"results\[\d+\]\{[^}]+\}:\s*(.*)", block, re.DOTALL)
    if not m:
        return rows, next_cursor

    data_section = m.group(1)
    for rec in csv_reader_lines(data_section.splitlines()):
        if len(rec) < 6:
            continue
        rec_id, rec_text, rec_user, rec_likes, _lang, rec_created = rec[:6]
        rows.append(
            {
                "id": rec_id.strip('"'),
                "text": rec_text,
                "created_at": rec_created.strip('"'),
                "username": rec_user,
                "likes": safe_int(rec_likes),
                "retweets": None,
            }
        )
    return rows, next_cursor


def csv_reader_lines(lines: Iterable[str]) -> Iterable[List[str]]:
    import csv

    reader = csv.reader(
        (ln for ln in lines if ln and ln.strip()), skipinitialspace=False
    )
    return reader


def safe_int(val: str) -> Optional[int]:
    try:
        return int(val.replace(",", ""))
    except Exception:
        return None


def make_client() -> httpx.Client:
    if not API_KEY:
        raise SystemExit("XPOZ_API_KEY missing")
    transport = httpx.HTTPTransport(retries=2, verify=False)
    return httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers=HEADERS,
        transport=transport,
        follow_redirects=True,
    )


def stream_page(
    client: httpx.Client, topic: str, cursor: Optional[str]
) -> Tuple[List[Dict], Optional[str]]:
    """
    Call MCP with stream=True and responseType='paging'.
    Returns tweets parsed from the streamed text block and next cursor (if any).
    If paging yields no rows, falls back to responseType='fast' to avoid stalls.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": f"call-{time.time_ns()}",
        "method": "tools/call",
        "params": {
            "name": "getTwitterPostsByKeywords",
            "arguments": {
                "query": topic,
                "limit": PAGE_LIMIT,
                "responseType": "paging",
                **({"cursor": cursor} if cursor else {}),
            },
            "stream": True,
        },
    }

    with client.stream("POST", MCP_URL, json=payload) as resp:
        if resp.status_code != 200:
            body = resp.read().decode(errors="ignore")
            raise RuntimeError(f"HTTP {resp.status_code}: {body}")
        for line in resp.iter_lines():
            if not line:
                continue
            s = (
                line.decode(errors="ignore")
                if isinstance(line, (bytes, bytearray))
                else line
            )
            if not s.startswith("data:"):
                continue
            try:
                obj = json.loads(s[5:].strip())
            except json.JSONDecodeError:
                continue
            # Prefer structured data if present
            content = obj.get("result", {}).get("content", [])
            for item in content:
                if item.get("type") == "text":
                    rows, next_cursor = parse_records_from_block(item.get("text", ""))
                    if rows:
                        return rows, next_cursor
            # Fallback: if result contains 'data'
            data = obj.get("result", {}).get("data")
            if isinstance(data, list) and data:
                rows = []
                for d in data:
                    rows.append(
                        {
                            "id": d.get("id"),
                            "text": d.get("text"),
                            "created_at": d.get("createdAt") or d.get("createdAtDate"),
                            "username": d.get("authorUsername") or d.get("username"),
                            "likes": d.get("likeCount") or d.get("likes"),
                            "retweets": d.get("retweetCount") or d.get("retweets"),
                        }
                    )
                next_cursor = obj.get("result", {}).get("nextPageCursor")
                return rows, next_cursor

    # If paging produced nothing, fall back to fast mode to at least collect data.
    fast_payload = {
        "jsonrpc": "2.0",
        "id": f"fast-{time.time_ns()}",
        "method": "tools/call",
        "params": {
            "name": "getTwitterPostsByKeywords",
            "arguments": {"query": topic, "limit": PAGE_LIMIT, "responseType": "fast"},
            "stream": True,
        },
    }
    with client.stream("POST", MCP_URL, json=fast_payload) as resp:
        if resp.status_code != 200:
            body = resp.read().decode(errors="ignore")
            raise RuntimeError(f"HTTP {resp.status_code}: {body}")
        for line in resp.iter_lines():
            if not line:
                continue
            s = (
                line.decode(errors="ignore")
                if isinstance(line, (bytes, bytearray))
                else line
            )
            if not s.startswith("data:"):
                continue
            try:
                obj = json.loads(s[5:].strip())
            except json.JSONDecodeError:
                continue
            content = obj.get("result", {}).get("content", [])
            for item in content:
                if item.get("type") == "text":
                    rows, _ = parse_records_from_block(item.get("text", ""))
                    if rows:
                        return rows, None
            data = obj.get("result", {}).get("data")
            if isinstance(data, list) and data:
                rows = []
                for d in data:
                    rows.append(
                        {
                            "id": d.get("id"),
                            "text": d.get("text"),
                            "created_at": d.get("createdAt") or d.get("createdAtDate"),
                            "username": d.get("authorUsername") or d.get("username"),
                            "likes": d.get("likeCount") or d.get("likes"),
                            "retweets": d.get("retweetCount") or d.get("retweets"),
                        }
                    )
                return rows, None
    return [], None


def save_dedup(tweets: List[Dict]) -> None:
    deduped = {}
    for t in tweets:
        tid = str(t.get("id"))
        if tid and tid not in deduped:
            deduped[tid] = t
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(deduped)} tweets -> {OUTPUT_PATH}")


def collect_topic(client: httpx.Client, topic: str) -> List[Dict]:
    collected: List[Dict] = []
    cursor: Optional[str] = None

    print(f"Initiating stream request for topic: {topic}")
    attempts = 0
    max_attempts = 120  # safety to avoid infinite loops
    seen_ids = set()
    while len(collected) < TARGET_PER_TOPIC and attempts < max_attempts:
        attempts += 1
        rows, cursor = stream_page(client, topic, cursor)
        if not rows:
            print("No rows returned; stopping early to avoid loop.")
            break
        added = 0
        for r in rows:
            rid = str(r.get("id"))
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                collected.append(r)
                added += 1
        print(f"Collected {len(collected)}/{TARGET_PER_TOPIC} so far... (+{added})")
        time.sleep(0.5)  # polite pacing
    # hard cap
    return collected[:TARGET_PER_TOPIC]


def main() -> None:
    client = make_client()
    all_tweets: List[Dict] = []
    for topic in TOPICS:
        topic_tweets = collect_topic(client, topic)
        # attach topic tag
        for t in topic_tweets:
            t["topic"] = topic
        all_tweets.extend(topic_tweets)
    save_dedup(all_tweets)
    print("SUCCESS")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        sys.exit(1)
