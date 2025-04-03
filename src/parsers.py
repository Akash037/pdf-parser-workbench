import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io
import subprocess
import os
import time
import torch  # Required for Nougat GPU/CPU detection

# --- Configuration ---
# Add any necessary configurations, e.g., Tesseract path if not in PATH
# TESSERACT_CMD = '/usr/bin/tesseract' # Example for Linux, adjust if needed
# pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# --- Caching ---
# Cache parsing results to avoid re-computation
# Use @st.cache_data for functions returning data like text, dicts, etc.

# --- Parser Implementations ---

@st.cache_data
def parse_pymupdf(pdf_path, page_range=None):
    """Parses PDF using PyMuPDF (fitz) for basic text and metadata."""
    result = {'text': "", 'metadata': {}, 'error': None}
    try:
        doc = fitz.open(pdf_path)
        result['metadata'] = doc.metadata
        
        pages_to_process = range(doc.page_count)
        if page_range:
             # Assuming page_range is a tuple (start_page, end_page), 1-based index
             start = max(0, page_range[0] - 1)
             end = min(doc.page_count, page_range[1])
             pages_to_process = range(start, end)

        full_text = []
        for page_num in pages_to_process:
            page = doc.load_page(page_num)
            full_text.append(page.get_text("text"))
            
        result['text'] = "\n".join(full_text)
        doc.close()
    except Exception as e:
        result['error'] = f"PyMuPDF Error: {e}"
    return result

@st.cache_data
def parse_pdfplumber(pdf_path, page_range=None):
    """Parses PDF using pdfplumber, focusing on layout and tables."""
    result = {'text': "", 'tables': [], 'error': None}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_process = pdf.pages
            if page_range:
                # pdfplumber uses 0-based index, page_range is 1-based
                start = max(0, page_range[0] - 1)
                end = min(len(pdf.pages), page_range[1])
                if start >= end:
                     result['error'] = f"Invalid page range: {page_range}. Start page must be less than end page."
                     return result
                pages_to_process = pdf.pages[start:end]
            
            full_text = []
            all_tables = []
            for i, page in enumerate(pages_to_process):
                page_num_actual = page.page_number # Get actual page number (1-based)
                # Extract text
                text = page.extract_text(x_tolerance=3, y_tolerance=3) # Adjust tolerance as needed
                if text:
                    full_text.append(text)
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    # Add page number info to tables for context
                    all_tables.extend([{"page": page_num_actual, "table_index": t_idx, "data": table} for t_idx, table in enumerate(tables)])

            result['text'] = "\n---\n".join(full_text) # Use a separator for clarity between pages
            result['tables'] = all_tables
            
    except Exception as e:
        # Check for the specific pdfminer.six incompatibility error if it occurs
        if "pdfminer.six" in str(e) and "20250327" in str(e):
             result['error'] = f"pdfplumber Error: Potential incompatibility with installed pdfminer.six version. Details: {e}"
        else:
            result['error'] = f"pdfplumber Error: {e}"
    return result

@st.cache_data
def parse_ocr(pdf_path, lang='eng', page_range=None, dpi=300):
    """Parses PDF using an OCR workflow (PyMuPDF render + Tesseract)."""
    result = {'text': "", 'error': None}
    full_text = []
    try:
        doc = fitz.open(pdf_path)
        pages_to_process = range(doc.page_count)
        if page_range:
             # Assuming page_range is a tuple (start_page, end_page), 1-based index
             start = max(0, page_range[0] - 1)
             end = min(doc.page_count, page_range[1])
             if start >= end:
                 result['error'] = f"Invalid page range: {page_range}. Start page must be less than end page."
                 doc.close()
                 return result
             pages_to_process = range(start, end)

        for page_num in pages_to_process:
            page = doc.load_page(page_num)
            # Render page to an image (pixmap)
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png") # Convert pixmap to PNG bytes
            img = Image.open(io.BytesIO(img_bytes))

            # Perform OCR using pytesseract
            try:
                page_text = pytesseract.image_to_string(img, lang=lang)
                full_text.append(page_text)
            except pytesseract.TesseractNotFoundError:
                result['error'] = "Tesseract Error: Executable not found. Please ensure Tesseract is installed and in your PATH or configure the path in parsers.py."
                doc.close()
                return result
            except Exception as ocr_err:
                 # Log specific page error but continue if possible
                 st.warning(f"OCR Error on page {page_num + 1}: {ocr_err}")
                 full_text.append(f"[OCR Error on page {page_num + 1}]")


        result['text'] = "\n\n--- Page Break ---\n\n".join(full_text) # Add clear page separators
        doc.close()
    except Exception as e:
        result['error'] = f"OCR Workflow Error: {e}"
        # Ensure doc is closed if it was opened
        if 'doc' in locals() and doc.is_open:
            doc.close()
    return result

