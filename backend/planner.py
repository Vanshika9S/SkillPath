"""
planner.py — Study Planner Module
====================================
DETERMINISTIC LOGIC ONLY. No AI, no randomness.

Generates a structured, week-by-week study plan based on:
  1. Skill gaps (prioritized: CRITICAL → IMPORTANT → OPTIONAL)
  2. Time available per day (user input, in hours)
  3. Dependency logic (e.g., must learn basics before advanced topics)
  4. Estimated learning time per skill (from skill_resources.json)

The plan is fully deterministic: same gaps + same time = same plan.

Planning Algorithm:
  - Sort skills by priority (CRITICAL first)
  - Resolve dependencies: if skill A requires skill B, schedule B first
  - Assign skills to weeks based on available hours per day
  - Each skill gets estimated_days to learn (from resource data)
  - Minimum 1 hour/day of study assumed regardless of input

Output Structure:
  - Weekly plan: each week contains one or more skills to focus on
  - Each week specifies: skill, hours/day, activities, resources
  - Total duration estimate in weeks
"""

import json
import os
from typing import List


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

HOURS_PER_DAY_TO_DAYS_MULTIPLIER = {
    # Maps hours/day to an adjustment factor
    # More hours/day = fewer calendar days needed
    0.5:  2.0,   # 0.5 hr/day = 2x longer
    1.0:  1.5,   # 1 hr/day = 1.5x standard
    1.5:  1.2,   # 1.5 hr/day = 1.2x standard
    2.0:  1.0,   # 2 hr/day = standard (baseline)
    3.0:  0.75,  # 3 hr/day = 25% faster
    4.0:  0.60,  # 4 hr/day = 40% faster
}
DEFAULT_MULTIPLIER = 1.0   # Fallback if hours not in table
DAYS_PER_WEEK = 7


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

def _load_skill_resources():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'skill_resources.json')
    with open(path, 'r') as f:
        data = json.load(f)
    return data['skills']


# ─────────────────────────────────────────────
# DEPENDENCY RESOLVER
# ─────────────────────────────────────────────

