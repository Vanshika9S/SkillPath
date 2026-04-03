"""
skill_gap.py — Skill Gap Analyzer
===================================
DETERMINISTIC LOGIC ONLY. No AI, no randomness.

This module identifies the gap between what the user currently has
and what a target career requires.

Gap Classification (Priority Levels):
  CRITICAL  → Skill has weight ≥ 0.15 AND user level < 50% of required
  IMPORTANT → Skill has weight ≥ 0.08 AND user level < 70% of required
  OPTIONAL  → All other gaps

Every output is fully explainable: the priority classification,
the gap size, and the reason are all derived from explicit rules.
"""

import json
import os


# ─────────────────────────────────────────────
# PRIORITY THRESHOLDS (adjust here to tune)
# ─────────────────────────────────────────────

CRITICAL_WEIGHT_THRESHOLD  = 0.15   # Skill contributes ≥15% of career score
CRITICAL_RATIO_THRESHOLD   = 0.50   # User is at <50% of what's needed

IMPORTANT_WEIGHT_THRESHOLD = 0.08   # Skill contributes ≥8% of career score
IMPORTANT_RATIO_THRESHOLD  = 0.70   # User is at <70% of what's needed


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

def _load_skill_resources():
    """Load skill learning resources from JSON."""
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'skill_resources.json')
    with open(path, 'r') as f:
        data = json.load(f)
    return data['skills']


# ─────────────────────────────────────────────
# MAIN GAP ANALYSIS FUNCTION
# ─────────────────────────────────────────────

def analyze_skill_gaps(user_skills: dict, career: dict) -> dict:
    """
    Perform a detailed skill gap analysis between the user's current
    skill levels and the career's requirements.

    Logic flow:
    1. For each skill required by the career:
       a. Compute gap = required_level - user_level
       b. Compute ratio = user_level / required_level
       c. Classify priority: CRITICAL / IMPORTANT / OPTIONAL / MET
    2. For completely missing skills, user_level = 0
    3. Sort gaps by priority (critical first), then by gap size

    Parameters:
        user_skills: {"programming": 7, "mathematics": 4, ...}
        career: career dict from careers.json

    Returns:
        {
          "career_name": "Software Engineer",
          "gaps": [
            {
              "skill": "data_analysis",
              "user_level": 0,
              "required_level": 6,
              "gap": 6,
              "ratio": 0.0,
              "priority": "CRITICAL",
              "priority_reason": "This skill has high weight (0.03) and you score below 50% of required.",
              "resources": [...],
              "estimated_days": 10,
              "is_missing": True
            },
            ...
          ],
          "met_skills": ["logical_thinking", "problem_solving"],
          "summary": {
            "critical": 2,
            "important": 1,
            "optional": 3,
            "met": 4
          },
          "overall_readiness": 62.5   # % of skills already at required level
        }
    """
    required_skills = career.get('required_skills', {})
    skill_weights = career.get('skill_weights', {})
    skill_resources = _load_skill_resources()

    gaps = []
    met_skills = []
    total_skills = len(required_skills)
    skills_met = 0

    for skill, req_level in required_skills.items():
        user_level = user_skills.get(skill, 0)
        gap = max(0, req_level - user_level)  # Can't have negative gap
        ratio = (user_level / req_level) if req_level > 0 else 1.0
        ratio = min(1.0, ratio)  # Cap at 1.0 (can't over-qualify for gap calc)
        weight = skill_weights.get(skill, 0)
        is_missing = (skill not in user_skills or user_level == 0)

        if gap == 0:
            # User meets or exceeds requirement
            met_skills.append(skill)
            skills_met += 1
            continue

        # ── CLASSIFY PRIORITY (deterministic rules) ──
        priority, priority_reason = _classify_priority(skill, weight, ratio, gap, req_level)

        # ── LOOK UP LEARNING RESOURCES ──
        resource_info = skill_resources.get(skill, {})
        resources = resource_info.get('resources', ['Search online for beginner tutorials'])
        estimated_days = resource_info.get('estimated_days', 14)
        dependencies = resource_info.get('dependencies', [])

        gaps.append({
            'skill': skill,
            'skill_label': skill.replace('_', ' ').title(),
            'user_level': user_level,
            'required_level': req_level,
            'gap': gap,
            'ratio': round(ratio, 3),
            'weight': round(weight, 3),
            'priority': priority,
            'priority_reason': priority_reason,
            'resources': resources,
            'estimated_days': estimated_days,
            'dependencies': dependencies,
            'is_missing': is_missing
        })

    # Sort gaps: CRITICAL first, then IMPORTANT, then OPTIONAL; within each by gap size descending
    priority_order = {'CRITICAL': 0, 'IMPORTANT': 1, 'OPTIONAL': 2}
    gaps.sort(key=lambda g: (priority_order.get(g['priority'], 3), -g['gap']))

    # ── SUMMARY ──
    summary = {
        'critical': sum(1 for g in gaps if g['priority'] == 'CRITICAL'),
        'important': sum(1 for g in gaps if g['priority'] == 'IMPORTANT'),
        'optional': sum(1 for g in gaps if g['priority'] == 'OPTIONAL'),
        'met': len(met_skills)
    }

    # Overall readiness = % of required skills that are currently met
    overall_readiness = (skills_met / total_skills * 100) if total_skills > 0 else 100.0

    return {
        'career_name': career['name'],
        'career_id': career['id'],
        'gaps': gaps,
        'met_skills': met_skills,
        'summary': summary,
        'overall_readiness': round(overall_readiness, 1),
        'total_required_skills': total_skills,
        'skills_currently_met': skills_met
    }


