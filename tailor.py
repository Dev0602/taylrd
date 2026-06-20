"""Resume tailoring + AI-powered fix suggestions — STRICT HONESTY MODE."""

import re
import json


def tailor_resume(client, resume_text, job_description, keywords):
    """Tailors resume. STRICT: only uses facts from the original resume."""

    missing = [k for k in keywords if k.lower() not in resume_text.lower()]
    missing_str = ', '.join(missing) if missing else 'None'

    prompt = f"""You are an expert resume writer. Rewrite the resume below to score 85%+ on ATS systems.

═══════════════════════════════════════════════════
🚨 CRITICAL HONESTY RULES — NEVER VIOLATE 🚨
═══════════════════════════════════════════════════

ABSOLUTE RULES:
1. NEVER add skills the candidate didn't list in the original resume
2. NEVER add programming languages they didn't mention (e.g. if they don't have Rust/Scala/R, DO NOT ADD THEM)
3. NEVER add technologies/tools/frameworks not in the original
4. NEVER invent new bullet points or experiences (e.g. "mentored 2 junior developers" if not stated)
5. NEVER add false claims (e.g. "SMTP email service" if they didn't build one)
6. NEVER change job dates — keep EXACT dates from original resume
7. NEVER add fake metrics — only use numbers already present or reasonable estimates of EXISTING work
8. NEVER invent certifications or coursework
9. NEVER add "Domain Expertise" or made-up skill categories

WHAT YOU CAN DO:
✓ Reword existing bullets with stronger action verbs
✓ Add measurable numbers ONLY if reasonable for existing work
✓ Reorder skills/bullets for emphasis
✓ Use synonyms for keywords ONLY if the candidate actually has those skills
✓ Improve grammar and clarity
✓ Make bullets more impactful using language from existing work

WHAT TO DO WITH MISSING KEYWORDS:
- If the candidate clearly has the skill (mentioned elsewhere or in projects), include it
- If they DON'T have the skill — DO NOT ADD IT, leave as missing
- The goal is HONEST keyword matching, not faking credentials

═══════════════════════════════════════════════════
CRITICAL OUTPUT FORMAT — MUST FOLLOW EXACTLY:
═══════════════════════════════════════════════════

Output structure:
  Line 1: Full Name (no extras)
  Line 2: phone | email | github | linkedin
  Blank line
  Section header in ALL CAPS (e.g. EDUCATION)
  Then entries — each entry is 2 lines + bullets

FOR EDUCATION ENTRIES — use this EXACT 2-line format:
  University Name, Location    May 2026
  Degree Name
  Coursework: subject 1, subject 2, subject 3

(Note: TWO OR MORE SPACES between university and date)

FOR EXPERIENCE ENTRIES — use this EXACT 2-line format:
  Company Name    Jan 2023 - May 2024
  Job Title
  • Bullet 1 with action verb + result + number
  • Bullet 2 with action verb + result + number

(Note: TWO OR MORE SPACES between company name and date)
(Note: Job title is on its OWN line)
(Note: KEEP EXACT DATES FROM ORIGINAL — DO NOT CHANGE)

FOR PROJECT ENTRIES — use this EXACT 2-line format:
  Project Name | Python, Flask, JavaScript    May 2025
  • Bullet 1 with action verb + result + number

FOR SKILLS — use this format with COLON:
  Languages: Python, Java, C++, JavaScript
  Frameworks: Flask, ReactJS, Django

═══════════════════════════════════════════════════
EXAMPLE:
═══════════════════════════════════════════════════

John Smith
(555) 123-4567 | john@email.com | github.com/john | linkedin.com/in/john

EDUCATION
New York University, Brooklyn, NY    May 2026
Master of Science in Computer Science
Coursework: Machine Learning, Algorithms, Big Data

TECHNICAL SKILLS
Languages: Python, Java, C++, JavaScript
Frameworks: Flask, ReactJS, Django

EXPERIENCE
HCL Technologies    Jan 2023 - May 2024
Software Engineer Intern
• Engineered authentication system serving 1,000+ users, reducing access by 60%
• Built RESTful APIs processing 500+ requests/min with sub-200ms latency

═══════════════════════════════════════════════════
SUGGESTED KEYWORDS TO ADD (ONLY if candidate truly has them):
═══════════════════════════════════════════════════
{missing_str}

⚠️ If a keyword above is NOT actually a skill the candidate has based on the original resume, LEAVE IT OUT. Better to score lower than to lie.

═══════════════════════════════════════════════════
CONTENT RULES:
═══════════════════════════════════════════════════

1. Every bullet: action verb + what you did + measurable result
2. Action verbs: Built, Led, Engineered, Designed, Deployed, Optimized, Scaled
3. Add numbers to bullets ONLY if reasonable for existing work
4. NO markdown — NO **bold**, NO *italic*, NO backticks
5. Use • symbol for bullets (not - or *)
6. Use plain dashes for dates, NOT em-dashes
7. TWO SPACES between left content and right date

═══════════════════════════════════════════════════
JOB DESCRIPTION:
═══════════════════════════════════════════════════
{job_description}

═══════════════════════════════════════════════════
ORIGINAL RESUME (USE ONLY FACTS FROM HERE):
═══════════════════════════════════════════════════
{resume_text}

═══════════════════════════════════════════════════
Return ONLY the plain text resume in the EXACT format above.
Use ONLY facts from the original resume. NO HALLUCINATIONS.
No explanations. No markdown. No code blocks.
═══════════════════════════════════════════════════
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    result = message.content[0].text.strip()

    # Cleanup markdown artifacts
    result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)
    result = re.sub(r'\*(.+?)\*', r'\1', result)
    result = result.replace('`', '')
    result = re.sub(r'^#{1,6}\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'^\s*[-–]\s+', '• ', result, flags=re.MULTILINE)
    result = re.sub(r'^(black|white|red|blue|green|gray)\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()

    # Calculate skipped keywords (AI honestly didn't add them)
    skipped_keywords = [k for k in missing if k.lower() not in result.lower()]

    return {
        'resume': result,
        'skipped_keywords': skipped_keywords,
    }


def generate_cover_letter(client, resume_text, job_description):
    """Generates a professional cover letter — using only real facts."""

    prompt = f"""You are an expert cover letter writer.

