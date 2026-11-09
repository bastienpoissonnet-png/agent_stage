from ddgs import DDGS

with DDGS() as d:
    # Test searches
    for query in [
        'stage data python "La Rochelle"',
        'stage "data engineer" Paris job',
        'stage "python" Niort',
        'stage data "Paris" job',
    ]:
        print("Query:", query)
        try:
            results = list(d.text(query, max_results=3))
            for r in results:
                print("  ->", r.get("title"), "|", r.get("href"))
        except Exception as e:
            print("  -> Err:", e)
