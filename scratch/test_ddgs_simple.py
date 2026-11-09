from duckduckgo_search import DDGS

test_queries = [
    'stage data "La Rochelle"',
    'stage python "Niort"',
    'stage "data engineer" Paris site:welcometothejungle.com',
    'stage "data" site:jobteaser.com Paris',
    'stage developpeur python "La Roche-sur-Yon"',
]

with DDGS() as ddgs:
    for q in test_queries:
        res = list(ddgs.text(q, max_results=3))
        print(f"Query '{q}' -> {len(res)} results")
        for r in res:
            print("   ->", r.get("title"), "|", r.get("href"))
