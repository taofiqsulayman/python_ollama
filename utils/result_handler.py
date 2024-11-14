import json
import pandas as pd


def construct_tables_content(result):
    # Store all output in a list to return
    output = []

    if "data" in result:
        for idx, table_with_context in enumerate(result["data"]):
            parsing_report = table_with_context.get("parsing_report", "")
            table = table_with_context.get("table", None)

            if isinstance(table, pd.DataFrame):
                # Filter parsing report
                filtered_report = {k: v for k, v in parsing_report.items() if
                                   k not in ["whitespace", "order", "context"]}

                # Create table output for each DataFrame found
                table_output = {
                    "table_index": idx + 1,
                    "context": parsing_report.get("context", "No context provided"),
                    "parsing_report": json.dumps(filtered_report, indent=2),
                    "table_data": table.to_dict()
                }
                output.append(table_output)
            else:
                # Log skipped items
                output.append({"warning": f"Skipped a non-DataFrame item at index {idx}: {table}"})

    return output


def construct_images_content(result):
    """
    Processes each image in the result, accepts prompts, and returns the text outputs.
    """
    images = result.get("data", [])
    output_data = []

    # Check if there are images in the result data
    if not images:
        return [{"warning": "No images found in the result."}]

    # Process each image URL and collect results
    for idx, image_url in enumerate(images):
        output_data.append({
            "image_index": idx + 1,
            "image_url": image_url})

    return output_data
