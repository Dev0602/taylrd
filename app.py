"""Taylrd — AI Resume Tailor (Production)."""

from flask import Flask, render_template, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from datetime import datetime, date
from threading import Lock
import os
import io
import logging

import anthropic
from parser import extract_text_from_pdf, extract_keywords_from_jd
from tailor import tailor_resume, generate_cover_letter, get_fix_suggestions
from ats_scorer import calculate_ats_score
from pdf_generator import generate_pdf, generate_cover_letter_pdf

load_dotenv()

app = Flask(__name__)

# ── Production safety configuration ─────────────────────────────
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max
ALLOWED_EXTENSIONS = {'pdf'}

logging.basicConfig(level=logging.INFO)

# ═══════════════════════════════════════════════════════════════
# RATE LIMITING — Protect API credits
# ═══════════════════════════════════════════════════════════════
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["50 per day", "10 per hour"]
)

# ═══════════════════════════════════════════════════════════════
# DAILY GLOBAL CAP — Hard limit on total API calls per day
# ═══════════════════════════════════════════════════════════════
DAILY_LIMITS = {
    'max_total_calls_per_day': 50,    # Total resumes generated app-wide per day
    'max_fix_calls_per_day': 100,     # Total "Fix" button uses per day
}

# In-memory counter (resets when server restarts — that's fine for free tier)
_call_tracker = {
    'date': date.today(),
    'tailor_count': 0,
    'fix_count': 0,
    'lock': Lock(),
}


def _check_daily_limit(call_type='tailor'):
    """Returns True if under daily limit, False if exceeded."""
    with _call_tracker['lock']:
        # Reset counter if it's a new day
        if _call_tracker['date'] != date.today():
            _call_tracker['date'] = date.today()
            _call_tracker['tailor_count'] = 0
            _call_tracker['fix_count'] = 0

        if call_type == 'tailor':
            if _call_tracker['tailor_count'] >= DAILY_LIMITS['max_total_calls_per_day']:
                return False
            _call_tracker['tailor_count'] += 1
        elif call_type == 'fix':
            if _call_tracker['fix_count'] >= DAILY_LIMITS['max_fix_calls_per_day']:
                return False
            _call_tracker['fix_count'] += 1
        return True


client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 5 MB.'}), 413


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/job-description')
def job_description():
    return render_template('job_description.html')


@app.route('/results')
def results():
    return render_template('results.html')


@app.route('/download')
def download_page():
    return render_template('download.html')


