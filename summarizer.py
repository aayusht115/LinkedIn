import json
import re

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from resume_utils import fallback_profile_from_resume

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

_tokenizer = None
_model = None

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "our", "are", "have", "has", "will", "their", "role", "team", "work", "years",
    "year", "experience", "strong", "plus", "good", "nice", "must", "ability",
    "about", "using", "used", "build", "building", "candidate", "skills", "skill",
}

ROUND_OBJECTIVES = {
    "screening_call": "Validate interest, communication quality, and obvious role-fit risks before deeper evaluation.",
    "technical_round": "Probe technical depth, execution quality, and stack familiarity using concrete examples.",
    "manager_round": "Assess ownership, stakeholder management, prioritisation, and delivery maturity.",
    "final_panel": "Stress-test readiness, judgment, cross-functional fit, and long-term upside.",
    "culture_round": "Explore values, collaboration style, resilience, and behavioural fit.",
    "hr_round": "Clarify motivation, logistics, compensation expectations, and closing concerns.",
}

def _load_model():
    global _tokenizer, _model
    if _tokenizer is None:
        try:
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            _model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float32)
        except Exception as e:
            print(f"[summarizer] Could not load model ({e}). AI features will use fallback text.")
            _tokenizer = False  # sentinel: attempted but failed
            _model = None

def _parse_json_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []

def _extract_json_object(text):
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None

def _tokenize(text):
    return [
        token for token in re.split(r"[\s,;:+/|()\-–—]+", (text or "").lower())
        if len(token) > 2 and token not in STOP_WORDS
    ]

def _extract_years(text):
    match = re.search(r"(\d+)\+?\s*year", (text or "").lower())
    return int(match.group(1)) if match else None

def _location_signal(profile_location, job_location, work_type):
    if work_type and work_type.lower() == "remote":
        return {"label": "Location", "status": "positive", "detail": "Remote role reduces location constraints."}
    profile_tokens = set(_tokenize(profile_location))
    job_tokens = set(_tokenize(job_location))
    overlap = profile_tokens.intersection(job_tokens)
    if overlap:
        return {"label": "Location", "status": "positive", "detail": f"Location overlap found: {', '.join(sorted(overlap)[:2])}."}
    if profile_location and job_location:
        return {"label": "Location", "status": "gap", "detail": f"Profile location ({profile_location}) differs from job location ({job_location})."}
    return {"label": "Location", "status": "unknown", "detail": "Location information is incomplete."}

def _profile_strings(profile):
    experience_entries = _parse_json_list(profile.get("experience"))
    education_entries = _parse_json_list(profile.get("education"))
    resume_text = profile.get("resume_text", "") or ""
    experience_text = " ".join(
        " ".join(filter(None, [
            item.get("title", ""),
            item.get("company", ""),
            item.get("location", ""),
            item.get("duration", ""),
            item.get("desc", ""),
        ]))
        for item in experience_entries
    )
    education_text = " ".join(
        " ".join(filter(None, [
            item.get("school", ""),
            item.get("degree", ""),
            item.get("years", ""),
        ]))
        for item in education_entries
    )
    profile_text = " ".join(filter(None, [
        profile.get("headline", ""),
        profile.get("bio", ""),
        profile.get("skills", ""),
        profile.get("location", ""),
        experience_text,
        education_text,
        resume_text,
    ]))
    return experience_entries, education_entries, profile_text, experience_text, education_text, resume_text

def round_objective_for(round_type):
    return ROUND_OBJECTIVES.get(round_type or "", "Assess this round's most important competencies and capture a clear go/no-go signal.")

def _experience_summary(profile, limit=3):
    entries = _parse_json_list(profile.get("experience"))
    lines = []
    for item in entries[:limit]:
        parts = [item.get("title"), f"at {item.get('company')}" if item.get("company") else ""]
        if item.get("duration"):
            parts.append(f"({item.get('duration')})")
        line = " ".join(part for part in parts if part).strip()
        if line:
            lines.append(line)
    return lines

def _resume_highlights(profile, limit=4):
    highlights = []
    for item in _parse_json_list(profile.get("experience"))[:3]:
        line = " - ".join(part for part in [item.get("title"), item.get("company"), item.get("location")] if part)
        if line:
            highlights.append(line)
        desc = (item.get("desc") or "").strip()
        if desc:
            highlights.append(desc.split(".")[0][:180].strip())
    for line in (profile.get("resume_text", "") or "").splitlines():
        clean = line.strip(" -\t")
        if len(clean) > 12 and clean not in highlights:
            highlights.append(clean[:180])
        if len(highlights) >= limit:
            break
    return highlights[:limit]

