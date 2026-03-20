import os
import re
from pathlib import Path

from pypdf import PdfReader
from werkzeug.utils import secure_filename

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads" / "resumes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "our", "are", "have", "has", "will", "their", "role", "team", "work", "years",
    "year", "experience", "strong", "plus", "good", "nice", "must", "ability",
    "about", "using", "used", "build", "building", "candidate", "skills", "skill",
}

COMMON_SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Node.js", "Flask", "Django",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "AWS", "GCP", "Azure", "Docker", "Kubernetes",
    "Git", "REST", "GraphQL", "HTML", "CSS", "Tailwind", "Figma", "Tableau", "Power BI",
    "Excel", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "NLP", "Pandas",
    "NumPy", "Scikit-learn", "C++", "C", "Go", "Rust", "Data Analysis", "Product Management",
    "Marketing", "Strategy", "Finance", "Operations", "Leadership", "Agile", "Jira",
]

HEADER_WORDS = {
    "academic", "qualification", "qualifications", "education", "experience", "skills",
    "projects", "summary", "profile", "objective", "curriculum", "vitae", "resume",
    "certifications", "achievements", "internships", "employment", "contact",
}


def save_resume_file(file_storage, user_identifier):
    filename = secure_filename(file_storage.filename or "resume.pdf")
    ext = os.path.splitext(filename)[1].lower()
    if ext != ".pdf":
        raise ValueError("Only PDF resumes are supported.")
    safe_name = f"{user_identifier}_{filename}"
    path = UPLOAD_DIR / safe_name
    file_storage.save(path)
    return path, filename


def extract_resume_text(path):
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        lines = [re.sub(r"\s+", " ", line).strip() for line in page_text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        if cleaned:
            pages.append(cleaned)
    return "\n\n".join(pages).strip()


def _tokenize(text):
    return {
        token for token in re.split(r"[\s,;:+/|()\-–—]+", (text or "").lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def profile_resume_sync(profile, resume_text):
    if not resume_text:
        return {
            "status": "missing_resume",
            "note": "No resume text was extracted, so profile sync could not be checked.",
            "missing_from_resume": [],
            "resume_only_signals": [],
        }

    resume_lower = resume_text.lower()
    profile_items = []

    for skill in (profile.get("skills") or "").split(","):
        skill = skill.strip()
        if skill:
            profile_items.append(("skill", skill))

    for field_name in ("headline", "location", "bio"):
        value = (profile.get(field_name) or "").strip()
        if value:
            profile_items.append((field_name, value))

    experience_text = profile.get("experience") or ""
    education_text = profile.get("education") or ""
    for bucket, raw_text in (("experience", experience_text), ("education", education_text)):
        tokens = sorted(_tokenize(raw_text))
        for token in tokens[:10]:
            profile_items.append((bucket, token))

    missing = []
    matched_count = 0
    for item_type, value in profile_items:
        if value.lower() in resume_lower or _tokenize(value).intersection(_tokenize(resume_lower)):
            matched_count += 1
        else:
            missing.append(value)

    resume_terms = sorted(_tokenize(resume_text))
    profile_terms = sorted(_tokenize(" ".join([
        profile.get("headline", ""),
        profile.get("location", ""),
        profile.get("bio", ""),
        profile.get("skills", ""),
        experience_text,
        education_text,
    ])))
    profile_set = set(profile_terms)
    resume_only = [term for term in resume_terms if term not in profile_set][:8]

    if not profile_items:
        status = "needs_profile"
        note = "Resume uploaded, but the profile is still sparse. Fill in your profile so both stay aligned."
    elif len(missing) <= 2:
        status = "aligned"
        note = "Profile and resume look mostly aligned."
    elif len(missing) <= 6:
        status = "partial"
        note = "Resume is uploaded, but parts of your profile are missing from it or vice versa. Review the listed gaps."
    else:
        status = "mismatch"
        note = "Profile and resume appear meaningfully out of sync. Update one of them before applying broadly."

    return {
        "status": status,
        "note": note,
        "missing_from_resume": missing[:10],
        "resume_only_signals": resume_only,
        "matched_count": matched_count,
        "checked_items": len(profile_items),
    }

def _resume_lines(resume_text):
    return [line.strip() for line in (resume_text or "").splitlines() if line.strip()]

def guess_resume_name(resume_text):
    for line in _resume_lines(resume_text)[:10]:
        if "@" in line or re.search(r"\d{7,}", line):
            continue
        lowered_words = {word.lower() for word in re.findall(r"[A-Za-z]+", line)}
        if lowered_words.intersection(HEADER_WORDS):
            continue
        words = [word for word in re.split(r"\s+", line) if word]
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z.'-]+", word) for word in words):
            return " ".join(word.capitalize() for word in words)
    return None

def guess_resume_location(resume_text):
    location_patterns = [
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s?[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b",
        r"\b([A-Z][a-z]+,\s?[A-Z]{2})\b",
    ]
    header = " | ".join(_resume_lines(resume_text)[:10])
    for pattern in location_patterns:
        match = re.search(pattern, header)
        if match:
            return match.group(1)
    return None

def extract_skills_from_resume(resume_text, limit=12):
    found = []
    haystack = resume_text or ""
    for skill in COMMON_SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, haystack, re.IGNORECASE):
            found.append(skill)
    return found[:limit]

def fallback_profile_from_resume(resume_text, existing_profile=None):
    existing_profile = existing_profile or {}
    name = guess_resume_name(resume_text) or existing_profile.get("name") or "Aayush Thakur"
    location = guess_resume_location(resume_text) or existing_profile.get("location") or ""
    skills = extract_skills_from_resume(resume_text)
    headline = existing_profile.get("headline") or ""
    if not headline and skills:
        headline = f"{skills[0]} professional open to new opportunities"

    return {
        "name": name,
        "headline": headline,
        "one_liner": headline or (f"{skills[0]} talent open to new opportunities" if skills else ""),
        "location": location,
        "skills": skills,
        "experience": [],
        "education": [],
    }

def quick_bio_from_profile(profile):
    name = profile.get("name") or "I"
    headline = (profile.get("headline") or "").strip()
    location = (profile.get("location") or "").strip()
    skills = [skill.strip() for skill in (profile.get("skills") or "").split(",") if skill.strip()]

    opening = "I am"
    if name and name != "I":
        opening = f"I am {name}"

    parts = []
    if headline:
        parts.append(headline)
    elif skills:
        parts.append(f"a professional with strength in {', '.join(skills[:3])}")
    else:
        parts.append("a professional open to new opportunities")

    if location:
        parts.append(f"based in {location}")

    bio = f"{opening} {' '.join(parts)}."
    if skills:
        bio += f" My experience includes {', '.join(skills[:4])}, and I am looking for roles where I can keep building impact."
    else:
        bio += " I am looking for roles where I can contribute, learn quickly, and grow."
    return bio
