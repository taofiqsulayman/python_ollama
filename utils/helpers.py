from io import BytesIO
import zipfile
import aioboto3

def create_zip(images):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for filename, image_stream in images:
            zipf.writestr(filename, image_stream.getbuffer())
    zip_buffer.seek(0)
    return zip_buffer

def parse_page_range(page_range_str, num_pages):
    try:
        if not page_range_str:
            return list(range(num_pages))
        pages = []
        ranges = page_range_str.split(',')
        for range_str in ranges:
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                pages.extend(range(start - 1, end))
            else:
                pages.append(int(range_str) - 1)
        pages = [p for p in pages if 0 <= p < num_pages]
        return pages if pages else None
    except (ValueError, TypeError):
        return None


async def delete_all_objects(bucket_name):
    async with aioboto3.Session().client('s3') as s3_client:
        objects_to_delete = []
        paginator = s3_client.get_paginator('list_objects_v2')
        async for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({"Key": obj["Key"]})

        if objects_to_delete:
            await s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": objects_to_delete}
            )
            print(f"All objects in bucket '{bucket_name}' have been deleted.")
        else:
            print(f"The bucket '{bucket_name}' is already empty.")


async def upload_image_to_s3(image_bytes, bucket_name, object_name):
    session = aioboto3.Session()
    async with session.client('s3') as s3_client:
        try:
            await s3_client.put_object(Bucket=bucket_name, Key=object_name, Body=image_bytes)
            print(f"Uploaded {object_name} to S3 bucket {bucket_name}.")
        except Exception as e:
            print(f"Failed to upload {object_name}: {e}")


def validate_page_range(page_range_str, num_pages):
    page_indices = parse_page_range(page_range_str, num_pages)
    if page_indices is None:
        return {"error": "Invalid page range or out of bounds. Please check the document page numbers."}

    return page_indices if page_indices else list(range(num_pages))