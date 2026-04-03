"""
aptitude.py — Aptitude Test Evaluation Module
==============================================
DETERMINISTIC LOGIC ONLY. No AI, no randomness.

Responsibilities:
- Load aptitude questions from JSON
- Evaluate user answers
- Calculate per-category scores (logical / quantitative / verbal)
- Return structured result with per-question explanations
"""

import json
import os


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

def _load_questions():
    """Load all aptitude questions from the JSON data file."""
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'aptitude_questions.json')
    with open(path, 'r') as f:
        data = json.load(f)
    return data['aptitude_questions'], data['scoring']


def get_questions_by_category():
    """
    Returns questions grouped by category.
    Used by frontend to display the test.
    """
    questions, _ = _load_questions()
    grouped = {'logical': [], 'quantitative': [], 'verbal': []}
    for q in questions:
        cat = q['category']
        if cat in grouped:
            grouped[cat].append({
                'id': q['id'],
                'question': q['question'],
                'options': q['options'],
                'category': q['category'],
                'difficulty': q['difficulty']
                # NOTE: 'answer' and 'explanation' are NOT sent to frontend
                #       to prevent cheating. They are only used server-side.
            })
    return grouped


# ─────────────────────────────────────────────
# SCORING LOGIC
# ─────────────────────────────────────────────

def evaluate_aptitude(user_answers: dict) -> dict:
    """
    Evaluate a user's aptitude test responses.

    Parameters:
        user_answers: dict of {question_id: selected_option_index}
                      e.g. {"L001": 1, "L002": 0, "Q001": 2, ...}

    Returns:
        {
          "scores": {
            "logical": 70,       # 0–100 score
            "quantitative": 80,
            "verbal": 60
          },
          "levels": {
            "logical": "proficient",
            "quantitative": "advanced",
            "verbal": "developing"
          },
          "details": [           # Per-question breakdown
            {
              "id": "L001",
              "category": "logical",
              "correct": true,
              "explanation": "..."
            }, ...
          ],
          "total_answered": 30,
          "summary": "You scored well in Quantitative..."
        }
    """
    questions, scoring_config = _load_questions()

    # Build a lookup dict: question_id → question_data
    q_lookup = {q['id']: q for q in questions}

    # Track per-category correct/total counts
    category_results = {
        'logical': {'correct': 0, 'total': 0},
        'quantitative': {'correct': 0, 'total': 0},
        'verbal': {'correct': 0, 'total': 0}
    }

    details = []

    # ── EVALUATE EACH ANSWER ──
    for q_id, user_choice in user_answers.items():
        if q_id not in q_lookup:
            continue  # Skip unknown question IDs

        q = q_lookup[q_id]
        cat = q['category']
        is_correct = (user_choice == q['answer'])

        if cat in category_results:
            category_results[cat]['total'] += 1
            if is_correct:
                category_results[cat]['correct'] += 1

        details.append({
            'id': q_id,
            'category': cat,
            'question': q['question'],
            'user_answer': q['options'][user_choice] if user_choice < len(q['options']) else 'No answer',
            'correct_answer': q['options'][q['answer']],
            'correct': is_correct,
            'explanation': q['explanation']
        })

    # ── CALCULATE PERCENTAGE SCORES PER CATEGORY ──
    # Rule: score = (correct / total) × 100, rounded to nearest integer
    # If no questions answered in a category, score = 0
    scores = {}
    for cat, result in category_results.items():
        if result['total'] > 0:
            scores[cat] = round((result['correct'] / result['total']) * 100)
        else:
            scores[cat] = 0

    # ── MAP SCORES TO PROFICIENCY LEVELS ──
    levels = {}
    level_ranges = scoring_config['levels']
    for cat, score in scores.items():
        levels[cat] = _get_level(score, level_ranges)

    # ── GENERATE SUMMARY TEXT ──
    summary = _generate_aptitude_summary(scores, levels)

    return {
        'scores': scores,
        'levels': levels,
        'details': details,
        'total_answered': len(user_answers),
        'summary': summary
    }


def _get_level(score: int, level_ranges: dict) -> str:
    """
    Map a numeric score (0–100) to a proficiency level string.

    Level Ranges (from config):
        beginner:   0–40
        developing: 41–60
        proficient: 61–80
        advanced:   81–100
    """
    for level_name, (low, high) in level_ranges.items():
        if low <= score <= high:
            return level_name
    return 'beginner'  # Fallback


def _generate_aptitude_summary(scores: dict, levels: dict) -> str:
    """
    Generate a human-readable summary of aptitude results.
    Deterministic: same input always yields same output.
    """
    parts = []
    for cat in ['logical', 'quantitative', 'verbal']:
        score = scores.get(cat, 0)
        level = levels.get(cat, 'beginner')
        parts.append(f"{cat.capitalize()}: {score}/100 ({level})")

    # Identify strongest and weakest area
    best_cat = max(scores, key=scores.get)
    weak_cat = min(scores, key=scores.get)

    summary = (
        f"Aptitude Results — " + " | ".join(parts) + ". "
        f"Your strongest area is {best_cat.capitalize()} and "
        f"your weakest area is {weak_cat.capitalize()}."
    )
    return summary


# ─────────────────────────────────────────────
# UTILITY: Get aptitude score for a single category
# ─────────────────────────────────────────────

def aptitude_meets_requirement(user_score: int, required_score: int) -> dict:
    """
    Check if a user's aptitude score meets a career's requirement.

    Returns:
        {
          "meets": True/False,
          "gap": 0 (or positive int if short),
          "percentage": 90  (user score as % of required)
        }
    """
    meets = user_score >= required_score
    gap = max(0, required_score - user_score)
    percentage = round((user_score / required_score * 100) if required_score > 0 else 100)
    return {
        'meets': meets,
        'gap': gap,
        'percentage': min(100, percentage)
    }