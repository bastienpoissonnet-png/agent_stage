from ddgs import DDGS

with DDGS() as d:
    queries = [
        'site:welcometothejungle.com/fr/companies "stage" "data" Paris',
        'site:jobteaser.com/fr/job-offers "stage" "data" Paris',
        'site:welcometothejungle.com/fr/companies "stage" ("python" OR "data")',
    ]
    for q in queries:
        print("Query:", q)
        res = list(d.text(q, max_results=3))
        for r in res:
            print("  ->", r.get("title"))
            print("     URL:", r.get("href"))
