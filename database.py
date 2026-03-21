import json
import sqlite3
import os
import uuid

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interviews.db")

# ── Seed data (no CSVs) ───────────────────────────────────────────────────────

RECRUITERS_SEED = [
    ("rec_shopify_001",  "Alex Kim",      "Shopify",      2,  0.70, 4.5, 1, 90.0),
    ("rec_stripe_002",   "Jordan Lee",    "Stripe",       5,  0.50, 4.0, 2, 75.0),
    ("rec_deepmind_003", "Sam Patel",     "DeepMind",    10,  0.30, 3.5, 4, 55.0),
    ("rec_meta_004",     "Priya Sharma",  "Meta",         3,  0.60, 4.2, 1, 85.0),
    ("rec_google_005",   "Chris Wang",    "Google",       6,  0.40, 3.8, 3, 65.0),
    ("rec_amazon_006",   "Maya Roberts",  "Amazon",       1,  0.80, 4.8, 0, 97.0),
    ("rec_netflix_007",  "Liam Foster",   "Netflix",      8,  0.35, 3.6, 4, 58.0),
    ("rec_apple_008",    "Nina Chen",     "Apple",        4,  0.65, 4.3, 1, 88.0),
    ("rec_uber_009",     "Tom Garcia",    "Uber",         7,  0.45, 3.9, 2, 70.0),
    ("rec_airbnb_010",   "Sara Mitchell", "Airbnb",       3,  0.72, 4.6, 1, 92.0),
    ("rec_openai_011",   "Aiden Park",    "OpenAI",       2,  0.75, 4.7, 0, 95.0),
    ("rec_msft_012",     "Rachel Brown",  "Microsoft",    9,  0.38, 3.7, 3, 60.0),
    ("rec_salesforce_013","David Kim",    "Salesforce",   5,  0.55, 4.1, 2, 78.0),
    ("rec_adobe_014",    "Emma Wilson",   "Adobe",        6,  0.42, 3.9, 3, 66.0),
    ("rec_twilio_015",   "James Taylor",  "Twilio",       4,  0.60, 4.2, 1, 83.0),
]

