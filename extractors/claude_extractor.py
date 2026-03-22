import json
import os
import anthropic
from extractors.pdf_extractor import build_pdf_document_block
from prompts.extraction_prompt import EXTRACTION_PROMPT


def extract_property_data(pdf_files: list[dict]) -> dict:
    """
    複数のPDFファイルからClaude APIを使って物件情報を抽出する。

    Args:
        pdf_files: [{"name": "filename.pdf", "bytes": b"..."}] のリスト

    Returns:
        抽出した物件情報の辞書（JSONパース済み）

    Raises:
        ValueError: APIキー未設定・JSONパース失敗時
        anthropic.APIError: API呼び出しエラー時
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。")

    client = anthropic.Anthropic(api_key=api_key)

    # コンテンツブロックを構築: PDFドキュメント + 抽出プロンプト
    content = []
    for pdf in pdf_files:
        content.append(build_pdf_document_block(pdf["bytes"]))

    content.append({"type": "text", "text": EXTRACTION_PROMPT})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text.strip()

    # コードブロックが含まれる場合は除去
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Claude のレスポンスをJSONとしてパースできませんでした。\n"
            f"エラー: {e}\n"
            f"レスポンス内容:\n{raw_text}"
        )
