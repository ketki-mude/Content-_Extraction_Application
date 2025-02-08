import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
from pathlib import Path
from datetime import datetime
from backend.utils.s3 import upload_image_to_s3, upload_markdown_to_s3

def convert_table_to_markdown(table):
    """Convert HTML table to markdown format with advanced features"""
    markdown_table = []
    
    # Process header row
    headers = []
    alignments = []
    header_row = table.find('thead')
    if header_row:
        header_cells = header_row.find_all(['th', 'td'])
        for cell in header_cells:
            text = cell.get_text().strip()
            headers.append(text)
            # Determine alignment from style or align attribute
            align = cell.get('align', '') or cell.get('style', '')
            if 'right' in align:
                alignments.append('-:')
            elif 'center' in align:
                alignments.append(':-:')
            else:
                alignments.append('-')
    
    if headers:
        # Add header row
        markdown_table.append('| ' + ' | '.join(headers) + ' |')
        # Add separator row with alignments
        markdown_table.append('| ' + ' | '.join([f':{a}:' if a == ':-:' else a for a in alignments]) + ' |')
    
    # Process table body
    for row in table.find_all('tr'):
        if row.parent.name == 'thead':
            continue  # Skip header row we've already processed
        
        cells = []
        for cell in row.find_all(['td', 'th']):
            # Handle colspan
            colspan = int(cell.get('colspan', 1))
            text = cell.get_text().strip()
            cells.extend([text] * colspan)
        
        if any(cells):  # Only add row if it contains any content
            markdown_table.append('| ' + ' | '.join(cells) + ' |')
    
    return '\n'.join(markdown_table) if markdown_table else ''


def scrape_website(url: str):
    print("Scraping website")
    try:
        # Generate unique document ID using domain name
        domain = urlparse(url).netloc.replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"{domain}_{timestamp}"
        
        # Fetch and parse webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()
        
        # Initialize markdown content and track images
        markdown_content = []
        image_urls = {}
        
        # Add title
        if soup.title:
            markdown_content.append(f"# {soup.title.string.strip()}\n\n")
        
        # Process content
        for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'img', 'table','article']):
            if element.name == 'table':
                table_markdown = convert_table_to_markdown(element)
                if table_markdown:
                    markdown_content.append(f"\n{table_markdown}\n\n")
            
            elif element.name == 'img':
                src = element.get('src')
                if src:
                    try:
                        if src.startswith('data:image/'):
                            # Handle base64 encoded images
                            import base64
                            # Extract content type and base64 data
                            content_type = src.split(';')[0].split(':')[1]
                            ext = content_type.split('/')[-1]
                            if ext not in ['jpeg', 'jpg', 'png', 'gif']:
                                ext = 'png'
                            
                            # Get the base64 content after the comma
                            base64_data = src.split(',')[1]
                            img_data = base64.b64decode(base64_data)
                            
                            # Generate unique filename
                            img_filename = f"image_{len(image_urls) + 1}.{ext}"
                            
                            # Upload to S3
                            s3_key = f"web_sources/extracted_images/{document_id}/{img_filename}"
                            s3_url = upload_image_to_s3(img_data, s3_key, ext)
                            
                            # Store URL
                            image_urls[img_filename] = {s3_url}
                            
                            # Add URL to markdown
                            markdown_content.append(f"![Image]({s3_url})")
                            
                        else:
                            # Handle regular image URLs
                            # Convert relative URLs to absolute
                            if not src.startswith(('http://', 'https://')):
                                src = urljoin(url, src)
                            
                            # Download image
                            img_response = requests.get(src, headers=headers)
                            if img_response.status_code == 200:
                                # Rest of the existing image processing code
                                content_type = img_response.headers.get('content-type', '')
                                ext = content_type.split('/')[-1] if '/' in content_type else 'png'
                                if ext not in ['jpeg', 'jpg', 'png', 'gif']:
                                    ext = 'png'
                                
                                img_filename = f"image_{len(image_urls) + 1}.{ext}"
                                s3_key = f"web_sources/extracted_images/{document_id}/{img_filename}"
                                s3_url = upload_image_to_s3(img_response.content, s3_key, ext)
                                
                                image_urls[img_filename] = {s3_url}
                                markdown_content.append(f"![Image]({s3_url})")
                    
                    except Exception as e:
                        print(f"Failed to process image {src}: {e}")
                        markdown_content.append(f"\n{src}\n\n")
                        
            else:
                text = element.get_text().strip()
                if text:
                    if element.name.startswith('h'):
                        level = int(element.name[1])
                        markdown_content.append(f"{'#' * level} {text}\n\n")
                    else:
                        markdown_content.append(f"{text}\n\n")
        # Save as markdown
        markdown_filename = f"{domain}.md"
        markdown_key = f"web_sources/extracted_markdown/{document_id}/{markdown_filename}"
        markdown_content_str = "\n".join(markdown_content)
        
        markdown_url = upload_markdown_to_s3(markdown_content_str, markdown_key)
        
        return {
            'source_type': 'web',
            'document_id': document_id,
            'urls': {
                'markdown': markdown_url,
                'images': image_urls
            },
            'metadata': {
                'source_type': 'web',
                'domain': domain,
                'content_type': 'webpage',
                'image_count': len(image_urls),
            }
        }
        
    except Exception as e:
        raise Exception(f"Failed to process website: {str(e)}")