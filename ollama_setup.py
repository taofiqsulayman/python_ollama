import ollama
import orjson
import logging

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

    prompt = f"""You are a professional Data Analyst and your job is to extract detailed information from documents.
    If a particular field is not found in the document, please return 'not found' for that field (very important).
    Your response should be only the specified fields and information extracted from the document in JSON format (very important).
    Here are the fields to extract: {unique_instructions},
    The document is as follows: {data}
    """

    response = ollama.generate(
        model="llama3.2",
        prompt=prompt,
        format="json", 
        stream=False
    )
    refined_response = extract_json_from_response(response)
    return refined_response


