import uuid
from database import save_interview

def schedule_interview(data):
    interview = {
        "id": str(uuid.uuid4()),
        "candidate": data["candidate"],
        "recruiter": data["recruiter"],
        "time": data["time"],
        "job_id": data.get("job_id") or None,
        "meeting_link": "https://meet.fake/" + str(uuid.uuid4())[:6]
    }
    save_interview(interview)
    return interview
