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

KEYWORD_GENERATION_PROMPT = """You are an expert academic research scout. Your goal is to generate 5-6 highly specific, niche search keywords to find professors who would be a perfect match for a student.

STUDENT INFO:
- Research interests: {research_interests}
- Thesis summary: {thesis_summary}
- Target field: {target_field}
- User-provided custom keywords: {additional_keywords}

GUIDELINES:
1. Combine terms to create specific research niches (e.g., "machine learning for single-cell genomics" instead of just "Bioinformatics").
2. Include technical methods (e.g., "transformer models", "scRNA-seq", "CRISPR") mentioned in the student's background.
3. Generate queries that would work well in academic databases like OpenAlex or Semantic Scholar.
4. If user-provided keywords are present, prioritize including them in the generated queries.
5. Queries should be 2-4 words long.

Return a JSON object:
{{
  "search_queries": ["query1", "query2", "query3", "query4", "query5", "query6"]
}}
"""
