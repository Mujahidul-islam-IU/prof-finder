
import asyncio
from app.services import semantic_scholar

async def main():
    queries = ["Bioinformatics Canada", "Machine Learning Canada", "Artificial Intelligence Canada"]
    for q in queries:
        print(f"\nTesting query: {q}")
        results = await semantic_scholar.search_authors(q, limit=5)
        print(f"Found {len(results)} results")
        for r in results:
            print(f"- {r.get('name')} (Papers: {r.get('paperCount')})")

if __name__ == "__main__":
    asyncio.run(main())
