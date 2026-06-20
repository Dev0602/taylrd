"""Resume parser and smart keyword extractor."""

from pypdf import PdfReader
import io
import re


def extract_text_from_pdf(file):
    """Extract text from uploaded PDF file."""
    try:
        pdf_reader = PdfReader(io.BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Could not read PDF file: {str(e)}")


def extract_keywords_from_jd(job_description):
    """
    Smartly extract only the most important keywords from a job description.
    Focuses on: technical skills, tools, languages, frameworks, qualifications.
    """

    jd_lower = job_description.lower()

    # ── 1. Known technical keywords to always look for ───────────
    tech_keywords = [
        # Languages
        'python', 'java', 'javascript', 'typescript', 'golang', 'go',
        'c++', 'c#', 'ruby', 'swift', 'kotlin', 'rust', 'scala', 'r',
        'bash', 'shell', 'sql', 'html', 'css', 'php', 'matlab',

        # Frameworks & Libraries
        'react', 'angular', 'vue', 'node', 'node.js', 'express',
        'django', 'flask', 'fastapi', 'spring', 'rails', 'laravel',
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas',
        'numpy', 'opencv', 'nltk', 'huggingface', 'langchain',

        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'jenkins', 'github', 'gitlab', 'ci/cd', 'devops', 'ansible',
        'linux', 'unix', 'nginx', 'apache',

        # Databases
        'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'cassandra', 'dynamodb', 'sqlite', 'oracle', 'firebase',
        'snowflake', 'bigquery',

        # Concepts
        'machine learning', 'deep learning', 'nlp', 'computer vision',
        'data science', 'artificial intelligence', 'api', 'rest',
        'graphql', 'microservices', 'agile', 'scrum', 'oop',
        'algorithms', 'data structures', 'system design',
        'distributed systems', 'cloud computing', 'cybersecurity',
        'blockchain', 'iot', 'reinforcement learning',

        # Tools
        'git', 'jira', 'confluence', 'slack', 'figma', 'postman',
        'tableau', 'powerbi', 'excel', 'spark', 'hadoop', 'kafka',
        'airflow', 'mlflow', 'kubernetes',

        # Soft skills
        'leadership', 'communication', 'collaboration', 'teamwork',
        'problem solving', 'analytical', 'project management',
        'cross-functional', 'mentoring',
    ]

    # Filter to only include keywords that appear in the JD
    matched_tech = [kw for kw in tech_keywords if kw in jd_lower]

    # ── 2. Extract multi-word phrases (2-3 words) ─────────────────
    phrase_patterns = [
        r'\b(full[- ]stack)\b',
        r'\b(back[- ]end|frontend|front[- ]end)\b',
        r'\b(real[- ]time)\b',
        r'\b(open[- ]source)\b',
        r'\b(large[- ]scale)\b',
        r'\b(high[- ]performance)\b',
        r'\b(object[- ]oriented)\b',
        r'\b(test[- ]driven)\b',
        r'\b(cloud[- ]native)\b',
        r'\b(data pipeline)\b',
        r'\b(web application)\b',
        r'\b(mobile application)\b',
        r'\b(software engineer(?:ing)?)\b',
        r'\b(product manager)\b',
        r'\b(data engineer(?:ing)?)\b',
        r'\b(machine learning engineer)\b',
    ]

    phrases_found = []
    for pattern in phrase_patterns:
        matches = re.findall(pattern, jd_lower)
        phrases_found.extend(matches)

    # ── 3. Extract years of experience mentions ───────────────────
    exp_patterns = re.findall(
        r'(\d+\+?\s*years?\s*(?:of\s*)?(?:experience|exp))',
        jd_lower
    )

    # ── 4. Extract education requirements ─────────────────────────
    edu_terms = ["bachelor", "master", "phd", "degree", "computer science",
                 "engineering", "information technology", "b.s", "m.s", "b.tech", "m.tech"]
    edu_keywords = [e for e in edu_terms if e in jd_lower]

    # ── 5. Extract capitalized words (likely proper nouns/tools) ──
    cap_words = re.findall(r'\b([A-Z][a-zA-Z0-9]{2,})\b', job_description)
    cap_filtered = [
        w.lower() for w in cap_words
        if w.lower() not in ['the', 'and', 'for', 'our', 'you', 'your',
                              'will', 'this', 'that', 'with', 'have',
                              'from', 'they', 'what', 'when', 'where',
                              'who', 'how', 'are', 'was', 'been', 'being',
                              'we', 'us', 'can', 'may', 'must', 'shall']
        and len(w) > 2
    ]

    # ── Combine all keywords ──────────────────────────────────────
    all_keywords = list(set(
        matched_tech +
        phrases_found +
        edu_keywords +
        cap_filtered[:15]
    ))

    # Sort by length (longer = more specific)
    all_keywords = sorted(list(set(all_keywords)), key=len, reverse=True)

    # Limit to top 40 most relevant
    return all_keywords[:40]