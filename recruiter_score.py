from database import get_all_recruiters_db, get_recruiter_by_id_db
from sklearn.linear_model import LinearRegression
import numpy as np

_model = None
_avg = None

def _ensure_model():
    global _model, _avg
    if _model is not None:
        return
    rows = get_all_recruiters_db()
    if not rows:
        return
    X = [[r["response_time"], r["hire_rate"], r["rating"], r["cancellations"]] for r in rows]
    y = [r["score"] for r in rows]
    _model = LinearRegression()
    _model.fit(X, y)
    _avg = np.mean(X, axis=0).tolist()

def get_recruiter_score(recruiter_id):
    _ensure_model()
    row = get_recruiter_by_id_db(recruiter_id)
    if row:
        sample = [[row["response_time"], row["hire_rate"], row["rating"], row["cancellations"]]]
        score = round(float(_model.predict(sample)[0]), 2)
        return {
            "score": score,
            "name": row["name"],
            "company": row["company"],
            "response_time": row["response_time"],
            "hire_rate": row["hire_rate"],
            "rating": row["rating"],
            "cancellations": row["cancellations"],
        }
    else:
        score = round(float(_model.predict([_avg])[0]), 2) if _model and _avg else 70.0
        return {
            "score": score,
            "name": "Unknown Recruiter",
            "company": "—",
            "response_time": int(_avg[0]) if _avg else 5,
            "hire_rate": round(_avg[1], 2) if _avg else 0.5,
            "rating": round(_avg[2], 1) if _avg else 4.0,
            "cancellations": int(_avg[3]) if _avg else 2,
        }

def get_all_recruiters():
    rows = get_all_recruiters_db()
    return [{"id": r["id"], "name": r["name"], "company": r["company"]} for r in rows]
