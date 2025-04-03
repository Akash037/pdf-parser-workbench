import json
import streamlit as st
import os
import re # Need re for get_safe_filename
from io import BytesIO
# Import python-docx for DOCX export
try:
    from docx import Document
    # from docx.shared import Inches # Not used in basic implementation
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# --- Export Helper Functions ---

def get_safe_filename(base_name):
    """Creates a safe filename by removing/replacing invalid characters."""
    # Remove path components and invalid chars
    base_name = os.path.basename(base_name)
    safe_name = re.sub(r'[\\/*?:"<>|]', "", base_name)
    # Replace spaces with underscores
    safe_name = safe_name.replace(" ", "_")
    # Truncate if too long (optional)
    max_len = 100
    if len(safe_name) > max_len:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:max_len - len(ext) - 1] + ext
    return safe_name

def export_text(content, filename="output.txt"):
    """Prepares text content for download."""
    if not isinstance(content, str):
        st.error("Error preparing text export: Content must be a string.")
        return None
    try:
        # Ensure content is UTF-8 encoded bytes for download button
        return content.encode('utf-8')
    except Exception as e:
        st.error(f"Error encoding text for export: {e}")
        return None

def export_markdown(content, filename="output.md"):
     """Prepares markdown content for download."""
     # Same as text export for now
     return export_text(content, filename)

def export_xml(content, filename="output.xml"):
     """Prepares XML content for download."""
     # Same as text export
     return export_text(content, filename)

def export_json(data, filename="output.json"):
    """Prepares dictionary or list data as JSON for download."""
    if not isinstance(data, (dict, list)):
        st.error("Error preparing JSON export: Data must be a dictionary or list.")
        return None
    try:
        json_string = json.dumps(data, indent=4, ensure_ascii=False)
        return json_string.encode('utf-8')
    except Exception as e:
        st.error(f"Error encoding JSON for export: {e}")
        return None

def export_docx(content, filename="output.docx"):
     """Converts text content to DOCX and prepares for download."""
     if not DOCX_AVAILABLE:
         st.error("`python-docx` library not found. Cannot export to DOCX.")
         return None
     if not isinstance(content, str):
        st.error("Error preparing DOCX export: Input content must be a string.")
        return None
        
     try:
         document = Document()
         # Add content as paragraphs - simple approach
         # For markdown, more sophisticated parsing could be added (e.g., using markdown library)
         for paragraph in content.split('\n'):
              document.add_paragraph(paragraph)
         
         # Save to a BytesIO object to return bytes
         bio = BytesIO()
         document.save(bio)
         bio.seek(0)
         return bio.getvalue()
     except Exception as e:
         st.error(f"Error creating DOCX file: {e}")
         return None

# --- Main (for testing if needed) ---
if __name__ == '__main__':
    import re # Need re for get_safe_filename if testing here
    print("Utils module created. Implement DOCX export.")
    test_dict = {"key": "value", "list": [1, 2, 3]}
    json_bytes = export_json(test_dict)
    if json_bytes:
        print("JSON export prepared (bytes):", len(json_bytes))
    
    safe = get_safe_filename("my file /:*?<>|.pdf")
    print("Safe filename:", safe)
