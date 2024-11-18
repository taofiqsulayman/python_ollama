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
    prompt = f"""You are a helpful AI assistant with access to several documents. Your task is to help the user by providing accurate information based on these documents.

    CONTEXT:
    1. Previous Conversation:
    {format_conversation_history(conversation_history)}

    2. Available Documents:
    {document_content}

    USER QUESTION:
    {user_input}

    INSTRUCTIONS:
    1. Base your response only on the provided documents
    2. If information isn't in the documents, say so clearly
    3. Use specific references from documents when possible
    4. Keep responses concise but informative
    5. Maintain a helpful and professional tone

    Please provide your response:"""

    response = ollama.generate(model="llama3.2", prompt=prompt, stream=False)
    return response.get("response", "").strip()

def run_inference_on_document(data: str, instructions: list):
    # Format instructions for better clarity
    formatted_instructions = "\n".join(
        f"- {i+1}. {instr['title']}: {instr['description']}"
        for i, instr in enumerate(instructions)
    )

    prompt = f"""You are an expert document analyzer. Your task is to extract specific information from the provided documents.

    INPUT DOCUMENTS:
    {data}

    EXTRACTION REQUIREMENTS:
    {formatted_instructions}

    INSTRUCTIONS:
    1. Extract ONLY the requested information
    2. For each field:
       - Provide direct quotes where relevant
       - Mark clearly if information is not found
       - Indicate if information is ambiguous
    3. Format output as a clean JSON object
    4. Use null for missing values
    5. Include confidence level for each extraction (high/medium/low)

    OUTPUT FORMAT:
    {{
        "field_title": {{
            "value": "extracted_value",
            "confidence": "high/medium/low",
            "source": "document_name_if_applicable"
        }}
    }}

    Please provide your analysis:"""

    response = ollama.generate(
        model="llama3.2", prompt=prompt, format="json", stream=False
    )
    
    return extract_json_from_response(response)

def chat_with_image(image_bytes: bytes, prompt: str, conversation_history: list = None):
    system_prompt = {
        "role": "system",
        "content": """You are a precise image analysis assistant. Follow these guidelines:

    1. OBSERVATION:
    - Describe what you see with high accuracy
    - Note visual details systematically
    - Highlight key elements in the image

    2. ANALYSIS:
    - Answer questions specifically about visible elements
    - Clearly state when something is unclear or ambiguous
    - Don't make assumptions about non-visible aspects

    3. COMMUNICATION:
    - Be clear and concise
    - Use structured responses when appropriate
    - Reference specific parts of the image in your answers

    4. CONTEXT:
    - Consider previous conversation context
    - Maintain consistency in your observations
    - Build upon earlier responses when relevant"""
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

def format_conversation_history(history: list) -> str:
    """Helper function to format conversation history"""
    if not history:
        return "No previous conversation"
    
    formatted = "\n".join(
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in history
    )
    return formatted