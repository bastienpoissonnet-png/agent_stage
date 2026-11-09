from duckduckgo_search import DDGS

try:
    with DDGS() as ddgs:
        query = 'stage ("data" OR "python") ("la rochelle" OR "niort" OR "paris" OR "vendée") (site:jobteaser.com OR site:welcometothejungle.com OR site:hellowork.com)'
        results = list(ddgs.text(query, max_results=10))
        print("DDGS count:", len(results))
        for r in results[:5]:
            print(" -", r.get("title"), "|", r.get("href"))
except Exception as e:
    print("DDGS error:", e)
