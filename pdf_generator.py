"""PDF generator — 3 templates. Summary section only in Template 3."""

import subprocess
import os
import tempfile
import re


# ═══════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════

def escape_latex(text):
    chars = {
        '&':  '\\&', '%':  '\\%', '$':  '\\$', '#':  '\\#',
        '_':  '\\_', '{':  '\\{', '}':  '\\}',
        '~':  '\\textasciitilde{}', '^':  '\\^{}',
        '<':  '\\textless{}', '>':  '\\textgreater{}',
    }
    for c, r in chars.items():
        text = text.replace(c, r)
    return text


def parse_resume(resume_text):
    """Parse AI resume text into structured entries."""
    cleaned = resume_text.strip()
    cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*(.+?)\*', r'\1', cleaned)
    cleaned = cleaned.replace('`', '')
    cleaned = re.sub(r'^(black|white|red|blue|green|gray)\s*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\\color\{[^}]+\}', '', cleaned)

    lines = cleaned.split('\n')

    SECTION_KEYWORDS = {
        'EDUCATION', 'TECHNICAL SKILLS', 'SKILLS', 'EXPERIENCE',
        'WORK EXPERIENCE', 'PROJECTS', 'CERTIFICATIONS', 'AWARDS',
        'PUBLICATIONS', 'SUMMARY', 'OBJECTIVE',
    }

    name = ''
    contact_raw = ''
    sections = []
    current_section = None
    current_entries = []
    current_entry = None

    def flush_entry():
        nonlocal current_entry
        if current_entry:
            current_entries.append(current_entry)
            current_entry = None

    def flush_section():
        nonlocal current_entries
        flush_entry()
        if current_section and current_entries:
            sections.append({'title': current_section, 'entries': current_entries})
        current_entries = []

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            continue

        if not name:
            name = stripped
            continue

        if not contact_raw and ('|' in stripped or '@' in stripped):
            contact_raw = stripped
            continue

        upper = stripped.upper()
        if (len(stripped) < 60 and upper in SECTION_KEYWORDS) or \
           (stripped == stripped.upper() and len(stripped) > 2 and len(stripped) < 60 and
            not stripped.startswith(('•','-','*'))):
            flush_section()
            current_section = stripped.upper()
            continue

        if stripped.startswith(('•', '-', '*', '\u2022')):
            bullet_text = stripped.lstrip('•-*\u2022 ').strip()
            if current_entry is None:
                current_entry = {'header_left': '', 'header_right': '',
                                 'sub': '', 'bullets': []}
            current_entry['bullets'].append(bullet_text)
            continue

        skill_m = re.match(r'^([A-Za-z][^:]{2,50}):\s*(.+)$', stripped)
        if skill_m and current_section and ('SKILL' in current_section):
            flush_entry()
            current_entries.append({
                'header_left': skill_m.group(1).strip(),
                'header_right': '',
                'sub': skill_m.group(2).strip(),
                'bullets': [],
                'is_skill': True,
            })
            continue

        parts = re.split(r'\s{2,}', stripped, maxsplit=1)
        if len(parts) == 2:
            flush_entry()
            current_entry = {
                'header_left':  parts[0].strip(),
                'header_right': parts[1].strip(),
                'sub': '',
                'bullets': [],
            }
            continue

        if current_entry and not current_entry['sub']:
            current_entry['sub'] = stripped
            continue

        if current_entry:
            if current_entry['sub']:
                current_entry['sub'] += '\n' + stripped
            else:
                current_entry['sub'] = stripped
        else:
            current_entry = {'header_left': stripped, 'header_right': '',
                             'sub': '', 'bullets': []}

    flush_section()

    contact_parts = [p.strip() for p in contact_raw.split('|') if p.strip()] if contact_raw else []

    return {'name': name, 'contact': contact_parts, 'sections': sections}


def _is_summary_section(section):
    """Check if a section is a Summary/Objective section."""
    title_upper = section['title'].upper()
    return 'SUMMARY' in title_upper or 'OBJECTIVE' in title_upper or 'PROFILE' in title_upper


