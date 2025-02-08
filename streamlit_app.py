import streamlit as st
import requests
import json
from pathlib import Path
from urllib.parse import urlparse
from streamlit.components.v1 import html
import base64
import io
import fitz
# API Configuration
API_BASE_URL = "https://fastapi-service-284663540593.us-central1.run.app"
 
 
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_PROCESSING_TIME = 300  # 5 minutes timeout
ALLOWED_MIME_TYPES = ['application/pdf']
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for streaming
 
def validate_pdf_file(uploaded_file):
    try:
        # Check if file is uploaded
        if uploaded_file is None:
            return False, "No file uploaded"
 
        # Check file size
        if uploaded_file.size > MAX_FILE_SIZE:
            return False, f"File size exceeds {MAX_FILE_SIZE/1024/1024:.0f}MB limit"
 
        # Check file type
        if not uploaded_file.name.lower().endswith('.pdf'):
            return False, "File must be a PDF"
 
        # Check if PDF is readable/not corrupted
        try:
            pdf_buffer = io.BytesIO(uploaded_file.getvalue())
            doc = fitz.open(stream=pdf_buffer, filetype="pdf")
           
            # Basic PDF validation
            if doc.page_count == 0:
                return False, "PDF file appears to be empty"
           
            # Check if PDF is password protected
            if doc.needs_pass:
                return False, "Password-protected PDFs are not supported"
           
            doc.close()
            pdf_buffer.close()
           
        except Exception as e:
            return False, f"Invalid or corrupted PDF file: {str(e)}"
 
        # Reset file pointer
        uploaded_file.seek(0)
        return True, None
 
    except Exception as e:
        return False, f"Error validating file: {str(e)}"
 
 
def process_pdf(file):
    """Send PDF file to API for processing"""
    try:
        files = {"file": file}
        response = requests.post(f"{API_BASE_URL}/process-pdf/", files=files)
        response.raise_for_status()  # Raise exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None
 
def process_website(url, category):
    """Send website URL to API for processing"""
    try:
        payload = {"url": url, "category": category}
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{API_BASE_URL}/process-website/",
            data=json.dumps(payload),
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error processing website: {str(e)}")
        return None
 
st.set_page_config(page_title="PDF & Web Scraper", page_icon="✨", layout="wide")
 
# Add main title
st.title("PDF & Web Scraper")
# Set page configuration
# st.set_page_config(page_title="File Selector", page_icon="✨", layout="wide")
 
# Sidebar Content
st.sidebar.title("Menu")
main_option = st.sidebar.radio(
    "How would you like to scrape?",
    ["Open Source", "Enterprise", "Docling"],
    index=None,
    key="main_option_radio"
)
 
def create_markdown_container(content, height=400):
    """Create a scrollable container that properly renders markdown"""
    # Container and markdown styles
    styles = f"""
        <style>
            .markdown-scroll-container {{
                height: {height}px;
                overflow-y: auto;
                overflow-x: auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
                margin: 10px 0;
                width: 100%;  /* Ensure full width usage */
            }}
            .markdown-content {{
                max-width: 100%;
                margin: 0 auto;
                padding-right: 15px;  /* Add padding for scrollbar */
            }}
            .markdown-content img {{
                height: auto;
                display: block;
                margin: 1em auto;
            }}
            .markdown-content table {{
                width: 100%;
                border-collapse: collapse;
                margin: 1em 0;
            }}
            .markdown-content th, .markdown-content td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            .markdown-content pre {{
                background-color: #f6f8fa;
                padding: 16px;
                overflow-x: auto;
                border-radius: 4px;
            }}
            .markdown-content code {{
                background-color: #f6f8fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: monospace;
            }}
            .markdown-content h1 {{ font-size: 1.8em; margin-top: 0.5em; }}
            .markdown-content h2 {{ font-size: 1.5em; margin-top: 0.5em; }}
            .markdown-content h3 {{ font-size: 1.3em; margin-top: 0.5em; }}
            .markdown-content p {{ margin: 0.5em 0; }}
            .markdown-content ul, .markdown-content ol {{
                margin: 0.5em 0;
                padding-left: 1.5em;
            }}
        </style>
    """
   
    # Create the container with the content
    container_html = f"""
        <div class="markdown-scroll-container">
            <div class="markdown-content">
                {content}
            </div>
        </div>
    """
   
    # Render both styles and container
    st.markdown(styles, unsafe_allow_html=True)
    st.markdown(container_html, unsafe_allow_html=True)
 
def create_image_links_container(image_urls, height=400):
    styles = f"""
        <style>
            .image-scroll-container {{
                height: {height}px;
                overflow-y: auto;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
                margin: 10px 0;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}
            .image-scroll-container a {{
                background: whitesmoke;
                border-radius: 10px;
                height: 20px;
                padding: 10px;
            }}
            /* Custom scrollbar styling */
            .image-scroll-container::-webkit-scrollbar {{
                width: 8px;
                height: 8px;
            }}
            .image-scroll-container::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 4px;
            }}
            .image-scroll-container::-webkit-scrollbar-thumb {{
                background: #888;
                border-radius: 4px;
            }}
            .image-scroll-container::-webkit-scrollbar-thumb:hover {{
                background: #555;
            }}
        </style>
    """
    links_html = "<div class='image-scroll-container'>"
    for i, url in enumerate(image_urls.values(), 1):
        # Extract the direct URL from the set/list if it's not already a string
        image_url = url.pop() if isinstance(url, set) else url
        if isinstance(image_url, (list, set)):
            image_url = next(iter(image_url)) if isinstance(image_url, set) else image_url[0]
        links_html += f"""
            <a href="{image_url}" target="_blank" class="image-link">
                📷 Image {i}
            </a>
        """
    links_html += "</div>"
   
    return styles + links_html
