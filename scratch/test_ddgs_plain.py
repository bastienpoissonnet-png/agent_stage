from duckduckgo_search import DDGS

queries = [
    'stage data engineer paris',
    'stage developpeur python la rochelle',
    'stage data niort',
    'stage developpeur informatiques vendee la roche sur yon',
    'stage intelligence artificielle paris',
]

with DDGS() as ddgs:
    for q in queries:
        try:
            results = list(ddgs.text(q, max_results=3))
            print(f"Query: '{q}' -> {len(results)} results")
            for r in results:
                print("   Title:", r.get("title"))
                print("   Link:", r.get("href"))
                print("   Snippet:", r.get("body", "")[:100])
        except Exception as e:
            print("Err:", e)
