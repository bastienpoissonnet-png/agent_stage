from duckduckgo_search import DDGS

queries = [
    'intitle:"stage" ("data engineer" OR "data analyst") Paris -alternance',
    'intitle:"stage" ("développeur python" OR "data") "La Rochelle" -alternance',
    'intitle:"stage" ("informatique" OR "data") "Niort" -alternance',
    '"stage" "data" site:welcometothejungle.com/fr/companies -alternance',
]

with DDGS() as ddgs:
    for q in queries:
        try:
            results = list(ddgs.text(q, max_results=5))
            print(f"Query: {q} -> {len(results)} results")
            for r in results:
                print("   Title:", r.get("title"))
                print("   Link:", r.get("href"))
                print("   Snippet:", r.get("body", "")[:120])
        except Exception as e:
            print("Err:", e)
