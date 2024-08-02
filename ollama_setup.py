import ollama
import json


def extract_json_from_response(response):
    # Extract the "response" field from the response object
    response_text = response.get("response", "")

    # Find the starting position of the JSON-like string in the response
    start_pos = response_text.find("{")
    # Find the ending position of the JSON-like string in the response
    end_pos = response_text.rfind("}") + 1

    # Extract the JSON-like string from the response text
    json_like_str = response_text[start_pos:end_pos]

    # Convert the JSON-like string to a dictionary
    try:
        extracted_info = eval(json_like_str)
    except SyntaxError as e:
        print(f"Error parsing JSON-like string: {e}")
        extracted_info = {}

    return extracted_info


def get_ollama_response(data: str, instructions: list, model):
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

    response_format = (
        "{\n"
        + ",\n".join([f'  "{instr["title"]}": ""' for instr in unique_instructions])
        + "\n}"
    )

    prompt = f"""You are a professional Data Analyst / Data Miner and your job is to extract detailed information from documents.
    If a particular field is not found in the document, please return 'not found' for that field. Return the response as a JSON based on the instructions below;
    Here are the fields to extract: {unique_instructions},
    Also, return response in this format: {response_format}
    The document is as follows: {data}
    """

    response = ollama.generate(
        model=model, prompt=prompt, stream=False
    )
    refined_response = extract_json_from_response(response)

    return refined_response

