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


_DATE_SPAN_RE = re.compile(
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s*\d{4}\s*[-–—to]+\s*(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s*\d{4}|'
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s*\d{4}\s*[-–—to]+\s*(?:Present|Current|Now|Till\s*[Dd]ate)|'
    r'\d{4}\s*[-–—]\s*(?:\d{4}|Present|Current)',
    re.IGNORECASE,
)


def _has_date_span(text):
    return bool(_DATE_SPAN_RE.search(text))


def _extract_date_span(text):
    m = _DATE_SPAN_RE.search(text)
    return m.group().strip() if m else ""


def _is_section_header(line):
    tokens = [w for w in re.findall(r'[a-z]+', line.lower()) if len(w) > 2]
    if not tokens or len(line.split()) > 6:
        return False
    header_hits = sum(1 for t in tokens if t in HEADER_WORDS)
    # Majority of meaningful words must be section-header words
    return header_hits / len(tokens) >= 0.5


def _get_section_lines(all_lines, target_words):
    in_target = False
    result = []
    for line in all_lines:
        low = line.lower()
        if _is_section_header(line):
            words = set(re.findall(r'[a-z]+', low))
            if words.intersection(target_words):
                in_target = True
                continue
            elif in_target:
                break
        if in_target:
            result.append(line)
    return result


def extract_experience_from_resume(resume_text, limit=4):
    lines = _resume_lines(resume_text)
    exp_lines = _get_section_lines(lines, {"experience", "employment", "work"})
    if not exp_lines:
        return []

    entries = []
    i = 0
    while i < len(exp_lines) and len(entries) < limit:
        line = exp_lines[i]
        span = _extract_date_span(line)
        next_span = _extract_date_span(exp_lines[i + 1]) if i + 1 < len(exp_lines) else ""

        if not span and not next_span:
            i += 1
            continue

        title, company, duration = "", "", span or next_span
        clean = _DATE_SPAN_RE.sub("", line).strip().strip("|-–,•").strip()

        at_match = re.match(r'^(.+?)\s+at\s+(.+)$', clean, re.IGNORECASE)
        pipe_parts = [p.strip() for p in re.split(r'\s*[|•]\s*', clean) if p.strip()]

        if at_match:
            title = at_match.group(1).strip()
            company = at_match.group(2).strip()
        elif len(pipe_parts) >= 2:
            title = pipe_parts[0]
            company = pipe_parts[1]
        elif clean:
            if i > 0 and not _is_section_header(exp_lines[i - 1]) and not _has_date_span(exp_lines[i - 1]):
                company = clean
                title = exp_lines[i - 1].strip()
            else:
                title = clean

        if next_span and not span:
            # current line has no date — title/company here, date on next line
            title = line.strip()
            company = ""
            duration = next_span
            i += 1

        # Collect up to 2 description bullet lines
        desc_parts = []
        j = i + 1
        while j < len(exp_lines) and len(desc_parts) < 2:
            dl = exp_lines[j].strip()
            if not dl or _is_section_header(exp_lines[j]) or _has_date_span(dl):
                break
            if j + 1 < len(exp_lines) and _has_date_span(exp_lines[j + 1]):
                break
            desc_parts.append(dl.lstrip("•-–▸▪ ").strip())
            j += 1

        if title or company:
            entries.append({
                "title": title[:80],
                "company": company[:60],
                "duration": duration[:40],
                "location": "",
                "desc": " ".join(desc_parts)[:200],
            })
        i = j

    return entries


def extract_education_from_resume(resume_text, limit=3):
    lines = _resume_lines(resume_text)
    edu_lines = _get_section_lines(lines, {"education", "academic", "qualification", "qualifications"})
    if not edu_lines:
        return []

    entries = []
    i = 0
    while i < len(edu_lines) and len(entries) < limit:
        line = edu_lines[i]
        span = _extract_date_span(line)
        next_span = _extract_date_span(edu_lines[i + 1]) if i + 1 < len(edu_lines) else ""

        if not span and not next_span:
            i += 1
            continue

        school, degree, years = "", "", span or next_span
        clean = _DATE_SPAN_RE.sub("", line).strip().strip("|-–,•").strip()
        pipe_parts = [p.strip() for p in re.split(r'\s*[|,]\s*', clean) if p.strip()]

        if len(pipe_parts) >= 2:
            # "Degree, School | 2016-2020" → degree=parts[0], school=parts[1]
            degree = pipe_parts[0]
            school = pipe_parts[1]
        elif clean and i > 0 and not _is_section_header(edu_lines[i - 1]) and not _has_date_span(edu_lines[i - 1]):
            school = edu_lines[i - 1].strip()
            degree = clean
        elif clean:
            school = clean

        if next_span and not span:
            school = line.strip()
            next_clean = _DATE_SPAN_RE.sub("", edu_lines[i + 1]).strip().strip("|-–,•").strip()
            degree = next_clean
            years = next_span
            i += 1

        if school or degree:
            entries.append({
                "school": school[:80],
                "degree": degree[:80],
                "years": years[:40],
            })
        i += 1

    return entries

def guess_resume_name(resume_text):
    lines = _resume_lines(resume_text)
    # First pass: top 5 lines only — name is almost always here
    for line in lines[:5]:
        if "@" in line or re.search(r"\d{5,}", line):
            continue
        lowered_words = {word.lower() for word in re.findall(r"[A-Za-z]+", line)}
        if lowered_words.intersection(HEADER_WORDS):
            continue
        words = [word for word in re.split(r"\s+", line) if word]
        if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z.'-]+", word) for word in words):
            return " ".join(word.capitalize() for word in words)
    # Second pass: widen to top 10 lines
    for line in lines[5:10]:
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
    name = existing_profile.get("name") or ""
    location = guess_resume_location(resume_text) or existing_profile.get("location") or ""
    skills = extract_skills_from_resume(resume_text)
    headline = existing_profile.get("headline") or ""
    if not headline and skills:
        headline = f"{skills[0]} professional open to new opportunities"
    experience = extract_experience_from_resume(resume_text)
    education = extract_education_from_resume(resume_text)

    return {
        "name": name,
        "headline": headline,
        "one_liner": headline or (f"{skills[0]} talent open to new opportunities" if skills else ""),
        "location": location,
        "skills": skills,
        "experience": experience,
        "education": education,
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
