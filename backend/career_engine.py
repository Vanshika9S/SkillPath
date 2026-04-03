"""
career_engine.py — Career Matching & Recommendation Engine
===========================================================
DETERMINISTIC LOGIC ONLY. No AI, no randomness.

This module is the CORE of the system. It computes career match scores
using three weighted components:
  1. Skill Match     (how well user's skills align with career needs)
  2. Aptitude Match  (how well test scores meet career aptitude requirements)
  3. Interest Match  (how many interests overlap with career's related interests)

Plus an optional Parent Input Boost when parent observations are provided.

Formula (explainable, traceable):
  total_score = (skill_score × 0.45)
              + (aptitude_score × 0.35)
              + (interest_score × 0.15)
              + (parent_boost × 0.05)

Score range: 0–100 (match percentage)
"""

import json
import os


# ─────────────────────────────────────────────
# WEIGHT CONSTANTS (modify here to tune system)
# ─────────────────────────────────────────────

SKILL_WEIGHT       = 0.45   # Skills are the most important factor
APTITUDE_WEIGHT    = 0.35   # Aptitude test is second most important
INTEREST_WEIGHT    = 0.15   # Interest alignment is a secondary signal
PARENT_WEIGHT      = 0.05   # Parent observations are a soft signal


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

def _load_careers():
    """Load career definitions from JSON data file."""
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'careers.json')
    with open(path, 'r') as f:
        data = json.load(f)
    return data['careers']


def get_all_careers():
    """Return all career definitions (for frontend career explorer)."""
    return _load_careers()


def get_career_by_id(career_id: str) -> dict | None:
    """Fetch a single career by its ID."""
    careers = _load_careers()
    for career in careers:
        if career['id'] == career_id:
            return career
    return None


# ─────────────────────────────────────────────
# COMPONENT 1: SKILL MATCH SCORE (0–100)
# ─────────────────────────────────────────────

def compute_skill_score(user_skills: dict, career: dict) -> dict:
    """
    Compare user's skill levels against career's required skills.

    Logic:
    - Each required skill has a weight (from career data)
    - User provides skill level 1–10 (or 0 if skill is absent)
    - Career requires a minimum skill level 1–10
    - For each skill: contribution = weight × (user_level / required_level)
    - Capped at 1.0 per skill (can't get more than full weight by exceeding requirement)
    - Final score = sum of contributions × 100

    This means:
    - A skill not listed by user = 0 contribution (penalized)
    - A skill at exactly the required level = full contribution
    - Exceeding the requirement = capped at full contribution

    Parameters:
        user_skills: {"programming": 7, "mathematics": 5, ...}
        career: career dict with 'required_skills' and 'skill_weights'

    Returns:
        {
          "score": 72.5,
          "breakdown": {
            "programming": {"user": 7, "required": 9, "contribution": 0.23, "weight": 0.30}
          },
          "missing_skills": ["data_analysis", ...]
        }
    """
    required = career.get('required_skills', {})
    weights = career.get('skill_weights', {})
    total_possible_weight = sum(weights.values())

    breakdown = {}
    weighted_score = 0.0
    missing_skills = []

    for skill, req_level in required.items():
        weight = weights.get(skill, 0)
        user_level = user_skills.get(skill, 0)  # 0 if skill not listed

        if user_level == 0:
            missing_skills.append(skill)

        # Ratio of user's level to required level (max 1.0)
        ratio = min(1.0, user_level / req_level) if req_level > 0 else 1.0

        # Contribution of this skill to total score
        contribution = weight * ratio
        weighted_score += contribution

        breakdown[skill] = {
            'user_level': user_level,
            'required_level': req_level,
            'weight': round(weight, 3),
            'ratio': round(ratio, 3),
            'contribution': round(contribution, 4)
        }

    # Normalize to 100 (in case weights don't sum to exactly 1.0)
    if total_possible_weight > 0:
        score = (weighted_score / total_possible_weight) * 100
    else:
        score = 0

    return {
        'score': round(score, 2),
        'breakdown': breakdown,
        'missing_skills': missing_skills
    }


# ─────────────────────────────────────────────
# COMPONENT 2: APTITUDE MATCH SCORE (0–100)
# ─────────────────────────────────────────────

