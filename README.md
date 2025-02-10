# **Content Extraction From PDF & Website Application**
This project provides a web-based application for extracting structured data from PDFs and websites using open-source and enterprise solutions. Users can upload PDFs or provide website links, process them through various extraction tools, and receive structured Markdown output.  

The system integrates **PyMuPDF, BeautifulSoup, Azure, Apify, and Docling** to efficiently extract **text, images, and tables**.

---

## **🔹 Project Resources**
- 📘 **Google Codelab:** [Codelab Link](https://codelabs-preview.appspot.com/?file_id=1usAx0qLEXFL69Lre5rC8xEt_LDOmLpTq5wOk0jLJ7Ss#4)  
- 🌐 **App (Streamlit Cloud):** [Streamlit Link](https://dataextractionfrompdfwebsite-jy4he5ukj9eg2g7tfho9dh.streamlit.app/)  
- 🎥 **YouTube Demo:** [Demo Link](https://youtu.be/7x4iwCADyJA)  

---

## **🔹 Technologies**
![Streamlit](https://img.shields.io/badge/-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Amazon S3](https://img.shields.io/badge/-AWS_S3-569A31?style=for-the-badge&logo=amazon-s3&logoColor=white)
![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Azure](https://img.shields.io/badge/-Microsoft%20Azure-0089D6?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![Apify](https://img.shields.io/badge/-Apify-FF9900?style=for-the-badge&logo=apify&logoColor=white)
![Google Cloud](https://img.shields.io/badge/-Google%20Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/-BeautifulSoup-4B8BBE?style=for-the-badge&logo=python&logoColor=white)

---

## **🔹 Architecture Diagram**
<p align="center">
  <img src="https://github.com/Damg7245-BigDataIntelligence/DataExtraction_From_PDF_Website/blob/main/architecture-diagram/pdf_%26_web_content_extraction_architecture.png" 
       alt="Architecture Diagram" width="600">
</p>

---

## **🔹 Project Flow**

### **Step 1: User Selection in Streamlit UI**
- Users select the category for processing **PDF/URL** from the Streamlit UI.
- Available categories: **Open Source, Enterprise, and Docling**.

### **Step 2: Sending Request to FastAPI**
- The selected **PDF/URL** is sent to the backend for extraction via **FastAPI**, based on the chosen category.

### **Step 3: Processing Based on Category**
- **FastAPI routes the request** to the appropriate function for processing:

#### **📌 Open Source**
- **PDF** → Sent to **PyMuPDF** for extraction.
- **URL** → Sent to **BeautifulSoup** for processing.

#### **📌 Enterprise**
- **PDF** → Sent to **Azure** for advanced extraction.
- **URL** → Sent to **Apify Actor** for structured content retrieval.

#### **📌 Docling**
- **PDF** → Processed using **Docling** for structured text and image extraction.
- **URL** → Sent to **Docling’s HTML processor** for structured text and table extraction.

### **Step 4: Storing Processed Data in S3**
- Once processing is complete, **FastAPI stores the extracted data** in **AWS S3**.

### **Step 5: Retrieving Data from S3**
- **FastAPI fetches the processed data** from AWS S3 for display.

### **Step 6: Displaying Output in Streamlit UI**
- **FastAPI sends the retrieved data** back to the **Streamlit UI**.
- The **output consists of extracted content and images** displayed in **Markdown format**.

---

## **🔹 Repository Structure**
<p align="center">
  <img src="https://github.com/Damg7245-BigDataIntelligence/DataExtraction_From_PDF_Website/blob/main/architecture-diagram/input_icons/tree.png" 
       alt="Repository Structure" width="600">
</p>

---

## **🔹 Attestation**
**WE CERTIFY THAT WE HAVE NOT USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND COMPLY WITH THE POLICIES OUTLINED IN THE STUDENT HANDBOOK.**
