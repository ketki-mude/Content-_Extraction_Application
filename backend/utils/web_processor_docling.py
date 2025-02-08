import requests
import logging
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from datetime import datetime
from backend.utils.s3 import upload_markdown_to_s3

# Configure logging
logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

def fetch_html(url):
    """Fetch HTML content from a URL and save it to a temporary file."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
   
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch {url}. HTTP status code: {response.status_code}")
   
    # Create a temporary file that will be automatically deleted
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
    try:
        # Process HTML to handle image tags before saving
        soup = BeautifulSoup(response.content, 'html.parser')
       
        # Convert image tags to markdown format while preserving URLs
        for img in soup.find_all('img'):
            src = img.get('src')
            alt = img.get('alt', 'Image')
            if src:
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(url, src)
               
                # Create a new paragraph element for the image
                new_p = soup.new_tag('p')
                # Add the markdown image syntax as text
                new_p.string = f'![{alt}]({src})'
                # Replace the original img tag with our new paragraph
                img.replace_with(new_p)
       
        # Write the modified HTML to temp file
        temp_file.write(str(soup))
        temp_file.flush()
        return temp_file.name
    except Exception as e:
        _log.error(f"An error occurred: {str(e)}")
        return None
    finally:
        temp_file.close()
 
def process_html_with_docling(url):
    """Process HTML with Docling and save as Markdown to S3."""
    try:
        # Generate unique document ID using domain name
        domain = urlparse(url).netloc.replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"{domain}_{timestamp}"
        
        # Fetch HTML content and save to temporary file
        temp_html_path = fetch_html(url)
        if not temp_html_path:
            raise ValueError("Failed to fetch HTML content")

        try:
            # Initialize Docling converter
            doc_converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
            
            # Convert HTML to markdown
            result = doc_converter.convert(temp_html_path)
            if not result:
                raise ValueError("Failed to process the HTML file with Docling")
            
            # Get markdown content
            markdown_content = result.document.export_to_markdown()
            
            # Generate filename and S3 key
            markdown_filename = f"{domain}.md"
            markdown_key = f"web_sources/extracted_markdown/{document_id}/{markdown_filename}"
            
            # Upload to S3
            markdown_url = upload_markdown_to_s3(markdown_content, markdown_key)
            
            return {
                'source_type': 'web',
                'document_id': document_id,
                'urls': {
                    'markdown': markdown_url,
                },
                'metadata': {
                    'source_type': 'web',
                    'domain': domain,
                    'content_type': 'webpage',
                    'processor': 'docling'
                }
            }
            
        finally:
            # Clean up the temporary file
            Path(temp_html_path).unlink(missing_ok=True)
            
    except Exception as e:
        _log.error(f"An error occurred: {str(e)}")
        raise Exception(f"Failed to process website with Docling: {str(e)}")