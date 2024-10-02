import ollama
import io
import orjson

def extract_json_from_response(response):
    
    json_like_str = response.get("response", "").strip()

    if not json_like_str.startswith("{") or not json_like_str.endswith("}"):
        print(f"Warning: Response does not contain valid JSON format: {json_like_str}")
        return {}

    try:
        # Convert the string to a dictionary using orjson
        extracted_info = orjson.loads(json_like_str)
    except orjson.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        extracted_info = {}

    return extracted_info


def run_inference_on_document(data: str, instructions: list):
    # Ensure unique titles in a case-insensitive manner
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
        model="llama3.1",
        prompt=prompt,
        format="json", 
        stream=False
    )
    refined_response = extract_json_from_response(response)
    return refined_response


def run_inference_on_image(image, text_input: str):
    # Convert the PIL image to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')  # Save the image in PNG format
    img_byte_arr = img_byte_arr.getvalue()  # Get the image as bytes
    
    prompt = f"{text_input}"
    
    # Pass the image bytes to the ollama.generate function
    response = ollama.generate(
        model="llava:13b",
        prompt=prompt,
        images=[img_byte_arr], 
        stream=False
    )
    
    return response.get("response", "")

    
    