def _candidate_summary(profile):
    skills = ", ".join(skill.strip() for skill in (profile.get("skills", "") or "").split(",")[:6] if skill.strip())
    experience_summary = "; ".join(_experience_summary(profile, limit=2))
    parts = [
        profile.get("name") or "Candidate",
        profile.get("headline") or "",
        profile.get("location") or "",
        f"Skills: {skills}" if skills else "",
        f"Recent experience: {experience_summary}" if experience_summary else "",
        profile.get("bio") or "",
    ]
    return " | ".join(part for part in parts if part)

def calculate_fit_breakdown(profile, job):
    experience_entries, education_entries, profile_text, experience_text, education_text, resume_text = _profile_strings(profile)
    job_text = " ".join(filter(None, [
        job.get("skills", ""),
        job.get("requirements", ""),
        job.get("qualifications", ""),
        job.get("nice_to_have", ""),
        job.get("about_role", ""),
    ]))

    profile_tokens = set(_tokenize(profile_text))
    job_tokens = list(dict.fromkeys(_tokenize(job_text)))
    matched = [token for token in job_tokens if token in profile_tokens]
    missing = [token for token in job_tokens if token not in profile_tokens]

    keyword_score = round((len(matched) / len(job_tokens)) * 65) if job_tokens else 0
    profile_years = _extract_years(profile_text)
    required_years = _extract_years(job_text)
    if required_years is None and experience_entries:
        profile_years = max(profile_years or 0, len(experience_entries) * 2)

    if required_years is None:
        experience_score = 10 if experience_entries else 4
        experience_detail = "Experience entries are present." if experience_entries else "No prior experience entries added yet."
        experience_status = "positive" if experience_entries else "gap"
    elif profile_years is None:
        experience_score = 4 if experience_entries else 0
        experience_detail = f"Job asks for ~{required_years}+ years, but your profile does not state total years clearly."
        experience_status = "gap"
    elif profile_years >= required_years:
        experience_score = 10
        experience_detail = f"Profile suggests ~{profile_years} years against a {required_years}+ year requirement."
        experience_status = "positive"
    else:
        experience_score = 3
        experience_detail = f"Profile suggests ~{profile_years} years against a {required_years}+ year requirement."
        experience_status = "gap"

    education_score = 5 if education_entries else 2
    education_status = "positive" if education_entries else "unknown"
    education_detail = "Education details are filled in." if education_entries else "Education details are missing."

    location_signal = _location_signal(profile.get("location", ""), job.get("location", ""), job.get("work_type", ""))
    location_score = {"positive": 10, "unknown": 5, "gap": 2}[location_signal["status"]]

    completeness_score = 10 if profile.get("bio") and profile.get("headline") else 5

    score = min(100, keyword_score + experience_score + education_score + location_score + completeness_score)
    recommendation = (
        "Apply"
        if score >= 72 else
        "Apply selectively"
        if score >= 55 else
        "Upskill first"
    )

    return {
        "score": score,
        "matched": matched[:10],
        "gaps": missing[:10],
        "signals": [
            {"label": "Skills", "status": "positive" if matched else "gap", "detail": f"{len(matched)} requirement keywords matched."},
            {"label": "Experience", "status": experience_status, "detail": experience_detail},
            location_signal,
            {"label": "Education", "status": education_status, "detail": education_detail},
        ],
        "recommendation": recommendation,
        "profile_summary": {
            "experience_entries": len(experience_entries),
            "education_entries": len(education_entries),
            "profile_text": profile_text,
            "experience_text": experience_text,
            "education_text": education_text,
            "resume_text": resume_text,
        },
    }

def _model_available():
    return _model is not None and _tokenizer is not False

