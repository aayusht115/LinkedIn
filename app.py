import os
import json

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from interview_scheduler import schedule_interview
from recruiter_score import get_recruiter_score, get_all_recruiters
from summarizer import summarize_post, calculate_fit_breakdown
from resume_utils import (
    save_resume_file,
    extract_resume_text,
    profile_resume_sync,
    fallback_profile_from_resume,
    quick_bio_from_profile,
)
from database import (
    init_db,
    get_all_interviews, get_interview_by_id,
    get_all_jobs, get_job_by_id, create_job, update_job, update_job_status, get_jobs_by_recruiter,
    save_job, get_saved_jobs, is_job_saved,
    get_candidate_profile, upsert_candidate_profile, save_candidate_resume, update_candidate_sync,
    apply_to_job, get_application, has_applied, get_applications_by_user, get_applications_by_job,
    update_application_status, get_application_by_id, update_application_ai, update_application_notes,
    update_application_offer, update_application_candidate_decision,
    create_interview_round, get_interview_round, get_interview_rounds_by_application, update_interview_round, delete_interview_round,
    delete_interview_round,
)

app = Flask(__name__)

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://127.0.0.1:5000")
CORS(app, origins=[ALLOWED_ORIGIN])

init_db()

def _profile_for_application(application):
    profile = get_candidate_profile(application["user_identifier"]) or {}
    if application.get("profile_snapshot"):
        try:
            profile = json.loads(application["profile_snapshot"]) or profile
        except json.JSONDecodeError:
            pass
    if application.get("resume_text"):
        profile = {
            **profile,
            "resume_text": application["resume_text"],
            "resume_filename": application.get("resume_filename"),
        }
    return profile

# ── UI routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("candidate_ui.html")

@app.route("/candidate")
def candidate():
    return render_template("candidate_ui.html")

@app.route("/recruiter")
def recruiter_ui():
    return render_template("recruiter_ui.html")

@app.route("/recruiter/pipeline")
def recruiter_pipeline():
    return render_template("recruiter_pipeline.html")

@app.route("/profile")
def profile_page():
    return render_template("profile.html")

@app.route("/job/<job_id>")
def job_detail(job_id):
    job = get_job_by_id(job_id)
    if not job:
        return "Job not found", 404
    return render_template("job_detail.html", job=job)

# ── Interviews ─────────────────────────────────────────────────────────────────

