import fitz
import shutil
from pathlib import Path
from datetime import datetime
from backend.utils.s3 import upload_image_to_s3, upload_markdown_to_s3
import io

def process_pdf_with_open_source(pdf_buffer: io.BytesIO, document_id: str, original_filename: str):
    print("Processing PDF with open source")
    try:
        doc = fitz.open(stream=pdf_buffer, filetype="pdf")
        base_name = Path(original_filename).stem
        
        markdown_content = []
        image_urls = {}
        tables_found = 0
        
        # Process the PDF
        for page_num, page in enumerate(doc):
            # Extract tables first
            tables = page.find_tables()
            table_areas = []  # Store table areas for text exclusion
            
            if tables and tables.tables:
                tables_found += len(tables.tables)
                for table in tables.tables:
                    cells = table.extract()
                    if cells:
                        header = cells[0]
                        markdown_content.append('\n| ' + ' | '.join(str(cell) for cell in header) + ' |')
                        markdown_content.append('| ' + ' | '.join(['---' for _ in header]) + ' |')
                        for row in cells[1:]:
                            markdown_content.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')
                        markdown_content.append('\n')
                    
                    # Store table area
                    table_areas.append(table.bbox)  # Use bbox instead of rect
            
            # Extract images
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                image_filename = f"image_p{page_num + 1}_{img_index + 1}.{image_ext}"
                s3_image_key = f"pdf_sources/extracted_images/{document_id}/{image_filename}"
                
                try:
                    image_url = upload_image_to_s3(image_bytes, s3_image_key, image_ext)
                    image_urls[f"p{page_num + 1}_{img_index + 1}"] = image_url
                    markdown_content.append(f"\n![Image {page_num + 1}-{img_index + 1}]({image_url})\n")
                    
                except Exception as e:
                    print(f"Failed to upload image {image_filename}: {str(e)}")
                    continue
            
            # Extract text
            text_blocks = page.get_text("blocks")
            for block in text_blocks:
                # Check if block overlaps with any table
                is_in_table = False
                for table_bbox in table_areas:
                    # Check if the block intersects with table area
                    block_rect = fitz.Rect(block[:4])
                    if block_rect.intersects(table_bbox):
                        is_in_table = True
                        break
                
                if not is_in_table:
                    markdown_content.append(block[4] + "\n\n")
            
            markdown_content.append("\n---\n")
        
        # Close the PDF before copying
        doc.close()
        
        # Upload markdown content with proper path
        markdown_filename = f"{base_name}.md"
        markdown_key = f"pdf_sources/extracted_markdown/{document_id}/{markdown_filename}"
        markdown_content_str = "\n".join(markdown_content)
        
        # Use the existing upload_markdown_to_s3 function
        markdown_url = upload_markdown_to_s3(markdown_content_str, markdown_key)

        return {
            'source_type': 'pdf',
            'document_id': document_id,
            'urls':{
                'markdown': markdown_url,
                'images': image_urls
            },
            'metadata': {
                'source_type': 'pdf',
                'original_filename': original_filename,
                'content_type': 'document',
                'image_count': len(image_urls),
                'tables_found': tables_found
            }
        }
        
    except Exception as e:
        # Make sure to close the document even if an error occurs
        if 'doc' in locals():
            doc.close()
        raise Exception(f"Failed to process PDF: {str(e)}")