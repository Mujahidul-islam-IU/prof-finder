"""Test OpenAlex API directly to verify paper search works."""
import asyncio
import sys
sys.path.insert(0, ".")


async def test_openalex():
    from app.services import openalex

    print("=" * 60)
    print("TEST 1: search_works() - Search papers by keyword + country")
    print("=" * 60)
    results = await openalex.search_works(
        query="bioinformatics scRNA-seq",
        institution_country="CA",
        year_from=2020,
        limit=5,
    )
    print(f"Found {len(results)} papers")
    for r in results:
        print(f"  Title: {r['title']}")
        print(f"  Year: {r['year']} | Venue: {r['venue']}")
        print(f"  Authors ({len(r['authors'])}):")
        for a in r['authors'][:3]:
            print(f"    - {a['name']} ({a['institution']}, {a['institution_country']})")
        print()

    print("=" * 60)
    print("TEST 2: get_author_works() - Get papers by author ID")
    print("=" * 60)
    if results and results[0]['authors']:
        author_id = results[0]['authors'][0]['openalex_id']
        print(f"Testing with author ID: {author_id}")
        works = await openalex.get_author_works(author_id, limit=5, year_from=2020)
        print(f"Found {len(works)} works")
        for w in works:
            print(f"  {w['title']} ({w['year']})")
    else:
        print("No authors to test with")

    print("\n" + "=" * 60)
    print("TEST 3: search_works() without country filter")
    print("=" * 60)
    results2 = await openalex.search_works(
        query="bioinformatics machine learning",
        year_from=2020,
        limit=5,
    )
    print(f"Found {len(results2)} papers")
    for r in results2:
        print(f"  {r['title']} ({r['year']})")
        for a in r['authors'][:2]:
            print(f"    - {a['name']} ({a['institution']})")
        print()


asyncio.run(test_openalex())
