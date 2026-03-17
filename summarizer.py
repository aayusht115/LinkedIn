from transformers import pipeline

generator = pipeline(
    "text-generation",
    model="gpt2"
)

def summarize_post(text):

    prompt = f"Summarize this LinkedIn post in ONE short sentence:\n{text}\nSummary:"

    result = generator(
        prompt,
        max_length=60,
        num_return_sequences=1,
        temperature=0.3
    )

    output = result[0]["generated_text"]

    summary = output.split("Summary:")[-1]

    return summary.strip().split(".")[0] + "."
