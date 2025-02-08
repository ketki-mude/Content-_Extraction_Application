import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import fitz  # PyMuPD
from pathlib import Path
from datetime import datetime
from backend.utils.s3 import upload_image_to_s3, upload_markdown_to_s3

def process_pdf_with_enterprise(pdf_buffer, document_id, original_filename):
    try:
        # Initialize Azure Form Recognizer client
        endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
        api_key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
        
        if not endpoint or not api_key:
            raise ValueError("Azure Form Recognizer credentials not found in environment variables")
            
        client = DocumentAnalysisClient(endpoint, AzureKeyCredential(api_key))
        print("✅ Azure Form Recognizer client initialized")
        # Create directory structure
        base_dir = Path("pdf_sources") / document_id
        raw_dir = base_dir / "raw"
        markdown_dir = base_dir / "extracted_markdown"
        images_dir = base_dir / "extracted_images"

        # Create directories
        for dir_path in [base_dir, raw_dir, markdown_dir, images_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        print("✅ Directories created")
        # Initialize content storage
        markdown_content = "# PDF Extraction Output\n\n"
        content_map = {}
        image_urls = {}
        
        # Analyze document with Azure Form Recognizer
        poller = client.begin_analyze_document("prebuilt-document", document=pdf_buffer)
        result = poller.result()
        print("✅ Document analyzed")


        # Process each page
        if result.pages:
            for page in result.pages:
                page_num = page.page_number
                content_map[page_num] = {
                    "text": f"## Page {page_num}\n\n",
                    "tables": [],
                    "images": []
                }
                print("✅ Page content initialized")
                # Add page dimensions
                content_map[page_num]["text"] += f"**Page Dimensions:** {page.width} x {page.height}\n\n"
                print("✅ Page dimensions added")

                # Extract text
                if page.lines:
                    content_map[page_num]["text"] += "**Text Content:**\n\n"
                    for line in page.lines:
                        content_map[page_num]["text"] += f"{line.content}\n\n"
                print("✅ Text content extracted")


        # Extract and process tables
        if result.tables:
            print("✅ Tables found")
            for table in result.tables:
                table_markdown = "\n**Table:**\n\n"
                for row in range(table.row_count):
                    row_cells = [cell.content for cell in table.cells if cell.row_index == row]
                    table_markdown += "| " + " | ".join(row_cells) + " |\n"
                    if row == 0:
                        table_markdown += "| " + " | ".join(["---"] * len(row_cells)) + " |\n"

                if table.bounding_regions:
                    page_number = table.bounding_regions[0].page_number
                    content_map[page_number]["tables"].append(table_markdown)
                print("✅ Tables extracted")

        # Extract and process images using PyMuPDF
        print("✅ PyMuPDF document opening")
        doc = fitz.open(stream=pdf_buffer, filetype="pdf")
        print("✅ PyMuPDF document opened")
        for page_number in range(len(doc)):
            page = doc[page_number]
            images = page.get_images(full=True)
            print("✅ Images found")
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                print("✅ Image extracted")
                image_filename = f"page{page_number+1}_img{img_index+1}.{image_ext}"
                s3_image_key = f"pdf_sources/extracted_images/{document_id}/{image_filename}"
                print("✅ Image filename and S3 key initialized")
                # Upload image to S3
                try:
                    image_url = upload_image_to_s3(image_bytes, s3_image_key, image_ext)
                    image_urls[f"p{page_number + 1}_{img_index + 1}"] = image_url
                    print("✅ Image uploaded to S3")
                    # Save locally and add to markdown
                    image_path = images_dir / image_filename
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    print("✅ Image saved locally")
                    image_markdown = f"\n![Image {page_number + 1}-{img_index + 1}]({image_url})\n"
                    content_map[page_number + 1]["images"].append(image_markdown)
                    print("✅ Image markdown added to content map")
                except Exception as e:
                    print(f"Failed to process image {image_filename}: {str(e)}")

        # Combine all content in order
        for page_number in sorted(content_map.keys()):
            markdown_content += content_map[page_number]["text"]
            for image_markdown in content_map[page_number]["images"]:
                markdown_content += image_markdown
            for table_markdown in content_map[page_number]["tables"]:
                markdown_content += table_markdown

        # Save markdown locally and to S3
        markdown_filename = f"{Path(original_filename).stem}.md"
        markdown_path = markdown_dir / markdown_filename
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # Upload markdown to S3
        s3_markdown_key = f"pdf_sources/extracted_markdown/{document_id}/{markdown_filename}"
        markdown_url = upload_markdown_to_s3(markdown_content, s3_markdown_key)

        doc.close()

        return {
            'source_type': 'pdf',
            'document_id': document_id,
            'urls': {
                'markdown': markdown_url,
                'images': image_url
            },
            'metadata': {
                'source_type': 'pdf',
                'original_filename': original_filename,
                'processing_date': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'content_type': 'document'
            }
        }

    except Exception as e:
        if 'doc' in locals():
            doc.close()
        raise Exception(f"Failed to process PDF with enterprise method: {str(e)}")