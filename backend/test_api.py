"""
ProfFinder — Robust test with timeout and full event collection.
"""
import requests
import json
import sys
import time

url = "http://127.0.0.1:8000/api/search"

dummy_cv = """
Kh Mujahidul Islam
Email: mujahidul@example.com
Education: BSc in Biotechnology, University of Dhaka, GPA 3.6/4.0
Research Interests: Bioinformatics, Computational Biology, scRNA-seq analysis, Machine Learning for genomics
Skills: Python, R, PyTorch, TensorFlow, Biopython, Linux, Docker
Experience:
- Research Assistant at Bioinformatics Lab (2024-2025): Worked on single-cell RNA sequencing data analysis.
- Undergraduate thesis: "Deep learning approaches for scRNA-seq cell type classification"
Publications:
- "A machine learning framework for cell type annotation in scRNA-seq data", bioRxiv, 2025.
"""

files = {'cv_file': ('dummy_cv.txt', dummy_cv.encode('utf-8'), 'text/plain')}
data = {
    'target_field': 'Bioinformatics',
    'degree_type': 'MSc',
    'target_countries': 'Canada',
    'intake_sessions': 'Fall 2026',
    'is_international': True,
    'ielts_score': 7.0,
}

print("=" * 60)
print("Running ProfFinder Search Test")
print("=" * 60)

start = time.time()

try:
    response = requests.post(url, files=files, data=data, stream=True, timeout=120)
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"ERROR: {response.text}")
        sys.exit(1)

    events_received = 0
    professor_events = 0

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue

        elapsed = time.time() - start
        if elapsed > 120:
            print(f"\nTIMEOUT after {elapsed:.0f}s")
            break

        if line.startswith('data:'):
            data_content = line[5:].strip()
            if not data_content:
                continue

            try:
                event = json.loads(data_content)
                event_type = event.get('event_type', 'unknown')
                events_received += 1

                if event_type == 'status':
                    agent = event.get('agent', '?')
                    msg = event.get('message', '')
                    prog = event.get('progress', '')
                    print(f"  [{agent}] {msg} ({prog}) [{elapsed:.1f}s]")

                elif event_type == 'professor_result':
                    professor_events += 1
                    prof = event.get('professor', {})
                    name = prof.get('name', '?')
                    uni = prof.get('university', '?')
                    score = prof.get('match_score', 0)
                    tier = prof.get('result_tier', '?')
                    print(f"  >> PROFESSOR: {name} | {uni} | Score: {score} | Tier: {tier}")

                elif event_type == 'agent_output':
                    agent = event.get('agent', '?')
                    data_keys = list(event.get('data', {}).keys())
                    print(f"  [{agent}] Output keys: {data_keys}")

                elif event_type == 'complete':
                    total = event.get('total_professors', 0)
                    high = event.get('high_chance', 0)
                    good = event.get('good_chance', 0)
                    tluck = event.get('try_your_luck', 0)
                    print(f"\n{'=' * 60}")
                    print(f"COMPLETE: {total} professors found")
                    print(f"  High Chance: {high}")
                    print(f"  Good Chance: {good}")
                    print(f"  Try Your Luck: {tluck}")
                    print(f"  Time: {elapsed:.1f}s")
                    print(f"{'=' * 60}")
                    break

                elif event_type == 'error':
                    print(f"  !! ERROR: {event.get('message', '?')}")
                    break

            except json.JSONDecodeError:
                print(f"  [RAW] {data_content[:200]}")
        elif line.startswith('event:'):
            pass  # SSE event name line, skip
        else:
            print(f"  [OTHER] {line[:200]}")

    print(f"\nTotal SSE events received: {events_received}")
    print(f"Professor result events: {professor_events}")

except requests.exceptions.Timeout:
    print("REQUEST TIMED OUT after 120s")
except requests.exceptions.ConnectionError:
    print("CONNECTION ERROR — is the backend running on port 8000?")
except Exception as e:
    print(f"ERROR: {e}")
