import boto3
import os
from dotenv import load_dotenv
from pathlib import Path
import io
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

# Add error checking for environment variables
if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_S3_BUCKET_NAME]):
    raise ValueError("Missing required AWS credentials in .env file")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def test_s3_connection():
    try:
        s3_client.head_bucket(Bucket=AWS_S3_BUCKET_NAME)
        return True
    except Exception as e:
        print(f"S3 Connection Error: {str(e)}")
        return False

def ensure_s3_structure():
    """Ensure the basic folder structure exists in S3"""
    base_folders = [
        'pdf_sources/',
        'pdf_sources/raw/',
        'pdf_sources/extracted_markdown/',
        'pdf_sources/extracted_images/',
        'web_sources/',
        'web_sources/raw/',
        'web_sources/extracted_markdown/',
        'web_sources/extracted_images/'
    ]
    
    try:
        for folder in base_folders:
            s3_client.put_object(
                Bucket=AWS_S3_BUCKET_NAME,
                Key=folder
            )
        return True
    except Exception as e:
        print(f"Error creating S3 structure: {e}")
        return False

def upload_to_s3(content: bytes, key: str, content_type: str = None) -> str:
    """Upload content to S3 and return the URL"""
    try:
        extra_args = {'ACL': 'public-read'}
        if content_type:
            extra_args['ContentType'] = content_type
            
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=key,
            Body=content,
            **extra_args
        )
        
        return f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
    except Exception as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")

def get_from_s3(key: str) -> bytes:
    """Get content from S3"""
    try:
        response = s3_client.get_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=key
        )
        return response['Body'].read()
    except Exception as e:
        raise Exception(f"Failed to get file from S3: {str(e)}")

def upload_image_buffer_to_s3(image_buffer: io.BytesIO, key: str) -> str:
    """Upload image buffer to S3 and return the URL"""
    try:
        s3_client.upload_fileobj(
            image_buffer,
            AWS_S3_BUCKET_NAME,
            key,
            ExtraArgs={'ContentType': 'image/png'}
        )
        return f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/{key}"
    except Exception as e:
        raise Exception(f"Failed to upload image to S3: {str(e)}")
        
def upload_image_to_s3(image_bytes: bytes, key: str, image_ext: str) -> str:
    """Helper function to upload an image to S3 and return its URL"""
    try:
        content_type = f'image/{image_ext}' if image_ext in ['jpeg', 'jpg', 'png'] else 'application/octet-stream'
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=key,
            Body=image_bytes,
            ContentType=content_type,
            ACL='public-read'
        )
        return f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
    except Exception as e:
        raise Exception(f"Failed to upload image to S3: {str(e)}")
    
def upload_pdf_to_s3(file_content: bytes, original_filename: str, document_id: str) -> dict:
    """
    Uploads PDF and its processed content to S3 with proper structure.
    Returns dict of URLs for each uploaded file.
    """
    urls = {}
    try:
        # Upload original PDF
        raw_key = f"pdf_sources/raw/{document_id}/{original_filename}"
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=raw_key,
            Body=file_content
        )
        urls['raw_pdf'] = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{raw_key}"
        
        return urls
    except Exception as e:
        raise Exception(f"Failed to upload PDF to S3: {e}")

def upload_processed_content_to_s3(local_directory: str, document_id: str, source_type: str) -> dict:
    """
    Uploads processed content with proper content types and disposition
    """
    urls = {}
    base_path = Path(local_directory)  # Convert string to Path object
    try:
        # Handle raw files (PDF)  
        if source_type == 'pdf':  
            raw_dir = base_path / "raw"
            if raw_dir.exists():
                for file in raw_dir.iterdir():
                    if file.is_file():
                        raw_key = f"{source_type}_sources/raw/{document_id}/{file.name}"
                        with open(file, 'rb') as f:
                            s3_client.put_object(
                                Bucket=AWS_S3_BUCKET_NAME,
                                Key=raw_key,
                                Body=f.read(),
                                ACL='public-read',
                                ContentType='application/pdf',
                                ContentDisposition='inline'
                            )
                        urls['raw_file'] = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{raw_key}"

        # Handle markdown and images
        for root, _, files in os.walk(base_path):
            for filename in files:  # Changed 'file' to 'filename'
                local_path = Path(root) / filename  # Use filename string
                relative_path = local_path.relative_to(base_path)
                
                # Skip raw directory as we've already handled it
                if 'raw' in str(relative_path):
                    continue
                
                # Determine the correct S3 prefix and content type
                if 'extracted_markdown' in str(relative_path):
                    s3_prefix = f"{source_type}_sources/extracted_markdown/{document_id}"
                    content_type = 'text/markdown'
                elif 'extracted_images' in str(relative_path):
                    s3_prefix = f"{source_type}_sources/extracted_images/{document_id}"
                    ext = filename.lower().split('.')[-1]  # Get extension from filename
                    if ext in ['png']:
                        content_type = 'image/png'
                    elif ext in ['jpg', 'jpeg']:
                        content_type = 'image/jpeg'
                    else:
                        content_type = 'application/octet-stream'
                else:
                    continue
                
                s3_key = f"{s3_prefix}/{filename}"  # Use filename directly
                
                # Upload file with proper content type
                with open(local_path, 'rb') as f:
                    s3_client.put_object(
                        Bucket=AWS_S3_BUCKET_NAME,
                        Key=s3_key,
                        Body=f.read(),
                        ACL='public-read',
                        ContentType=content_type,
                        ContentDisposition='inline'
                    )
                    urls[str(relative_path)] = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        
        return urls
    except Exception as e:
        raise Exception(f"Failed to upload content to S3: {str(e)}")  # Added str() for better error messages

def upload_markdown_to_s3(content: str, key: str) -> str:
    """Upload markdown content to S3"""
    try:
        s3_client.put_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType='text/markdown'
        )
        return f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
    except Exception as e:
        raise Exception(f"Failed to upload markdown to S3: {str(e)}")
    
# Run this when the module loads to ensure S3 structure exists
ensure_s3_structure()

if not test_s3_connection():
    print("WARNING: Cannot access S3 bucket. Please check your credentials and permissions.")