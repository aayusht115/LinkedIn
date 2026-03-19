from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float32)

def summarize_post(text):
    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes LinkedIn posts in exactly one short sentence. Reply with only the summary sentence, nothing else."},
        {"role": "user", "content": f"Summarize this LinkedIn post in one sentence:\n\n{text}"}
    ]

    # Apply chat template as a plain string first, then tokenize separately
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"]

    with torch.no_grad():
        output = model.generate(
            input_ids,
            max_new_tokens=60,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )

    new_tokens = output[0][input_ids.shape[-1]:]
    summary = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return summary.strip()