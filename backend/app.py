"""
app.py — SkillPath Flask API Server
=====================================
DETERMINISTIC LOGIC ONLY. No AI, no runtime API calls.

Endpoints:
  GET  /api/careers              → List all careers
  GET  /api/careers/<id>         → Single career detail
  GET  /api/questions            → Get aptitude questions (no answers)
  POST /api/aptitude/evaluate    → Evaluate aptitude test responses
  POST /api/recommend            → Get top 3 career recommendations
  POST /api/validate             → Validate a user-chosen career
  POST /api/gaps                 → Analyze skill gaps for a career
  POST /api/plan                 → Generate a study plan
  POST /api/whatif               → Simulate profile improvements
  GET  /api/health               → Health check
"""

import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS

# Add backend directory to path for module imports
sys.path.insert(0, os.path.dirname(__file__))
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (allows React/HTML frontend to call API)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response
from aptitude import get_questions_by_category, evaluate_aptitude
from career_engine import (
    get_all_careers, get_career_by_id,
    get_top_careers, validate_career_choice,
    score_career, simulate_improvement
)
from skill_gap import analyze_skill_gaps, compare_gaps_across_careers, estimate_gap_impact
from planner import generate_study_plan





# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    """Simple health check endpoint."""
    return jsonify({
        'status': 'ok',
        'system': 'SkillPath Career Guidance',
        'ai_used': False,
        'deterministic': True
    })


# ─────────────────────────────────────────────
# CAREER EXPLORER ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/careers', methods=['GET'])
def list_careers():
    """
    Return all career definitions for the Career Explorer.
    Optionally filter by category: ?category=Tech
    """
    careers = get_all_careers()
    category = request.args.get('category')

    if category:
        careers = [c for c in careers if c.get('category', '').lower() == category.lower()]

    # Return a simplified view for listing (full data available via /api/careers/<id>)
    career_list = [{
        'id': c['id'],
        'name': c['name'],
        'category': c['category'],
        'description': c['description'],
        'related_interests': c.get('related_interests', [])
    } for c in careers]

    return jsonify({'careers': career_list, 'total': len(career_list)})


@app.route('/api/careers/<career_id>', methods=['GET'])
def get_career(career_id):
    """Return full details for a single career."""
    career = get_career_by_id(career_id)
    if not career:
        return jsonify({'error': f"Career '{career_id}' not found"}), 404
    return jsonify(career)