def _find_pdflatex():
    for path in ['/Library/TeX/texbin/pdflatex', '/usr/local/bin/pdflatex',
                 '/usr/bin/pdflatex', 'pdflatex']:
        try:
            r = subprocess.run([path, '--version'], capture_output=True, text=True)
            if r.returncode == 0:
                return path
        except FileNotFoundError:
            continue
    return None


def _compile(latex):
    pdflatex = _find_pdflatex()
    if not pdflatex:
        raise Exception("pdflatex not found.")
    with tempfile.TemporaryDirectory() as tmpdir:
        tex = os.path.join(tmpdir, 'doc.tex')
        pdf = os.path.join(tmpdir, 'doc.pdf')
        with open(tex, 'w', encoding='utf-8') as f:
            f.write(latex)
        for _ in range(2):
            result = subprocess.run(
                [pdflatex, '-interaction=nonstopmode', '-output-directory', tmpdir, tex],
                capture_output=True, text=True
            )
        if not os.path.exists(pdf):
            print("LaTeX ERROR:\n", result.stdout[-3000:])
            raise Exception("PDF compilation failed.")
        with open(pdf, 'rb') as f:
            return f.read()


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE 1 — Charter font (Friend's template)
# 🚫 NO SUMMARY SECTION
# ═══════════════════════════════════════════════════════════════════

def _t1_contact_line(contact_list):
    parts = []
    for c in contact_list:
        if '@' in c:
            parts.append(f'\\href{{mailto:{c}}}{{{escape_latex(c)}}}')
        elif 'github' in c.lower() or 'linkedin' in c.lower():
            url = c if c.startswith('http') else f'https://{c}'
            display = re.sub(r'https?://', '', c)
            parts.append(f'\\href{{{url}}}{{{escape_latex(display)}}}')
        else:
            parts.append(escape_latex(c))
    return '\n  \\enspace\\textbar\\enspace\n  '.join(parts)


def build_template1(data):
    name = escape_latex(data['name'])
    contact_line = _t1_contact_line(data['contact'])

    body = ''
    for sec in data['sections']:
        # 🚫 SKIP Summary section for Template 1
        if _is_summary_section(sec):
            continue

        sec_title = sec['title'].title()
        sec_upper = sec['title'].upper()
        body += f"\n%-- {sec_title.upper()} {'-'*(58-len(sec_title))}\n"
        body += f"\\section{{{sec_title}}}\n\n"

        if 'EDUCATION' in sec_upper:
            for i, entry in enumerate(sec['entries']):
                school = escape_latex(entry['header_left'])
                date_  = escape_latex(entry['header_right'])
                sub    = entry.get('sub', '')

                sub_lines = [s.strip() for s in sub.split('\n') if s.strip()]
                degree = escape_latex(sub_lines[0]) if sub_lines else ''
                note_lines = sub_lines[1:] if len(sub_lines) > 1 else []

                note_parts = []
                for nl in note_lines:
                    cm = re.match(r'^([A-Za-z][^:]{2,40}):\s*(.+)$', nl)
                    if cm:
                        lbl = escape_latex(cm.group(1).strip())
                        val = escape_latex(cm.group(2).strip())
                        note_parts.append(f'\\textbf{{{lbl}:}} {val}')
                    else:
                        note_parts.append(escape_latex(nl))
                note = ' '.join(note_parts) if note_parts else ''

                body += (
                    f"\\edu{{{school}}}\n"
                    f"    {{{degree}}}\n"
                    f"    {{{date_}}}\n"
                    f"    {{{note}}}\n\n"
                )
                if i < len(sec['entries']) - 1:
                    body += "\\vspace{4pt}\n\n"

        elif 'SKILL' in sec_upper:
            for entry in sec['entries']:
                label = escape_latex(entry['header_left'])
                value = escape_latex(entry.get('sub', ''))
                body += f"\\sk{{{label}}}{{{value}}}\n\n"

        elif 'EXPERIENCE' in sec_upper:
            for entry in sec['entries']:
                company = escape_latex(entry['header_left'])
                date_   = escape_latex(entry['header_right'])
                sub     = entry.get('sub', '')
                title   = escape_latex(sub.split('\n')[0].strip()) if sub else ''

                body += f"\\role{{{company}}}{{{title}}}{{{date_}}}\n"

                if entry['bullets']:
                    body += "\\begin{itemize}\n"
                    for b in entry['bullets']:
                        body += f"  \\item {escape_latex(b)}\n"
                    body += "\\end{itemize}\n\n"

        elif 'PROJECT' in sec_upper:
            for entry in sec['entries']:
                hl = entry['header_left']
                date_ = escape_latex(entry['header_right'])
                if '|' in hl:
                    name_part, tech_part = hl.split('|', 1)
                    proj_name = escape_latex(name_part.strip())
                    proj_tech = escape_latex(tech_part.strip())
                else:
                    proj_name = escape_latex(hl)
                    proj_tech = escape_latex(entry.get('sub', '').split('\n')[0].strip())

                body += f"\\proj{{{proj_name}}}\n"
                body += f"     {{{proj_tech}}}{{{date_}}}\n"

                if entry['bullets']:
                    body += "\\begin{itemize}\n"
                    for b in entry['bullets']:
                        body += f"  \\item {escape_latex(b)}\n"
                    body += "\\end{itemize}\n\n"

        else:
            body += "\\begin{itemize}\n"
            for entry in sec['entries']:
                if entry['bullets']:
                    for b in entry['bullets']:
                        body += f"  \\item {escape_latex(b)}\n"
                elif entry['header_left']:
                    body += f"  \\item {escape_latex(entry['header_left'])}\n"
            body += "\\end{itemize}\n\n"

    return r"""%=============================================================
%  Resume (Single Page, pdfLaTeX)
%=============================================================
\documentclass[10.5pt, letterpaper]{article}

\usepackage[top=0.42in, bottom=0.42in, left=0.55in, right=0.55in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{charter}
\usepackage{microtype}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\hypersetup{colorlinks=true, urlcolor=blue, linkcolor=blue}
\usepackage{xcolor}
\usepackage{tabularx}

\titleformat{\section}
  {\normalsize\bfseries\color{black}}
  {}{0em}{}
  [\vspace{1pt}{\color{black}\hrule height 0.8pt}\vspace{2pt}]
\titlespacing*{\section}{0pt}{6pt}{3pt}

\setlist[itemize]{
  leftmargin=1.4em, itemsep=1.5pt, parsep=0pt, topsep=2pt,
  label={\small\color{black}\textbullet}
}

\newcommand{\role}[3]{%
  \vspace{3pt}%
  \noindent
  \begin{tabularx}{\linewidth}{@{}l@{\extracolsep{\fill}}r@{}}
    \textbf{#1} & \textbf{\small #3} \\[-2pt]
    \textbf{\small #2} &
  \end{tabularx}\vspace{1pt}%
}

\newcommand{\edu}[4]{%
  \noindent
  \begin{tabularx}{\linewidth}{@{}l@{\extracolsep{\fill}}r@{}}
    \textbf{#1} & \textbf{\small #3} \\[-2pt]
    \textbf{\small #2} &
  \end{tabularx}\par\vspace{1.5pt}%
  {\small #4}\par%
}

\newcommand{\sk}[2]{%
  \noindent\textbf{\small #1:}~{\small #2}\par\vspace{1.5pt}%
}

\newcommand{\proj}[3]{%
  \vspace{3pt}%
  \noindent
  \begin{tabularx}{\linewidth}{@{}l@{\extracolsep{\fill}}r@{}}
    \textbf{#1} \textnormal{\small $|$ \textit{#2}} & \textbf{\small #3}
  \end{tabularx}\par\vspace{1pt}%
}

\begin{document}
\pagestyle{empty}
\setlength{\parindent}{0pt}

\begin{center}
  {\Large\bfseries """ + name + r"""}\\[4pt]
  \small
  """ + contact_line + r"""
\end{center}
\vspace{1pt}
""" + body + r"""
\end{document}
"""


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE 2 — Jake's Resume style (Pavan's template)
# 🚫 NO SUMMARY SECTION
# ═══════════════════════════════════════════════════════════════════

