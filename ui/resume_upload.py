"""Bounded resume-file extraction at the candidate UI boundary."""

from __future__ import annotations

import csv
import hashlib
import io
import shutil
import subprocess
import tempfile
import unicodedata
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath

from docx import Document
from docx.table import Table
from pypdf import PdfReader


MAX_RESUME_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_TEXT_BYTES = 100_000
MAX_PDF_PAGES = 30
MAX_CSV_ROWS = 2_000
MAX_CSV_COLUMNS = 100
MAX_ARCHIVE_MEMBERS = 1_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
SUPPORTED_RESUME_TYPES = ("pdf", "docx", "doc", "csv", "md", "markdown")


class ResumeFormat(str, Enum):
    """Resume formats accepted by the candidate upload control."""

    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    CSV = "csv"
    MARKDOWN = "markdown"


class ResumeUploadError(ValueError):
    """Candidate-safe extraction failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ExtractedResume:
    """Normalized resume text and non-content upload provenance."""

    filename: str
    format: ResumeFormat
    media_type: str
    size_bytes: int
    sha256: str
    text: str
    extraction_method: str
    warnings: tuple[str, ...] = ()

    @property
    def candidate_id(self) -> str:
        """Derive a stable opaque ID from the exact uploaded bytes."""

        return f"upload-{self.sha256[:16]}"


LegacyDocConverter = Callable[[bytes], str]

_FORMAT_BY_SUFFIX = {
    ".pdf": ResumeFormat.PDF,
    ".docx": ResumeFormat.DOCX,
    ".doc": ResumeFormat.DOC,
    ".csv": ResumeFormat.CSV,
    ".md": ResumeFormat.MARKDOWN,
    ".markdown": ResumeFormat.MARKDOWN,
}
_MEDIA_TYPES = {
    ResumeFormat.PDF: {"application/pdf"},
    ResumeFormat.DOCX: {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ResumeFormat.DOC: {"application/msword", "application/rtf", "text/rtf"},
    ResumeFormat.CSV: {"text/csv", "application/csv", "text/plain"},
    ResumeFormat.MARKDOWN: {"text/markdown", "text/plain"},
}
_GENERIC_MEDIA_TYPES = {"", "application/octet-stream"}
_OLE_SIGNATURE = bytes.fromhex("d0cf11e0a1b11ae1")


def extract_resume(
    filename: str,
    data: bytes,
    content_type: str | None = None,
    *,
    legacy_doc_converter: LegacyDocConverter | None = None,
) -> ExtractedResume:
    """Validate an untrusted upload and return bounded normalized text."""

    safe_name, resume_format = _validate_envelope(filename, data, content_type)
    warnings: tuple[str, ...] = ()

    if resume_format is ResumeFormat.PDF:
        text = _extract_pdf(data)
        method = "pypdf"
    elif resume_format is ResumeFormat.DOCX:
        text = _extract_docx(data)
        method = "python-docx"
    elif resume_format is ResumeFormat.DOC:
        text = _extract_doc(data, legacy_doc_converter or _convert_legacy_doc)
        method = "system-text-converter"
        warnings = (
            "Legacy DOC conversion depends on the host converter; DOCX is preferred.",
        )
    elif resume_format is ResumeFormat.CSV:
        text = _extract_csv(data)
        method = "python-csv"
    else:
        text = _decode_utf8(data, "Markdown")
        method = "utf-8"

    normalized = _normalize_text(text)
    if not normalized:
        raise ResumeUploadError(
            "no_extractable_text",
            "The resume contains no extractable text. Scanned documents need OCR, "
            "which is not enabled.",
        )
    if len(normalized.encode("utf-8")) > MAX_EXTRACTED_TEXT_BYTES:
        raise ResumeUploadError(
            "extracted_text_too_large",
            "The extracted resume text exceeds the 100 KB processing limit.",
        )

    return ExtractedResume(
        filename=safe_name,
        format=resume_format,
        media_type=(content_type or "application/octet-stream").lower(),
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        text=normalized,
        extraction_method=method,
        warnings=warnings,
    )


def _validate_envelope(
    filename: str,
    data: bytes,
    content_type: str | None,
) -> tuple[str, ResumeFormat]:
    """Validate name, size, extension, and browser-declared media type."""

    if not filename.strip() or "\x00" in filename or any(
        separator in filename for separator in ("/", "\\")
    ):
        raise ResumeUploadError("invalid_filename", "The resume filename is invalid.")
    if not data:
        raise ResumeUploadError("empty_file", "The selected resume is empty.")
    if len(data) > MAX_RESUME_BYTES:
        raise ResumeUploadError(
            "file_too_large", "The selected resume exceeds the 10 MB upload limit."
        )

    resume_format = _FORMAT_BY_SUFFIX.get(Path(filename).suffix.lower())
    if resume_format is None:
        raise ResumeUploadError(
            "unsupported_format", "Use a PDF, DOCX, DOC, CSV, MD, or MARKDOWN resume."
        )

    media_type = (content_type or "").split(";", maxsplit=1)[0].strip().lower()
    if (
        media_type not in _GENERIC_MEDIA_TYPES
        and media_type not in _MEDIA_TYPES[resume_format]
    ):
        raise ResumeUploadError(
            "media_type_mismatch",
            "The file type reported by the browser does not match its extension.",
        )
    return Path(filename).name, resume_format


def _extract_pdf(data: bytes) -> str:
    """Extract selectable PDF text and reject encrypted or oversized files."""

    if not data.startswith(b"%PDF-"):
        raise ResumeUploadError(
            "invalid_signature", "The selected PDF does not have a valid PDF signature."
        )
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ResumeUploadError(
                "encrypted_document",
                "Password-protected PDFs are not supported. Upload an unlocked copy.",
            )
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ResumeUploadError(
                "too_many_pages", f"PDF resumes are limited to {MAX_PDF_PAGES} pages."
            )
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ResumeUploadError:
        raise
    except Exception as error:
        raise ResumeUploadError(
            "malformed_document", "The PDF could not be read safely."
        ) from error


def _extract_docx(data: bytes) -> str:
    """Extract paragraphs and tables after bounded ZIP safety checks."""

    _validate_docx_archive(data)
    try:
        document = Document(io.BytesIO(data))
        lines: list[str] = []
        for block in document.iter_inner_content():
            if isinstance(block, Table):
                for row in block.rows:
                    values = [_normalize_text(cell.text) for cell in row.cells]
                    if any(values):
                        lines.append(" | ".join(values))
            elif block.text.strip():
                lines.append(block.text)
        return "\n".join(lines)
    except Exception as error:
        raise ResumeUploadError(
            "malformed_document", "The DOCX file could not be read safely."
        ) from error


def _validate_docx_archive(data: bytes) -> None:
    """Reject malformed, expansive, macro-bearing, or embedded archives."""

    if not data.startswith(b"PK"):
        raise ResumeUploadError(
            "invalid_signature", "The selected DOCX is not a valid Office document."
        )
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            names = {item.filename for item in members}
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ResumeUploadError(
                    "unsafe_archive", "The DOCX archive contains too many entries."
                )
            if sum(item.file_size for item in members) > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ResumeUploadError(
                    "unsafe_archive", "The expanded DOCX exceeds the safety limit."
                )
            for item in members:
                parts = PurePosixPath(item.filename).parts
                lowered = item.filename.lower()
                if ".." in parts or item.filename.startswith(("/", "\\")):
                    raise ResumeUploadError(
                        "unsafe_archive", "The DOCX archive contains an unsafe path."
                    )
                if "vbaproject.bin" in lowered or "/embeddings/" in lowered:
                    raise ResumeUploadError(
                        "active_content",
                        "Macro-enabled or embedded DOCX content is not supported.",
                    )
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise ResumeUploadError(
                    "malformed_document", "The DOCX is missing required document parts."
                )
    except ResumeUploadError:
        raise
    except (OSError, zipfile.BadZipFile) as error:
        raise ResumeUploadError(
            "malformed_document", "The DOCX file could not be read safely."
        ) from error


def _extract_doc(data: bytes, converter: LegacyDocConverter) -> str:
    """Validate legacy Word bytes before using an isolated converter."""

    if not (data.startswith(_OLE_SIGNATURE) or data.lstrip().startswith(b"{\\rtf")):
        raise ResumeUploadError(
            "invalid_signature", "The selected DOC is not a recognized legacy Word file."
        )
    try:
        return converter(data)
    except ResumeUploadError:
        raise
    except Exception as error:
        raise ResumeUploadError(
            "legacy_conversion_failed",
            "The legacy DOC could not be converted. Save it as DOCX and try again.",
        ) from error


def _convert_legacy_doc(data: bytes) -> str:
    """Convert legacy Word on macOS using a bounded shell-free subprocess."""

    converter = shutil.which("textutil")
    if converter is None:
        raise ResumeUploadError(
            "legacy_converter_unavailable",
            "Legacy DOC conversion is unavailable on this host. Save it as DOCX.",
        )
    with tempfile.TemporaryDirectory(prefix="ig-resume-") as directory:
        source = Path(directory) / "resume.doc"
        source.write_bytes(data)
        try:
            completed = subprocess.run(
                [converter, "-convert", "txt", "-stdout", str(source)],
                check=False,
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ResumeUploadError(
                "legacy_conversion_failed",
                "The legacy DOC conversion failed. Save the file as DOCX.",
            ) from error
    if completed.returncode != 0:
        raise ResumeUploadError(
            "legacy_conversion_failed",
            "The legacy DOC conversion failed. Save the file as DOCX.",
        )
    return _decode_utf8(completed.stdout, "Converted DOC")


def _extract_csv(data: bytes) -> str:
    """Turn bounded UTF-8 CSV cells into visible row text."""

    decoded = _decode_utf8(data, "CSV")
    try:
        lines: list[str] = []
        for position, row in enumerate(
            csv.reader(io.StringIO(decoded, newline="")), start=1
        ):
            if position > MAX_CSV_ROWS:
                raise ResumeUploadError(
                    "too_many_rows", f"CSV resumes are limited to {MAX_CSV_ROWS} rows."
                )
            if len(row) > MAX_CSV_COLUMNS:
                raise ResumeUploadError(
                    "too_many_columns",
                    f"CSV resumes are limited to {MAX_CSV_COLUMNS} columns.",
                )
            values = [_normalize_text(value) for value in row]
            if any(values):
                lines.append(" | ".join(values))
        return "\n".join(lines)
    except ResumeUploadError:
        raise
    except csv.Error as error:
        raise ResumeUploadError(
            "malformed_document", "The CSV file could not be read safely."
        ) from error


def _decode_utf8(data: bytes, label: str) -> str:
    """Decode plain-text formats without lossy replacement."""

    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ResumeUploadError(
            "invalid_encoding", f"{label} resumes must use UTF-8 text encoding."
        ) from error


def _normalize_text(text: str) -> str:
    """Normalize Unicode, line endings, nulls, and surrounding whitespace."""

    if "\x00" in text:
        raise ResumeUploadError(
            "invalid_text", "The resume contains unsupported null characters."
        )
    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    return "\n".join(line.strip() for line in normalized.splitlines()).strip()


__all__ = [
    "ExtractedResume",
    "MAX_RESUME_BYTES",
    "ResumeFormat",
    "ResumeUploadError",
    "SUPPORTED_RESUME_TYPES",
    "extract_resume",
]
