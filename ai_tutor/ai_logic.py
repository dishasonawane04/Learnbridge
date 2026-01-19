import ollama

def chat_with_ai(prompt):
    response = ollama.chat(
        model="llama3:latest",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI tutor. "
                    "Respond exactly how the user asks. "
                    "If user asks bullet points, use bullet points. "
                    "If user asks paragraph, use paragraph. "
                    "Do not use stars (*). "
                    "Keep answers clean and structured."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]