def _jake_contact_line(contact_list):
    parts = []
    for c in contact_list:
        if '@' in c:
            parts.append(f'\\href{{mailto:{c}}}{{{escape_latex(c)}}}')
        elif 'github' in c.lower() or 'linkedin' in c.lower():
            url = c if c.startswith('http') else f'https://{c}'
            display = re.sub(r'https?://', '', c)
            parts.append(f'\\href{{{url}}}{{{escape_latex(display)}}}')
        else:
            parts.append(escape_latex(c))
    return ' $|$\n    '.join(parts)


def build_template2(data):
    name = escape_latex(data['name'])
    contact_line = _jake_contact_line(data['contact'])

    body = ''
    for sec in data['sections']:
        # 🚫 SKIP Summary section for Template 2
        if _is_summary_section(sec):
            continue

        sec_title = sec['title'].title()
        sec_upper = sec['title'].upper()
        body += f"\n%-----------{sec_title.upper()}-----------\n"
        body += f"\\section{{{sec_title}}}\n"

        if 'EDUCATION' in sec_upper:
            body += "\\resumeSubHeadingListStart\n"
            for entry in sec['entries']:
                school = escape_latex(entry['header_left'])
                date_  = escape_latex(entry['header_right'])
                sub    = entry.get('sub', '')

                sub_lines = [s.strip() for s in sub.split('\n') if s.strip()]
                degree = escape_latex(sub_lines[0]) if sub_lines else ''
                extra_lines = sub_lines[1:] if len(sub_lines) > 1 else []

                body += (
                    f"  \\resumeSubheading\n"
                    f"    {{{school}}}{{}}\n"
                    f"    {{{degree}}}{{{date_}}}\n"
                )
                for el in extra_lines:
                    cm = re.match(r'^([A-Za-z][^:]{2,40}):\s*(.+)$', el)
                    if cm:
                        lbl = escape_latex(cm.group(1).strip())
                        val = escape_latex(cm.group(2).strip())
                        body += f"    \\resumeItem{{\\textbf{{{lbl}:}} {val}}}\n"
                    else:
                        body += f"    \\resumeItem{{{escape_latex(el)}}}\n"
            body += "\\resumeSubHeadingListEnd\n\n"

        elif 'SKILL' in sec_upper:
            body += "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
            body += "  \\small{\\item{\n"
            for i, entry in enumerate(sec['entries']):
                label = escape_latex(entry['header_left'])
                value = escape_latex(entry.get('sub', ''))
                body += f"   \\textbf{{{label}:}} {value}"
                if i < len(sec['entries']) - 1:
                    body += " \\\\\n"
                else:
                    body += "\n"
            body += "  }}\n\\end{itemize}\n\n\\vspace{-14pt}\n\n"

        elif 'EXPERIENCE' in sec_upper:
            body += "\\resumeSubHeadingListStart\n\n"
            for entry in sec['entries']:
                company = escape_latex(entry['header_left'])
                date_   = escape_latex(entry['header_right'])
                sub     = entry.get('sub', '')
                role    = escape_latex(sub.split('\n')[0].strip()) if sub else ''

                body += (
                    f"  \\resumeSubheading\n"
                    f"    {{{company}}}{{}}\n"
                    f"    {{{role}}}{{{date_}}}\n"
                )
                if entry['bullets']:
                    body += "  \\resumeItemListStart\n"
                    for b in entry['bullets']:
                        body += f"    \\resumeItem{{{escape_latex(b)}}}\n"
                    body += "  \\resumeItemListEnd\n\n"
            body += "\\resumeSubHeadingListEnd\n\n\\vspace{-14pt}\n\n"

        elif 'PROJECT' in sec_upper:
            body += "\\resumeSubHeadingListStart\n\n"
            for entry in sec['entries']:
                hl = entry['header_left']
                date_ = escape_latex(entry['header_right'])
                if '|' in hl:
                    name_part, tech_part = hl.split('|', 1)
                    proj_name = escape_latex(name_part.strip())
                    proj_tech = escape_latex(tech_part.strip())
                    heading = f"\\textbf{{{proj_name}}} $|$ \\emph{{{proj_tech}}}"
                else:
                    heading = f"\\textbf{{{escape_latex(hl)}}}"

                body += (
                    f"  \\resumeProjectHeading\n"
                    f"    {{{heading}}}{{\\textbf{{{date_}}}}}\n"
                )
                if entry['bullets']:
                    body += "  \\resumeItemListStart\n"
                    for b in entry['bullets']:
                        body += f"    \\resumeItem{{{escape_latex(b)}}}\n"
                    body += "  \\resumeItemListEnd\n\n"
            body += "\\resumeSubHeadingListEnd\n\n"

        else:
            body += "\\resumeSubHeadingListStart\n"
            body += "  \\resumeItemListStart\n"
            for entry in sec['entries']:
                if entry['bullets']:
                    for b in entry['bullets']:
                        body += f"    \\resumeItem{{{escape_latex(b)}}}\n"
                elif entry['header_left']:
                    body += f"    \\resumeItem{{{escape_latex(entry['header_left'])}}}\n"
            body += "  \\resumeItemListEnd\n\\resumeSubHeadingListEnd\n\n"

    return r"""%-------------------------
% Resume in Latex
%------------------------

\documentclass[letterpaper,10pt]{article}

\usepackage[empty]{fullpage}
\usepackage{titlesec, enumitem, hyperref, fancyhdr, xcolor, tabularx, babel, amsmath}
\input{glyphtounicode}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.6in}
\addtolength{\evensidemargin}{-0.6in}
\addtolength{\textwidth}{1.2in}
\addtolength{\topmargin}{-0.65in}
\addtolength{\textheight}{1.5in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-5pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{\item\small{#1 \vspace{-2pt}}}
\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubRole}[2]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeProjectHeading}[2]{
  \item
  \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
    \small#1 & #2 \\
  \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[leftmargin=0.15in]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-4pt}}

\begin{document}

\begin{center}
    \textbf{\Huge \scshape """ + name + r"""} \\
    \vspace{2pt}
    \small """ + contact_line + r"""
\end{center}

\vspace{-14pt}
""" + body + r"""
\end{document}
"""


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE 3 — Jake's style + Summary section
# ✅ SHOWS SUMMARY SECTION (always — auto-generates if AI didn't include one)
# ═══════════════════════════════════════════════════════════════════

