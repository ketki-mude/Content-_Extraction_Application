import os
import time
import requests
import json
import re
from datetime import datetime  
from pathlib import Path
from urllib.parse import urlparse
from backend.utils.s3 import upload_markdown_to_s3, upload_image_to_s3
 
# Constants
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
ACTOR_ID = os.getenv("ACTOR_ID")
 
# Apify page function
PAGE_FUNCTION = """
async function pageFunction(context) {
    const $ = context.jQuery;
    const baseUrl = new URL(context.request.url);
    const extractedData = [];
 
    $('*').each((_, el) => {
        const tag = el.tagName.toLowerCase();
        let text = $(el).contents().map(function() {
            return (this.nodeType === 3) ? this.nodeValue.trim() : ' ';
        }).get().join(' ').replace(/\\s+/g, ' ').trim();  // Preserve spaces
 
        if (tag === 'h1' || tag === 'h2' || tag === 'h3' || tag === 'h4' || tag === 'h5' || tag === 'h6') {
            if (text) extractedData.push({ type: 'heading', tag, text });
        } else if (tag === 'p' || tag === 'span' || tag === 'div') {
            if (text) extractedData.push({ type: 'text', text });
        } else if (tag === 'img') {
            const src = $(el).attr('src');
            if (src) extractedData.push({ type: 'image', src: new URL(src, baseUrl).href });
        } else if (tag === 'a') {
            const href = $(el).attr('href');
            if (href) extractedData.push({ type: 'link', href: new URL(href, baseUrl).href, text });
        } else if (tag === 'table') {
            const rows = [];
            $(el).find('tr').each((_, row) => {
                const rowData = [];
                $(row).find('th, td').each((_, cell) => {
                    let cellText = $(cell).text().replace(/\\s+/g, ' ').trim();
                    if (cellText) rowData.push(cellText);
                });
                if (rowData.length) rows.push(rowData);
            });
            if (rows.length) extractedData.push({ type: 'table', rows });
        }
    });
 
    context.log.info(`Extracted data from: ${context.request.url}`);
    return { url: context.request.url, extractedData };
}"""
 
def scrape_website_with_pdf(url: str):
    try:
        # Generate unique document ID
        domain = urlparse(url).netloc.replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"{domain}_{timestamp}"
 
        # Define S3 paths
        s3_markdown_key = f"web_sources/extracted_markdown/{document_id}.md"
        s3_images_key_prefix = f"web_sources/extracted_images/{document_id}"
 
        # Start the actor and fetch results
        run_id, dataset_id = start_actor(url)
        wait_for_actor_completion(run_id)
        results = fetch_results(dataset_id)
 
        # Convert JSON to Markdown
        md_content = json_to_markdown(results)
 
        # Extract original image URLs
        original_images = [data["src"] for item in results for data in item.get("extractedData", []) if data.get("type") == "image"]
 
        # Download and upload images to S3
        new_images = download_images_to_s3(results, s3_images_key_prefix)
        # Replace image URLs in markdown content
        updated_md_content = replace_image_urls(md_content, original_images, new_images)
 
        # Upload updated Markdown to S3
        markdown_url = upload_markdown_to_s3(updated_md_content, s3_markdown_key)
 
        # Extract metadata
        title = results[0].get("pageTitle", domain) if results else domain
        has_tables = any(item.get("tables") for item in results)

        print(markdown_url)
        print(new_images)
        response_data = {
            'source_type': 'web',
            'document_id': document_id,
            'urls': {
                'markdown': markdown_url,
                'images': new_images
            },
            'metadata': {
                'source_type': 'web',
                'source_url': url,
                'processing_date': timestamp,
                'content_type': 'webpage',
                'domain': domain,
                'title': title,
                'has_tables': has_tables,
                'image_count': len(new_images),
                'images': new_images
            }
        }
 
        return response_data
 
    except Exception as e:
        raise Exception(f"Failed to process website: {str(e)}")    
 