JOBS_SEED = [
    {
        "id": "job_shopify_001",
        "title": "Senior Frontend Engineer",
        "company": "Shopify",
        "location": "London, UK",
        "work_type": "Remote",
        "job_type": "Full-time",
        "experience_level": "Mid-Senior level",
        "industry": "E-Commerce / Technology",
        "salary_min": 90000,
        "salary_max": 130000,
        "salary_currency": "GBP",
        "salary_period": "year",
        "openings": 2,
        "applicants": 47,
        "recruiter_id": "rec_shopify_001",
        "logo": "SH",
        "skills": "React,TypeScript,Node.js,GraphQL,CSS,Git",
        "requirements": "3+ years React, TypeScript, Node.js, REST APIs, CI/CD, Agile",
        "about_role": "Join Shopify's frontend platform team to build the tools that power millions of merchants worldwide. You'll work on high-traffic React applications, contribute to our design system, and collaborate with product and design to ship features used by merchants globally.",
        "responsibilities": "Build and maintain core merchant dashboard UI components\nLead performance optimisation of our React codebase\nContribute to and evolve our internal design system\nMentor junior engineers and conduct code reviews\nCollaborate cross-functionally with backend, design, and PM teams",
        "qualifications": "3+ years of professional experience with React and TypeScript\nStrong understanding of web performance and accessibility\nExperience with CI/CD pipelines and Git workflows\nComfort working in a remote-first, async environment",
        "nice_to_have": "Experience with GraphQL or REST API design\nFamiliarity with Shopify's platform or e-commerce domain\nContributions to open-source projects",
        "deadline": "2026-05-01",
        "status": "active",
        "posted_at": "2026-03-18 10:00:00",
    },
    {
        "id": "job_stripe_002",
        "title": "React Developer",
        "company": "Stripe",
        "location": "Dublin, Ireland",
        "work_type": "Hybrid",
        "job_type": "Full-time",
        "experience_level": "Associate",
        "industry": "FinTech / Payments",
        "salary_min": 70000,
        "salary_max": 100000,
        "salary_currency": "EUR",
        "salary_period": "year",
        "openings": 1,
        "applicants": 112,
        "recruiter_id": "rec_stripe_002",
        "logo": "ST",
        "skills": "React,JavaScript,TypeScript,Jest,REST APIs,Figma",
        "requirements": "React, JavaScript, payment systems, 2+ years experience, testing, documentation",
        "about_role": "Stripe's developer products are used by millions of businesses to accept payments online. As a React Developer on our Dashboard team, you'll build the interfaces that help businesses understand their revenue, manage disputes, and configure their Stripe integrations.",
        "responsibilities": "Build and ship UI features for the Stripe Dashboard\nWrite comprehensive unit and integration tests\nContribute to our shared component library\nCollaborate with designers to ensure pixel-perfect implementation\nDocument components and patterns for internal use",
        "qualifications": "2+ years of professional React/JavaScript experience\nFamiliarity with testing frameworks (Jest, React Testing Library)\nAttention to detail and strong design sensibility\nClear written communication skills",
        "nice_to_have": "Experience with payment flows or financial products\nKnowledge of TypeScript\nFigma proficiency",
        "deadline": "2026-04-15",
        "status": "active",
        "posted_at": "2026-03-17 14:00:00",
    },
    {
        "id": "job_deepmind_003",
        "title": "UI Engineer",
        "company": "DeepMind",
        "location": "London, UK",
        "work_type": "On-site",
        "job_type": "Full-time",
        "experience_level": "Mid-Senior level",
        "industry": "Artificial Intelligence / Research",
        "salary_min": 100000,
        "salary_max": 150000,
        "salary_currency": "GBP",
        "salary_period": "year",
        "openings": 1,
        "applicants": 203,
        "recruiter_id": "rec_deepmind_003",
        "logo": "DM",
        "skills": "React,Python,D3.js,Data Visualisation,TypeScript,ML basics",
        "requirements": "React, Python, data visualisation, ML knowledge, 4+ years experience, strong communication",
        "about_role": "DeepMind is looking for a UI Engineer to build research tooling and internal interfaces that help our scientists understand and interpret AI models. This role sits at the intersection of software engineering and research, working directly with researchers to build bespoke visualisation tools.",
        "responsibilities": "Design and build data visualisation dashboards for model evaluation\nBuild research tooling used by ML scientists daily\nDevelop frontend for internal experiment tracking systems\nTranslate complex research requirements into clean, intuitive UIs\nWork closely with ML researchers and infrastructure teams",
        "qualifications": "4+ years experience in frontend/UI engineering\nStrong React skills with experience in data visualisation (D3.js or similar)\nComfort reading or writing Python scripts\nAbility to communicate with non-technical researchers",
        "nice_to_have": "Academic or industry background in ML/AI\nExperience with Jupyter notebooks or research tooling\nKnowledge of WebGL or Canvas-based rendering",
        "deadline": "2026-04-30",
        "status": "active",
        "posted_at": "2026-03-19 09:00:00",
    },
]

# ── Connection ────────────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ── Schema + seeding ──────────────────────────────────────────────────────────

