import requests
import feedparser

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 1. Indeed RSS
try:
    url_indeed = "https://fr.indeed.com/rss?q=stage+data+python&l=France"
    r = requests.get(url_indeed, headers=headers, timeout=5)
    print("Indeed RSS status:", r.status_code, "len:", len(r.text))
    feed = feedparser.parse(r.text)
    print("Indeed items count:", len(feed.entries))
    if feed.entries:
        print("Sample Indeed item:", feed.entries[0].title, "|", getattr(feed.entries[0], "link", ""))
except Exception as e:
    print("Indeed error:", e)

# 2. Arbeitnow API (European tech jobs, free open API)
try:
    url_arbeit = "https://www.arbeitnow.com/api/job-board-api"
    r = requests.get(url_arbeit, headers=headers, timeout=5)
    print("Arbeitnow status:", r.status_code)
    if r.status_code == 200:
        data = r.json().get("data", [])
        print("Arbeitnow items count:", len(data))
        if data:
            print("Sample Arbeitnow item:", data[0].get("title"), "|", data[0].get("company_name"), "|", data[0].get("location"))
except Exception as e:
    print("Arbeitnow error:", e)

# 3. Google Jobs RSS via public bridge or WeLoveDevs
for url in [
    "https://welovedevs.com/fr/feed",
    "https://welovedevs.com/feed.xml",
    "https://remotive.com/api/remote-jobs?category=data",
    "https://remotive.com/api/remote-jobs?category=software-dev",
    "https://jobicy.com/api/v2/remote-jobs?count=20&geo=france",
    "https://jobicy.com/api/v2/remote-jobs?count=20&industry=data-science"
]:
    try:
        res = requests.get(url, headers=headers, timeout=5)
        print(url, "->", res.status_code, len(res.content))
    except Exception as e:
        print(url, "error:", e)