def summarize_post(text):
    _load_model()
    if not _model_available():
        return (text[:180] + "…") if len(text) > 180 else text

    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes LinkedIn posts in exactly one short sentence. Reply with only the summary sentence, nothing else."},
        {"role": "user", "content": f"Summarize this LinkedIn post in one sentence:\n\n{text}"}
    ]

    prompt = _tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = _tokenizer(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"]

    with torch.no_grad():
        output = _model.generate(
            input_ids,
            max_new_tokens=60,
            do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )

    new_tokens = output[0][input_ids.shape[-1]:]
    summary = _tokenizer.decode(new_tokens, skip_special_tokens=True)
    return summary.strip()


def analyze_fit(profile, job):
    """AI-powered fit analysis using Qwen."""
    _load_model()
    breakdown = calculate_fit_breakdown(profile, job)
    if not _model_available():
        return {**breakdown, "analysis": "AI analysis unavailable — model could not be loaded on this server."}
    skills = profile.get("skills", "") or "not specified"
    location = profile.get("location", "") or "not specified"
    experience_entries = _parse_json_list(profile.get("experience"))
    education_entries = _parse_json_list(profile.get("education"))
    exp_summary = ", ".join(
        f"{entry.get('title', '')} at {entry.get('company', '')}".strip()
        for entry in experience_entries[:3]
        if entry.get("title") or entry.get("company")
    ) or "not specified"
    edu_summary = ", ".join(
        f"{entry.get('degree', '')} at {entry.get('school', '')}".strip()
        for entry in education_entries[:2]
        if entry.get("degree") or entry.get("school")
    ) or "not specified"

    prompt = (
        f"<|im_start|>system\nYou are a sharp career advisor. Be brief, direct, and practical.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Candidate: skills={skills}, location={location}, experience={exp_summary}, education={edu_summary}, bio={profile.get('bio', '') or 'not specified'}\n"
        f"Resume highlights: {(breakdown['profile_summary']['resume_text'] or 'not specified')[:1200]}\n"
        f"Job: {job.get('title','')} at {job.get('company','')}, location={job.get('location','')} ({job.get('work_type','')}), "
        f"requires: {job.get('requirements','') or job.get('skills','')}\n\n"
        f"Deterministic fit signals: score={breakdown['score']}, recommendation={breakdown['recommendation']}, matched={', '.join(breakdown['matched']) or 'none'}, gaps={', '.join(breakdown['gaps']) or 'none'}.\n"
        f"In 4 short sentences: state overall fit, strengths, important gaps, and whether to apply now or what to improve first.\n"
        f"<|im_end|>\n<|im_start|>assistant\n"
    )

    inputs = _tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = _model.generate(
            **inputs, max_new_tokens=180, do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    result = _tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    return {
        "score": breakdown["score"],
        "matched": breakdown["matched"],
        "gaps": breakdown["gaps"],
        "signals": breakdown["signals"],
        "recommendation": breakdown["recommendation"],
        "analysis": result.strip(),
    }


def generate_screening_note(profile, job, application=None):
    _load_model()
    breakdown = calculate_fit_breakdown(profile, job)
    if not _model_available():
        return {"note": "AI screening unavailable — model could not be loaded.", "score": breakdown["score"], "breakdown": breakdown}
    prompt = (
        f"<|im_start|>system\nYou write recruiter screening notes. Be concise and actionable.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Candidate headline: {profile.get('headline', '')}\n"
        f"Candidate skills: {profile.get('skills', '')}\n"
        f"Candidate location: {profile.get('location', '')}\n"
        f"Candidate bio: {profile.get('bio', '')}\n"
        f"Candidate resume: {(profile.get('resume_text', '') or 'not provided')[:1200]}\n"
        f"Job: {job.get('title', '')} at {job.get('company', '')}\n"
        f"Job requirements: {job.get('requirements', '') or job.get('qualifications', '')}\n"
        f"Deterministic fit score: {breakdown['score']} with matched={', '.join(breakdown['matched']) or 'none'} and gaps={', '.join(breakdown['gaps']) or 'none'}.\n"
        f"Application cover note: {(application or {}).get('cover_note', '') or 'none'}\n"
        f"Write 3 bullet points: strengths, concerns, recruiter recommendation.\n"
        f"<|im_end|>\n<|im_start|>assistant\n"
    )
    inputs = _tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = _model.generate(
            **inputs, max_new_tokens=220, do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    result = _tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return {"note": result.strip(), "score": breakdown["score"], "breakdown": breakdown}


def generate_interview_questions(job):
    """Generate role-specific interview questions using Qwen."""
    _load_model()
    if not _model_available():
        return "AI question generation unavailable — model could not be loaded."
    prompt = (
        f"<|im_start|>system\nYou are a technical interviewer. List interview questions only.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Generate 6 interview questions for: {job.get('title','')} at {job.get('company','')}\n"
        f"Requirements: {job.get('requirements','') or job.get('qualifications','')}\n"
        f"Skills needed: {job.get('skills','')}\n"
        f"Format: numbered list, mix of technical and behavioural questions.\n"
        f"<|im_end|>\n<|im_start|>assistant\n"
    )

    inputs = _tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = _model.generate(
            **inputs, max_new_tokens=250, do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    result = _tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    return result.strip()

def generate_round_brief_pack(profile, job, application=None, round_info=None):
    _load_model()
    round_info = round_info or {}
    if not _model_available():
        return {"candidate_summary": _candidate_summary(profile), "screening_bullets": "AI unavailable.", "recruiter_notes": (application or {}).get("recruiter_notes") or "", "resume_highlights": _resume_highlights(profile), "gaps_to_probe": [], "round_objective": round_objective_for((round_info or {}).get("round_type")), "interviewer_guidance": "AI guidance unavailable — model could not be loaded."}
    breakdown = calculate_fit_breakdown(profile, job)
    objective = round_info.get("objective") or round_objective_for(round_info.get("round_type"))
    candidate_summary = _candidate_summary(profile)
    recruiter_notes = (application or {}).get("recruiter_notes") or "No recruiter notes recorded yet."
    resume_highlights = _resume_highlights(profile)
    gaps_to_probe = breakdown["gaps"][:5] or [
        signal["label"].lower()
        for signal in breakdown["signals"]
        if signal["status"] == "gap"
    ][:5]

    prompt = (
        f"<|im_start|>system\nYou create concise recruiter brief packs. Be practical and specific.\n<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Candidate: {candidate_summary}\n"
        f"Resume: {'; '.join(resume_highlights) or 'not provided'}\n"
        f"Cover note: {(application or {}).get('cover_note') or 'none'}\n"
        f"Job: {job.get('title', '')} at {job.get('company', '')}\n"
        f"Requirements: {job.get('requirements', '') or job.get('qualifications', '')}\n"
        f"Fit score: {breakdown['score']} | matched: {', '.join(breakdown['matched']) or 'none'} | gaps: {', '.join(gaps_to_probe) or 'none'}\n"
        f"Round {round_info.get('round_number', '?')}: {round_info.get('round_type', 'general')} — {objective}\n\n"
        f"Write:\n"
        f"SCREENING NOTE:\n"
        f"- Strengths: one sentence\n"
        f"- Concerns: one sentence\n"
        f"- Recommendation: one sentence\n\n"
        f"ROUND BRIEFING: 5 sentences covering what is promising, what to validate, what to probe, and what a strong signal looks like in this round.\n"
        f"<|im_end|>\n<|im_start|>assistant\n"
    )

    inputs = _tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = _model.generate(
            **inputs, max_new_tokens=300, do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    full_text = _tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    screening_text = ""
    briefing_text = full_text
    if "ROUND BRIEFING:" in full_text:
        parts = full_text.split("ROUND BRIEFING:", 1)
        screening_text = parts[0].replace("SCREENING NOTE:", "").strip()
        briefing_text = parts[1].strip()
    elif "SCREENING NOTE:" in full_text:
        screening_text = full_text.replace("SCREENING NOTE:", "").strip()
        briefing_text = ""

    return {
        "candidate_summary": candidate_summary,
        "screening_bullets": screening_text,
        "recruiter_notes": recruiter_notes,
        "resume_highlights": resume_highlights,
        "gaps_to_probe": gaps_to_probe,
        "round_objective": objective,
        "interviewer_guidance": briefing_text,
    }

def generate_candidate_interview_questions(profile, job, application=None, round_info=None, previous_feedback=None):
    _load_model()
    round_info = round_info or {}
    if not _model_available():
        return "AI question generation unavailable — model could not be loaded."
    breakdown = calculate_fit_breakdown(profile, job)
    objective = round_info.get("objective") or round_objective_for(round_info.get("round_type"))
    candidate_summary = _candidate_summary(profile)
    experience_summary = "; ".join(_experience_summary(profile, limit=3)) or "not specified"
    resume_highlights = "; ".join(_resume_highlights(profile, limit=5)) or "not provided"
    recruiter_notes = (
        (application or {}).get("recruiter_notes")
        or (application or {}).get("screening_note")
        or "none"
    )
    prev_feedback_line = f"Previous round feedback: {previous_feedback}\n" if previous_feedback else ""

    prompt = (
        f"<|im_start|>system\nYou are an expert interviewer preparing a highly targeted interview pack.\n<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Round: {round_info.get('round_number', '?')} / {round_info.get('round_type', 'general')}\n"
        f"Objective: {objective}\n"
        f"Candidate summary: {candidate_summary}\n"
        f"Experience: {experience_summary}\n"
        f"Resume highlights: {resume_highlights}\n"
        f"Recruiter notes: {recruiter_notes}\n"
        f"{prev_feedback_line}"
        f"Candidate location: {profile.get('location', '') or 'not specified'}\n"
        f"Job: {job.get('title', '')} at {job.get('company', '')}\n"
        f"Tech stack / skills: {job.get('skills', '')}\n"
        f"Requirements: {job.get('requirements', '') or job.get('qualifications', '')}\n"
        f"Fit gaps to probe: {', '.join(breakdown['gaps'][:6]) or 'none'}\n"
        f"Generate 10 numbered interview questions with a mix of:\n"
        f"1. technical questions tied to the role and stack\n"
        f"2. project/work experience questions from the candidate profile or resume\n"
        f"3. behavioural questions from their history and ownership signals\n"
        f"4. gap-probe questions based on missing skills/experience/location concerns\n"
        f"5. motivation, transition, and logistics questions\n"
        f"Format each line as: [Category] Question\n"
        f"<|im_end|>\n<|im_start|>assistant\n"
    )

    inputs = _tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = _model.generate(
            **inputs, max_new_tokens=320, do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    result = _tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return result.strip()

def generate_resume_bio(resume_text, existing_profile=None):
    _load_model()
    existing_profile = existing_profile or {}
    if not _model_available():
        return existing_profile.get("bio") or ""
    fallback = fallback_profile_from_resume(resume_text, existing_profile)
    prompt = (
        f"<|im_start|>system\nYou write concise professional bios for job platforms.\n<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Candidate name: {existing_profile.get('name') or fallback.get('name')}\n"
        f"Candidate headline: {existing_profile.get('headline') or fallback.get('headline')}\n"
        f"Resume text:\n{(resume_text or '')[:3000]}\n\n"
        f"Write a polished 2-sentence bio in first person that sounds professional, specific, and recruiter-friendly.\n"
        f"<|im_end|>\n<|im_start|>assistant\n"
    )
    inputs = _tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = _model.generate(
            **inputs, max_new_tokens=140, do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    result = _tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return result or existing_profile.get("bio") or ""

def infer_profile_from_resume(resume_text, existing_profile=None):
    _load_model()
    existing_profile = existing_profile or {}
    fallback = fallback_profile_from_resume(resume_text, existing_profile)
    prompt = (
        f"<|im_start|>system\nExtract resume details into valid JSON only. No commentary.\n<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Resume text:\n{(resume_text or '')[:4500]}\n\n"
        f"Existing profile hints: {json.dumps({'name': existing_profile.get('name'), 'headline': existing_profile.get('headline'), 'location': existing_profile.get('location')})}\n"
        f"Return JSON with exactly these keys:\n"
        f"name (string), headline (string), location (string), skills (array of strings),\n"
        f"experience (array of objects with title, company, duration, location, desc),\n"
        f"education (array of objects with school, degree, years).\n"
        f"If a field is unknown, use an empty string or empty array.\n"
        f"<|im_end|>\n<|im_start|>assistant\n"
    )
    inputs = _tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = _model.generate(
            **inputs, max_new_tokens=360, do_sample=False,
            pad_token_id=_tokenizer.eos_token_id
        )
    raw = _tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    parsed = _extract_json_object(raw) or {}

    skills = parsed.get("skills")
    if not isinstance(skills, list):
        skills = fallback.get("skills", [])
    else:
        skills = [str(skill).strip() for skill in skills if str(skill).strip()][:12]

    experience = parsed.get("experience")
    if not isinstance(experience, list):
        experience = fallback.get("experience", [])
    else:
        experience = [
            {
                "title": str(item.get("title", "")).strip(),
                "company": str(item.get("company", "")).strip(),
                "duration": str(item.get("duration", "")).strip(),
                "location": str(item.get("location", "")).strip(),
                "desc": str(item.get("desc", "")).strip(),
            }
            for item in experience[:4]
            if isinstance(item, dict)
        ]

    education = parsed.get("education")
    if not isinstance(education, list):
        education = fallback.get("education", [])
    else:
        education = [
            {
                "school": str(item.get("school", "")).strip(),
                "degree": str(item.get("degree", "")).strip(),
                "years": str(item.get("years", "")).strip(),
            }
            for item in education[:3]
            if isinstance(item, dict)
        ]

    return {
        "name": (parsed.get("name") or fallback.get("name") or "").strip(),
        "headline": (parsed.get("headline") or fallback.get("headline") or "").strip(),
        "location": (parsed.get("location") or fallback.get("location") or "").strip(),
        "skills": skills,
        "experience": experience,
        "education": education,
    }
