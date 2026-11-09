import requests
import feedparser

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0"
}

# Check APEC or Google Alerts RSS formats
urls = [
    # Google Alert RSS format:
    # "https://www.google.com/alerts/feeds/..."
    # Open tech jobs RSS
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://remoteok.com/api",
    "https://hubspot.github.io/remote-jobs/feed.xml"
]

for u in urls:
    try:
        r = requests.get(u, headers=headers, timeout=5)
        print(u, "->", r.status_code, "len:", len(r.content))
    except Exception as e:
        print(u, "-> error:", e)