def build_template3(data):
    name = escape_latex(data['name'])
    contact_line = _jake_contact_line(data['contact'])

    # Find Summary section from AI output (if any)
    summary_text = ''
    other_sections = []
    for sec in data['sections']:
        if _is_summary_section(sec):
            sum_parts = []
            for entry in sec['entries']:
                if entry.get('header_left'):
                    sum_parts.append(entry['header_left'])
                if entry.get('sub'):
                    sum_parts.append(entry['sub'])
                for b in entry.get('bullets', []):
                    sum_parts.append(b)
            summary_text = ' '.join(sum_parts).strip()
        else:
            other_sections.append(sec)

    # If no summary was generated by AI, build a basic one from existing sections
    if not summary_text:
        # Find education and experience to build a default summary
        edu_info = ''
        skills_info = ''
        for sec in other_sections:
            upper = sec['title'].upper()
            if 'EDUCATION' in upper and sec['entries']:
                first_edu = sec['entries'][0]
                school = first_edu['header_left']
                degree = first_edu.get('sub', '').split('\n')[0]
                edu_info = f"{degree} candidate at {school.split(',')[0]}"
                break

        for sec in other_sections:
            upper = sec['title'].upper()
            if 'SKILL' in upper and sec['entries']:
                # Get languages
                for e in sec['entries']:
                    if 'language' in e['header_left'].lower():
                        skills_info = e.get('sub', '')[:80]
                        break
                break

        if edu_info or skills_info:
            summary_text = f"{edu_info}. Skilled in {skills_info}." if edu_info and skills_info else (edu_info or skills_info)

    body = ''
    if summary_text:
        body += "\n%-----------SUMMARY-----------\n"
        body += "\\section{Summary}\n"
        body += "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
        body += "  \\small{\\item{\n"
        body += f"    {escape_latex(summary_text)}\n"
        body += "  }}\n\\end{itemize}\n\n\\vspace{-14pt}\n\n"

    for sec in other_sections:
        sec_title = sec['title'].title()
        sec_upper = sec['title'].upper()
        body += f"\n%-----------{sec_title.upper()}-----------\n"
        body += f"\\section{{{sec_title}}}\n"

        if 'EDUCATION' in sec_upper:
            body += "\\resumeSubHeadingListStart\n\n"
            for entry in sec['entries']:
                school = escape_latex(entry['header_left'])
                date_  = escape_latex(entry['header_right'])
                sub    = entry.get('sub', '')

                sub_lines = [s.strip() for s in sub.split('\n') if s.strip()]
                degree = escape_latex(sub_lines[0]) if sub_lines else ''
                extra_lines = sub_lines[1:] if len(sub_lines) > 1 else []

                body += (
                    f"  \\resumeSubheading\n"
                    f"    {{{school}}}{{}}\n"
                    f"    {{{degree}}}{{{date_}}}\n"
                )
                if extra_lines:
                    body += "  \\resumeItemListStart\n"
                    for el in extra_lines:
                        cm = re.match(r'^([A-Za-z][^:]{2,40}):\s*(.+)$', el)
                        if cm:
                            lbl = escape_latex(cm.group(1).strip())
                            val = escape_latex(cm.group(2).strip())
                            body += f"    \\resumeItem{{\\textbf{{{lbl}:}} {val}}}\n"
                        else:
                            body += f"    \\resumeItem{{{escape_latex(el)}}}\n"
                    body += "  \\resumeItemListEnd\n\n"
            body += "\\resumeSubHeadingListEnd\n\n\\vspace{-14pt}\n\n"

        elif 'SKILL' in sec_upper:
            body += "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
            body += "  \\small{\\item{\n"
            for i, entry in enumerate(sec['entries']):
                label = escape_latex(entry['header_left'])
                value = escape_latex(entry.get('sub', ''))
                body += f"    \\textbf{{{label}:}} {value}"
                if i < len(sec['entries']) - 1:
                    body += " \\\\\n"
                else:
                    body += "\n"
            body += "  }}\n\\end{itemize}\n\n\\vspace{-14pt}\n\n"

        elif 'EXPERIENCE' in sec_upper:
            body += "\\resumeSubHeadingListStart\n\n"
            for entry in sec['entries']:
                company = escape_latex(entry['header_left'])
                date_   = escape_latex(entry['header_right'])
                sub     = entry.get('sub', '')
                role    = escape_latex(sub.split('\n')[0].strip()) if sub else ''

                body += (
                    f"  \\resumeSubheading\n"
                    f"    {{{company}}}{{}}\n"
                    f"    {{{role}}}{{{date_}}}\n"
                )
                if entry['bullets']:
                    body += "  \\resumeItemListStart\n"
                    for b in entry['bullets']:
                        body += f"    \\resumeItem{{{escape_latex(b)}}}\n"
                    body += "  \\resumeItemListEnd\n\n"
            body += "\\resumeSubHeadingListEnd\n\n\\vspace{-14pt}\n\n"

        elif 'PROJECT' in sec_upper:
            body += "\\resumeSubHeadingListStart\n\n"
            for entry in sec['entries']:
                hl = entry['header_left']
                date_ = escape_latex(entry['header_right'])
                if '|' in hl:
                    name_part, tech_part = hl.split('|', 1)
                    proj_name = escape_latex(name_part.strip())
                    proj_tech = escape_latex(tech_part.strip())
                    heading = f"\\textbf{{{proj_name}}} $|$ \\emph{{{proj_tech}}}"
                else:
                    heading = f"\\textbf{{{escape_latex(hl)}}}"

                body += (
                    f"  \\resumeProjectHeading\n"
                    f"    {{{heading}}}{{{date_}}}\n"
                )
                if entry['bullets']:
                    body += "  \\resumeItemListStart\n"
                    for b in entry['bullets']:
                        body += f"    \\resumeItem{{{escape_latex(b)}}}\n"
                    body += "  \\resumeItemListEnd\n\n"
            body += "\\resumeSubHeadingListEnd\n\n\\vspace{-14pt}\n\n"

        else:
            body += "\\resumeSubHeadingListStart\n"
            body += "  \\resumeItemListStart\n"
            for entry in sec['entries']:
                if entry['bullets']:
                    for b in entry['bullets']:
                        body += f"    \\resumeItem{{{escape_latex(b)}}}\n"
                elif entry['header_left']:
                    body += f"    \\resumeItem{{{escape_latex(entry['header_left'])}}}\n"
            body += "  \\resumeItemListEnd\n\\resumeSubHeadingListEnd\n\n"

    return r"""%-------------------------
% Resume in Latex
%------------------------

\documentclass[letterpaper,10pt]{article}

\usepackage[empty]{fullpage}
\usepackage{titlesec, enumitem, hyperref, fancyhdr, xcolor, tabularx, babel, amsmath}
\input{glyphtounicode}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.6in}
\addtolength{\evensidemargin}{-0.6in}
\addtolength{\textwidth}{1.2in}
\addtolength{\topmargin}{-0.65in}
\addtolength{\textheight}{1.5in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-5pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{\item\small{#1 \vspace{-2pt}}}
\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeProjectHeading}[2]{
  \item
  \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
    \small#1 & #2 \\
  \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}[leftmargin=0.15in]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-4pt}}

\begin{document}

\begin{center}
    \textbf{\Huge \scshape """ + name + r"""} \\
    \vspace{2pt}
    \small """ + contact_line + r"""
\end{center}

\vspace{-14pt}
""" + body + r"""
\end{document}
"""


