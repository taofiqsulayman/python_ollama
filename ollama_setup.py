import ollama
import orjson
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
load_dotenv()

def extract_json_from_response(response):
    """Extract JSON from ChatCompletionOutput response"""
    try:
        # Get content from the first choice's message
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Remove markdown code block indicators if present
            json_str = content.replace('```json', '').replace('```', '').strip()
            
            return orjson.loads(json_str)
    except (AttributeError, orjson.JSONDecodeError) as e:
        print(f"Error parsing JSON: {e}")
        print(f"Problematic content: {response}")
        return {}

def run_inference_on_document(data: str, instructions: list):
    seen_titles = set()
    unique_instructions = []
    for instruction in instructions:
        title = instruction["title"].strip().lower().replace(" ", "_")
        if title not in seen_titles:
            seen_titles.add(title)
            unique_instructions.append(
                {
                    "title": title,
                    "data_type": instruction["data_type"],
                    "description": instruction["description"],
                }
            )

    prompt = f"""Here are the fields to extract: {unique_instructions},
    The document is as follows: {data}
    """

    client = InferenceClient(api_key=os.getenv("API_KEY"))

    response = client.chat_completion(
        model="meta-llama/Llama-3.2-3B-Instruct",
        messages=[
            {
                "role": "system",
                "content": "You are a professional Data Analyst and your job is to extract detailed information from documents and always return the information in JSON format. If a particular field is not found in the document, please return 'not found' for that field (very important). ONLY JSON IS ALLOWED as an answer. No explanation or other text is allowed.",
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=False,
    )
    
    return extract_json_from_response(response)

def summarize_image(image_url: str, prompt: str) -> str:
    client = InferenceClient(api_key=os.getenv("API_KEY"))

    response = client.chat_completion(
        model="meta-llama/Llama-3.2-11B-Vision-Instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ],
        max_tokens=500,
        stream=False,
    )

    response_text = ""
    if response.choices and len(response.choices) > 0:
        response_text = response.choices[0].message.content

    return response_text.strip()


def chat_with_document(document_content: str, user_input: str, conversation_history: list):
    prompt = f"""You are a professional Data Analyst. Here is the document content: {document_content}
    Here is the conversation history: {conversation_history}
    User: {user_input}
    Please respond accordingly.
    """

    client = InferenceClient(api_key=os.getenv("API_KEY"))

    response = client.chat_completion(
        model="meta-llama/Llama-3.2-3B-Instruct",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=False,
    )

    return response.choices[0].message.content.strip() if response.choices else ""