import requests
import json

url = "http://127.0.0.1:8000/api/search"

# We'll create a dummy text that looks like a CV to feed the agents
dummy_cv = """
John Doe
Email: john.doe@example.com
Education: BSc in Computer Science, State University, GPA 3.9/4.0
Research Interests: Machine Learning, Natural Language Processing, AI Agents
Skills: Python, PyTorch, React
Experience: 
- Research Assistant at AI Lab (2025-2026): Worked on LLM agent optimization.
Publications:
- \"Enhancing LLM reasoning\", arXiv, 2026.
"""

files = {'cv_file': ('dummy_cv.txt', dummy_cv.encode('utf-8'), 'text/plain')}
data = {
    'target_field': 'Computer Science (AI/ML)',
    'degree_type': 'MSc',
    'target_countries': 'USA, Canada',
    'intake_sessions': 'Fall 2026',
    'is_international': True,
    'ielts_score': 8.0,
    'gre_score': 325
}

print("Running Search API with a mock profile...")
response = requests.post(url, files=files, data=data, stream=True)
print(f"Status Code: {response.status_code}")

# Read Server-Sent Events from the response
for line in response.iter_lines():
    if line:
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith('data: '):
            data_content = decoded_line[6:]
            try:
                event_data = json.loads(data_content)
                event_type = event_data.get('event_type', 'unknown')
                print(f"[{event_type.upper()}] {data_content[:300]}")
                if event_type == 'error':
                    print("Error occurred, stopping.")
                    break
                elif event_type == 'complete':
                    print("Search pipeline completed.")
                    break
            except json.JSONDecodeError:
                print(f"Raw data: {data_content}")
        else:
            print(decoded_line)
