"""
ProfFinder — LLM Prompts
All prompt templates for the 6 agents.
"""

# ═══════════════════════════════════════════════════════════════
# A1 — PROFILE ANALYSIS & TIER CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

TIER_CLASSIFICATION_PROMPT = """You are an expert academic admissions advisor. Based on the student's profile below, classify them into an academic tier for graduate school applications.

STUDENT PROFILE:
- GPA (normalized to 4.0): {gpa_normalized}
- University: {university}
- Degree: {degree_details}
- IELTS Score: {ielts_score}
- GRE Score: {gre_score}
- Publications: {publications_count} ({verified_count} verified on Semantic Scholar)
- Publication details: {publications}
- Research interests: {research_interests}
- Skills: {skills}
- Thesis/Research: {thesis_summary}
- Work experience: {work_experience}

TIER DEFINITIONS:
- Tier A: Strong candidate for top-100 universities. Typically: GPA >= 3.5/4.0, 1+ publications in HIGH-IMPACT indexed venues (Q1/Q2 journals, top conferences like CVPR, NeurIPS, ISMB), OR 3+ standard publications, strong research alignment.
- Tier B: Competitive for rank 100-400 universities. GPA >= 3.0/4.0, 0-1 publications, or several local publications, decent research background.
- Tier C: Suitable for rank 500+ or regional universities. GPA < 3.0/4.0, no publications, limited research.

IMPORTANT RULES:
- PRIORITIZE QUALITY: A single paper in a top-tier international journal (e.g., Nature, IEEE, ISMB) is worth more than 5 low-tier local papers.
- A student from a well-ranked university with strong research gets a tier boost.
- If a student has verified publications on Semantic Scholar with citations, this is a strong indicator of Tier A potential regardless of slightly lower GPA.

Return a JSON object:
{{
  "tier": "A" | "B" | "C",
  "reasoning": "2-3 sentence justification for the tier assignment",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "recommended_focus": "Brief advice on what would strengthen their application"
}}
"""


# ═══════════════════════════════════════════════════════════════
# A2 — COUNTRY RANKING
# ═══════════════════════════════════════════════════════════════

COUNTRY_RANKING_PROMPT = """You are an expert graduate school advisor for Bangladeshi international students. Rank the following countries for a {degree_type} student in {target_field}.

STUDENT TIER: {tier} (A=top-100 viable, B=100-400, C=500+ regional)
GPA: {gpa_normalized}/4.0
IELTS: {ielts_score}
GRE: {gre_score}

COUNTRIES TO RANK: {countries}

SEARCH RESULTS FOR CONTEXT:
{search_results}

Score each country on these 5 dimensions (each 0-100):
1. Funding Availability (30% weight) - How likely is funded position for this student's tier?
2. Admission Competitiveness (25% weight) - How competitive is admission vs this student's tier?
3. Post-Study Work Rights (20% weight) - Post-study work visa, PR pathway for BD nationals?
4. Visa Ease (15% weight) - Visa approval rates and process for Bangladeshi students?
5. Language Barrier (10% weight) - Is English sufficient or is local language needed?

Return JSON array:
[
  {{
    "country": "country name",
    "funding_score": 0-100,
    "admission_score": 0-100,
    "work_rights_score": 0-100,
    "visa_score": 0-100,
    "language_score": 0-100,
    "overall_score": weighted average,
    "search_priority": "high" | "normal",
    "reasoning": "2-3 sentences explaining ranking"
  }}
]

RULES:
- search_priority = "high" if overall_score >= 70, else "normal"
- Be realistic about BD student success rates per country
- Consider current (2025-2026) policies and trends
- More professors/universities to search in high-priority countries
"""


# ═══════════════════════════════════════════════════════════════
# A4 — LAB PAGE EXTRACTION (CONSERVATIVE)
# ═══════════════════════════════════════════════════════════════