def compute_aptitude_score(aptitude_scores: dict, career: dict) -> dict:
    """
    Compare user's aptitude test scores against career requirements.

    Logic:
    - Career defines minimum aptitude levels for each category (0–100 scale)
    - User's test scores are on the same 0–100 scale
    - For each category: ratio = user_score / required_score (capped at 1.0)
    - Final aptitude score = average of all category ratios × 100
    - If career doesn't require aptitude in a category, it's ignored

    Parameters:
        aptitude_scores: {"logical": 70, "quantitative": 55, "verbal": 80}
        career: career dict with 'required_aptitude'

    Returns:
        {
          "score": 81.3,
          "breakdown": {
            "logical": {"user": 70, "required": 75, "ratio": 0.93}
          },
          "weak_areas": ["quantitative"]
        }
    """
    required = career.get('required_aptitude', {})
    breakdown = {}
    weak_areas = []
    ratios = []

    for cat, req_score in required.items():
        user_score = aptitude_scores.get(cat, 0)
        ratio = min(1.0, user_score / req_score) if req_score > 0 else 1.0
        ratios.append(ratio)

        if ratio < 1.0:
            weak_areas.append(cat)

        breakdown[cat] = {
            'user_score': user_score,
            'required_score': req_score,
            'ratio': round(ratio, 3),
            'meets_requirement': ratio >= 1.0
        }

    # Average ratio across all aptitude categories, scaled to 100
    score = (sum(ratios) / len(ratios) * 100) if ratios else 100.0

    return {
        'score': round(score, 2),
        'breakdown': breakdown,
        'weak_areas': weak_areas
    }


# ─────────────────────────────────────────────
# COMPONENT 3: INTEREST MATCH SCORE (0–100)
# ─────────────────────────────────────────────

def compute_interest_score(user_interests: list, career: dict) -> dict:
    """
    Calculate how many of the user's interests align with the career.

    Logic:
    - Career defines a list of related interests
    - User provides their interests as a list
    - Interest score = (matching interests / total career interests) × 100
    - Normalized to max 100

    Parameters:
        user_interests: ["coding", "math", "gaming", "music"]
        career: career dict with 'related_interests'

    Returns:
        {
          "score": 66.7,
          "matched": ["coding", "math"],
          "career_interests": ["technology", "gaming", "robotics", ...]
        }
    """
    career_interests = [i.lower() for i in career.get('related_interests', [])]
    user_interests_lower = [i.lower() for i in user_interests]

    matched = [i for i in user_interests_lower if i in career_interests]

    total_career_interests = len(career_interests)
    score = (len(matched) / total_career_interests * 100) if total_career_interests > 0 else 0

    return {
        'score': round(score, 2),
        'matched': matched,
        'career_interests': career_interests,
        'match_count': len(matched),
        'total_career_interests': total_career_interests
    }


# ─────────────────────────────────────────────
# COMPONENT 4: PARENT BOOST (0–10 → normalized)
# ─────────────────────────────────────────────

def compute_parent_boost(parent_observations: list, career: dict) -> dict:
    """
    Apply parent-observed strengths as a boost factor.

    Logic:
    - Parent provides observed strengths (list of skill/trait names)
    - If these match career's required skills → boost is higher
    - Boost score range: 0–10 (later normalized by PARENT_WEIGHT)

    Parameters:
        parent_observations: ["good at math", "very focused", "loves reading"]
        career: career dict

    Returns:
        {
          "score": 7.5,
          "matched_observations": ["math", "focused"]
        }
    """
    if not parent_observations:
        return {'score': 0, 'matched_observations': []}

    required_skills = list(career.get('required_skills', {}).keys())
    career_name_lower = career.get('name', '').lower()

    matched = []
    boost_score = 0

    for obs in parent_observations:
        obs_lower = obs.lower()
        # Check if observation mentions any required skill
        for skill in required_skills:
            skill_parts = skill.replace('_', ' ').split()
            if any(part in obs_lower for part in skill_parts):
                matched.append(obs)
                boost_score += 2  # +2 per matching observation
                break

    # Cap at 10
    boost_score = min(10, boost_score)

    # Normalize to 0–100
    normalized = boost_score * 10

    return {
        'score': normalized,
        'matched_observations': list(set(matched))  # Deduplicate
    }


