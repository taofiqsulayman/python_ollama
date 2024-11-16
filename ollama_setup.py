import ollama
import orjson
import logging
from dotenv import load_dotenv

load_dotenv()

def extract_json_from_response(response):
    json_like_str = response.get("response", "").strip()

    if not json_like_str.startswith("{") or not json_like_str.endswith("}"):
        logging.warning(f"Response does not contain valid JSON format: {json_like_str}")
        return {}

    try:
        extracted_info = orjson.loads(json_like_str)
    except orjson.JSONDecodeError as e:
        logging.error(f"Error parsing JSON: {e}")
        extracted_info = {}

    return extracted_info

def chat_with_document(
    document_content: str, user_input: str, conversation_history: list
):
    prompt = f"""You are a knowledgeable and helpful assistant. 

    **Context:**

    * Document content: {document_content}
    * Conversation history: {conversation_history}
    * User's query: {user_input}

    **Response Guidelines:**

    1. Provide accurate and relevant information based on the context.
    2. Ensure responses are clear, concise, and easy to understand.
    3. Address the user's query directly and thoroughly.

    Please respond helpfully.
    """

    response = ollama.generate(model="llama3.2", prompt=prompt, stream=False)
    return response.get("response", "").strip()


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

    prompt = f"""You are a professional Data Analyst specializing in document information extraction.
    Your task is to accurately extract specific fields from the provided document.

    **Extraction Guidelines:**

    1. Extract the following fields: {unique_instructions}
    2. If a field is not found in the document, return 'not found' for that field.
    3. Format your response as a JSON object containing only the specified fields and extracted information.

    **Document:**
    {data}
    
    Please provide the extracted information in JSON format.
    """

    response = ollama.generate(
        model="llama3.2", prompt=prompt, format="json", stream=False
    )

    refined_response = extract_json_from_response(response)
    return refined_response

def chat_with_image(image_bytes: bytes, prompt: str, conversation_history: list = None):
    
    system_prompt = {
        "role": "system",
        "content": """You are a highly accurate Image Analysis AI Assistant. 

        **Guiding Principles:**

        1. **Verification**: Only provide statements that can be directly verified from the image.
        2. **Uncertainty**: Clearly indicate uncertainty or ambiguity when applicable.
        3. **Contextual Understanding**: Consider the provided context to enhance comprehension.
        4. **Consistency**: Ensure responses align with previous statements.
        5. **Objectivity**: Focus on factual observations, avoiding assumptions or inferences.

        **Operational Priority:** Accuracy and clarity in image analysis take precedence over all other considerations.
        """
    }


    max_history = 5
    recent_messages = conversation_history[-max_history:] if conversation_history else []

    try:
        response = ollama.chat(
            model='llama3.2-vision',
            messages=[
                system_prompt,
                *recent_messages,
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_bytes]
                }
            ]
        )
        return response['message']['content']
    except Exception as e:
        logging.error(f"Error in image chat: {str(e)}")
        return f"Error processing image: {str(e)}"
