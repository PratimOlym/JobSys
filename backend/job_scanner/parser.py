"""Job description parser.

Wraps the shared parser for backwards compatibility and job-specific extensions.
"""

from shared.parser import (
    ParsedJobDetails,
    parse_jd_text,
    parse_pdf_bytes,
    parse_docx_bytes,
    extract_text_from_file
)