# ═══════════════════════════════════════════════════════════════
# Tailor route — STRICT LIMITS: 3 per day per person, 50/day total
# ═══════════════════════════════════════════════════════════════
@app.route('/tailor', methods=['POST'])
@limiter.limit("3 per day; 1 per minute")
def tailor():
    # ── Check global daily cap first ─────────────────────────
    if not _check_daily_limit('tailor'):
        return jsonify({
            'error': 'Daily limit reached. We have a free tier limit of 50 resumes per day. Please try again tomorrow!'
        }), 429

    if 'resume' not in request.files:
        return jsonify({'error': 'No resume uploaded'}), 400
    if 'job_description' not in request.form:
        return jsonify({'error': 'No job description provided'}), 400

    resume_file = request.files['resume']
    job_description_text = request.form['job_description'].strip()

    if not resume_file.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(resume_file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    if len(job_description_text) < 100:
        return jsonify({'error': 'Job description too short (min 100 chars).'}), 400
    if len(job_description_text) > 15000:
        return jsonify({'error': 'Job description too long (max 15,000 chars).'}), 400

    try:
        resume_text = extract_text_from_pdf(resume_file)
        if not resume_text or len(resume_text.strip()) < 50:
            return jsonify({'error': 'Could not extract text from PDF.'}), 400
        if len(resume_text) > 30000:
            return jsonify({'error': 'Resume too long. Use a 1-2 page resume.'}), 400

        keywords = extract_keywords_from_jd(job_description_text)
        score_before = calculate_ats_score(resume_text, keywords)

        tailor_result = tailor_resume(client, resume_text, job_description_text, keywords)
        tailored_resume = tailor_result['resume']
        skipped_keywords = tailor_result['skipped_keywords']

        cover_letter = generate_cover_letter(client, resume_text, job_description_text)
        score_after = calculate_ats_score(tailored_resume, keywords)

        return jsonify({
            'tailored_resume': tailored_resume,
            'cover_letter': cover_letter,
            'job_description': job_description_text,
            'ats_score_before': score_before['score'],
            'ats_score_after': score_after['score'],
            'matched_keywords': score_after['matched_keywords'],
            'missing_keywords': score_after['missing_keywords'],
            'skipped_keywords': skipped_keywords,
            'issues': score_after['issues'],
            'completed': score_after['completed'],
            'breakdown': score_after['breakdown'],
        })

    except anthropic.APIError as e:
        app.logger.error(f"Anthropic API error: {e}")
        return jsonify({'error': 'AI service temporarily unavailable.'}), 503
    except Exception as e:
        app.logger.exception("Tailoring failed")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500


# ═══════════════════════════════════════════════════════════════
# Re-score (no AI call — free)
# ═══════════════════════════════════════════════════════════════
@app.route('/rescore', methods=['POST'])
@limiter.limit("20 per minute")
def rescore():
    data = request.get_json()
    if not data or 'resume_text' not in data:
        return jsonify({'error': 'No resume text provided'}), 400

    resume_text = data['resume_text'].strip()
    job_description_text = data.get('job_description', '').strip()

    if len(resume_text) < 50:
        return jsonify({'error': 'Resume too short'}), 400

    try:
        keywords = extract_keywords_from_jd(job_description_text) if job_description_text else []
        result = calculate_ats_score(resume_text, keywords)
        return jsonify({
            'score': result['score'],
            'matched_keywords': result['matched_keywords'],
            'missing_keywords': result['missing_keywords'],
            'issues': result['issues'],
            'completed': result['completed'],
            'breakdown': result['breakdown'],
        })
    except Exception as e:
        app.logger.exception("Re-scoring failed")
        return jsonify({'error': 'Re-scoring failed.'}), 500


# ═══════════════════════════════════════════════════════════════
# Fix suggestions — STRICT: 5 per day per person, 100/day total
# ═══════════════════════════════════════════════════════════════
@app.route('/get-fix-suggestions', methods=['POST'])
@limiter.limit("5 per day; 1 per minute")
def get_fix_suggestions_route():
    # ── Check global daily cap first ─────────────────────────
    if not _check_daily_limit('fix'):
        return jsonify({
            'error': 'Daily fix limit reached. Please try again tomorrow!'
        }), 429

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    resume_text = data.get('resume_text', '').strip()
    issue = data.get('issue', {})
    job_description_text = data.get('job_description', '').strip()

    if not resume_text or not issue:
        return jsonify({'error': 'Resume text and issue required'}), 400

    try:
        suggestions = get_fix_suggestions(client, resume_text, issue, job_description_text)

        keywords = extract_keywords_from_jd(job_description_text) if job_description_text else []
        for s in suggestions:
            if s.get('modified_resume'):
                score_result = calculate_ats_score(s['modified_resume'], keywords)
                s['new_score'] = score_result['score']

        return jsonify({'suggestions': suggestions})

    except anthropic.APIError as e:
        app.logger.error(f"Anthropic API error: {e}")
        return jsonify({'error': 'AI service temporarily unavailable.'}), 503
    except Exception as e:
        app.logger.exception("Fix suggestions failed")
        return jsonify({'error': 'Could not generate suggestions.'}), 500


# ═══════════════════════════════════════════════════════════════
# PDF downloads (no AI cost — just LaTeX)
# ═══════════════════════════════════════════════════════════════
@app.route('/download-pdf', methods=['POST'])
@limiter.limit("10 per minute")
def download_pdf():
    data = request.get_json()
    if not data or 'resume_text' not in data:
        return jsonify({'error': 'No resume text provided'}), 400
    try:
        pdf_bytes = generate_pdf(data['resume_text'], template=data.get('template', 1))
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='tailored_resume.pdf'
        )
    except Exception as e:
        app.logger.exception("PDF generation failed")
        return jsonify({'error': 'PDF generation failed.'}), 500


@app.route('/download-cover-letter', methods=['POST'])
@limiter.limit("10 per minute")
def download_cover_letter():
    data = request.get_json()
    if not data or 'cover_letter' not in data:
        return jsonify({'error': 'No cover letter provided'}), 400
    try:
        pdf_bytes = generate_cover_letter_pdf(data['cover_letter'])
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='cover_letter.pdf'
        )
    except Exception as e:
        app.logger.exception("Cover letter PDF generation failed")
        return jsonify({'error': 'PDF generation failed.'}), 500


# ═══════════════════════════════════════════════════════════════
# Health check (for Render monitoring)
# ═══════════════════════════════════════════════════════════════
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'tailor_today': _call_tracker['tailor_count'],
        'fix_today': _call_tracker['fix_count'],
        'tailor_limit': DAILY_LIMITS['max_total_calls_per_day'],
        'fix_limit': DAILY_LIMITS['max_fix_calls_per_day'],
    })


# ═══════════════════════════════════════════════════════════════
# Production-safe entry point (NO debug, NO auto-reload)
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    # Production: no debug mode, no auto-reload
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=False,
        use_reloader=False,
    )