def resolve_skill_order(skill_list: list, skill_resources: dict) -> list:
    """
    Sort skills so that prerequisites always come before dependent skills.
    Uses topological sort (Kahn's algorithm — deterministic BFS).

    Example:
        programming_basics depends on logical_thinking
        → logical_thinking is scheduled first

    Parameters:
        skill_list: list of skill IDs to include in the plan
        skill_resources: dict of skill metadata with 'dependencies'

    Returns:
        Ordered list of skill IDs (prerequisite-first order)
    """
    # Build adjacency: skill → list of skills that depend on it
    # and in-degree counter for Kahn's algorithm
    skill_set = set(skill_list)
    in_degree = {skill: 0 for skill in skill_list}
    adjacency = {skill: [] for skill in skill_list}

    for skill in skill_list:
        deps = skill_resources.get(skill, {}).get('dependencies', [])
        for dep in deps:
            if dep in skill_set:
                # dep must come before skill
                adjacency[dep].append(skill)
                in_degree[skill] += 1

    # Start with skills that have no prerequisites (in-degree 0)
    # Sort alphabetically for determinism when multiple have in-degree 0
    queue = sorted([s for s in skill_list if in_degree[s] == 0])
    ordered = []

    while queue:
        current = queue.pop(0)
        ordered.append(current)

        # Reduce in-degree for dependents
        for dependent in adjacency[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                # Insert in sorted position for determinism
                queue.append(dependent)
                queue.sort()

    # If there are remaining skills (cyclic deps, shouldn't happen in our data),
    # append them in alphabetical order as fallback
    remaining = [s for s in skill_list if s not in ordered]
    ordered.extend(sorted(remaining))

    return ordered


# ─────────────────────────────────────────────
# MAIN PLAN GENERATOR
# ─────────────────────────────────────────────

def generate_study_plan(gap_analysis: dict, hours_per_day: float) -> dict:
    """
    Generate a structured week-by-week study plan.

    Parameters:
        gap_analysis: output from skill_gap.analyze_skill_gaps()
        hours_per_day: float (e.g. 1.5 = 1.5 hours/day)

    Returns:
        {
          "total_weeks": 14,
          "total_days": 98,
          "hours_per_day": 1.5,
          "weeks": [
            {
              "week_number": 1,
              "skills": ["logical_thinking"],
              "activities": ["..."],
              "resources": ["..."],
              "notes": "Foundation phase — start here",
              "estimated_days": 7
            },
            ...
          ],
          "phases": {
            "foundation": ["logical_thinking", "mathematics_basics"],
            "intermediate": ["programming_basics"],
            "advanced": ["data_structures"]
          },
          "plan_summary": "..."
        }
    """
    hours_per_day = max(0.5, min(8.0, hours_per_day))  # Clamp to reasonable range
    skill_resources = _load_skill_resources()

    # ── STEP 1: Extract gaps and sort by priority ──
    # Priority order: CRITICAL → IMPORTANT → OPTIONAL
    priority_order = {'CRITICAL': 0, 'IMPORTANT': 1, 'OPTIONAL': 2}
    gaps = sorted(gap_analysis.get('gaps', []),
                  key=lambda g: (priority_order.get(g['priority'], 3), -g['gap']))

    # ── STEP 2: Get skill IDs that need to be learned ──
    # Also add required prerequisites for those skills (even if not in gaps)
    skills_to_learn = [g['skill'] for g in gaps]
    all_skills_with_deps = _expand_with_dependencies(skills_to_learn, skill_resources)

    # ── STEP 3: Resolve learning order via topological sort ──
    ordered_skills = resolve_skill_order(all_skills_with_deps, skill_resources)

    # ── STEP 4: Estimate adjusted duration per skill ──
    # Adjust standard estimated_days by the hours_per_day factor
    time_multiplier = _get_time_multiplier(hours_per_day)

    skill_day_estimates = {}
    for skill in ordered_skills:
        base_days = skill_resources.get(skill, {}).get('estimated_days', 14)
        adjusted_days = round(base_days * time_multiplier)
        adjusted_days = max(3, adjusted_days)  # Minimum 3 days per skill
        skill_day_estimates[skill] = adjusted_days

    # ── STEP 5: Assign skills to weeks ──
    weeks = []
    current_day = 0
    week_number = 1

    # Group skills into weeks (pack skills that fit within ~7 day windows)
    i = 0
    while i < len(ordered_skills):
        skill = ordered_skills[i]
        skill_days = skill_day_estimates[skill]
        skill_info = skill_resources.get(skill, {})
        gap_info = next((g for g in gaps if g['skill'] == skill), None)

        # Determine phase label
        phase = skill_info.get('level', 'intermediate')
        priority = gap_info['priority'] if gap_info else 'OPTIONAL'

        # Build week entry
        week_entry = {
            'week_number': week_number,
            'start_day': current_day + 1,
            'end_day': current_day + skill_days,
            'skills': [skill],
            'skill_labels': [skill.replace('_', ' ').title()],
            'priority': priority,
            'phase': phase,
            'estimated_days': skill_days,
            'hours_per_day': hours_per_day,
            'total_hours': round(skill_days * hours_per_day, 1),
            'activities': _get_activities(skill, phase, skill_info),
            'resources': skill_info.get('resources', ['Search for online tutorials']),
            'learning_goal': _get_learning_goal(skill, skill_info),
            'notes': _get_week_notes(priority, phase, week_number)
        }

        # Pack a second skill into the same week if it's small and we have room
        if (i + 1 < len(ordered_skills) and
                skill_days <= 5 and
                skill_day_estimates[ordered_skills[i + 1]] <= 3):
            next_skill = ordered_skills[i + 1]
            next_info = skill_resources.get(next_skill, {})
            next_days = skill_day_estimates[next_skill]
            next_gap = next((g for g in gaps if g['skill'] == next_skill), None)

            week_entry['skills'].append(next_skill)
            week_entry['skill_labels'].append(next_skill.replace('_', ' ').title())
            week_entry['estimated_days'] = max(skill_days, next_days)
            week_entry['activities'].extend(_get_activities(next_skill, next_info.get('level', 'intermediate'), next_info))
            week_entry['resources'].extend(next_info.get('resources', []))
            i += 1  # Skip next skill as it's packed in this week

        weeks.append(week_entry)
        current_day = week_entry['end_day']
        
        i += 1
    for week_entry in weeks:
        week_entry['week_number'] = ((week_entry['start_day'] - 1) // 7) + 1
    # ── STEP 6: Compute totals ──
    total_days  = current_day
    # Calculate actual calendar weeks from total days
    import math
    total_weeks = (total_days + 6) // 7

    # ── STEP 7: Build phases summary ──
    phases = _build_phase_summary(ordered_skills, skill_resources)

    # ── STEP 8: Plan summary ──
    plan_summary = _build_plan_summary(gap_analysis, total_weeks, total_days, hours_per_day)

    return {
        'career_name': gap_analysis.get('career_name', 'Your Target Career'),
        'total_weeks': total_weeks,          # now = ceil(total_days / 7)
        'total_days': total_days,
        'hours_per_day': hours_per_day,
        'total_study_hours': round(total_days * hours_per_day, 1),
        'weeks': weeks,
        'phases': phases,
        'skills_in_plan': ordered_skills,
        'plan_summary': plan_summary,
        'note': f"Plan for {hours_per_day}h/day. Review and adjust weekly."
    }


# ─────────────────────────────────────────────
# DEPENDENCY EXPANDER
# ─────────────────────────────────────────────

def _expand_with_dependencies(skills: list, skill_resources: dict) -> list:
    """
    Add any missing prerequisites for the given skills.
    Ensures you don't skip fundamentals.

    Example: If 'programming_basics' is in skills, and it requires
    'logical_thinking' which is NOT in skills, add 'logical_thinking'.
    """
    expanded = set(skills)
    to_process = list(skills)

    while to_process:
        skill = to_process.pop(0)
        deps = skill_resources.get(skill, {}).get('dependencies', [])
        for dep in deps:
            if dep not in expanded:
                expanded.add(dep)
                to_process.append(dep)

    return list(expanded)


# ─────────────────────────────────────────────
# TIME MULTIPLIER HELPER
# ─────────────────────────────────────────────

def _get_time_multiplier(hours_per_day: float) -> float:
    """
    Find the closest time multiplier for given hours/day.
    More hours/day = lower multiplier (faster completion).
    """
    # Find nearest key in the table
    keys = sorted(HOURS_PER_DAY_TO_DAYS_MULTIPLIER.keys())
    closest = min(keys, key=lambda k: abs(k - hours_per_day))
    return HOURS_PER_DAY_TO_DAYS_MULTIPLIER[closest]


# ─────────────────────────────────────────────
# CONTENT GENERATORS (DETERMINISTIC)
# ─────────────────────────────────────────────

def _get_activities(skill: str, phase: str, skill_info: dict) -> list:
    """
    Return a list of recommended learning activities for a skill.
    Deterministic: based on skill level and type.
    """
    activities = []
    skill_label = skill.replace('_', ' ').title()

    if phase == 'foundational':
        activities = [
            f"Read introductory material on {skill_label}",
            f"Watch beginner tutorial videos for {skill_label}",
            f"Complete 5–10 practice exercises daily",
            f"Take notes and summarize key concepts"
        ]
    elif phase == 'intermediate':
        activities = [
            f"Study core concepts of {skill_label} through structured course",
            f"Build 1–2 small projects applying {skill_label}",
            f"Solve practice problems increasing in difficulty",
            f"Review and revise weekly"
        ]
    elif phase == 'advanced':
        activities = [
            f"Deep-dive into advanced topics in {skill_label}",
            f"Build a significant project demonstrating {skill_label}",
            f"Peer review or get mentor feedback",
            f"Explore real-world case studies"
        ]

    return activities


def _get_learning_goal(skill: str, skill_info: dict) -> str:
    """Return the specific goal for learning this skill."""
    label = skill.replace('_', ' ').title()
    description = skill_info.get('description', f"Develop proficiency in {label}")
    return f"By end of this period: {description}"


def _get_week_notes(priority: str, phase: str, week_num: int) -> str:
    """Return contextual notes for the week."""
    if priority == 'CRITICAL' and phase == 'foundational':
        return '⚠️ Critical foundation — do not skip this step.'
    elif priority == 'CRITICAL':
        return '⚠️ Critical skill — prioritize this over everything else.'
    elif priority == 'IMPORTANT':
        return '📌 Important skill — steady progress here will improve your career match significantly.'
    elif week_num <= 2:
        return '🚀 Great start! Build momentum with consistent daily practice.'
    else:
        return '✅ Keep going — you\'re building a strong profile.'


def _build_phase_summary(ordered_skills: list, skill_resources: dict) -> dict:
    """Group skills into foundational / intermediate / advanced phases."""
    phases = {'foundational': [], 'intermediate': [], 'advanced': []}
    for skill in ordered_skills:
        level = skill_resources.get(skill, {}).get('level', 'intermediate')
        if level in phases:
            phases[level].append(skill.replace('_', ' ').title())
    return phases


def _build_plan_summary(gap_analysis, total_weeks, total_days, hours_per_day):
    critical  = gap_analysis['summary']['critical']
    important = gap_analysis['summary']['important']
    career    = gap_analysis.get('career_name', 'your target career')
    return (
        f"Your personalized plan to reach {career} spans "
        f"~{total_weeks} week(s) ({total_days} study-days) at {hours_per_day}h/day. "
        f"Addresses {critical} critical gap(s) and {important} important gap(s). "
        f"Prerequisites are always taught before dependent skills."
    )