def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id TEXT PRIMARY KEY,
            candidate TEXT NOT NULL,
            recruiter TEXT NOT NULL,
            time TEXT NOT NULL,
            meeting_link TEXT NOT NULL,
            job_id TEXT,
            application_id TEXT,
            round_id TEXT,
            round_type TEXT,
            interviewer_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('candidate', 'recruiter')),
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS recruiters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            response_time INTEGER NOT NULL,
            hire_rate REAL NOT NULL,
            rating REAL NOT NULL,
            cancellations INTEGER NOT NULL,
            score REAL NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            work_type TEXT NOT NULL,
            job_type TEXT DEFAULT 'Full-time',
            experience_level TEXT DEFAULT 'Mid-Senior level',
            industry TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            salary_currency TEXT DEFAULT 'USD',
            salary_period TEXT DEFAULT 'year',
            openings INTEGER DEFAULT 1,
            applicants INTEGER DEFAULT 0,
            recruiter_id TEXT,
            logo TEXT,
            skills TEXT,
            requirements TEXT,
            about_role TEXT,
            responsibilities TEXT,
            qualifications TEXT,
            nice_to_have TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'active',
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recruiter_id) REFERENCES recruiters(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_jobs (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            user_identifier TEXT NOT NULL DEFAULT 'candidate_default',
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, user_identifier),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS candidate_profiles (
            user_identifier TEXT PRIMARY KEY,
            name TEXT,
            headline TEXT,
            one_liner TEXT,
            location TEXT,
            bio TEXT,
            skills TEXT,
            experience TEXT,
            education TEXT,
            resume_filename TEXT,
            resume_path TEXT,
            resume_text TEXT,
            profile_sync_note TEXT,
            profile_sync_status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            user_identifier TEXT NOT NULL DEFAULT 'candidate_default',
            status TEXT DEFAULT 'applied' CHECK(status IN ('applied','screening','assessment','interview','final_round','offer','hired','rejected')),
            cover_note TEXT,
            ai_score REAL,
            ai_analysis TEXT,
            recruiter_notes TEXT,
            screening_note TEXT,
            profile_snapshot TEXT,
            resume_filename TEXT,
            resume_text TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, user_identifier),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS interview_rounds (
            id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            round_type TEXT NOT NULL,
            interviewer_name TEXT,
            scheduled_time TEXT,
            meeting_link TEXT,
            notes TEXT,
            feedback TEXT,
            decision TEXT,
            objective TEXT,
            brief_pack TEXT,
            question_pack TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(application_id, round_number),
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
        )
    """)

    _ensure_column(conn, "interviews", "application_id", "TEXT")
    _ensure_column(conn, "interviews", "round_id", "TEXT")
    _ensure_column(conn, "interviews", "round_type", "TEXT")
    _ensure_column(conn, "interviews", "interviewer_name", "TEXT")
    _ensure_column(conn, "applications", "ai_analysis", "TEXT")
    _ensure_column(conn, "applications", "recruiter_notes", "TEXT")
    _ensure_column(conn, "applications", "screening_note", "TEXT")
    _ensure_column(conn, "applications", "profile_snapshot", "TEXT")
    _ensure_column(conn, "applications", "resume_filename", "TEXT")
    _ensure_column(conn, "applications", "resume_text", "TEXT")
    _ensure_column(conn, "interview_rounds", "meeting_link", "TEXT")
    _ensure_column(conn, "interview_rounds", "objective", "TEXT")
    _ensure_column(conn, "interview_rounds", "brief_pack", "TEXT")
    _ensure_column(conn, "interview_rounds", "question_pack", "TEXT")
    _ensure_column(conn, "candidate_profiles", "resume_filename", "TEXT")
    _ensure_column(conn, "candidate_profiles", "resume_path", "TEXT")
    _ensure_column(conn, "candidate_profiles", "resume_text", "TEXT")
    _ensure_column(conn, "candidate_profiles", "one_liner", "TEXT")
    _ensure_column(conn, "candidate_profiles", "profile_sync_note", "TEXT")
    _ensure_column(conn, "candidate_profiles", "profile_sync_status", "TEXT")
    _ensure_column(conn, "applications", "rejection_reason", "TEXT")
    _ensure_column(conn, "applications", "offer_due_date", "TEXT")
    _ensure_column(conn, "applications", "candidate_decision", "TEXT")

    conn.commit()
    _seed_recruiters(conn)
    _seed_jobs(conn)
    conn.close()

def _ensure_column(conn, table_name, column_name, column_type):
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in cols:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

def _seed_recruiters(conn):
    if conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0] > 0:
        return
    conn.executemany("""
        INSERT OR IGNORE INTO recruiters
          (id, name, company, response_time, hire_rate, rating, cancellations, score)
        VALUES (?,?,?,?,?,?,?,?)
    """, RECRUITERS_SEED)
    conn.commit()

def _seed_jobs(conn):
    if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] > 0:
        return
    for job in JOBS_SEED:
        conn.execute("""
            INSERT OR IGNORE INTO jobs
              (id,title,company,location,work_type,job_type,experience_level,industry,
               salary_min,salary_max,salary_currency,salary_period,openings,applicants,
               recruiter_id,logo,skills,requirements,about_role,responsibilities,
               qualifications,nice_to_have,deadline,status,posted_at)
            VALUES
              (:id,:title,:company,:location,:work_type,:job_type,:experience_level,:industry,
               :salary_min,:salary_max,:salary_currency,:salary_period,:openings,:applicants,
               :recruiter_id,:logo,:skills,:requirements,:about_role,:responsibilities,
               :qualifications,:nice_to_have,:deadline,:status,:posted_at)
        """, job)
    conn.commit()

# ── Interviews ────────────────────────────────────────────────────────────────

def save_interview(interview):
    conn = get_connection()
    conn.execute("""
        INSERT INTO interviews (
            id, candidate, recruiter, time, meeting_link, job_id,
            application_id, round_id, round_type, interviewer_name
        )
        VALUES (
            :id, :candidate, :recruiter, :time, :meeting_link, :job_id,
            :application_id, :round_id, :round_type, :interviewer_name
        )
    """, interview)
    conn.commit()
    conn.close()

def get_all_interviews(page=1, per_page=20):
    offset = (page - 1) * per_page
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM interviews").fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM interviews ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows], total

def get_interview_by_id(interview_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_interview_round(round_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM interview_rounds WHERE id = ?",
        (round_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_interview_rounds_by_application(application_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT *
        FROM interview_rounds
        WHERE application_id = ?
        ORDER BY round_number ASC, created_at ASC
    """, (application_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_interview_round(application_id, round_type, interviewer_name=None, scheduled_time=None,
                           notes=None, feedback=None, decision=None, objective=None,
                           brief_pack=None, question_pack=None, round_number=None):
    conn = get_connection()
    if round_number is None:
        row = conn.execute(
            "SELECT COALESCE(MAX(round_number), 0) + 1 FROM interview_rounds WHERE application_id = ?",
            (application_id,)
        ).fetchone()
        round_number = row[0]
    round_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO interview_rounds (
            id, application_id, round_number, round_type, interviewer_name,
            scheduled_time, notes, feedback, decision, objective, brief_pack, question_pack
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        round_id,
        application_id,
        round_number,
        round_type,
        interviewer_name,
        scheduled_time,
        notes,
        feedback,
        decision,
        objective,
        json.dumps(brief_pack) if isinstance(brief_pack, (dict, list)) else brief_pack,
        json.dumps(question_pack) if isinstance(question_pack, (dict, list)) else question_pack,
    ))
    conn.commit()
    conn.close()
    return get_interview_round(round_id)

def update_interview_round(round_id, data):
    allowed = {
        "round_number",
        "round_type",
        "interviewer_name",
        "scheduled_time",
        "meeting_link",
        "notes",
        "feedback",
        "decision",
        "objective",
        "brief_pack",
        "question_pack",
    }
    updates = []
    values = []
    for key, value in data.items():
        if key not in allowed:
            continue
        if key in {"brief_pack", "question_pack"} and isinstance(value, (dict, list)):
            value = json.dumps(value)
        updates.append(f"{key} = ?")
        values.append(value)
    if not updates:
        return get_interview_round(round_id)

    conn = get_connection()
    conn.execute(
        f"UPDATE interview_rounds SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*values, round_id),
    )
    conn.commit()
    conn.close()
    return get_interview_round(round_id)

# ── Recruiters ────────────────────────────────────────────────────────────────

def get_all_recruiters_db():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM recruiters ORDER BY score DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_recruiter_by_id_db(recruiter_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM recruiters WHERE id = ?", (recruiter_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ── Jobs ──────────────────────────────────────────────────────────────────────

def get_all_jobs(status=None):
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT j.*, r.name as recruiter_name FROM jobs j LEFT JOIN recruiters r ON j.recruiter_id=r.id WHERE j.status=? ORDER BY j.posted_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT j.*, r.name as recruiter_name FROM jobs j LEFT JOIN recruiters r ON j.recruiter_id=r.id ORDER BY j.posted_at DESC"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_job_by_id(job_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT j.*, r.name as recruiter_name, r.company as recruiter_company,
               r.response_time, r.hire_rate, r.rating, r.cancellations
        FROM jobs j
        LEFT JOIN recruiters r ON j.recruiter_id = r.id
        WHERE j.id = ?
    """, (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_job(data):
    job_id = "job_" + str(uuid.uuid4()).replace("-", "")[:12]
    conn = get_connection()
    conn.execute("""
        INSERT INTO jobs
          (id,title,company,location,work_type,job_type,experience_level,industry,
           salary_min,salary_max,salary_currency,salary_period,openings,
           recruiter_id,logo,skills,requirements,about_role,responsibilities,
           qualifications,nice_to_have,deadline,status)
        VALUES
          (:id,:title,:company,:location,:work_type,:job_type,:experience_level,:industry,
           :salary_min,:salary_max,:salary_currency,:salary_period,:openings,
           :recruiter_id,:logo,:skills,:requirements,:about_role,:responsibilities,
           :qualifications,:nice_to_have,:deadline,'active')
    """, {**data, "id": job_id})
    conn.commit()
    conn.close()
    return get_job_by_id(job_id)

def update_job(job_id, data):
    defaults = {
        "job_type": "Full-time", "experience_level": "Mid-Senior level",
        "industry": None, "salary_min": None, "salary_max": None,
        "salary_currency": "USD", "salary_period": "year", "openings": 1,
        "skills": None, "requirements": None, "about_role": None,
        "responsibilities": None, "qualifications": None,
        "nice_to_have": None, "deadline": None,
    }
    row = {**defaults, **data, "id": job_id}
    conn = get_connection()
    conn.execute("""
        UPDATE jobs SET
          title=:title, company=:company, location=:location, work_type=:work_type,
          job_type=:job_type, experience_level=:experience_level, industry=:industry,
          salary_min=:salary_min, salary_max=:salary_max, salary_currency=:salary_currency,
          salary_period=:salary_period, openings=:openings, recruiter_id=:recruiter_id,
          skills=:skills, requirements=:requirements, about_role=:about_role,
          responsibilities=:responsibilities, qualifications=:qualifications,
          nice_to_have=:nice_to_have, deadline=:deadline
        WHERE id=:id
    """, row)
    conn.commit()
    conn.close()
    return get_job_by_id(job_id)

def update_job_status(job_id, status):
    conn = get_connection()
    conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()

def get_jobs_by_recruiter(recruiter_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE recruiter_id=? ORDER BY posted_at DESC",
        (recruiter_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ── Saved Jobs ────────────────────────────────────────────────────────────────

def save_job(job_id, user_identifier="candidate_default"):
    conn = get_connection()
    try:
        save_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO saved_jobs (id, job_id, user_identifier) VALUES (?,?,?)",
            (save_id, job_id, user_identifier)
        )
        conn.commit()
        saved = True
    except sqlite3.IntegrityError:
        # already saved — unsave it
        conn.execute(
            "DELETE FROM saved_jobs WHERE job_id=? AND user_identifier=?",
            (job_id, user_identifier)
        )
        conn.commit()
        saved = False
    conn.close()
    return saved

def get_saved_jobs(user_identifier="candidate_default"):
    conn = get_connection()
    rows = conn.execute("""
        SELECT j.*, r.name as recruiter_name, sj.saved_at
        FROM saved_jobs sj
        JOIN jobs j ON sj.job_id = j.id
        LEFT JOIN recruiters r ON j.recruiter_id = r.id
        WHERE sj.user_identifier = ?
        ORDER BY sj.saved_at DESC
    """, (user_identifier,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def is_job_saved(job_id, user_identifier="candidate_default"):
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM saved_jobs WHERE job_id=? AND user_identifier=?",
        (job_id, user_identifier)
    ).fetchone()
    conn.close()
    return row is not None

# ── Candidate Profiles ────────────────────────────────────────────────────────

def get_candidate_profile(user_identifier="candidate_default"):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM candidate_profiles WHERE user_identifier = ?",
        (user_identifier,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def upsert_candidate_profile(data):
    user = data.get("user_identifier", "candidate_default")
    conn = get_connection()
    conn.execute("""
        INSERT INTO candidate_profiles
          (user_identifier, name, headline, one_liner, location, bio, skills, experience, education, profile_sync_note, profile_sync_status, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(user_identifier) DO UPDATE SET
          name=excluded.name,
          headline=excluded.headline,
          one_liner=excluded.one_liner,
          location=excluded.location,
          bio=excluded.bio,
          skills=excluded.skills,
          experience=excluded.experience,
          education=excluded.education,
          profile_sync_note=COALESCE(excluded.profile_sync_note, candidate_profiles.profile_sync_note),
          profile_sync_status=COALESCE(excluded.profile_sync_status, candidate_profiles.profile_sync_status),
          updated_at=CURRENT_TIMESTAMP
    """, (user, data.get("name"), data.get("headline"), data.get("one_liner"), data.get("location"),
          data.get("bio"), data.get("skills"), data.get("experience"), data.get("education"),
          data.get("profile_sync_note"), data.get("profile_sync_status")))
    conn.commit()
    conn.close()
    return get_candidate_profile(user)

def save_candidate_resume(user_identifier, resume_filename, resume_path, resume_text, profile_sync_note=None, profile_sync_status=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO candidate_profiles
          (user_identifier, resume_filename, resume_path, resume_text, profile_sync_note, profile_sync_status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_identifier) DO UPDATE SET
          resume_filename=excluded.resume_filename,
          resume_path=excluded.resume_path,
          resume_text=excluded.resume_text,
          profile_sync_note=COALESCE(excluded.profile_sync_note, candidate_profiles.profile_sync_note),
          profile_sync_status=COALESCE(excluded.profile_sync_status, candidate_profiles.profile_sync_status),
          updated_at=CURRENT_TIMESTAMP
    """, (user_identifier, resume_filename, resume_path, resume_text, profile_sync_note, profile_sync_status))
    conn.commit()
    conn.close()
    return get_candidate_profile(user_identifier)

def update_candidate_sync(user_identifier, profile_sync_note, profile_sync_status):
    conn = get_connection()
    conn.execute("""
        UPDATE candidate_profiles
        SET profile_sync_note = ?, profile_sync_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_identifier = ?
    """, (profile_sync_note, profile_sync_status, user_identifier))
    conn.commit()
    conn.close()
    return get_candidate_profile(user_identifier)

# ── Applications ──────────────────────────────────────────────────────────────

def apply_to_job(job_id, user_identifier="candidate_default", cover_note=None, profile_snapshot=None, resume_filename=None, resume_text=None):
    conn = get_connection()
    app_id = str(uuid.uuid4())
    try:
        conn.execute(
            """
            INSERT INTO applications (id, job_id, user_identifier, cover_note, profile_snapshot, resume_filename, resume_text)
            VALUES (?,?,?,?,?,?,?)
            """,
            (app_id, job_id, user_identifier, cover_note, profile_snapshot, resume_filename, resume_text)
        )
        # increment applicant count
        conn.execute("UPDATE jobs SET applicants = applicants + 1 WHERE id = ?", (job_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return None  # already applied
    conn.close()
    return get_application(job_id, user_identifier)

def get_application(job_id, user_identifier="candidate_default"):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM applications WHERE job_id=? AND user_identifier=?",
        (job_id, user_identifier)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def has_applied(job_id, user_identifier="candidate_default"):
    return get_application(job_id, user_identifier) is not None

def get_application_by_id(application_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM applications WHERE id=?",
        (application_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_applications_by_user(user_identifier="candidate_default"):
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.id, a.job_id, a.user_identifier, a.status, a.cover_note, a.ai_score,
               a.ai_analysis, a.recruiter_notes, a.screening_note, a.resume_filename,
               a.rejection_reason, a.offer_due_date, a.candidate_decision,
               a.applied_at, a.updated_at,
               j.title, j.company, j.logo, j.work_type, j.location, j.status as job_status,
               r.name as recruiter_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN recruiters r ON j.recruiter_id = r.id
        WHERE a.user_identifier = ?
        ORDER BY a.applied_at DESC
    """, (user_identifier,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_applications_by_job(job_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.id, a.job_id, a.user_identifier, a.status, a.cover_note, a.ai_score,
               a.ai_analysis, a.recruiter_notes, a.screening_note, a.resume_filename,
               a.rejection_reason, a.offer_due_date, a.candidate_decision,
               a.applied_at, a.updated_at,
               cp.name as candidate_name, cp.headline, cp.one_liner, cp.location as candidate_location,
               cp.skills as candidate_skills, cp.experience as candidate_experience,
               cp.bio as candidate_bio
        FROM applications a
        LEFT JOIN candidate_profiles cp ON a.user_identifier = cp.user_identifier
        WHERE a.job_id = ?
        ORDER BY a.applied_at DESC
    """, (job_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_application_status(application_id, status):
    conn = get_connection()
    conn.execute(
        "UPDATE applications SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, application_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_application_ai(application_id, ai_score=None, ai_analysis=None, screening_note=None):
    conn = get_connection()
    conn.execute("""
        UPDATE applications
        SET ai_score = COALESCE(?, ai_score),
            ai_analysis = COALESCE(?, ai_analysis),
            screening_note = COALESCE(?, screening_note),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (ai_score, ai_analysis, screening_note, application_id))
    conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_application_notes(application_id, recruiter_notes):
    conn = get_connection()
    conn.execute("""
        UPDATE applications
        SET recruiter_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (recruiter_notes, application_id))
    conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_application_offer(application_id, offer_due_date=None, rejection_reason=None, status=None):
    """Set offer due date, rejection reason, or status on an application."""
    conn = get_connection()
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    values = []
    if offer_due_date is not None:
        updates.append("offer_due_date = ?")
        values.append(offer_due_date)
    if rejection_reason is not None:
        updates.append("rejection_reason = ?")
        values.append(rejection_reason)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if values:
        conn.execute(
            f"UPDATE applications SET {', '.join(updates)} WHERE id = ?",
            (*values, application_id),
        )
        conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_application_candidate_decision(application_id, decision):
    """Record candidate's accept/decline on an offer and update status."""
    new_status = "hired" if decision == "accepted" else "rejected"
    conn = get_connection()
    conn.execute("""
        UPDATE applications
        SET candidate_decision = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (decision, new_status, application_id))
    conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
