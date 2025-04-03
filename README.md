# PDF Parser Evaluation Workbench

This project provides a Streamlit-based web application designed to evaluate, compare, and analyze the output of various PDF parsing methods. It is particularly useful for understanding how different tools handle complex documents, such as academic papers with mathematical content, tables, and varied layouts.

## Core Features

*   **Multiple Parsing Methods:** Supports several popular PDF parsing libraries and tools:
    *   **PyMuPDF (`fitz`):** Extracts basic text and metadata.
    *   **pdfplumber:** Focuses on layout-aware text extraction and table detection.
    *   **OCR (Tesseract):** Performs Optical Character Recognition on PDF pages, useful for scanned documents or image-based PDFs.
    *   **Nougat:** Utilizes the Nougat model (specifically designed for scientific documents) to generate Markdown/LaTeX output. Requires a local Nougat installation.
    *   **GROBID:** Connects to a GROBID server instance to extract structured TEI XML, metadata, and citations from scholarly articles. Requires a running GROBID server.
*   **Side-by-Side Comparison:** Select up to two parsing methods and view their outputs alongside each other.
*   **Detailed Output Display:** Shows extracted content including:
    *   Raw Text
    *   Markdown/LaTeX (from Nougat)
    *   Structured TEI XML (from GROBID)
    *   Detected Tables (from pdfplumber)
    *   Extracted Metadata (from PyMuPDF, GROBID)
*   **Difference View:** Provides a visual diff (using `difflib`) to highlight differences between the text/markdown outputs of two selected parsers.
*   **Basic Quality Metrics:** Calculates simple metrics on the extracted text:
    *   Character Count
    *   Word Count
    *   Estimated Equation Count (based on `$...$` and `$$...$$` patterns)
    *   Estimated Section Count (based on simple Markdown/numbered list patterns)
*   **Chunking Preview:** Simulates text chunking using LangChain's `RecursiveCharacterTextSplitter` to preview how the extracted text might be prepared for Retrieval-Augmented Generation (RAG) pipelines.
*   **Export Functionality:** Download the output from individual parsers in various formats:
    *   `.txt` (Raw Text)
    *   `.md` (Markdown, primarily from Nougat)
    *   `.xml` (Structured Text, primarily from GROBID)
    *   `.json` (Tables, Metadata)
    *   `.docx` (Basic conversion of primary text/markdown output)

## Technology Stack

This application is built primarily using the following frameworks and libraries:

*   **Streamlit:** The core framework used to create the interactive web application interface. It allows for rapid development of data-centric apps purely in Python, handling the UI components, state management, and overall application flow.
*   **LangChain:** Utilized specifically for the "Chunking Preview" feature. The `RecursiveCharacterTextSplitter` from LangChain demonstrates how extracted text can be prepared for downstream tasks like Retrieval-Augmented Generation (RAG).
*   **Parsing Libraries:** The various PDF parsing tools themselves (PyMuPDF, pdfplumber, pytesseract, Nougat CLI, GROBID API via `requests`) are the subjects of evaluation within the workbench, rather than framework components of the application itself.
*   **Other Libraries:** Standard Python libraries (`os`, `subprocess`, `json`, `difflib`, etc.) and `python-docx` (for DOCX export) are also used.

## Setup & Installation

1.  **Prerequisites:**
    *   Python 3.8 or higher recommended.
    *   Git (for cloning the repository).

2.  **Clone the Repository (Optional):**
    ```bash
    git clone <repository-url>
    cd PDF_Parser 
    ```
    *(Replace `<repository-url>` with the actual URL if applicable)*

3.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate  # Windows
    ```

4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Install External Dependencies (Crucial):**
    This application relies on external tools for some parsing methods. You only need to install the ones you intend to use.

    *   **Tesseract OCR:**
        *   Install Tesseract OCR engine following the official instructions for your operating system: [https://tesseract-ocr.github.io/tessdoc/Installation.html](https://tesseract-ocr.github.io/tessdoc/Installation.html)
        *   Ensure the `tesseract` command is available in your system's PATH.
        *   Install necessary language data packs (e.g., `eng` for English).

    *   **Nougat:**
        *   Follow the official Nougat installation guide: [https://github.com/facebookresearch/nougat](https://github.com/facebookresearch/nougat)
        *   A GPU is highly recommended for reasonable processing times.
        *   Ensure the `nougat` command is executable from the environment where you run the Streamlit app.

    *   **GROBID:**
        *   Set up and run a GROBID instance. Using Docker is often the easiest way: [https://grobid.readthedocs.io/en/latest/Install-Grobid/](https://grobid.readthedocs.io/en/latest/Install-Grobid/)
        *   The application defaults to connecting to `http://localhost:8070`. If your GROBID instance runs elsewhere, you can change the URL in the Streamlit UI.

## Running the Application

1.  Ensure any required external dependencies (Tesseract, Nougat, GROBID) are installed and running if you plan to use those parsers.
2.  Place the PDF files you want to analyze into the `PDF/` directory within the project folder.
3.  Navigate to the project directory in your terminal (where `app.py` is located).
4.  Make sure your virtual environment is activated.
5.  Run the Streamlit application:
    ```bash
    streamlit run app.py
    ```
6.  The application should open in your web browser.

## Usage

1.  The application interface will load in your browser.
2.  Use the sidebar on the left:
    *   **Select PDF File:** Choose a PDF from the dropdown list (populated from the `PDF/` directory).
    *   **Select Parsing Method(s):** Choose one or two methods to run and compare.
    *   **Adjust Parameters:** Configure options like page range, OCR language/DPI, Nougat processing timeout, or the GROBID server URL if needed.
    *   **Execute:** Click the "Parse / Compare" button to start the processing.
3.  The main area will display the results once parsing is complete:
    *   Outputs from selected parsers will be shown side-by-side (if two were selected).
    *   Expand sections to view extracted text, markdown, tables, metadata, etc.
    *   If two parsers were selected, a "Difference View" section will show a comparison diff.
    *   The "Evaluation Tools" section provides quality metrics and a chunking preview.
    *   The "Export Results" section provides download buttons for the outputs of each parser.

## Project Structure

```
PDF_Parser/
├── PDF/                  # Directory to place your input PDF files
├── src/                  # Source code
│   ├── parsers.py        # Implementation of different PDF parsing methods
│   ├── evaluation.py     # Functions for metrics and chunking preview
│   └── utils.py          # Helper functions for export and filename safety
├── app.py                # Main Streamlit application script
├── requirements.txt      # Python dependencies
└── README.md             # This file
