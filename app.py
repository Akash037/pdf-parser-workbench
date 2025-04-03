import streamlit as st
import os
# from streamlit_pdf_viewer import pdf_viewer # Removed import
import base64
import json # For displaying metadata/tables nicely
import difflib # For diff view
import streamlit.components.v1 as components # For rendering HTML diff

# --- Import Parsers & Evaluation & Utils ---
# Ensure src directory is in path or use relative import if structure allows
try:
    from src.parsers import (
        parse_pymupdf,
        parse_pdfplumber,
        parse_ocr,
        parse_nougat,
        parse_grobid
    )
    from src.evaluation import calculate_metrics, get_chunking_preview # Import metrics & chunking
    # Import export functions
    from src.utils import (
        export_text, 
        export_markdown, 
        export_xml, 
        export_json, 
        export_docx, 
        get_safe_filename
    ) 
except ImportError as e:
    st.error(f"Error importing modules: {e}. Make sure src/parsers.py, src/evaluation.py and src/utils.py exist.")
    # Add dummy functions to prevent app crash if import fails
    def parse_pymupdf(*args, **kwargs): return {'error': 'Parser not loaded'}
    def parse_pdfplumber(*args, **kwargs): return {'error': 'Parser not loaded'}
    def parse_ocr(*args, **kwargs): return {'error': 'Parser not loaded'}
    def parse_nougat(*args, **kwargs): return {'error': 'Parser not loaded'}
    def parse_grobid(*args, **kwargs): return {'error': 'Parser not loaded'}
    def calculate_metrics(*args, **kwargs): return {'error': 'Metrics not loaded'}
    def get_chunking_preview(*args, **kwargs): return {'error': 'Chunking not loaded'}
    # Dummy export functions
    def export_text(*args, **kwargs): return None
    def export_markdown(*args, **kwargs): return None
    def export_xml(*args, **kwargs): return None
    def export_json(*args, **kwargs): return None
    def export_docx(*args, **kwargs): return None
    def get_safe_filename(name): return "error"


# --- Configuration ---
PDF_DIR = "PDF"
PARSER_OPTIONS = {
    "PyMuPDF": parse_pymupdf,
    "pdfplumber": parse_pdfplumber,
    "OCR (Tesseract)": parse_ocr,
    "Nougat": parse_nougat,
    "GROBID": parse_grobid,
}

# --- Helper Functions ---
def get_pdf_files(directory):
    """Scans the specified directory for PDF files."""
    pdf_files = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.lower().endswith(".pdf"):
                pdf_files.append(filename)
    return sorted(pdf_files)

# Removed load_and_encode_pdf and display_pdf functions

# --- Streamlit App Layout ---
st.set_page_config(layout="wide", page_title="PDF Parser Evaluation Workbench")

st.title("📄 PDF Parser Evaluation Workbench")
st.markdown("""
    Select a PDF file and choose parsing methods to evaluate and compare their outputs,
    especially for academic papers with complex layouts and mathematical content.
""")

# --- Sidebar for Controls ---
with st.sidebar:
    st.header("Controls")

    # PDF File Selection
    st.subheader("1. Select PDF File")
    pdf_files = get_pdf_files(PDF_DIR)
    if not pdf_files:
        st.warning(f"No PDF files found in the '{PDF_DIR}/' directory. Please add some PDFs.")
        selected_pdf_file = None
    else:
        selected_pdf_file = st.selectbox("Choose a PDF:", pdf_files, index=None, key="pdf_select", placeholder="Select a PDF...") # Use index=None and placeholder

    if selected_pdf_file:
        selected_pdf_path = os.path.join(PDF_DIR, selected_pdf_file)
        st.success(f"Selected: {selected_pdf_file}")
    else:
        selected_pdf_path = None

    # Parser Selection
    st.subheader("2. Select Parsing Method(s)")
    selected_parser_names = st.multiselect(
        "Choose one or two methods:",
        options=list(PARSER_OPTIONS.keys()),
        max_selections=2,
        key="parser_select"
    )

    # Parameters (Conditional)
    st.subheader("3. Adjust Parameters")
    
    # Nougat Specific Parameters
    nougat_timeout = 1800  # Default 30 minutes
    if "Nougat" in selected_parser_names:
        with st.expander("Nougat Parameters"):
            nougat_timeout = st.slider(
                "Timeout (minutes)",
                min_value=1,
                max_value=60,
                value=30,
                step=1,
                key="nougat_timeout"
            ) * 60  # Convert to seconds
    
    # Page Range (Apply to all parsers that support it)
    parse_all_pages = st.checkbox("Parse all pages", value=True, key="all_pages")
    page_range = None # Initialize page_range
    if not parse_all_pages:
        col_start, col_end = st.columns(2)
        with col_start:
            start_page = st.number_input("Start Page", min_value=1, value=1, step=1, key="start_page")
        with col_end:
            # We don't know the total pages yet, user needs to be careful
            end_page = st.number_input("End Page", min_value=start_page, value=max(1, start_page), step=1, key="end_page") # Ensure end >= start
        page_range = (start_page, end_page)
        # No warning needed here as min_value handles it

    # OCR Specific Parameters
    ocr_lang = 'eng'
    ocr_dpi = 300
    if "OCR (Tesseract)" in selected_parser_names:
        with st.expander("OCR Parameters"):
            ocr_lang = st.text_input("Language(s) (e.g., 'eng', 'eng+fra')", value='eng', key="ocr_lang")
            ocr_dpi = st.slider("Image DPI for OCR", min_value=150, max_value=600, value=300, step=50, key="ocr_dpi")

    # GROBID Specific Parameters
    grobid_url = "http://localhost:8070"
    if "GROBID" in selected_parser_names:
         with st.expander("GROBID Parameters"):
              grobid_url = st.text_input("GROBID Server URL", value="http://localhost:8070", key="grobid_url")

    # Parse Button
    st.subheader("4. Execute")
    parse_button = st.button(
        "Parse / Compare", 
        disabled=not selected_pdf_file or not selected_parser_names, 
        key="parse_button",
        type="primary" # Make button more prominent
    )

