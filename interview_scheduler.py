import uuid
from database import save_interview

def schedule_interview(data):
    interview = {
        "id": str(uuid.uuid4()),
        "candidate": data["candidate"],
        "recruiter": data["recruiter"],
        "time": data["time"],
        "job_id": data.get("job_id") or None,
        "application_id": data.get("application_id") or None,
        "round_id": data.get("round_id") or None,
        "round_type": data.get("round_type") or None,
        "interviewer_name": data.get("interviewer_name") or data.get("recruiter"),
        "meeting_link": "https://meet.google.com/new"
    }
    save_interview(interview)
    return interview