# Function to convert JSON to Markdown
def json_to_markdown(json_data):
    md_lines = []
    for item in json_data:
        url = item.get("url", "No URL")
        extracted_data = item.get("extractedData", [])
        md_lines.append(f"**URL:** {url}\n")
 
        for data in extracted_data:
            data_type = data.get("type")
            text = data.get("text", "").strip()
 
            if data_type == "text" and text:
                md_lines.append(text + "\n")
 
            elif data_type == "heading" and text:
                md_lines.append(f"## {text}\n")
 
            elif data_type == "image":
                src = data.get("src", "").strip()
                if src:
                    md_lines.append(f"![Image]({src})\n")
 
            elif data_type == "link":
                href = data.get("href", "").strip()
                link_text = data.get("text", "No Text").strip()
                if href:
                    md_lines.append(f"[{link_text}]({href})\n")
 
            elif data_type == "table":
                rows = data.get("rows", [])
                if rows:
                    md_lines.append("")  
                    header = " | ".join(rows[0])
                    separator = " | ".join(["---"] * len(rows[0]))
                    md_lines.append(header)
                    md_lines.append(separator)
                    for row in rows[1:]:
                        md_lines.append(" | ".join(row))
                    md_lines.append("\n")
 
        md_lines.append("---")
    return "\n".join(md_lines)
 
# Function to start the actor
def start_actor(url: str):
    start_url = url
    api_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_API_TOKEN}"
    payload = {
        "startUrls": [{"url": start_url}],
        "pageFunction": PAGE_FUNCTION
    }
    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["data"]["id"], data["data"]["defaultDatasetId"]
 
# Function to wait for the actor to complete
def wait_for_actor_completion(run_id):
    while True:
        api_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}?token={APIFY_API_TOKEN}"
        response = requests.get(api_url)
        response.raise_for_status()
        status = response.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        elif status == "FAILED":
            raise Exception("Actor run failed!")
        else:
            time.sleep(5)
 
# Function to fetch results
def fetch_results(dataset_id):
    api_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}&format=json"
    response = requests.get(api_url)
    response.raise_for_status()
    return response.json()
    
# Function to download images and upload them directly to S3
def download_images_to_s3(data, s3_key_prefix):
    images_path = []
    
    for item in data:
        images = [data["src"] for data in item.get("extractedData", []) if data.get("type") == "image"]
        
        print(f"Extracted images: {images}")  # Debugging
        
        for img_url in images:
            try:
                print(f"Downloading image: {img_url}")  # Debugging
                
                # Extract image name
                image_name = os.path.basename(img_url)
                s3_key = f"{s3_key_prefix}/{image_name}"
 
                # Download image
                response = requests.get(img_url, stream=True)
                response.raise_for_status()
                
                image_bytes = response.content
                image_ext = image_name.split('.')[-1].lower()
 
                # Upload image to S3
                s3_url = upload_image_to_s3(image_bytes, s3_key, image_ext)
                print(s3_url)
                images_path.append(s3_url)
                print(f"Uploaded to S3: {s3_url}")
 
            except Exception as e:
                print(f"Failed to process {img_url}: {e}")
    
    return images_path
 
def replace_image_urls(md_content, original_images, new_images):
    """
    Replace old image URLs in markdown content with new S3 URLs.
    
    :param md_content: The markdown content as a string.
    :param original_images: List of original image URLs extracted from JSON.
    :param new_images: List of new S3 image URLs.
    :return: Updated markdown content with replaced image URLs.
    """
    if not original_images or not new_images or len(original_images) != len(new_images):
        print("⚠️ Warning: Image lists are mismatched or empty. Skipping URL replacement.")
        return md_content
 
    url_map = dict(zip(original_images, new_images))  # Map old URLs to new URLs
 
    def replace_match(match):
        old_url = match.group(1)
        return f"![Image]({url_map.get(old_url, old_url)})"  # Replace if exists
 
    updated_md_content = re.sub(r"!\[Image\]\((.*?)\)", replace_match, md_content)
    return updated_md_content       
        