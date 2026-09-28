"""File handler for document and image uploads.
Extracts text content from various file formats for analysis by the AI pipeline.
"""
import os
import base64
from fastapi import UploadFile

# Supported file types
TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp",
                   ".h", ".css", ".html", ".xml", ".json", ".yaml", ".yml", ".toml", ".ini",
                   ".cfg", ".conf", ".sh", ".bat", ".ps1", ".sql", ".csv", ".log", ".gradle",
                   ".properties", ".env", ".gitignore", ".dockerfile"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tiff"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def extract_file_content(file: UploadFile) -> tuple[str, dict]:
    """Extract text content from an uploaded file.
    
    Returns:
        tuple of (extracted_text, file_info_dict)
    """
    if not file.filename:
        raise ValueError("No filename provided")

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    raw_bytes = await file.read()

    if len(raw_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"File too large ({len(raw_bytes) / 1024 / 1024:.1f} MB). Max is 10 MB.")

    file_info = {
        "filename": filename,
        "extension": ext,
        "size_bytes": len(raw_bytes),
        "size_display": _format_size(len(raw_bytes)),
        "type": _get_file_type(ext),
    }

    # Handle text-based files
    if ext in TEXT_EXTENSIONS or ext == "":
        try:
            text = raw_bytes.decode("utf-8", errors="replace")
            file_info["lines"] = len(text.splitlines())
            return text, file_info
        except Exception:
            raise ValueError(f"Could not read file '{filename}' as text.")

    # Handle images — encode as base64 and provide description prompt
    if ext in IMAGE_EXTENSIONS:
        b64 = base64.b64encode(raw_bytes).decode("ascii")
        mime = _get_mime(ext)
        # Return a description request with the base64 data
        content = (
            f"[UPLOADED IMAGE: {filename} ({file_info['size_display']})]\n"
            f"[Image type: {mime}]\n\n"
            f"Please analyze this image. Describe its contents, identify any text, diagrams, "
            f"architecture patterns, code snippets, or data visualizations present.\n\n"
            f"[base64_data:{b64[:100]}...]"
        )
        file_info["mime_type"] = mime
        file_info["base64_preview"] = f"data:{mime};base64,{b64[:200]}"
        file_info["has_image"] = True
        return content, file_info

    # Handle PDF — extract text (basic approach)
    if ext == ".pdf":
        text = _extract_pdf_text(raw_bytes)
        if text.strip():
            file_info["lines"] = len(text.splitlines())
            return text, file_info
        raise ValueError("Could not extract text from PDF. The file may be image-based or encrypted.")

    raise ValueError(f"Unsupported file type: '{ext}'. Supported: text files, images, PDF, CSV.")


def _extract_pdf_text(raw_bytes: bytes) -> str:
    """Extract text from PDF bytes. Uses basic text extraction."""
    try:
        # Try PyPDF2/pypdf if available
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(raw_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n--- Page Break ---\n\n".join(pages)
        except ImportError:
            pass

        # Fallback: basic text extraction from PDF bytes
        text = raw_bytes.decode("latin-1", errors="replace")
        # Extract text between BT and ET markers (basic PDF text extraction)
        import re
        chunks = re.findall(r'\((.*?)\)', text)
        if chunks:
            return " ".join(c for c in chunks if len(c) > 1 and c.isprintable())
        return ""
    except Exception:
        return ""


def _get_file_type(ext: str) -> str:
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext == ".pdf":
        return "pdf"
    if ext in {".csv", ".json", ".xml", ".yaml", ".yml"}:
        return "data"
    if ext in {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h"}:
        return "code"
    return "text"


def _get_mime(ext: str) -> str:
    mimes = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
        ".svg": "image/svg+xml", ".tiff": "image/tiff",
    }
    return mimes.get(ext, "application/octet-stream")


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