LAB_PAGE_EXTRACTION_PROMPT = """You are extracting information from a professor's lab/personal webpage. Be EXTREMELY CONSERVATIVE — only extract what is EXPLICITLY stated.

PROFESSOR: {professor_name}
UNIVERSITY: {university}

WEB PAGE CONTENT:
{page_content}

Extract the following. For EACH field, if the information is NOT explicitly and clearly stated on the page, return null.

Return JSON:
{{
  "email": "professor's email if explicitly shown, null otherwise",
  "email_source": "scraped_direct" if email found on page, "inferred" if constructed from pattern, null if not found,
  "email_confidence": 0.0-1.0 (1.0 only if email is explicitly displayed),
  "funding_status": "funded" ONLY if the page EXPLICITLY states they have funding/positions/openings. "unknown" for everything else,
  "funding_source_url": "URL where funding info was found, null if unknown",
  "funding_confidence": 0.0-1.0,
  "student_count": number of current students if explicitly listed, null otherwise,
  "lab_description": "1-2 sentence summary of research focus",
  "recent_openings": "Any text about prospective students or openings, null if none"
}}

CRITICAL RULES:
- funding_status = "funded" ONLY if you see explicit phrases like:
  "PhD positions available", "funded position", "looking for students",
  "openings in my lab", "RA/TA positions", "scholarship available"
- DO NOT mark as "funded" based on:
  "We are a research lab" (every lab says this)
  "Join our team" (generic)
  Having current students (doesn't mean new positions open)
- If even slightly ambiguous → funding_status = "unknown"
- For email: prefer official university email over personal
- email_confidence = 1.0 ONLY if email is directly visible on page
- email_confidence = 0.5 if email is inferred from name pattern (e.g., firstname.lastname@uni.edu)
"""


# ═══════════════════════════════════════════════════════════════
# A5 — PROGRAM REQUIREMENTS EXTRACTION
# ═══════════════════════════════════════════════════════════════

REQUIREMENTS_EXTRACTION_PROMPT = """You are extracting graduate program admission requirements from university web pages. Be precise and extract ONLY explicitly stated information.

UNIVERSITY: {university}
DEPARTMENT: {department}
DEGREE: {degree_type}

WEB CONTENT:
{web_content}

Extract requirements. If ANY field is not explicitly stated, return null for that field.

Return JSON:
{{
  "program_name": "Official program name if found",
  "deadline_fall": "YYYY-MM-DD format if found, null otherwise",
  "deadline_spring": "YYYY-MM-DD format if found, null otherwise",
  "deadline_type": "fixed" | "rolling" | "unknown",
  "gre_required": "required" | "optional" | "not_required" | "unknown",
  "ielts_required": true | false | null,
  "ielts_min_score": 6.5 or whatever minimum, null if not stated,
  "wes_required": true | false | null,
  "application_fee_usd": integer in USD, null if not stated,
  "source_url": "URL where info was found",
  "confidence": 0.0-1.0 overall confidence in extracted data,
  "notes": "Any important caveats or additional info"
}}

RULES:
- Distinguish between INTERNATIONAL and DOMESTIC deadlines. Prioritize international.
- If only one deadline is given with no season label, assume Fall.
- For fees, convert to USD if stated in other currencies (approximate).
- WES evaluation is often required for international students from specific countries.
- confidence = 1.0 only if source is official university admissions page.
- confidence = 0.5-0.8 for departmental pages or indirect sources.
- confidence < 0.5 for blog posts, forums, or outdated content.
"""


# ═══════════════════════════════════════════════════════════════
# A6 — COLD EMAIL DRAFTING
# ═══════════════════════════════════════════════════════════════

COLD_EMAIL_PROMPT = """Write a cold email from a prospective {degree_type} student to a professor. The email must feel natural, specific, and demonstrate genuine research understanding.

PROFESSOR: {professor_name}
DEPARTMENT: {department}, {university}
INTAKE SESSION: {intake_session}

PROFESSOR'S PAPERS (selected by student):
{selected_papers}

STUDENT'S RESEARCH SUMMARY:
{student_research_summary}

STUDENT'S STRONGEST PUBLICATION:
{strongest_publication}

Write a professional cold email with these STRICT constraints:
1. MUST reference at least one specific paper by its actual title
2. MUST make a concrete, specific connection between the professor's paper and the student's own research/experience
3. MUST be under 200 words
4. MUST NOT use any of these clichés:
   - "I am highly motivated"
   - "I came across your profile"
   - "I am passionate about"
   - "I would be honored"
   - "your groundbreaking work"
   - Any generic flattery
5. MUST NOT ask about funding directly
6. MUST sound like a real human, not an AI-generated template
7. Include a clear, specific question or proposed collaboration point
8. End with a brief, professional sign-off

TONE: Direct, specific, confident but not arrogant. Like one researcher writing to another.

Return JSON:
{{
  "subject": "Email subject line (specific, not generic)",
    "body": "The email body text",
    "word_count": number of words in body
  }}
  """


# ═══════════════════════════════════════════════════════════════
# A3 — KEYWORD GENERATION
# ═══════════════════════════════════════════════════════════════

