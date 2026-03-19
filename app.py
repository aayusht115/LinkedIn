from flask import Flask, request, jsonify
from flask_cors import CORS
from interview_scheduler import schedule_interview
from recruiter_score import get_recruiter_score
from summarizer import summarize_post
from database import init_db, get_all_interviews, get_interview_by_id

app = Flask(__name__)
CORS(app)

init_db()  # creates the table if it doesn't exist

@app.route("/")
def home():
    return "LinkedIn AI Features Prototype"

@app.route("/schedule", methods=["POST"])
def schedule():
    data = request.json
    result = schedule_interview(data)
    return jsonify(result)

@app.route("/interviews", methods=["GET"])
def list_interviews():
    return jsonify(get_all_interviews())

@app.route("/interviews/<interview_id>", methods=["GET"])
def get_interview(interview_id):
    interview = get_interview_by_id(interview_id)
    if not interview:
        return jsonify({"error": "Interview not found"}), 404
    return jsonify(interview)

@app.route("/recruiter_score/<recruiter_id>")
def recruiter_score(recruiter_id):
    score = get_recruiter_score(recruiter_id)
    return jsonify({"score": score})

@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.json
    summary = summarize_post(data["text"])
    return jsonify({"summary": summary})

if __name__ == "__main__":
    app.run(debug=True)
