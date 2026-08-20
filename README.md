# CodeIntel — AI Developer Workspace & Code Intelligence Platform

A full-stack platform for writing, analyzing, debugging, documenting and
improving code, with an AI assistant built in.

**Stack:** React + Vite (frontend) → Django REST Framework (backend) →
a rule-based Python AI analysis engine (optionally enriched by the real
Claude API) → MySQL (database).

---

## 1. What's implemented

### User module
- Registration & login with server-side validation (username format,
  password strength via Django's validators, duplicate email/username checks)
- JWT authentication (access + refresh tokens, refresh rotation & blacklisting)
- Profile (bio, job title, preferred language, avatar URL)
- Dashboard (project/file/review counts, AI usage today, recent projects,
  recent reviews, recent activity — all in one API call)
- Saved projects list
- Activity history (every meaningful action is logged: login, project/file
  CRUD, uploads, shares, comments, AI feature usage)

### Code workspace
- Create/rename/delete projects, per-project language & visibility
- Multi-file editor (create, edit, save, delete) with a line-numbered editor
- Upload source files (validated extension + size + UTF-8 check) and
  download a single file or the whole project as a `.zip`
- Full version history per file with one-click restore
- Programming-language selection per project/file

### AI features (all real, working logic — see `backend/ai_engine/`)
| Feature | How it works |
|---|---|
| Explain code | AST-based structural summary (Python) / heuristic summary (other languages) |
| Find bugs | AST bug-pattern detector (mutable defaults, bare `except`, `== None`, unused vars, shadowed builtins, syntax errors) + regex heuristics for other languages |
| Fix bugs | Deterministic, safe textual fixes (e.g. `== None` → `is None`, mutable default → `None`) with a diff summary |
| Optimize code | Detects nested loops, string/list concatenation in loops, high-complexity functions |
| Generate code | Template engine keyed off the prompt (REST endpoint, class, function, sort, binary search, …) |
| Convert code | Structural Python ⇄ JavaScript conversion (`def`/`function`, `self`/`this`, `None`/`null`, etc.) |
| Generate comments | Inserts a one-line comment above every undocumented function/class (AST-based for Python) |
| Generate documentation | Produces Markdown docs from parsed classes/functions/docstrings |
| Generate test cases | Produces a `pytest` skeleton per top-level function |
| Generate SQL | Rule-based NL → SQL (SELECT/INSERT/UPDATE/DELETE, WHERE, ORDER BY, LIMIT, aggregates) |
| Explain error messages | A pattern-matched knowledge base (`NameError`, `KeyError`, `IndentationError`, Django/MySQL/CORS errors, …) with suggested fixes |
| Detect security issues | Regex scanner for `eval`/`exec`, `shell=True`, SQL string concatenation, hardcoded secrets, disabled TLS verification, etc. |
| Code quality score | Weighted 0–100 score combining bugs, security, complexity, comments, formatting, with a letter grade |
| Complexity analysis | Real McCabe cyclomatic complexity per function (AST-based for Python) |
| AI code review | Aggregates all of the above into one persisted review record |

If `ANTHROPIC_API_KEY` is set in the backend `.env`, every analysis feature
is additionally sent to the real Claude API for a natural-language
narrative layered on top of the static-analysis findings. **Without a key,
every feature still works fully offline** on the rule-based engine.

### Collaboration
- Share a project with another user by username/email, with viewer/editor/admin roles
- Project members list & removal
- Line-level or file-level comments with reply threading (model-level)
- Review history across every project you own or collaborate on
- Team activity feed

### Admin
- User management (change role, activate/deactivate)
- Project management (archive/unarchive/delete, filter by language/visibility)
- AI usage statistics (by feature, by status, by engine, top users, daily counts)
- Review statistics (average score, grade distribution, most-reviewed projects)
- System settings (arbitrary key/value JSON settings)

---

## 2. Project structure

```
ai-devworkspace/
├── backend/                 # Django REST API
│   ├── config/               # settings, urls, wsgi/asgi
│   ├── accounts/              # User model, auth, activity log, dashboard
│   ├── projects/               # Projects, files, versions, comments, sharing
│   ├── ai_engine/                # analyzers.py, generators.py, ai_client.py, views
│   ├── collaboration/              # shared projects, review history, team activity
│   ├── adminapi/                    # admin-only endpoints
│   ├── requirements.txt
│   └── .env.example
└── frontend/                # React + Vite SPA
    ├── src/
    │   ├── api/               # axios client + endpoint wrappers
    │   ├── context/            # AuthContext (JWT session state)
    │   ├── components/          # Sidebar, Topbar, FileTree, CodeEditor, AIPanel, ...
    │   ├── pages/                 # Login, Register, Dashboard, Projects, Workspace, ...
    │   └── styles/                 # design tokens + layout CSS
    └── package.json
```

---

## 3. Backend setup

### Requirements
- **Python 3.11 or 3.12** (Django 5.0 doesn't yet officially support 3.13+/3.14 — using a newer
  interpreter can cause package build/import failures, since prebuilt wheels lag behind new Python
  releases. The included `runtime.txt` pins Render to 3.12.7 for this reason.)
- MySQL 8+ or PostgreSQL 14+ (or use the SQLite fallback for a quick local trial)

### Steps

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
# Add a database driver only if you're using MySQL or Postgres (see note below):
#   pip install -r requirements-mysql.txt      # for MySQL
#   pip install -r requirements-postgres.txt   # for Postgres (e.g. Render's managed DB, uses psycopg v3)

cp .env.example .env
# edit .env: set DJANGO_SECRET_KEY, DB_* (or USE_SQLITE=True to skip a DB driver entirely)
```

> **Why the driver is separate:** `mysqlclient` and `psycopg2-binary` compile native
> extensions. On machines without matching build tools (or very new/unsupported Python
> versions), that install step can fail — and because pip aborts the whole batch when one
> package fails to build, everything *after* it in the list silently never gets installed
> too. Keeping `requirements.txt` itself driver-free means the core install always
> succeeds, and SQLite-only local dev needs nothing extra at all.

Create the MySQL database (skip this if using `USE_SQLITE=True`):

```sql
CREATE DATABASE ai_devworkspace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'your_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ai_devworkspace.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

Then:

```bash
python manage.py migrate
python manage.py runserver         # http://127.0.0.1:8000
```

### Creating an admin user

**Option A — via environment variables (recommended; also what `render.yaml` uses on deploy):**

Set these in `.env` (local) or your host's environment variables (production):
```
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=a-strong-password
```
then run:
```bash
python manage.py ensure_admin
```
This creates the account (superuser + `is_staff` + in-app `role='admin'`) or, if it
already exists, updates it to match those values — safe to re-run any time, including
on every deploy. On Render, set the three `DJANGO_SUPERUSER_*` env vars once in the
dashboard and every subsequent deploy keeps the admin account in sync automatically
(the build command already calls this command).

**Option B — interactively:**
```bash
python manage.py createsuperuser
python manage.py shell -c "
from accounts.models import User
u = User.objects.get(username='YOUR_USERNAME')
u.role = 'admin'
u.save()
"
```
(the second command promotes the account for the in-app Admin panel, which is
checked separately from Django's own `/admin/` superuser flag)

### Optional: enable the real LLM layer

Set in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-sonnet-4-6
```
All 14 AI endpoints will then include an `ai_narrative` field generated by
Claude, layered on top of the static-analysis results. Leave it blank to
run entirely offline.

---

## 4. Frontend setup

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`, so just
run both servers side by side. For production, `npm run build` outputs a
static `dist/` you can serve from any static host or from Django's
`STATIC_ROOT`.

If you deploy the frontend and backend on different origins, set
`VITE_API_BASE_URL` (frontend) and `CORS_ALLOWED_ORIGINS` (backend)
accordingly.

---

## 5. Quick smoke test

1. Start MySQL (or set `USE_SQLITE=True`), then run the backend and frontend as above.
2. Visit `http://localhost:5173`, register an account, log in.
3. Create a project, add a file, paste some code, and try each AI feature
   in the right-hand panel of the workspace.
4. Run "Full AI review" to see it appear under **Review history**.
5. Promote yourself to `role=admin` (see above) to see the **Admin panel**.

---

## 6. Notes on the AI engine's design

This platform intentionally ships a **deterministic, fully-offline AI
engine** as the default (`ai_engine/analyzers.py` + `generators.py`), with
the real Claude API as an optional enrichment layer
(`ai_engine/ai_client.py`). This means:
- The whole platform works with zero external API keys or costs.
- Every AI feature's output is inspectable, reproducible, and testable —
  useful for demos, grading, or offline environments.
- When you do add an API key, responses get richer without any feature
  breaking if the LLM call fails (it silently falls back to the
  static-analysis result).

Python receives the deepest analysis (via the standard library's `ast`
module — real cyclomatic complexity, real bug-pattern detection, real
docstring/test scaffolding). Other languages get regex/heuristic-based
analysis across the same feature set, which is honestly labelled as
best-effort in the generated notes.