# ─────────────────────────────────────────────
# MAIN SCORING FUNCTION
# ─────────────────────────────────────────────

def score_career(user_profile: dict, career: dict) -> dict:
    """
    Compute the overall match score between a user profile and a career.

    Parameters:
        user_profile: {
            "skills": {"programming": 7, "math": 5, ...},
            "interests": ["coding", "puzzles", ...],
            "aptitude_scores": {"logical": 70, "quantitative": 65, "verbal": 50},
            "parent_observations": ["good with numbers", ...]  # optional
        }
        career: career dict from careers.json

    Returns:
        {
          "career_id": "software_engineer",
          "career_name": "Software Engineer",
          "total_score": 78.4,        # 0–100 (this is the match percentage)
          "skill_result": {...},
          "aptitude_result": {...},
          "interest_result": {...},
          "parent_result": {...},
          "score_breakdown": {
            "skill_contribution": 35.3,
            "aptitude_contribution": 28.1,
            "interest_contribution": 11.7,
            "parent_contribution": 3.3
          },
          "explanation": "..."        # Human-readable explanation
        }
    """
    skills = user_profile.get('skills', {})
    interests = user_profile.get('interests', [])
    aptitude = user_profile.get('aptitude_scores', {})
    parent_obs = user_profile.get('parent_observations', [])

    # ── Compute all components ──
    skill_result     = compute_skill_score(skills, career)
    aptitude_result  = compute_aptitude_score(aptitude, career)
    interest_result  = compute_interest_score(interests, career)
    parent_result    = compute_parent_boost(parent_obs, career)

    # ── Weighted combination ──
    skill_contrib    = skill_result['score']    * SKILL_WEIGHT
    aptitude_contrib = aptitude_result['score'] * APTITUDE_WEIGHT
    interest_contrib = interest_result['score'] * INTEREST_WEIGHT
    parent_contrib   = parent_result['score']   * PARENT_WEIGHT

    total_score = skill_contrib + aptitude_contrib + interest_contrib + parent_contrib

    # ── Build explanation ──
    explanation = _build_explanation(
        career, skill_result, aptitude_result, interest_result, total_score
    )

    return {
        'career_id': career['id'],
        'career_name': career['name'],
        'career_category': career['category'],
        'career_description': career['description'],
        'total_score': round(total_score, 2),
        'skill_result': skill_result,
        'aptitude_result': aptitude_result,
        'interest_result': interest_result,
        'parent_result': parent_result,
        'score_breakdown': {
            'skill_contribution': round(skill_contrib, 2),
            'aptitude_contribution': round(aptitude_contrib, 2),
            'interest_contribution': round(interest_contrib, 2),
            'parent_contribution': round(parent_contrib, 2)
        },
        'weights_used': {
            'skill': SKILL_WEIGHT,
            'aptitude': APTITUDE_WEIGHT,
            'interest': INTEREST_WEIGHT,
            'parent': PARENT_WEIGHT
        },
        'explanation': explanation
    }


# ─────────────────────────────────────────────
# RECOMMENDATION ENGINE
# ─────────────────────────────────────────────

def get_top_careers(user_profile: dict, top_n: int = 3) -> dict:
    """
    Score all careers and return the top N matches.

    Parameters:
        user_profile: (see score_career)
        top_n: number of top careers to return (default 3)

    Returns:
        {
          "top_careers": [ranked list of score_career results],
          "all_scores": {career_id: total_score, ...},
          "ranking_explanation": "..."
        }
    """
    careers = _load_careers()
    all_results = []

    for career in careers:
        result = score_career(user_profile, career)
        all_results.append(result)

    # Sort by total_score descending — DETERMINISTIC (stable sort by career_id for ties)
    all_results.sort(key=lambda x: (-x['total_score'], x['career_id']))

    top_careers = all_results[:top_n]
    all_scores = {r['career_id']: r['total_score'] for r in all_results}

    return {
        'top_careers': top_careers,
        'all_scores': all_scores,
        'ranking_explanation': _build_ranking_explanation(top_careers)
    }


# ─────────────────────────────────────────────
# CAREER VALIDATION MODE
# ─────────────────────────────────────────────

