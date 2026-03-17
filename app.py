from flask import Flask, request, jsonify
from interview_scheduler import schedule_interview
from recruiter_score import get_recruiter_score
from summarizer import summarize_post
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "LinkedIn AI Features Prototype"

@app.route("/schedule", methods=["POST"])
def schedule():
    data = request.json
    result = schedule_interview(data)
    return jsonify(result)

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