# ─────────────────────────────────────────────
# APTITUDE TEST ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """
    Return aptitude questions grouped by category.
    Answers are NOT included to prevent cheating.
    """
    questions = get_questions_by_category()
    return jsonify({
        'questions': questions,
        'categories': list(questions.keys()),
        'total_questions': sum(len(q) for q in questions.values())
    })


@app.route('/api/aptitude/evaluate', methods=['POST'])
def evaluate_test():
    """
    Evaluate a completed aptitude test.

    Request body:
        {
          "answers": {
            "L001": 1,    // question_id: selected_option_index
            "L002": 0,
            "Q001": 2,
            ...
          }
        }

    Returns: Structured scores, levels, and per-question feedback.
    """
    data = request.get_json()
    if not data or 'answers' not in data:
        return jsonify({'error': 'Request must include "answers" object'}), 400

    answers = data['answers']
    if not isinstance(answers, dict):
        return jsonify({'error': '"answers" must be a dictionary of {question_id: option_index}'}), 400

    result = evaluate_aptitude(answers)
    return jsonify(result)


# ─────────────────────────────────────────────
# RECOMMENDATION ENGINE ENDPOINT
# ─────────────────────────────────────────────

@app.route('/api/recommend', methods=['POST'])
def recommend_careers():
    """
    Get top 3 career recommendations for a user profile.

    Request body:
        {
          "user_type": "student",              // student / parent / both
          "skills": {                          // skill: level (1-10)
            "programming": 6,
            "mathematics": 5,
            "logical_thinking": 7
          },
          "interests": ["coding", "puzzles", "gaming"],
          "aptitude_scores": {                 // from /api/aptitude/evaluate
            "logical": 72,
            "quantitative": 65,
            "verbal": 48
          },
          "time_per_day": 1.5,                // hours per day
          "parent_observations": [            // optional
            "good with numbers",
            "loves building things"
          ]
        }

    Returns: Top 3 careers with scores, explanations, and gap summaries.
    """
    data = request.get_json()
    validation_error = _validate_profile(data)
    if validation_error:
        return jsonify({'error': validation_error}), 400

    user_profile = _build_profile(data)
    result = get_top_careers(user_profile, top_n=3)

    # Augment each career result with a brief gap summary
    for career_result in result['top_careers']:
        career = get_career_by_id(career_result['career_id'])
        if career:
            gap = analyze_skill_gaps(user_profile['skills'], career)
            career_result['gap_summary'] = {
                'critical': gap['summary']['critical'],
                'important': gap['summary']['important'],
                'optional': gap['summary']['optional'],
                'readiness': gap['overall_readiness']
            }

    return jsonify(result)


# ─────────────────────────────────────────────
# CAREER VALIDATION ENDPOINT
# ─────────────────────────────────────────────

@app.route('/api/validate', methods=['POST'])
def validate_career():
    """
    Validate a user-selected career choice.

    Request body:
        {
          "career_id": "software_engineer",
          "skills": {...},
          "interests": [...],
          "aptitude_scores": {...},
          "parent_observations": [...]     // optional
        }

    Returns: Suitability, strengths, weaknesses, suggestions.
    """
    data = request.get_json()
    if not data or 'career_id' not in data:
        return jsonify({'error': 'Request must include "career_id"'}), 400

    user_profile = _build_profile(data)
    result = validate_career_choice(user_profile, data['career_id'])

    if 'error' in result:
        return jsonify(result), 404

    return jsonify(result)


# ─────────────────────────────────────────────
# SKILL GAP ANALYSIS ENDPOINT
# ─────────────────────────────────────────────

@app.route('/api/gaps', methods=['POST'])
def skill_gaps():
    """
    Perform detailed skill gap analysis for a target career.

    Request body:
        {
          "career_id": "data_scientist",
          "skills": {"mathematics": 5, "programming": 4, ...},
          "include_impact": true    // optional: include score impact estimate
        }

    Returns: Prioritized list of skill gaps with resources and explanations.
    """
    data = request.get_json()
    if not data or 'career_id' not in data or 'skills' not in data:
        return jsonify({'error': 'Request must include "career_id" and "skills"'}), 400

    career = get_career_by_id(data['career_id'])
    if not career:
        return jsonify({'error': f"Career '{data['career_id']}' not found"}), 404

    user_skills = data.get('skills', {})
    gap_result = analyze_skill_gaps(user_skills, career)

    # Optionally add score impact estimates
    if data.get('include_impact'):
        user_profile = _build_profile(data)
        career_score_result = score_career(user_profile, career)
        current_score = career_score_result['total_score']

        for gap in gap_result['gaps']:
            impact = estimate_gap_impact(gap, current_score)
            gap['score_impact'] = impact

    return jsonify(gap_result)


# ─────────────────────────────────────────────
# STUDY PLANNER ENDPOINT
# ─────────────────────────────────────────────

@app.route('/api/plan', methods=['POST'])
def generate_plan():
    """
    Generate a structured study plan based on skill gaps.

    Request body:
        {
          "career_id": "software_engineer",
          "skills": {...},
          "time_per_day": 1.5    // hours per day available for study
        }

    Returns: Week-by-week study plan with resources and activities.
    """
    data = request.get_json()
    if not data or 'career_id' not in data or 'skills' not in data:
        return jsonify({'error': 'Request must include "career_id" and "skills"'}), 400

    career = get_career_by_id(data['career_id'])
    if not career:
        return jsonify({'error': f"Career '{data['career_id']}' not found"}), 404

    user_skills = data.get('skills', {})
    hours_per_day = float(data.get('time_per_day', 1.5))

    # First analyze gaps, then build plan from gaps
    gap_result = analyze_skill_gaps(user_skills, career)

    if not gap_result['gaps']:
        return jsonify({
            'message': 'No skill gaps found! You already meet all skill requirements for this career.',
            'career_name': career['name'],
            'weeks': [],
            'total_weeks': 0
        })

    plan = generate_study_plan(gap_result, hours_per_day)
    return jsonify(plan)


# ─────────────────────────────────────────────
# WHAT-IF SIMULATOR ENDPOINT
# ─────────────────────────────────────────────

@app.route('/api/whatif', methods=['POST'])
def what_if():
    """
    Simulate how improving specific skills/aptitude would change career scores.

    Request body:
        {
          "current_profile": {
            "skills": {...},
            "interests": [...],
            "aptitude_scores": {...}
          },
          "improvements": {
            "skills": {"mathematics": 8},        // New skill levels
            "aptitude_scores": {"quantitative": 75}  // New aptitude scores
          }
        }

    Returns: Before/after comparison of career match scores.
    """
    data = request.get_json()
    if not data or 'current_profile' not in data or 'improvements' not in data:
        return jsonify({'error': 'Request must include "current_profile" and "improvements"'}), 400

    user_profile = _build_profile(data['current_profile'])
    improvements = data['improvements']

    result = simulate_improvement(user_profile, improvements)

    # Add career names to the change list for readability
    from career_engine import _load_careers
    career_names = {c['id']: c['name'] for c in _load_careers()}

    enhanced_changes = {}
    for career_id, change_data in result['changes'].items():
        enhanced_changes[career_id] = {
            **change_data,
            'career_name': career_names.get(career_id, career_id)
        }
    result['changes'] = enhanced_changes

    return jsonify(result)


# ─────────────────────────────────────────────
# FULL ANALYSIS ENDPOINT (convenience)
# ─────────────────────────────────────────────

@app.route('/api/full-analysis', methods=['POST'])
def full_analysis():
    """
    Run the complete analysis pipeline in a single call.
    Useful for the main results page.

    Request body: Same as /api/recommend
    Additionally accepts 'selected_career_id' for validation mode.

    Returns: Recommendations + gaps + plan for top career.
    """
    data = request.get_json()
    validation_error = _validate_profile(data)
    if validation_error:
        return jsonify({'error': validation_error}), 400

    user_profile = _build_profile(data)
    hours_per_day = float(data.get('time_per_day', 1.5))

    # 1. Get top 3 recommendations
    recommendation = get_top_careers(user_profile, top_n=3)
    top_career = recommendation['top_careers'][0] if recommendation['top_careers'] else None

    result = {
        'recommendations': recommendation,
        'top_career': None,
        'gap_analysis': None,
        'study_plan': None
    }

    if top_career:
        career = get_career_by_id(top_career['career_id'])
        if career:
            # 2. Gap analysis for top career
            gap_analysis = analyze_skill_gaps(user_profile['skills'], career)
            result['gap_analysis'] = gap_analysis

            # 3. Study plan for top career
            if gap_analysis['gaps']:
                plan = generate_study_plan(gap_analysis, hours_per_day)
                result['study_plan'] = plan

            result['top_career'] = top_career

    return jsonify(result)


# ─────────────────────────────────────────────
# INPUT VALIDATION HELPERS
# ─────────────────────────────────────────────

def _validate_profile(data: dict) -> str | None:
    """
    Validate incoming user profile data.
    Returns error message string if invalid, None if valid.
    """
    if not data:
        return 'Request body is required'

    if 'skills' not in data:
        return 'Field "skills" is required (dict of skill: level)'

    if not isinstance(data['skills'], dict):
        return '"skills" must be a dictionary'

    # Validate skill levels are integers 0–10
    for skill, level in data['skills'].items():
        if not isinstance(level, (int, float)) or not (0 <= level <= 10):
            return f'Skill level for "{skill}" must be a number between 0 and 10'

    # Aptitude scores must be 0–100 if provided
    if 'aptitude_scores' in data:
        for cat, score in data['aptitude_scores'].items():
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                return f'Aptitude score for "{cat}" must be a number between 0 and 100'

    return None


def _build_profile(data: dict) -> dict:
    """
    Normalize raw request data into a standardized user profile dict.
    Fills in defaults for missing optional fields.
    """
    return {
        'skills': data.get('skills', {}),
        'interests': [i.lower() for i in data.get('interests', [])],
        'aptitude_scores': data.get('aptitude_scores', {
            'logical': 50,
            'quantitative': 50,
            'verbal': 50
        }),
        'parent_observations': data.get('parent_observations', [])
    }


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 50)
    print("  SkillPath Career Guidance API")
    print("  Deterministic Intelligence — No AI at Runtime")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)