@app.route("/schedule", methods=["POST"])
def schedule():
    data = request.json or {}
    missing = [f for f in ("candidate", "recruiter", "time") if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    result = schedule_interview(data)
    if data.get("round_id"):
        if data.get("application_id"):
            update_application_status(data["application_id"], "interview")
        update_interview_round(data["round_id"], {
            "scheduled_time": data["time"],
            "meeting_link": result.get("meeting_link"),
            "interviewer_name": data.get("interviewer_name") or data.get("recruiter"),
            "round_type": data.get("round_type"),
        })
    return jsonify(result), 201

@app.route("/interviews", methods=["GET"])
def list_interviews():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    interviews, total = get_all_interviews(page=page, per_page=per_page)
    return jsonify({
        "interviews": interviews,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": -(-total // per_page),
    })

@app.route("/interviews/<interview_id>", methods=["GET"])
def get_interview(interview_id):
    interview = get_interview_by_id(interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    return jsonify(interview)

# ── Recruiters ─────────────────────────────────────────────────────────────────

@app.route("/recruiters")
def recruiters():
    return jsonify(get_all_recruiters())

@app.route("/recruiter_score/<recruiter_id>")
def recruiter_score(recruiter_id):
    return jsonify(get_recruiter_score(recruiter_id))

# ── Jobs ───────────────────────────────────────────────────────────────────────

@app.route("/jobs", methods=["GET"])
def jobs():
    status = request.args.get("status")   # ?status=active or omit for all
    return jsonify(get_all_jobs(status=status))

@app.route("/jobs/<job_id>", methods=["GET"])
def job_api(job_id):
    job = get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/jobs", methods=["POST"])
def create_job_route():
    data = request.json or {}
    required = ["title", "company", "location", "work_type", "recruiter_id"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    # derive logo from company initials if not provided
    if not data.get("logo"):
        words = data["company"].split()
        data["logo"] = "".join(w[0] for w in words[:2]).upper()

    job = create_job(data)
    return jsonify(job), 201

@app.route("/jobs/<job_id>", methods=["PUT"])
def update_job_route(job_id):
    data = request.json or {}
    required = ["title", "company", "location", "work_type", "recruiter_id"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    job = update_job(job_id, data)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/jobs/<job_id>/status", methods=["PATCH"])
def job_status(job_id):
    data = request.json or {}
    status = data.get("status")
    if status not in ("active", "closed"):
        return jsonify({"error": "status must be 'active' or 'closed'"}), 400
    update_job_status(job_id, status)
    return jsonify({"id": job_id, "status": status})

@app.route("/recruiter/<recruiter_id>/jobs", methods=["GET"])
def recruiter_jobs(recruiter_id):
    return jsonify(get_jobs_by_recruiter(recruiter_id))

# ── Saved Jobs ─────────────────────────────────────────────────────────────────

@app.route("/jobs/<job_id>/save", methods=["POST"])
def toggle_save_job(job_id):
    user = request.json.get("user", "candidate_default") if request.json else "candidate_default"
    saved = save_job(job_id, user)
    return jsonify({"job_id": job_id, "saved": saved})

@app.route("/saved-jobs", methods=["GET"])
def saved_jobs():
    user = request.args.get("user", "candidate_default")
    return jsonify(get_saved_jobs(user))

@app.route("/jobs/<job_id>/saved", methods=["GET"])
def check_saved(job_id):
    user = request.args.get("user", "candidate_default")
    return jsonify({"saved": is_job_saved(job_id, user)})

# ── Candidate Profile ──────────────────────────────────────────────────────────

@app.route("/profile/data", methods=["GET"])
def get_profile():
    user = request.args.get("user", "candidate_default")
    profile = get_candidate_profile(user)
    return jsonify(profile or {})

@app.route("/profile/data", methods=["POST"])
def save_profile():
    data = request.json or {}
    data.setdefault("user_identifier", "candidate_default")
    if data["user_identifier"] == "candidate_default" and not (data.get("name") or "").strip():
        data["name"] = "Aayush Thakur"
    if not (data.get("one_liner") or "").strip():
        data["one_liner"] = (data.get("headline") or "").strip()
    existing = get_candidate_profile(data["user_identifier"]) or {}
    if existing.get("resume_text"):
        sync = profile_resume_sync({**existing, **data}, existing.get("resume_text", ""))
        data["profile_sync_note"] = sync["note"]
        data["profile_sync_status"] = sync["status"]
    profile = upsert_candidate_profile(data)
    return jsonify(profile)

@app.route("/profile/resume", methods=["POST"])
def upload_resume():
    user = request.form.get("user", "candidate_default")
    uploaded = request.files.get("resume")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Missing PDF resume"}), 400
    try:
        path, original_name = save_resume_file(uploaded, user)
        resume_text = extract_resume_text(path)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Could not read the uploaded PDF"}), 400

    existing = get_candidate_profile(user) or {"user_identifier": user}
    inferred = fallback_profile_from_resume(resume_text, existing)
    generated_bio = existing.get("bio") or quick_bio_from_profile({
        **existing,
        "name": inferred.get("name") or existing.get("name"),
        "headline": inferred.get("headline") or existing.get("headline"),
        "location": inferred.get("location") or existing.get("location"),
        "skills": ",".join(inferred.get("skills") or []) or existing.get("skills") or "",
    })
    profile_payload = {
        "user_identifier": user,
        "name": inferred.get("name") or existing.get("name") or ("Aayush Thakur" if user == "candidate_default" else ""),
        "headline": inferred.get("headline") or existing.get("headline") or "",
        "one_liner": inferred.get("one_liner") or existing.get("one_liner") or inferred.get("headline") or "",
        "location": inferred.get("location") or existing.get("location") or "",
        "bio": generated_bio or existing.get("bio") or "",
        "skills": ",".join(inferred.get("skills") or []) or existing.get("skills") or "",
        "experience": json.dumps(inferred.get("experience") or []),
        "education": json.dumps(inferred.get("education") or []),
    }
    sync = profile_resume_sync(profile_payload, resume_text)
    profile_payload["profile_sync_note"] = sync["note"]
    profile_payload["profile_sync_status"] = sync["status"]
    upsert_candidate_profile(profile_payload)
    profile = save_candidate_resume(
        user,
        original_name,
        str(path),
        resume_text,
        sync["note"],
        sync["status"],
    )
    return jsonify({
        "profile": profile,
        "resume_filename": profile.get("resume_filename"),
        "profile_sync_note": profile.get("profile_sync_note"),
        "profile_sync_status": profile.get("profile_sync_status"),
        "resume_text_preview": (profile.get("resume_text") or "")[:500],
        "autofilled": True,
        "used_ai": False,
    }), 201

@app.route("/profile/ai-bio", methods=["POST"])
def generate_profile_bio():
    data = request.json or {}
    user = data.get("user", "candidate_default")
    profile = get_candidate_profile(user) or {"user_identifier": user}
    resume_text = data.get("resume_text") or profile.get("resume_text") or ""
    if not resume_text:
        return jsonify({"error": "Upload a resume first so AI can generate a bio."}), 400
    try:
        from summarizer import generate_resume_bio
        bio = generate_resume_bio(resume_text, profile)
    except Exception:
        bio = (resume_text[:260] + "...") if len(resume_text) > 260 else resume_text
    return jsonify({"bio": bio})

@app.route("/profile/resume", methods=["GET"])
def download_resume():
    user = request.args.get("user", "candidate_default")
    profile = get_candidate_profile(user)
    if not profile or not profile.get("resume_path") or not os.path.exists(profile["resume_path"]):
        return jsonify({"error": "Resume not found"}), 404
    return send_file(
        profile["resume_path"],
        mimetype="application/pdf",
        as_attachment=False,
        download_name=profile.get("resume_filename") or "resume.pdf",
    )

# ── Applications ───────────────────────────────────────────────────────────────

@app.route("/jobs/<job_id>/apply", methods=["POST"])
def apply_job(job_id):
    data = request.json or {}
    user = data.get("user", "candidate_default")
    cover_note = data.get("cover_note", "")
    profile = get_candidate_profile(user) or {}
    application = apply_to_job(
        job_id,
        user,
        cover_note,
        profile_snapshot=json.dumps(profile),
        resume_filename=profile.get("resume_filename"),
        resume_text=profile.get("resume_text"),
    )
    if application is None:
        return jsonify({"error": "Already applied"}), 409
    job = get_job_by_id(job_id)
    if job:
        fit = calculate_fit_breakdown(profile, job)
        application = update_application_ai(application["id"], ai_score=fit["score"]) or application
    return jsonify(application), 201

@app.route("/jobs/<job_id>/applied", methods=["GET"])
def check_applied(job_id):
    user = request.args.get("user", "candidate_default")
    application = get_application(job_id, user)
    return jsonify({"applied": application is not None, "application": application})

@app.route("/applications", methods=["GET"])
def list_applications():
    user = request.args.get("user", "candidate_default")
    return jsonify(get_applications_by_user(user))

@app.route("/jobs/<job_id>/applicants", methods=["GET"])
def job_applicants(job_id):
    return jsonify(get_applications_by_job(job_id))

@app.route("/applications/<application_id>/status", methods=["PATCH"])
def update_app_status(application_id):
    data = request.json or {}
    status = data.get("status")
    valid = ("applied", "screening", "assessment", "interview", "final_round", "offer", "hired", "rejected")
    if status not in valid:
        return jsonify({"error": f"status must be one of: {', '.join(valid)}"}), 400
    app = update_application_status(application_id, status)
    if not app:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(app)

@app.route("/applications/<application_id>/notes", methods=["PATCH"])
def save_app_notes(application_id):
    data = request.json or {}
    notes = (data.get("recruiter_notes") or "").strip()
    app_row = update_application_notes(application_id, notes)
    if not app_row:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(app_row)

@app.route("/applications/<application_id>/offer", methods=["PATCH"])
def update_offer_route(application_id):
    data = request.json or {}
    offer_due_date = (data.get("offer_due_date") or "").strip() or None
    result = update_application_offer(application_id, offer_due_date=offer_due_date)
    if not result:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(result)

@app.route("/applications/<application_id>/candidate-decision", methods=["PATCH"])
def candidate_decision_route(application_id):
    data = request.json or {}
    decision = (data.get("decision") or "").strip().lower()
    if decision not in ("accepted", "declined"):
        return jsonify({"error": "decision must be 'accepted' or 'declined'"}), 400
    result = update_application_candidate_decision(application_id, decision)
    if not result:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(result)

@app.route("/applications/<application_id>/rounds", methods=["GET"])
def application_rounds(application_id):
    application = get_application_by_id(application_id)
    if not application:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(get_interview_rounds_by_application(application_id))

@app.route("/applications/<application_id>/rounds", methods=["POST"])
def create_round_route(application_id):
    application = get_application_by_id(application_id)
    if not application:
        return jsonify({"error": "Application not found"}), 404

    existing_rounds = get_interview_rounds_by_application(application_id)
    if any(not round_row.get("finalized_at") for round_row in existing_rounds):
        return jsonify({"error": "Complete the current round before adding the next one."}), 409

    data = request.json or {}
    round_type = data.get("round_type", "screening_call")
    valid_types = {"screening_call", "technical_round", "manager_round", "final_panel", "culture_round", "hr_round"}
    if round_type not in valid_types:
        return jsonify({"error": f"round_type must be one of: {', '.join(sorted(valid_types))}"}), 400

    from summarizer import round_objective_for
    round_row = create_interview_round(
        application_id=application_id,
        round_type=round_type,
        interviewer_name=(data.get("interviewer_name") or "").strip() or None,
        scheduled_time=data.get("scheduled_time"),
        notes=data.get("notes"),
        feedback=data.get("feedback"),
        decision=data.get("decision"),
        objective=(data.get("objective") or round_objective_for(round_type)),
    )
    return jsonify(round_row), 201

@app.route("/interview-rounds/<round_id>", methods=["PATCH"])
def update_round_route(round_id):
    round_row = get_interview_round(round_id)
    if not round_row:
        return jsonify({"error": "Interview round not found"}), 404
    if round_row.get("finalized_at"):
        return jsonify({"error": "This round is already saved and locked."}), 409

    data = request.json or {}
    if "round_type" in data:
        valid_types = {"screening_call", "technical_round", "manager_round", "final_panel", "culture_round", "hr_round"}
        if data["round_type"] not in valid_types:
            return jsonify({"error": f"round_type must be one of: {', '.join(sorted(valid_types))}"}), 400
        if "objective" not in data:
            from summarizer import round_objective_for
            data["objective"] = round_objective_for(data["round_type"])
    if "round_number" in data:
        try:
            data["round_number"] = int(data["round_number"])
        except (TypeError, ValueError):
            return jsonify({"error": "round_number must be an integer"}), 400
        if data["round_number"] < 1:
            return jsonify({"error": "round_number must be at least 1"}), 400

    rejection_reason = (data.pop("rejection_reason", None) or "").strip() or None
    decision = (data.get("decision") or "").strip().lower()
    if decision:
        from datetime import datetime, timezone
        data["finalized_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    updated = update_interview_round(round_id, data)
    if updated and decision:
        if decision == "reject":
            update_application_offer(updated["application_id"], rejection_reason=rejection_reason, status="rejected")
        elif decision == "more_round_required":
            update_application_status(updated["application_id"], "final_round")
        elif decision == "advance":
            update_application_status(updated["application_id"], "offer")
    return jsonify(updated)

@app.route("/interview-rounds/<round_id>", methods=["DELETE"])
def delete_round_route(round_id):
    round_row = get_interview_round(round_id)
    if not round_row:
        return jsonify({"error": "Interview round not found"}), 404
    if round_row.get("finalized_at") or round_row.get("meeting_link"):
        return jsonify({"error": "Cannot remove a round that has been scheduled or finalized."}), 409
    delete_interview_round(round_id)
    return jsonify({"ok": True})

@app.route("/interview-rounds/<round_id>/brief-pack", methods=["POST"])
def generate_round_brief_route(round_id):
    round_row = get_interview_round(round_id)
    if not round_row:
        return jsonify({"error": "Interview round not found"}), 404

    application = get_application_by_id(round_row["application_id"])
    if not application:
        return jsonify({"error": "Application not found"}), 404
    job = get_job_by_id(application["job_id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404

    profile = _profile_for_application(application)
    from summarizer import generate_round_brief_pack
    pack = generate_round_brief_pack(profile, job, application, round_row)
    updated = update_interview_round(round_id, {
        "objective": pack.get("round_objective") or round_row.get("objective"),
        "brief_pack": pack,
    })
    return jsonify({"round": updated, "brief_pack": pack})

@app.route("/interview-rounds/<round_id>/questions", methods=["POST"])
def generate_round_questions_route(round_id):
    round_row = get_interview_round(round_id)
    if not round_row:
        return jsonify({"error": "Interview round not found"}), 404

    application = get_application_by_id(round_row["application_id"])
    if not application:
        return jsonify({"error": "Application not found"}), 404
    job = get_job_by_id(application["job_id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404

    profile = _profile_for_application(application)
    from summarizer import generate_candidate_interview_questions
    questions = generate_candidate_interview_questions(profile, job, application, round_row)
    updated = update_interview_round(round_id, {"question_pack": questions})
    return jsonify({"round": updated, "questions": questions})

@app.route("/interview-rounds/<round_id>/ai-pack", methods=["POST"])
def generate_round_ai_pack_route(round_id):
    round_row = get_interview_round(round_id)
    if not round_row:
        return jsonify({"error": "Interview round not found"}), 404

    application = get_application_by_id(round_row["application_id"])
    if not application:
        return jsonify({"error": "Application not found"}), 404
    job = get_job_by_id(application["job_id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404

    profile = _profile_for_application(application)
    all_rounds = get_interview_rounds_by_application(round_row["application_id"])
    prev_feedback = None
    for r in sorted(all_rounds, key=lambda x: x.get("round_number") or 0):
        if r["id"] != round_id and r.get("finalized_at") and r.get("feedback"):
            prev_feedback = r["feedback"]
    from summarizer import generate_round_brief_pack, generate_candidate_interview_questions
    brief_pack = generate_round_brief_pack(profile, job, application, round_row)
    questions = generate_candidate_interview_questions(profile, job, application, round_row, previous_feedback=prev_feedback)
    updated = update_interview_round(round_id, {
        "objective": brief_pack.get("round_objective") or round_row.get("objective"),
        "brief_pack": brief_pack,
        "question_pack": questions,
    })
    return jsonify({"round": updated, "brief_pack": brief_pack, "questions": questions})

# ── AI ─────────────────────────────────────────────────────────────────────────

@app.route("/analyze-fit", methods=["POST"])
def analyze_fit_route():
    data = request.json or {}
    user = data.get("user", "candidate_default")
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400
    profile = get_candidate_profile(user) or {}
    overrides = data.get("profile_overrides") or {}
    if isinstance(overrides, dict):
        profile = {**profile, **overrides}
    job = get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    from summarizer import analyze_fit
    result = analyze_fit(profile, job)
    return jsonify(result)

@app.route("/applications/<application_id>/analysis", methods=["POST"])
def application_analysis(application_id):
    application = get_application_by_id(application_id)
    if not application:
        return jsonify({"error": "Application not found"}), 404
    profile = _profile_for_application(application)
    job = get_job_by_id(application["job_id"])
    if not job:
        return jsonify({"error": "Job not found"}), 404

    from summarizer import analyze_fit, generate_screening_note
    fit = analyze_fit(profile, job)
    screening = generate_screening_note(profile, job, application)
    updated = update_application_ai(
        application_id,
        ai_score=fit["score"],
        ai_analysis=fit["analysis"],
        screening_note=screening["note"],
    )
    return jsonify({
        "application": updated or application,
        "fit": fit,
        "screening_note": screening["note"],
    })

@app.route("/jobs/<job_id>/interview-questions", methods=["POST"])
def gen_interview_questions(job_id):
    job = get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    from summarizer import generate_interview_questions
    questions = generate_interview_questions(job)
    return jsonify({"questions": questions})

# ── Summarize ──────────────────────────────────────────────────────────────────

@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Missing required field: text"}), 400
    summary = summarize_post(text)
    return jsonify({"summary": summary})

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug)
