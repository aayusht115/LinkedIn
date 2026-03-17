import uuid

interviews = []

def schedule_interview(data):
    interview = {
        "id": str(uuid.uuid4()),
        "candidate": data["candidate"],
        "recruiter": data["recruiter"],
        "time": data["time"],
        "meeting_link": "https://meet.fake/" + str(uuid.uuid4())[:6]
    }

    interviews.append(interview)

    return interview
