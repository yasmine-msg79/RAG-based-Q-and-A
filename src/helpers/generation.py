import ollama
import json
from helpers import config

settings = config.get_settings()
client = ollama.Client(
    host=settings.OLLAMA_HOST
)

def generate_answer(query, retrieved_chunks):
    context = "\n\n".join(
        chunk["text"] for chunk in retrieved_chunks
    )

    response = client.chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer using only the provided context. "
                    "If the answer isn't in the context, say you don't know."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion:\n{query}",
            },
        ],
    )

    return response.message.content


def generate_mcqs(retrieved_chunks, num_questions=5):
    context = "\n\n".join(
        chunk["text"] for chunk in retrieved_chunks
    )

    response = client.chat(
        model="llama3.2",
        format="json",
        messages=[
            {
                "role": "system",
                "content": """
You generate multiple-choice questions using only the
provided context.

Return valid JSON in this exact structure:
{
  "questions": [
    {
      "question": "Question text",
      "options": {
        "A": "First option",
        "B": "Second option",
        "C": "Third option",
        "D": "Fourth option"
      },
      "correct_answer": "A"
    }
  ]
}

Rules:
- Each question must have exactly four options.
- There must be exactly one correct answer.
- correct_answer must be A, B, C, or D.
- Make incorrect options plausible but clearly incorrect.
- Do not use information absent from the context.
- Return only the requested number of questions.
"""
            },
            {
                "role": "user",
                "content": (
                    f"Generate {num_questions} questions "
                    f"from this context:\n\n{context}"
                )
            }
        ],
    )

    return json.loads(response.message.content)



def generate_true_false(retrieved_chunks, num_questions=5):
    context = "\n\n".join(
        chunk["text"] for chunk in retrieved_chunks
    )

    response = client.chat(
        model="llama3.2",
        format="json",
        messages=[
            {
                "role": "system",
                "content": """
Generate True/False questions using only the provided context.

Return JSON in exactly this structure:
{
  "questions": [
    {
      "statement": "A statement about the context",
      "answer": true
    }
  ]
}

Rules:
- Every question must contain "statement" and "answer".
- "answer" must be a JSON boolean: true or false, never a string.
- Include a reasonable mix of true and false statements.
- False statements must contradict the context.
- Return exactly the requested number of questions.
- Return only valid JSON.
"""
            },
            {
                "role": "user",
                "content": (
                    f"Generate {num_questions} True/False questions "
                    f"from this context:\n\n{context}"
                )
            }
        ],
    )

    data = json.loads(response.message.content)

    if not isinstance(data.get("questions"), list):
        raise ValueError("True/false generation did not return a questions list.")

    for index, item in enumerate(data["questions"], start=1):
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("statement"), str)
            or not item["statement"].strip()
            or type(item.get("answer")) is not bool
        ):
            raise ValueError(
                f"Invalid true/false question at position {index}: {item}"
            )

    return data