def validate_career_choice(user_profile: dict, career_id: str) -> dict:
    """
    Evaluate how well a user's chosen career matches their profile.

    Returns a detailed suitability report with:
    - Match percentage
    - Strengths (where they already do well)
    - Weaknesses (areas to improve)
    - Suggestions (actionable advice)

    Parameters:
        user_profile: (see score_career)
        career_id: string career identifier

    Returns:
        {
          "match_percentage": 67.4,
          "suitability": "moderate",   # low / moderate / good / excellent
          "strengths": [...],
          "weaknesses": [...],
          "suggestions": [...],
          "score_result": {...}          # Full score breakdown
        }
    """
    career = get_career_by_id(career_id)
    if not career:
        return {'error': f"Career '{career_id}' not found"}

    score_result = score_career(user_profile, career)
    match_pct = score_result['total_score']

    # ── Determine suitability level ──
    if match_pct >= 80:
        suitability = 'excellent'
    elif match_pct >= 60:
        suitability = 'good'
    elif match_pct >= 40:
        suitability = 'moderate'
    else:
        suitability = 'low'

    # ── Identify Strengths ──
    strengths = []
    skill_bd = score_result['skill_result']['breakdown']
    for skill, info in skill_bd.items():
        if info['ratio'] >= 0.85:
            strengths.append(f"Strong in '{skill.replace('_', ' ')}' ({info['user_level']}/{info['required_level']} required)")

    if score_result['aptitude_result']['score'] >= 75:
        strengths.append(f"Good aptitude match ({score_result['aptitude_result']['score']:.0f}/100)")

    if score_result['interest_result']['score'] >= 50:
        matched = score_result['interest_result']['matched']
        strengths.append(f"Interest alignment: you share {len(matched)} relevant interest(s): {', '.join(matched)}")

    # ── Identify Weaknesses ──
    weaknesses = []
    for skill, info in skill_bd.items():
        if info['ratio'] < 0.5:
            weaknesses.append(f"Low level in '{skill.replace('_', ' ')}' (yours: {info['user_level']}, need: {info['required_level']})")

    for cat in score_result['aptitude_result']['weak_areas']:
        apt_info = score_result['aptitude_result']['breakdown'][cat]
        weaknesses.append(f"Aptitude gap in {cat} (yours: {apt_info['user_score']}, need: {apt_info['required_score']})")

    # ── Generate Suggestions ──
    suggestions = _build_suggestions(score_result, career, suitability)

    return {
        'career_id': career_id,
        'career_name': career['name'],
        'match_percentage': match_pct,
        'suitability': suitability,
        'strengths': strengths if strengths else ['No major strengths identified yet — keep building skills!'],
        'weaknesses': weaknesses if weaknesses else ['No critical weaknesses found for this career.'],
        'suggestions': suggestions,
        'score_result': score_result
    }


# ─────────────────────────────────────────────
# WHAT-IF SIMULATOR
# ─────────────────────────────────────────────

def simulate_improvement(user_profile: dict, improvements: dict) -> dict:
    """
    Simulate how improving certain skills/aptitude would change career scores.

    Parameters:
        user_profile: original user profile
        improvements: {
            "skills": {"mathematics": 3, "programming": 2},  # new levels
            "aptitude_scores": {"quantitative": 75}           # new scores
        }

    Returns:
        {
          "before": {career_id: score},
          "after": {career_id: score},
          "changes": {career_id: {"before": 67, "after": 78, "change": +11}},
          "most_improved": "software_engineer",
          "summary": "..."
        }
    """
    import copy

    # Create improved profile (deep copy so original is not mutated)
    improved_profile = copy.deepcopy(user_profile)

    # Apply skill improvements
    new_skills = improvements.get('skills', {})
    for skill, new_level in new_skills.items():
        improved_profile['skills'][skill] = new_level

    # Apply aptitude improvements
    new_aptitude = improvements.get('aptitude_scores', {})
    for cat, new_score in new_aptitude.items():
        improved_profile['aptitude_scores'][cat] = new_score

    # Score before and after
    before_results = get_top_careers(user_profile, top_n=50)  # Get all
    after_results  = get_top_careers(improved_profile, top_n=50)

    before_scores = before_results['all_scores']
    after_scores  = after_results['all_scores']

    # Compute changes
    changes = {}
    for career_id in before_scores:
        before = before_scores[career_id]
        after  = after_scores.get(career_id, before)
        delta  = after - before
        changes[career_id] = {
            'before': round(before, 2),
            'after': round(after, 2),
            'change': round(delta, 2),
            'change_label': f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        }

    # Find most improved career
    most_improved_id = max(changes, key=lambda cid: changes[cid]['change'])

    summary = _build_whatif_summary(improvements, changes, most_improved_id)

    return {
        'before': before_scores,
        'after': after_scores,
        'changes': changes,
        'most_improved': most_improved_id,
        'improvements_applied': improvements,
        'summary': summary
    }


