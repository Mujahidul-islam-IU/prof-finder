
import asyncio
from app.services import semantic_scholar

async def main():
    queries = ["Bioinformatics Canada", "Machine Learning Canada", "Artificial Intelligence Canada"]
    for q in queries:
        print(f"\nTesting query: {q}")
        results = await semantic_scholar.search_papers(q, limit=5)
        print(f"Found {len(results)} results")
        for r in results:
            authors = [a.get("name") for a in r.get("authors", [])]
            print(f"- \"{r.get('title')[:60]}...\" (Authors: {', '.join(authors[:2])})")

if __name__ == "__main__":
    asyncio.run(main())