# --- Initialize results_data in session state ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = {}

# --- Main Area for Display ---
if selected_pdf_path:
    # Removed PDF viewer section
    # st.header(f"Original PDF: {selected_pdf_file}")
    # with st.expander("View Original PDF", expanded=False): 
    #     display_pdf(selected_pdf_path)

    # st.divider() # Keep divider or remove based on desired spacing
    st.header("Parsing Results") # Start directly with results

    # --- Parsing Execution Logic ---
    if parse_button: # Only parse when button is clicked
        if selected_pdf_path and selected_parser_names:
            with st.spinner(f"Parsing '{selected_pdf_file}'..."): # Use spinner for feedback
                
                common_params = {'pdf_path': selected_pdf_path, 'page_range': page_range}
                current_results = {} # Store results for this run

                # Progress bar setup
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(progress, message):
                    progress_bar.progress(progress)
                    status_text.text(message)
                
                for parser_name in selected_parser_names:
                    parser_func = PARSER_OPTIONS[parser_name]
                    params = common_params.copy()
                    
                    # Add specific params
                    if parser_name == "OCR (Tesseract)":
                        params['lang'] = ocr_lang
                        params['dpi'] = ocr_dpi
                    elif parser_name == "GROBID":
                         params['grobid_url'] = grobid_url
                         # GROBID typically processes the whole document, ignore page_range for it
                         if 'page_range' in params: del params['page_range'] 
                    elif parser_name == "Nougat":
                         params['timeout'] = nougat_timeout
                         params['_progress_callback'] = update_progress

                    # Call the parser function
                    try:
                        current_results[parser_name] = parser_func(**params)
                        
                        # If Nougat failed but OCR is available, try fallback
                        if (parser_name == "Nougat" and 
                            current_results[parser_name].get('error') and 
                            "OCR (Tesseract)" in PARSER_OPTIONS):
                            status_text.text("Nougat failed, attempting OCR fallback...")
                            ocr_params = common_params.copy()
                            ocr_params['lang'] = ocr_lang
                            ocr_params['dpi'] = ocr_dpi
                            current_results["OCR Fallback"] = parse_ocr(**ocr_params)
                            
                    except Exception as e:
                        # Catch any unexpected error during the call itself
                        current_results[parser_name] = {'error': f"Failed to execute parser '{parser_name}': {e}"}
                
                # Clear progress UI when done
                progress_bar.empty()
                status_text.empty()
                
                # Store results in session state
                st.session_state.results_data = current_results 
                st.success("Parsing complete!")
                # Rerun to update display with new session state data
                st.rerun() 
        else:
             # This case should ideally not be reached due to button disable logic, but added for safety
             st.warning("Please select a PDF file and at least one parser.")

    # --- Display Logic (uses session state) ---
    if st.session_state.results_data:
        results_data = st.session_state.results_data
        parser_names = list(results_data.keys())

        def display_parser_output(parser_name, data):
            """Helper function to display results for a single parser."""
            st.subheader(f"Output: {parser_name}")
            if data.get('error'):
                st.error(f"Error: {data['error']}")
                return # Stop display for this parser if error occurred

            # Display different types of content based on what the parser returned
            if 'text' in data and data['text']:
                with st.expander("Extracted Text", expanded=True):
                    st.text_area("Text", data['text'], height=300, key=f"text_{parser_name}")
            if 'markdown' in data and data['markdown']:
                 with st.expander("Extracted Markdown/LaTeX", expanded=True):
                    st.markdown(data['markdown'], unsafe_allow_html=True) # Render markdown
                    st.text_area("Raw Markdown", data['markdown'], height=300, key=f"md_{parser_name}")
            if 'structured_text' in data and data['structured_text']: # e.g., GROBID XML
                 with st.expander("Structured Text (e.g., TEI XML)", expanded=True):
                     st.code(data['structured_text'], language='xml', line_numbers=True)
            if 'tables' in data and data['tables']:
                 with st.expander(f"Extracted Tables ({len(data['tables'])})"):
                     for i, table_info in enumerate(data['tables']):
                          st.write(f"Table {i+1} (Page {table_info.get('page', 'N/A')})")
                          # Try displaying as dataframe, fallback to raw list
                          try:
                               st.dataframe(table_info['data'])
                          except:
                               st.json(table_info['data'])
            if 'metadata' in data and data['metadata']:
                 with st.expander("Extracted Metadata"):
                     st.json(data['metadata'])

            # --- Calculate and Display Metrics ---
            primary_text = data.get('markdown', data.get('text', data.get('structured_text', '')))
            if primary_text:
                 with st.expander("Quality Metrics"):
                      metrics = calculate_metrics(primary_text)
                      if metrics.get('error'):
                           st.warning(f"Could not calculate metrics: {metrics['error']}")
                      else:
                           m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                           with m_col1:
                                st.metric("Characters", f"{metrics.get('char_count', 0):,}")
                           with m_col2:
                                st.metric("Words", f"{metrics.get('word_count', 0):,}")
                           with m_col3:
                                st.metric("Est. Equations", metrics.get('estimated_equation_count', 0))
                           with m_col4:
                                st.metric("Est. Sections", metrics.get('estimated_section_count', 0))


        # Display results based on number of parsers selected
        if len(parser_names) == 1:
            parser_name = parser_names[0]
            display_parser_output(parser_name, results_data[parser_name])
        elif len(parser_names) == 2:
            col1, col2 = st.columns(2)
            with col1:
                display_parser_output(parser_names[0], results_data[parser_names[0]])
            with col2:
                display_parser_output(parser_names[1], results_data[parser_names[1]])

            # --- Diff View ---
            st.divider()
            st.subheader("Difference View (Text Comparison)")
            
            # Get primary text output (prefer markdown, then text)
            text1 = results_data[parser_names[0]].get('markdown', results_data[parser_names[0]].get('text', ''))
            text2 = results_data[parser_names[1]].get('markdown', results_data[parser_names[1]].get('text', ''))
            
            if not text1 and not text2:
                 st.warning("No text output found for comparison.")
            elif results_data[parser_names[0]].get('error') or results_data[parser_names[1]].get('error'):
                 st.warning("Cannot generate diff due to parser errors.")
            else:
                # Generate HTML diff
                d = difflib.HtmlDiff(wrapcolumn=80)
                diff_html = d.make_table(text1.splitlines(), text2.splitlines(), 
                                         fromdesc=parser_names[0], todesc=parser_names[1])
                
                # Display HTML diff in Streamlit
                with st.expander("Show Differences", expanded=True):
                     components.html(diff_html, height=600, scrolling=True)

        # --- Evaluation Tools Section --- 
        st.divider()
        st.header("Evaluation Tools")

        # --- Chunking Preview ---
        st.subheader("Chunking Preview")
        
        # Select which parser's output to chunk (if multiple results)
        chunk_source_parser = parser_names[0] # Default to first parser
        if len(parser_names) > 1:
             chunk_source_parser = st.radio("Select parser output to chunk:", parser_names, index=0, key="chunk_source")
        
        source_data = results_data.get(chunk_source_parser, {})
        source_text = source_data.get('markdown', source_data.get('text', source_data.get('structured_text', '')))

        if not source_text or source_data.get('error'):
             st.warning(f"No valid text content found for '{chunk_source_parser}' to chunk.")
        else:
            # Chunking parameters
            chunk_strategy = st.selectbox("Chunking Strategy", ["recursive"], key="chunk_strategy") # Add more later if needed
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                 chunk_size = st.number_input("Chunk Size", min_value=50, max_value=5000, value=1000, step=50, key="chunk_size")
            with c_col2:
                 chunk_overlap = st.number_input("Chunk Overlap", min_value=0, max_value=1000, value=100, step=10, key="chunk_overlap")

            # Get and display chunking preview
            chunk_preview_data = get_chunking_preview(source_text, chunk_strategy, chunk_size, chunk_overlap)
            
            if chunk_preview_data.get('error'):
                 st.error(f"Chunking Error: {chunk_preview_data['error']}")
            else:
                 st.success(f"Total Chunks Estimated: {chunk_preview_data.get('total_chunks', 0)}")
                 st.write("Preview of first few chunks:")
                 for i, chunk in enumerate(chunk_preview_data.get('chunks', [])):
                      st.text_area(f"Chunk {i+1}", chunk, height=100, key=f"chunk_preview_{i}")
    
        # --- Export Results Section --- 
        st.divider()
        st.header("Export Results")
        export_cols = st.columns(len(parser_names) if len(parser_names) > 0 else 1)

        for i, parser_name in enumerate(parser_names):
             with export_cols[i % len(export_cols)]: # Cycle through columns if more parsers than columns (though max 2 here)
                  st.subheader(f"Export: {parser_name}")
                  data_to_export = results_data[parser_name]
                  
                  if data_to_export.get('error'):
                       st.warning("Cannot export due to parser error.")
                       continue # Skip export for this parser

                  base_filename = get_safe_filename(f"{os.path.splitext(selected_pdf_file)[0]}_{parser_name}")

                  # Export Text
                  if 'text' in data_to_export and data_to_export['text']:
                       txt_bytes = export_text(data_to_export['text'])
                       if txt_bytes:
                            st.download_button(
                                 label="Download Text (.txt)",
                                 data=txt_bytes,
                                 file_name=f"{base_filename}_text.txt",
                                 mime="text/plain",
                                 key=f"export_txt_{parser_name}"
                            )
                  # Export Markdown
                  if 'markdown' in data_to_export and data_to_export['markdown']:
                       md_bytes = export_markdown(data_to_export['markdown'])
                       if md_bytes:
                            st.download_button(
                                 label="Download Markdown (.md)",
                                 data=md_bytes,
                                 file_name=f"{base_filename}_markdown.md",
                                 mime="text/markdown",
                                 key=f"export_md_{parser_name}"
                            )
                  # Export Structured Text (XML for GROBID)
                  if 'structured_text' in data_to_export and data_to_export['structured_text']:
                       xml_bytes = export_xml(data_to_export['structured_text'])
                       if xml_bytes:
                            st.download_button(
                                 label="Download Structured Text (.xml)",
                                 data=xml_bytes,
                                 file_name=f"{base_filename}_structured.xml",
                                 mime="application/xml",
                                 key=f"export_xml_{parser_name}"
                            )
                  # Export Metadata
                  if 'metadata' in data_to_export and data_to_export['metadata']:
                       json_bytes = export_json(data_to_export['metadata'])
                       if json_bytes:
                            st.download_button(
                                 label="Download Metadata (.json)",
                                 data=json_bytes,
                                 file_name=f"{base_filename}_metadata.json",
                                 mime="application/json",
                                 key=f"export_meta_{parser_name}"
                            )
                  # Export Tables (as JSON)
                  if 'tables' in data_to_export and data_to_export['tables']:
                       json_bytes = export_json(data_to_export['tables'])
                       if json_bytes:
                            st.download_button(
                                 label="Download Tables (.json)",
                                 data=json_bytes,
                                 file_name=f"{base_filename}_tables.json",
                                 mime="application/json",
                                 key=f"export_tables_{parser_name}"
                            )
                  # Export DOCX (using primary text/markdown)
                  primary_text_for_docx = data_to_export.get('markdown', data_to_export.get('text', ''))
                  if primary_text_for_docx:
                       docx_bytes = export_docx(primary_text_for_docx) 
                       if docx_bytes: # Check if export was successful
                            st.download_button(
                                 label="Download DOCX (.docx)",
                                 data=docx_bytes,
                                 file_name=f"{base_filename}.docx",
                                 mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                 key=f"export_docx_{parser_name}",
                                 # disabled=False # Enable the button
                            )
                       # else: # Error message is handled within export_docx
                       #      pass 

    # --- Fallback Messages --- # Corrected indentation for this block
    elif not parse_button: # Show initial message if button hasn't been pressed yet (and PDF is selected)
         if not selected_parser_names:
              st.info("Please select one or two parsing methods from the sidebar.")
         else: # PDF selected, parsers selected, but button not pressed
              st.info("Click 'Parse / Compare' in the sidebar to begin.")
    # else: # Handles cases where results_data is empty after button press (already handled inside if parse_button)
    #    pass 

elif not selected_pdf_file: # No PDF selected (Corrected indentation)
    st.info(f"Please add PDF files to the '{PDF_DIR}/' directory and select one from the sidebar.")

# --- Footer ---
st.markdown("---")
st.caption("Developed for evaluating PDF parsing effectiveness.")
