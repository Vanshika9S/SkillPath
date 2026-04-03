# SkillPath — Skill Gap Identifier & Career Guidance System
## "AI Without the API: Deterministic Intelligence"

> Every output is explainable. Every decision is traceable. No AI at runtime.

---

## Architecture Overview

```
skillpath/
├── backend/
│   ├── app.py             ← Flask API server (all endpoints)
│   ├── career_engine.py   ← Core scoring + recommendation logic
│   ├── skill_gap.py       ← Gap analysis + prioritization
│   ├── planner.py         ← Study plan generator with dependency resolution
│   └── aptitude.py        ← Aptitude test evaluator
├── data/
│   ├── careers.json           ← 15 career definitions with weights
│   ├── aptitude_questions.json ← 30 questions (10 per category)
│   └── skill_resources.json   ← Skill learning resources + dependencies
├── frontend/
│   └── index.html         ← Single-file React-less frontend
└── requirements.txt
```

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Flask server
```bash
cd backend
python app.py
```
Server runs on: http://localhost:5000

### 3. Open the frontend
Open `frontend/index.html` in any browser.
*(No build step needed — pure HTML/CSS/JS)*

---

## How The Scoring Works (Fully Deterministic)

### Career Match Formula
```
total_score = (skill_score  × 0.45)
            + (aptitude_score × 0.35)
            + (interest_score × 0.15)
            + (parent_boost  × 0.05)
```

### Skill Match Score
```
For each required skill:
  ratio = min(1.0, user_level / required_level)
  contribution = skill_weight × ratio

skill_score = (sum of contributions / total_weight) × 100
```

### Aptitude Match Score
```
For each aptitude category (logical/quantitative/verbal):
  ratio = min(1.0, user_score / required_score)

aptitude_score = average(ratios) × 100
```

### Interest Match Score
```
interest_score = (matched_interests / total_career_interests) × 100
```

### Skill Gap Priority Classification
```
CRITICAL  → weight ≥ 15%  AND  user_level < 50% of required
IMPORTANT → weight ≥  8%  AND  user_level < 70% of required
OPTIONAL  → all other gaps
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/careers` | List all careers |
| GET | `/api/careers/<id>` | Single career detail |
| GET | `/api/questions` | Aptitude questions (no answers) |
| POST | `/api/aptitude/evaluate` | Evaluate test responses |
| POST | `/api/recommend` | Get top 3 career recommendations |
| POST | `/api/validate` | Validate a user-chosen career |
| POST | `/api/gaps` | Detailed skill gap analysis |
| POST | `/api/plan` | Generate study plan |
| POST | `/api/whatif` | What-if simulation |
| POST | `/api/full-analysis` | Full pipeline in one call |

---

## Hackathon Demo Script

1. **Show Profile Page** — Demonstrate skill sliders + interest tags
2. **Take Aptitude Test** — Answer a few questions, submit, show per-category scores
3. **Get Recommendations** — Show top 3 careers with score breakdown and explanation
4. **Skill Gap Analyzer** — Show CRITICAL/IMPORTANT/OPTIONAL classification with reasons
5. **Study Plan** — Show week-by-week plan with dependency ordering
6. **What-If Simulator** — Bump up "mathematics" by 3 points, show score changes live

### Key Talking Points
- "Every number you see comes from an explicit formula — I can show you the calculation"
- "Same inputs = same outputs, always. No randomness, no AI guessing"
- "The gap priority system uses two thresholds: weight and coverage ratio"
- "The study planner uses topological sort to respect learning dependencies"

---

## Extending The System

### Add a new career
Edit `data/careers.json` — add an entry with:
- `required_skills` with levels 1–10
- `skill_weights` that sum to ~1.0
- `required_aptitude` for logical/quantitative/verbal
- `related_interests` list

### Add aptitude questions
Edit `data/aptitude_questions.json` — follow the existing format.
Questions must have `id`, `category`, `question`, `options` (4), `answer` (index), `explanation`.

### Change scoring weights
In `career_engine.py`, modify:
```python
SKILL_WEIGHT    = 0.45
APTITUDE_WEIGHT = 0.35
INTEREST_WEIGHT = 0.15
PARENT_WEIGHT   = 0.05
```

### Change gap priority thresholds
In `skill_gap.py`, modify:
```python
CRITICAL_WEIGHT_THRESHOLD  = 0.15
CRITICAL_RATIO_THRESHOLD   = 0.50
IMPORTANT_WEIGHT_THRESHOLD = 0.08
IMPORTANT_RATIO_THRESHOLD  = 0.70
```