# ═══════════════════════════════════════════════════
# COVER LETTER PDF
# ═══════════════════════════════════════════════════

def generate_cover_letter_pdf(cover_letter_text):
    """Generate cover letter PDF with signature on separate lines."""
    text = cover_letter_text.strip()
    raw_paragraphs = text.split('\n\n')

    body_parts = []

    for i, para in enumerate(raw_paragraphs):
        para = para.strip()
        if not para:
            continue

        is_last = (i == len(raw_paragraphs) - 1)
        is_signature = is_last and any(
            w in para.lower() for w in ('regards', 'sincerely', 'best,', 'yours')
        )

        if is_signature:
            sig_lines = []
            for ln in para.split('\n'):
                ln = ln.strip()
                if not ln:
                    continue
                if ln.endswith(','):
                    sig_lines.append(ln)
                elif ',' in ln and len(ln) > 30:
                    for piece in ln.split(','):
                        piece = piece.strip()
                        if piece:
                            sig_lines.append(piece)
                else:
                    sig_lines.append(ln)

            sig_body = ''
            for j, sl in enumerate(sig_lines):
                if j == 0:
                    sig_body += escape_latex(sl) + '\\\\\n\\vspace{14pt}\n'
                else:
                    sig_body += '\\noindent ' + escape_latex(sl) + '\\\\\n'

            body_parts.append(sig_body)
        else:
            para_clean = ' '.join(para.split('\n'))
            body_parts.append(escape_latex(para_clean))

    body = '\n\n'.join(body_parts)

    latex = r"""\documentclass[letterpaper,11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[top=1in,bottom=1in,left=1.2in,right=1.2in]{geometry}
\usepackage{charter}
\usepackage{parskip}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{10pt}
\renewcommand{\baselinestretch}{1.3}
\pagestyle{empty}
\begin{document}
""" + body + r"""
\end{document}"""

    return _compile(latex)


# ═══════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════

def generate_pdf(resume_text, template=1):
    """
    template=1 → Template 1 (Charter) — NO SUMMARY
    template=2 → Template 2 (Jake's Resume) — NO SUMMARY
    template=3 → Template 3 (Jake's + Summary) — WITH SUMMARY
    """
    data = parse_resume(resume_text)
    builders = {1: build_template1, 2: build_template2, 3: build_template3}
    builder = builders.get(int(template), build_template1)
    return _compile(builder(data))