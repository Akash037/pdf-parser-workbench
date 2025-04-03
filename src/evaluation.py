import re
import streamlit as st
from langchain.text_splitter import RecursiveCharacterTextSplitter # Import splitter

# --- Basic Quality Metrics ---

def calculate_metrics(text_content):
    """Calculates basic metrics for a given text string."""
    metrics = {}
    if not isinstance(text_content, str):
        return {'error': 'Input must be a string'}
        
    # Character Count (including whitespace)
    metrics['char_count'] = len(text_content)
    
    # Word Count (simple split on whitespace)
    metrics['word_count'] = len(text_content.split())
    
    # Estimated Equation Count (simple regex for $...$ and $$...$$)
    # This is a rough estimate and might miscount nested or complex structures.
    inline_eq_count = len(re.findall(r'(?<!\\)\$.*?(?<!\\)\$', text_content)) # Matches $...$
    display_eq_count = len(re.findall(r'(?<!\\)\$\$.*?(?<!\\)\$\$', text_content, re.DOTALL)) # Matches $$...$$
    metrics['estimated_equation_count'] = inline_eq_count + display_eq_count
    
    # Estimated Section Count (simple regex for common header patterns like '# Header' or '1. Header')
    # This is very basic and highly dependent on markdown format.
    section_count = len(re.findall(r'^\s*#{1,6}\s+.*', text_content, re.MULTILINE)) # Markdown headers
    section_count += len(re.findall(r'^\s*\d+\.\s+.*', text_content, re.MULTILINE)) # Numbered list items (basic sections)
    metrics['estimated_section_count'] = section_count

    return metrics

# --- Chunking Preview ---

def get_chunking_preview(text_content, strategy='recursive', chunk_size=1000, chunk_overlap=100, max_preview_chunks=5):
    """Provides a preview of how text would be chunked using LangChain."""
    preview = {'chunks': [], 'total_chunks': 0, 'error': None}
    if not isinstance(text_content, str):
        preview['error'] = 'Input text must be a string'
        return preview
    if chunk_size <= 0:
         preview['error'] = 'Chunk size must be positive'
         return preview
    if chunk_overlap < 0:
         preview['error'] = 'Chunk overlap cannot be negative'
         return preview
    if chunk_overlap >= chunk_size:
         preview['error'] = 'Chunk overlap must be smaller than chunk size'
         return preview

    try:
        if strategy == 'recursive':
            # Using RecursiveCharacterTextSplitter by default
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                is_separator_regex=False, # Use default separators
            )
            chunks = splitter.split_text(text_content)
            preview['chunks'] = chunks[:max_preview_chunks] # Show only the first few chunks
            preview['total_chunks'] = len(chunks)
        # Add elif blocks here for other strategies (e.g., 'semantic', 'fixed') if implemented later
        # elif strategy == 'semantic':
        #     preview['error'] = "Semantic chunking not yet implemented."
        else:
            preview['error'] = f"Unknown or unimplemented chunking strategy: {strategy}"
            
    except Exception as e:
        preview['error'] = f"Chunking Error: {e}"
        
    return preview


# --- Main Function (for testing if needed) ---
if __name__ == '__main__':
    test_text = """
# Section 1

This is some text. It includes an inline equation $E=mc^2$. 

## Subsection 1.1

And a display equation:
$$
\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}
$$

More text here.

2. Another Section

Final words. $a=b$.
"""
    print("--- Testing Metrics ---")
    metrics = calculate_metrics(test_text)
    print(metrics)

    print("\n--- Testing Chunking (Placeholder) ---")
    chunk_preview = get_chunking_preview(test_text)
    print(chunk_preview)
