from pathlib import Path
import io
from docling.document_converter import DocumentConverter
from pydantic import BaseModel
from docling.datamodel.base_models import InputFormat, DocumentStream
from docling_core.types.doc import ImageRefMode
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)
from tempfile import NamedTemporaryFile
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from backend.utils.s3 import upload_markdown_to_s3

from datetime import datetime
import logging

logging.basicConfig(
    filename="output.log",  # File name where logs will be saved
    level=logging.DEBUG,  # Log level (DEBUG logs everything)
    format="%(message)s",  # Only log the message
)
logger = logging.getLogger()


def process_pdf_with_docling(pdf_buffer: io.BytesIO, document_id: str, original_filename: str):
    """Process PDF using Docling and return markdown with embedded images"""
    print("Processing PDF with Docling")
    try:
        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        print("Pipeline options set")

        # Initialize DocumentConverter
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend
                )
            }
        )
        print("Document converter initialized")

        # Get base name for file naming
        base_name = Path(original_filename).stem
        
        # Process the PDF directly from buffer
        pdf_buffer.seek(0)
        doc_stream = DocumentStream(
            name=f"{base_name}.pdf",
            stream=pdf_buffer,
            format=InputFormat.PDF
        )
        print("Document stream created")

        # Convert document
        conv_result = doc_converter.convert(doc_stream)
        print("Conversion completed")

        # Export to markdown with embedded images
        markdown_content = conv_result.document.export_to_markdown(
            image_mode=ImageRefMode.EMBEDDED
        )
        print("Markdown content generated")

        # Upload markdown to S3
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        markdown_key = f"pdf_sources/extracted_markdown/{document_id}/{base_name}_{timestamp}.md"
        markdown_url = upload_markdown_to_s3(markdown_content, markdown_key)
        print("Markdown uploaded to S3")

        return {
            'source_type': 'pdf',
            'document_id': document_id,
            'urls': {
                'markdown': markdown_url
            },
            'metadata': {
                'source_type': 'pdf',
                'original_filename': original_filename,
                'processing_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'content_type': 'document',
                'processor': 'docling'
            }
        }

    except Exception as e:
        print(f"Error in Docling processing: {str(e)}")
        raise Exception(f"Failed to process PDF with Docling: {str(e)}")