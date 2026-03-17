import pandas as pd
from sklearn.linear_model import LinearRegression

data = pd.read_csv("data/recruiter_data.csv")

X = data[["response_time","hire_rate","rating","cancellations"]]
y = data["score"]

model = LinearRegression()
model.fit(X, y)

def get_recruiter_score(recruiter_id):
    sample = [[4,0.6,4.1,1]]
    score = model.predict(sample)
    return round(score[0],2)