@st.cache_data(show_spinner=False)  # We'll handle progress manually
def parse_nougat(pdf_path, page_range=None, timeout=1800, _progress_callback=None):
    """Parses PDF using local Nougat installation.
    
    Args:
        pdf_path: Path to PDF file
        page_range: Optional tuple (start_page, end_page)
        timeout: Processing timeout in seconds (default 30 mins)
        _progress_callback: Function to call with progress updates (underscore prevents hashing)
    """
    result = {'markdown': "", 'latex': "", 'error': None}
    
    # Create a temporary directory for Nougat output
    output_dir = f"temp_nougat_output_{int(time.time())}"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Suppress Albumentations update warnings
        os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
        
        # Get total pages for progress tracking
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        if page_range:
            total_pages = min(page_range[1], total_pages) - max(1, page_range[0]) + 1
        doc.close()

        # Nougat automatically uses GPU if available
        gpu_available = torch.cuda.is_available()
        if _progress_callback:
            _progress_callback(0, f"Starting processing ({'GPU' if gpu_available else 'CPU'} mode)")

        # Construct the nougat command
        command = [
            "nougat", 
            pdf_path, 
            "-o", output_dir,
            "--no-skipping"
        ]
        
        # Execute the command with timeout
        start_time = time.time()
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Monitor progress
            while True:
                if _progress_callback:
                    elapsed = time.time() - start_time
                    progress = min(0.9, elapsed / timeout)  # Cap at 90% until done
                    _progress_callback(progress, f"Processing page {int(progress * total_pages)}/{total_pages}")

                if time.time() - start_time > timeout:
                    process.kill()
                    raise subprocess.TimeoutExpired(command, timeout)

                if process.poll() is not None:
                    break
                time.sleep(1)

            # Check return code
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)
        except subprocess.TimeoutExpired:
            result['error'] = "Nougat Error: Processing timed out after 10 minutes"
            return result
        
        # Find and process output file
        output_filename_base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_mmd_path = os.path.join(output_dir, f"{output_filename_base}.mmd")

        if os.path.exists(output_mmd_path):
            with open(output_mmd_path, 'r', encoding='utf-8') as f:
                result['markdown'] = f.read()
            
            # Extract LaTeX blocks
            latex_blocks = []
            in_latex = False
            current_block = []
            
            for line in result['markdown'].split('\n'):
                if line.strip().startswith('$$'):
                    if in_latex:
                        latex_blocks.append('\n'.join(current_block))
                        current_block = []
                        in_latex = False
                    else:
                        in_latex = True
                elif in_latex:
                    current_block.append(line)
            
            result['latex_blocks'] = latex_blocks
            result['latex_equations_count'] = len(latex_blocks)
            
        else:
            result['error'] = f"Nougat Error: Output file '{output_mmd_path}' not found.\n"
            if process.stderr:
                result['error'] += f"Error details:\n{process.stderr[:1000]}"  # Limit error message length

    except FileNotFoundError:
         result['error'] = "Nougat Error: 'nougat' command not found. Is Nougat installed and in your PATH?"
    except subprocess.CalledProcessError as e:
        result['error'] = f"Nougat Error: Process failed with exit code {e.returncode}.\nStdout: {e.stdout}\nStderr: {e.stderr}"
    except Exception as e:
        result['error'] = f"Nougat Error: An unexpected error occurred: {e}"
    finally:
        # Clean up the temporary output directory
        try:
            if os.path.exists(output_dir):
                # Basic cleanup, might need shutil.rmtree for non-empty dirs
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                os.rmdir(output_dir)
        except Exception as cleanup_err:
            st.warning(f"Could not clean up Nougat temp directory '{output_dir}': {cleanup_err}")
            
    return result

# Need requests library for GROBID API call
import requests 

@st.cache_data(show_spinner="Processing with GROBID...") # Add spinner
def parse_grobid(pdf_path, grobid_url="http://localhost:8070"):
    """Parses PDF using a local GROBID instance API."""
    result = {'metadata': {}, 'structured_text': "", 'error': None} # GROBID focuses on structure/metadata
    grobid_api_url = f"{grobid_url}/api/processFulltextDocument"
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'input': f}
            # Add parameters if needed, e.g., consolidate headers, include raw citations, etc.
            # data = {'consolidateHeader': '1'} 
            # response = requests.post(grobid_api_url, files=files, data=data, timeout=60) # Example with data
            response = requests.post(grobid_api_url, files=files, timeout=120) # Increased timeout for potentially large docs

        if response.status_code == 200:
            result['structured_text'] = response.text # TEI XML output
            # Basic metadata extraction could be added here by parsing the XML,
            # but for now, we return the full structured text.
            # Example: Extract title using regex or a lightweight XML parser if needed quickly
        else:
            result['error'] = f"GROBID Error: API request failed with status {response.status_code}. Response: {response.text[:500]}..." # Show partial response

    except requests.exceptions.ConnectionError:
        result['error'] = f"GROBID Error: Could not connect to GROBID instance at {grobid_api_url}. Is it running?"
    except requests.exceptions.Timeout:
         result['error'] = f"GROBID Error: Request timed out after 120 seconds."
    except Exception as e:
        result['error'] = f"GROBID Error: An unexpected error occurred: {e}"
        
    return result

# --- Main Function (for testing if needed) ---
if __name__ == '__main__':
    # Example usage (replace with an actual PDF path for testing)
    # test_pdf = "../PDF/example.pdf"
    # if os.path.exists(test_pdf):
    #     print("--- Testing PyMuPDF ---")
    #     pymupdf_result = parse_pymupdf(test_pdf)
    #     print(pymupdf_result)
    # else:
    #     print(f"Test PDF not found at {test_pdf}")
    print("Parser module created. Implement remaining parsers.")
