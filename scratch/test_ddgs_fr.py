from duckduckgo_search import DDGS

with DDGS() as ddgs:
    q = 'site:welcometothejungle.com/fr/companies "stage" ("data engineer" OR "developpeur python")'
    results = list(ddgs.text(q, region="fr-fr", max_results=5))
    print(f"Results for '{q}': {len(results)}")
    for r in results:
        print(" ->", r.get("title"), "|", r.get("href"))
        print("    Desc:", r.get("body", "")[:100])
