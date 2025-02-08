from pathlib import Path
import shutil
import os
import uvicorn
from pydantic import BaseModel, HttpUrl
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.utils.pdf_processor_open_source import process_pdf_with_open_source
from backend.utils.web_processor_open_source import scrape_website
from fastapi import Query
from backend.utils.pdf_processor_docling import process_pdf_with_docling
from backend.utils.web_processor_docling import process_html_with_docling
import io
from datetime import datetime
from backend.utils.s3 import upload_to_s3, get_from_s3
import logging
from backend.utils.pdf_processor_enterprise import process_pdf_with_enterprise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from backend.utils.web_processor_enterprise import scrape_website_with_pdf

app = FastAPI()
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WebsiteURL(BaseModel):
    url: HttpUrl
    category: str
    
@app.post("/process-pdf/")
async def process_pdf(
    file: UploadFile = File(...),
    category: str = Query(..., description="Processing category (opensource/docling/enterprise)")
):
    try:
        # Generate unique document ID using original filename and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(file.filename).stem
        document_id = f"{base_name}_{timestamp}"
        
        # Read file content
        file_content = await file.read()
        
        # First, upload the original PDF to S3
        pdf_key = f"pdf_sources/raw/{document_id}/{file.filename}"
        logger.info(f"Uploading original PDF to S3: {pdf_key}")
        
        upload_to_s3(
            file_content, 
            pdf_key, 
            content_type='application/pdf'
        )
        
        logger.info("PDF uploaded successfully, now processing...")
        
        # Get the PDF from S3 for processing
        pdf_content = get_from_s3(pdf_key)
        pdf_buffer = io.BytesIO(pdf_content)
        
        # Process based on category
        if category.lower() == "open source":
            result = process_pdf_with_open_source(pdf_buffer, document_id, file.filename)
        elif category.lower() == "docling":
            result = process_pdf_with_docling(pdf_buffer, document_id, file.filename)
        elif category.lower() == "enterprise":
            result = process_pdf_with_enterprise(pdf_buffer, document_id, file.filename)
        else:
            raise HTTPException(status_code=400, detail="Invalid category: " + category)
        
        return {
            "status": "success",
            "message": f"PDF processed using {category} method",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'pdf_buffer' in locals():
            pdf_buffer.close()

# Process a website URL and extract its content
@app.post("/process-website/")
async def process_website(website: WebsiteURL):
    try:
        if website.category.lower() == "open source":
            result = scrape_website(str(website.url))
        elif website.category.lower() == "docling":
            result = process_html_with_docling(str(website.url))
        elif website.category.lower() == "enterprise":
            result = scrape_website_with_pdf(str(website.url))
        else:
            raise HTTPException(status_code=400, detail="Invalid category")
        
        return {
                "status": "success",
                "message": "Website processed using " + website.category,
                "data": result
        }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
   

@app.get("/test-s3-connection")
async def test_connection():
    from backend.utils.s3 import test_s3_connection
    if test_s3_connection():
        return {"message": "Successfully connected to S3"}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to S3")
    
    
@app.get("/")
async def root():
    return {"message": "PDF Processing API is running"}

# Start the app on the port defined by Cloud Run
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))  # Default to 8080 if PORT is not set
    uvicorn.run(app, host="0.0.0.0", port=port)
 