KEYWORD_GENERATION_PROMPT = """You are an expert academic research scout helping a student find their perfect professor match. Generate two types of search queries.

STUDENT INFO:
- Research interests: {research_interests}
- Thesis summary: {thesis_summary}
- Target field: {target_field}
- User-provided custom keywords: {additional_keywords}

GENERATE TWO TYPES OF QUERIES:

1. **web_queries** (5-6 queries): Natural language queries a real student would type into Google to find professors. Be VERY specific — combine methods + disease/domain + "professor" or "lab".
   Examples:
   - "single-cell RNA sequencing cancer biomarkers professor lab"
   - "computational biology WGCNA gene co-expression research group"
   - "machine learning drug discovery molecular docking professor"

2. **academic_queries** (5-6 queries): Structured queries for academic paper databases. 4-7 words, combining specific methods with specific biological domains.
   Examples:
   - "single-cell RNA sequencing intellectual disability biomarkers"
   - "WGCNA kidney cancer staging machine learning"
   - "protein-protein interaction network neurodevelopmental disorders"

RULES:
- Queries MUST be 4-7 words long and highly specific to the student's niche
- Include the student's SPECIFIC methods (e.g., Seurat, WGCNA, molecular docking) not generic terms
- Include SPECIFIC diseases/domains from their publications, not broad fields
- If user-provided keywords are present, prioritize them
- DO NOT generate generic queries like "bioinformatics" or "machine learning"

Return a JSON object:
{{
  "web_queries": ["query1", "query2", "query3", "query4", "query5"],
  "academic_queries": ["query1", "query2", "query3", "query4", "query5"]
}}
"""


# ═══════════════════════════════════════════════════════════════
# A4 — PROFESSOR MATCH SCORING (LLM Multi-Dimensional)
# ═══════════════════════════════════════════════════════════════

PROFESSOR_MATCH_SCORING_PROMPT = """You are an expert graduate school advisor. Score how well this professor matches this prospective student for a {degree_type} program.

STUDENT PROFILE:
- Name: {student_name}
- Research interests: {research_interests}
- Publications: {publications}
- Skills/Methods: {skills}
- Target field: {target_field}
- Thesis/Research: {thesis_summary}

PROFESSOR:
- Name: {professor_name}
- University: {university}, {country}
- Department: {department}
- Recent paper titles and abstracts:
{paper_titles_and_abstracts}
- Lab page summary: {lab_page_summary}

Score on these dimensions (0-100 each):
1. **bio_fit**: How much do their BIOLOGICAL research topics overlap? Consider: diseases studied, cell types, organisms, biological questions.
2. **ml_fit**: How much do their COMPUTATIONAL methods/tools overlap? Consider: programming languages, bioinformatics tools (Seurat, WGCNA, etc.), ML frameworks, analysis pipelines.
3. **overall**: Overall match considering research topic + methods + career fit for a {degree_type} student.

SCORING GUIDELINES:
- 90-100: Nearly identical research niche. The student could start contributing to the lab immediately.
- 75-89: Strong overlap in either biology or methods, with good overlap in the other.
- 60-74: Moderate overlap. The student would need some ramp-up but has relevant transferable skills.
- 40-59: Weak overlap. Only broadly related field.
- 0-39: Minimal or no meaningful connection.

Return JSON:
{{
  "bio_fit": 0-100,
  "ml_fit": 0-100,
  "overall": 0-100,
  "research_tags": ["tag1", "tag2", "tag3", "tag4"],
  "match_reasoning": "2-3 sentences explaining WHY this is a match. Be SPECIFIC — mention exact papers, tools, or topics that overlap. Do not be generic.",
  "match_warning": "1 sentence caveat about potential misalignment, or null if none"
}}
"""


# ═══════════════════════════════════════════════════════════════
# A3 — PROFESSOR EXTRACTION FROM WEB SEARCH
# ═══════════════════════════════════════════════════════════════

PROFESSOR_EXTRACTION_PROMPT = """You are extracting professor names and affiliations from web search results. The goal is to find individual professors/researchers who work in the specified field.

TARGET FIELD: {target_field}
COUNTRY: {country}

WEB SEARCH RESULTS:
{search_results}

Extract all individual professors/researchers mentioned. For each, provide:
- name: Full name (e.g., "Jiarui Ding", "Tallulah Andrews")
- university: Their university or institution
- department: Their department if mentioned

RULES:
- ONLY extract names of individual researchers, NOT organizations, consortiums, or groups
- ONLY extract researchers who appear to work in or near the target field
- If a name appears multiple times, include it only once
- Skip names where you're unsure if they are a professor/PI
- Maximum 10 professors per extraction

Return JSON:
{{
  "professors": [
    {{
      "name": "Full Name",
      "university": "University Name",
      "department": "Department if known, empty string otherwise"
    }}
  ]
}}
"""