# ─────────────────────────────────────────────
# EXPLAINABILITY HELPERS
# ─────────────────────────────────────────────

def _build_explanation(career, skill_result, aptitude_result, interest_result, total_score):
    """Build a human-readable explanation for why a career was scored this way."""
    lines = []

    # Skill explanation
    skill_score = skill_result['score']
    if skill_score >= 75:
        lines.append(f"Your skills strongly match {career['name']} requirements (skill score: {skill_score:.0f}/100).")
    elif skill_score >= 50:
        lines.append(f"Your skills moderately match {career['name']} (skill score: {skill_score:.0f}/100). Some gaps exist.")
    else:
        lines.append(f"Significant skill gaps exist for {career['name']} (skill score: {skill_score:.0f}/100).")

    # Aptitude explanation
    apt_score = aptitude_result['score']
    if apt_score >= 80:
        lines.append(f"Your aptitude is well-suited for this career (aptitude score: {apt_score:.0f}/100).")
    elif apt_score >= 60:
        lines.append(f"Your aptitude partially meets requirements (aptitude score: {apt_score:.0f}/100).")
    else:
        lines.append(f"Your aptitude may need improvement for {career['name']} (aptitude score: {apt_score:.0f}/100).")

    # Interest explanation
    int_score = interest_result['score']
    matched = interest_result['matched']
    if matched:
        lines.append(f"You share {len(matched)} interest(s) with this career: {', '.join(matched)}.")
    else:
        lines.append("No direct interest matches found, but interests can develop over time.")

    return ' '.join(lines)


def _build_ranking_explanation(top_careers):
    """Explain why the top 3 careers were selected."""
    if not top_careers:
        return "No careers could be ranked."
    names = [f"{c['career_name']} ({c['total_score']:.1f}%)" for c in top_careers]
    return (
        f"Top matches based on combined skill, aptitude, and interest alignment: "
        + " > ".join(names) + "."
    )


def _build_suggestions(score_result, career, suitability):
    """Generate actionable suggestions based on score gaps."""
    suggestions = []

    # Suggest working on weak aptitude areas
    for cat in score_result['aptitude_result']['weak_areas']:
        suggestions.append(f"Improve your {cat} aptitude through practice tests and exercises.")

    # Suggest skills with low ratios
    for skill, info in score_result['skill_result']['breakdown'].items():
        if info['ratio'] < 0.7:
            suggestions.append(
                f"Build your '{skill.replace('_', ' ')}' skill from level {info['user_level']} to at least {info['required_level']}."
            )

    # General suggestion based on suitability
    if suitability == 'low':
        suggestions.append(
            f"Your current profile has a low match with {career['name']}. "
            "Consider exploring careers that better fit your current strengths, or plan a long-term development path."
        )
    elif suitability == 'moderate':
        suggestions.append(
            "With focused effort on the skill gaps above, you can significantly improve your match percentage."
        )

    if not suggestions:
        suggestions.append(
            f"You are a strong match for {career['name']}! "
            "Focus on maintaining and deepening your existing skills."
        )

    return suggestions


def _build_whatif_summary(improvements, changes, most_improved_id):
    """Summarize what-if simulation results."""
    skill_changes = improvements.get('skills', {})
    apt_changes = improvements.get('aptitude_scores', {})

    change_desc = []
    for skill, level in skill_changes.items():
        change_desc.append(f"{skill.replace('_', ' ')} → level {level}")
    for cat, score in apt_changes.items():
        change_desc.append(f"{cat} aptitude → {score}")

    best_change = changes[most_improved_id]['change']
    return (
        f"If you improve: {', '.join(change_desc)}, "
        f"your best career gain would be '{most_improved_id.replace('_', ' ')}' "
        f"with +{best_change:.1f} percentage points."
    )