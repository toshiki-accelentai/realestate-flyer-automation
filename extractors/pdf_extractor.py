import base64
from pathlib import Path


def pdf_to_base64(file_bytes: bytes) -> str:
    """PDFのバイトデータをBase64文字列に変換する"""
    return base64.standard_b64encode(file_bytes).decode("utf-8")


def build_pdf_document_block(file_bytes: bytes) -> dict:
    """Claude API用のdocumentコンテンツブロックを作成する"""
    return {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": pdf_to_base64(file_bytes),
        },
    }