# ─────────────────────────────────────────────
# PRIORITY CLASSIFICATION LOGIC
# ─────────────────────────────────────────────

def _classify_priority(skill: str, weight: float, ratio: float, gap: int, req_level: int) -> tuple:
    """
    Classify a skill gap as CRITICAL, IMPORTANT, or OPTIONAL.

    Rules (applied in order — first match wins):

    CRITICAL:
      - Skill weight is high (≥ CRITICAL_WEIGHT_THRESHOLD)
      - AND user is at less than 50% of the required level
      → This skill heavily influences career match AND the user is far behind.

    IMPORTANT:
      - Skill weight is moderate (≥ IMPORTANT_WEIGHT_THRESHOLD)
      - AND user is at less than 70% of the required level
      → This skill matters significantly but the gap is less severe.

    OPTIONAL:
      - All remaining gaps (lower weight or small gap)
      → Improving this would help but is not urgent.

    Returns:
        (priority_string, explanation_string)
    """
    skill_label = skill.replace('_', ' ')
    pct = round(ratio * 100)

    if weight >= CRITICAL_WEIGHT_THRESHOLD and ratio < CRITICAL_RATIO_THRESHOLD:
        reason = (
            f"'{skill_label}' is a HIGH-WEIGHT skill for this career (weight: {weight:.0%}) "
            f"and you're only at {pct}% of the required level. "
            f"This gap will significantly lower your match score."
        )
        return 'CRITICAL', reason

    elif weight >= IMPORTANT_WEIGHT_THRESHOLD and ratio < IMPORTANT_RATIO_THRESHOLD:
        reason = (
            f"'{skill_label}' contributes meaningfully to this career (weight: {weight:.0%}) "
            f"and you're at {pct}% of the required level. "
            f"Closing this gap will improve your match score noticeably."
        )
        return 'IMPORTANT', reason

    else:
        reason = (
            f"'{skill_label}' has a lower weight for this career (weight: {weight:.0%}) "
            f"or the gap is small (you're at {pct}% of required). "
            f"Improving this is beneficial but not urgent."
        )
        return 'OPTIONAL', reason


# ─────────────────────────────────────────────
# MULTI-CAREER COMPARISON
# ─────────────────────────────────────────────

def compare_gaps_across_careers(user_skills: dict, career_results: list) -> dict:
    """
    Identify which career has the smallest skill gap (easiest to pursue)
    and which has the largest.

    Parameters:
        user_skills: user's skill dict
        career_results: list of scored careers from career_engine

    Returns:
        {
          "easiest_career": {career_id, career_name, critical_gaps},
          "hardest_career": {career_id, career_name, critical_gaps},
          "comparison": [{career_id, critical, important, optional, readiness}]
        }
    """
    from career_engine import get_career_by_id

    comparison = []
    for scored in career_results:
        career = get_career_by_id(scored['career_id'])
        if not career:
            continue
        gap_analysis = analyze_skill_gaps(user_skills, career)
        comparison.append({
            'career_id': scored['career_id'],
            'career_name': scored['career_name'],
            'total_score': scored['total_score'],
            'critical_gaps': gap_analysis['summary']['critical'],
            'important_gaps': gap_analysis['summary']['important'],
            'optional_gaps': gap_analysis['summary']['optional'],
            'readiness': gap_analysis['overall_readiness']
        })

    if not comparison:
        return {'easiest_career': None, 'hardest_career': None, 'comparison': []}

    # Sort by readiness descending
    comparison.sort(key=lambda c: -c['readiness'])
    easiest = comparison[0]
    hardest = comparison[-1]

    return {
        'easiest_career': easiest,
        'hardest_career': hardest,
        'comparison': comparison
    }


# ─────────────────────────────────────────────
# SKILL GAP IMPACT ESTIMATOR
# ─────────────────────────────────────────────

def estimate_gap_impact(gap_item: dict, career_score: float) -> dict:
    """
    Estimate how much closing a specific skill gap would improve the career score.

    Logic:
    - If user goes from user_level to required_level, ratio becomes 1.0
    - Score increase = weight × (1.0 - current_ratio) × SKILL_WEIGHT × 100

    Parameters:
        gap_item: a gap dict from analyze_skill_gaps
        career_score: current total career match score

    Returns:
        {
          "potential_score_gain": 8.3,
          "new_estimated_score": 76.5
        }
    """
    from career_engine import SKILL_WEIGHT

    weight = gap_item.get('weight', 0)
    current_ratio = gap_item.get('ratio', 0)
    gap_ratio = 1.0 - current_ratio  # How much ratio improvement is possible

    # Score gain = (ratio improvement) × weight × skill component weight × 100
    score_gain = gap_ratio * weight * SKILL_WEIGHT * 100
    new_score = min(100, career_score + score_gain)

    return {
        'potential_score_gain': round(score_gain, 2),
        'new_estimated_score': round(new_score, 2)
    }