def get_binary_file_downloader_html(bin_data, file_label='File', file_name='file.md'):
    b64 = base64.b64encode(bin_data.encode()).decode()
    custom_css = f"""
        <style>
            .download-button {{
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 14px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 4px;
                float: right;
                width: 150px;
            }}
            .download-button:hover {{
                background-color: #45a049;
            }}
            .button-container {{
                margin: 10px 0;
                text-align: right;
            }}
        </style>
    """
    download_button = f"""
        <div class="button-container">
            <a href="data:file/txt;base64,{b64}" download="{file_name}" class="download-button">
                📥 Download MD
            </a>
        </div>
    """
    return custom_css + download_button
 
def display_processed_content(result):
    """Common function to display markdown and images for both PDF and website results"""
    if "urls" in result["data"] and "markdown" in result["data"]["urls"]:
        md_url = result["data"]["urls"]["markdown"]
        md_response = requests.get(md_url)
       
        if md_response.status_code == 200:
            # Get the markdown content
            md_content = md_response.text
           
            # Generate filename from the URL or use default
            filename = md_url.split('/')[-1] if md_url else 'extracted_content.md'
           
            # Create the download button
            st.markdown(
                get_binary_file_downloader_html(md_content, 'MD', filename),
                unsafe_allow_html=True
            )
           
            if st.session_state.main_option_radio in ["Docling","Enterprise"]:
                st.subheader("Extracted Content")
                create_markdown_container(md_content, height=800)
            else:
                # Create two columns for markdown and images
                md_col, img_col = st.columns([3, 1])
               
                with md_col:
                    st.subheader("Extracted Content")
                    create_markdown_container(md_content, height=800)
 
                with img_col:
                    st.subheader("Extracted Images")
                    if "urls" in result["data"] and "images" in result["data"]["urls"]:
                        image_urls = result["data"]["urls"]["images"]
                        html(create_image_links_container(image_urls, height=800))
 
 
def create_scrollable_container(content, height=400):
    scroll_css = f"""
        <style>
            .scrollable-container {{
                height: {height}px;
                overflow-y: auto;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0;
                background-color: white;
            }}
        </style>
        <div class="scrollable-container">
            {content}
        </div>
    """
    return scroll_css
 
# Main Page Content
if main_option:
    st.subheader(f"You selected: {main_option}")
 
    sub_option = st.radio(
            "How would you like to provide your input?",
            ["Upload a PDF", "Provide a Website Link"],
            index=None,
            key="sub_option_radio"
    )
 
    # Process PDF
    if sub_option == "Upload a PDF":
        uploaded_file = st.file_uploader("Upload your PDF here:", type=["pdf"])
        if uploaded_file is not None:
            is_valid, error_message = validate_pdf_file(uploaded_file)
           
            if not is_valid:
                st.error(error_message)
            elif st.button("Process PDF"):
                with st.spinner('Processing...'):
                    files = {"file": uploaded_file}
                    params = {"category": main_option.lower()}
                    try:
                        response = requests.post(f"{API_BASE_URL}/process-pdf/",
                                            files=files,
                                            params=params)
                        if response.status_code == 200:
                            result = response.json()
                            st.success("PDF processed successfully!")
                            display_processed_content(result)
                    except Exception as e:
                        st.error(f"Error processing PDF: {str(e)}")
    # Process Website
    elif sub_option == "Provide a Website Link":
        col1, col2 = st.columns([3, 1])
 
        with col1:
            website_link = st.text_input(
                label="Website URL",
                placeholder="https://example.com",
                key="website_input",
                help="Enter the complete URL including https://"
            )
 
        def is_valid_url(url):
            try:
                result = urlparse(url)
                return all([result.scheme in ['http', 'https'], result.netloc])
            except:
                return False
       
        # Show button but disable it if URL is invalid
        button_disabled = not is_valid_url(website_link)
       
        if website_link:  # Only show validation message if URL is entered
            if is_valid_url(website_link):
                st.success("Valid URL ✓")
            else:
                st.error("Please enter a valid URL including https://")
       
        if st.button("Process Website", disabled=button_disabled):
            with st.spinner('Processing website...'):
                payload = {"url": website_link, "category": main_option.lower()}
                try:
                    response = requests.post(f"{API_BASE_URL}/process-website/",
                                        json=payload)
                    if response.status_code == 200:
                        result = response.json()
                        st.success("Website processed successfully!")
                        display_processed_content(result)
                except Exception as e:
                    st.error(f"Error processing website: {str(e)}")
                                         
else:
    st.title("Welcome!")
    st.write("Select an option from the menu to extract data from different sources.")
 
# Styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        margin: 10px 0;
    }
    .markdown-container {
        background-color: white;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #ccc;
    }
    .markdown-container h1 { font-size: 1.8em; margin-top: 1em; }
    .markdown-container h2 { font-size: 1.5em; margin-top: 0.8em; }
    .markdown-container h3 { font-size: 1.3em; margin-top: 0.6em; }
    .markdown-container p { margin: 0.5em 0; }
    .markdown-container ul, .markdown-container ol { margin: 0.5em 0; padding-left: 1.5em; }
    .markdown-container table {
        border-collapse: collapse;
        margin: 1em 0;
        width: 100%;
    }
    .markdown-container th, .markdown-container td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    .markdown-container img {
        max-width: 100%;
        height: auto;
    }
    .image-container {
        background-color: white;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #ccc;
    }
    </style>
""", unsafe_allow_html=True)