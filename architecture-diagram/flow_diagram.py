from diagrams import Diagram, Cluster
from diagrams.programming.language import Python
from diagrams.onprem.client import Users
from diagrams.gcp.compute import Run
from diagrams.aws.storage import S3
from diagrams.custom import Custom

# Set diagram formatting
graph_attr = {
    "fontsize": "24",
    "bgcolor": "white",
    "splines": "ortho",
}

# Base path for images (Updated to your absolute path)
base_path = r"C:/Users/Ketki/OneDrive/Desktop/NEU/Big_data_7245/Lab01/architecture-diagram/input_icons"

# Create the diagram
with Diagram("PDF & Web Content Extraction Architecture", show=False, graph_attr=graph_attr, direction="TB"):
   
    # User/Client
    user = Users("End User")
   
    # Frontend Cluster
    with Cluster("Frontend"):
        streamlit = Custom("Streamlit UI", f"{base_path}/streamlit.png")
   
    # Cloud Infrastructure Cluster
    with Cluster("GCP"):
        # GCP Cloud Run hosting the FastAPI backend
        cloud_run = Run("Cloud Run")

        with Cluster("Backend"):
            fastapi = Custom("FastAPI", f"{base_path}/FastAPI.png")
           
            # Processing Options Cluster
            with Cluster("Processing Services"):
                # Open Source Stack
                with Cluster("Open Source"):
                    pymupdf = Custom("PyMuPDF", f"{base_path}/pymupdf.png")
                    beautifulsoup = Custom("BeautifulSoup", f"{base_path}/beautifulsoup.png")
               
                # Enterprise Stack
                with Cluster("Enterprise"):
                    azure = Custom("Azure PDF Services", f"{base_path}/azure.png")
                    apify = Custom("Apify", f"{base_path}/apify.png")
               
                # Docling Stack
                with Cluster("Docling"):
                    docling = Custom("Docling", f"{base_path}/docling.png")

    # Storage
    s3_storage = S3("AWS S3\nStorage")
 
    # Define the flow
    user >> streamlit >> cloud_run >> fastapi
    
    # Processing flows
    with Cluster("Processing Flows"):
        # Open Source flow
        fastapi >> pymupdf
        fastapi >> beautifulsoup

        # Enterprise flow
        fastapi >> azure
        fastapi >> apify

        # Docling flow
        fastapi >> docling

    # Single arrow from Processing Services to S3
    [pymupdf, beautifulsoup, azure, apify, docling] >> s3_storage

    # Return flow
    s3_storage >> fastapi >> cloud_run >> streamlit