🚨 STRICT HONESTY RULES:
- Use ONLY achievements/skills mentioned in the resume below
- NEVER invent experiences, metrics, or skills
- NEVER claim things the candidate hasn't actually done
- Reference SPECIFIC items from their real resume

Write a professional cover letter with this structure:

Paragraph 1 (2-3 sentences):
- Why you want THIS specific role at THIS specific company

Paragraph 2 (3-4 sentences):
- Top 2-3 most relevant REAL achievements WITH numbers from the resume

Paragraph 3 (2-3 sentences):
- Strong closing with call to action

RULES:
- Sound natural and human
- No placeholders like [Your Name]
- No markdown, no bold, no bullets
- End signature with EACH ITEM ON ITS OWN LINE:

Best regards,
Full Name
Phone Number
Email Address

RESUME (ONLY USE FACTS FROM HERE):
{resume_text}

JOB DESCRIPTION:
{job_description}

Return ONLY the cover letter text. Start with "Dear Hiring".
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    result = message.content[0].text.strip()
    result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)
    result = re.sub(r'\*(.+?)\*', r'\1', result)
    result = result.replace('`', '')
    return result.strip()


# ═══════════════════════════════════════════════════════════════
# AI-powered fix suggestions (3 options per issue)
# Also honesty-checked
# ═══════════════════════════════════════════════════════════════

def get_fix_suggestions(client, resume_text, issue, job_description=''):
    """Generate 3 different fix suggestions for a specific issue."""

    category = issue.get('category', '')
    issue_text = issue.get('issue', '')
    fix_hint = issue.get('fix', '')

    jd_section = ''
    if job_description:
        jd_section = 'JOB DESCRIPTION FOR CONTEXT:\n' + job_description

    prompt = f"""You are a professional resume coach. Generate exactly 3 different ways to fix this specific issue.

🚨 STRICT HONESTY RULES:
- Use ONLY facts from the candidate's current resume
- NEVER add fake skills, languages, or experiences
- NEVER invent new bullet points with made-up details
- Improve wording and emphasis, not the underlying facts

ISSUE TO FIX:
- Category: {category}
- Problem: {issue_text}
- Suggested Direction: {fix_hint}

CURRENT RESUME:
{resume_text}

{jd_section}

═══════════════════════════════════════════════════
TASK:
═══════════════════════════════════════════════════

Generate 3 different ways to fix this issue. Each option should:
1. Address ONLY the specific issue above (don't rewrite the whole resume)
2. Keep the same plain-text format (sections in CAPS, • bullets, dates after 2+ spaces)
3. Keep ALL other content unchanged
4. Be a complete resume text ready to use
5. NEVER add false skills or fake experiences

The 3 options should be DIFFERENT approaches:
- Option 1: CONSERVATIVE — minimal changes, safest fix
- Option 2: BALANCED — moderate improvements
- Option 3: AGGRESSIVE — bold rewrite with maximum impact (still honest!)

Return ONLY valid JSON in this EXACT format (no markdown, no code blocks):
{{
  "options": [
    {{
      "title": "Conservative",
      "description": "Brief 1-line summary of what changed",
      "modified_resume": "FULL RESUME TEXT HERE"
    }},
    {{
      "title": "Balanced",
      "description": "Brief 1-line summary of what changed",
      "modified_resume": "FULL RESUME TEXT HERE"
    }},
    {{
      "title": "Aggressive",
      "description": "Brief 1-line summary of what changed",
      "modified_resume": "FULL RESUME TEXT HERE"
    }}
  ]
}}

CRITICAL:
- Return ONLY the JSON, nothing else
- No markdown code fences
- No explanations
- Valid JSON (escape quotes/newlines)
- Each modified_resume must be the COMPLETE resume text
- NO HALLUCINATIONS — only real facts
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()
    response_text = re.sub(r'^```json\s*', '', response_text)
    response_text = re.sub(r'^```\s*', '', response_text)
    response_text = re.sub(r'\s*```$', '', response_text)
    response_text = response_text.strip()

    try:
        data = json.loads(response_text)
        options = data.get('options', [])

        for opt in options:
            r = opt.get('modified_resume', '')
            r = re.sub(r'\*\*(.+?)\*\*', r'\1', r)
            r = re.sub(r'\*(.+?)\*', r'\1', r)
            r = r.replace('`', '')
            opt['modified_resume'] = r.strip()

        return options[:3]

    except json.JSONDecodeError:
        return [{
            'title': 'AI Suggestion',
            'description': f'Apply the fix: {fix_hint}',
            'modified_resume': resume_text,
        }]