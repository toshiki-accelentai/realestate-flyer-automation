import os
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config.field_mapping import DATA_ENTRY_COLUMNS, FIELD_DEFINITIONS


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DATA_ENTRY_TAB = "data_entry"
TEMPLATE_TAB = "template"
TEMPLATE_ROW = 2  # テンプレートタブが参照している data_entry の行番号


def _get_client() -> gspread.Client:
    """Google Sheets クライアントを取得する"""
    service_account_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

    if not os.path.exists(service_account_path):
        raise FileNotFoundError(
            f"サービスアカウントファイルが見つかりません: {service_account_path}\n"
            ".env の GOOGLE_SERVICE_ACCOUNT_JSON を確認してください。"
        )

    creds = Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
    return gspread.authorize(creds)


def write_to_sheet(data: dict, tab_name: str | None = None) -> str:
    """
    抽出した物件データを Google Sheets に書き込む。

    処理フロー:
    1. data_entry タブに新規行を横型で追記
    2. テンプレートタブを複製して新規フライヤータブを作成
    3. 複製タブ内の data_entry 参照行番号を新しい行に更新

    Args:
        data: 物件情報の辞書
        tab_name: フライヤータブ名（省略時は住所+日付から自動生成）

    Returns:
        書き込み先のスプレッドシートURL
    """
    sheets_id = os.getenv("GOOGLE_SHEETS_ID")
    if not sheets_id:
        raise ValueError("GOOGLE_SHEETS_ID が設定されていません。.env を確認してください。")

    gc = _get_client()
    spreadsheet = gc.open_by_key(sheets_id)

    # Step 1: data_entry タブに横型で書き込む
    new_row = _append_to_data_entry(spreadsheet, data)

    # Step 2: テンプレートタブを複製し、参照行を更新
    tab_name = _generate_tab_name(data, tab_name)
    new_sheet = _duplicate_template(spreadsheet, tab_name, new_row)

    return f"https://docs.google.com/spreadsheets/d/{sheets_id}/edit#gid={new_sheet.id}"


def _write_data_entry_headers(ws: gspread.Worksheet) -> None:
    """data_entry タブの1行目にヘッダーを書き込む。"""
    label_map = {f["key"]: f["label"] for f in FIELD_DEFINITIONS}
    updates = []
    for field_key, col_letter in DATA_ENTRY_COLUMNS.items():
        label = label_map.get(field_key, field_key)
        updates.append({"range": f"{col_letter}1", "values": [[label]]})
    if updates:
        ws.batch_update(updates)


def _append_to_data_entry(spreadsheet: gspread.Spreadsheet, data: dict) -> int:
    """
    data_entry タブの次の空行にデータを横型で書き込む。

    Returns:
        書き込んだ行番号（1-indexed）
    """
    try:
        ws = spreadsheet.worksheet(DATA_ENTRY_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=DATA_ENTRY_TAB, rows=1000, cols=50)
        _write_data_entry_headers(ws)

    all_values = ws.get_all_values()
    new_row = len(all_values) + 1

    updates = []
    for field_key, col_letter in DATA_ENTRY_COLUMNS.items():
        value = data.get(field_key)
        if value is None or value == "null":
            value = ""
        else:
            value = str(value)
        updates.append({
            "range": f"{col_letter}{new_row}",
            "values": [[value]],
        })

    if updates:
        ws.batch_update(updates)

    return new_row


def _duplicate_template(
    spreadsheet: gspread.Spreadsheet,
    tab_name: str,
    new_row: int,
) -> gspread.Worksheet:
    """
    テンプレートタブを複製し、data_entry の行参照を new_row に更新する。

    テンプレートタブは =data_entry!B2 のような直接参照を持つ前提。
    複製後、行番号部分（TEMPLATE_ROW）を new_row に正規表現で置換する。

    Args:
        spreadsheet: スプレッドシートオブジェクト
        tab_name: 新規タブ名
        new_row: data_entry の参照先行番号

    Returns:
        作成された新規ワークシート
    """
    try:
        template_sheet = spreadsheet.worksheet(TEMPLATE_TAB)
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError(
            f"'{TEMPLATE_TAB}' タブが見つかりません。"
            f"スプレッドシートに '{TEMPLATE_TAB}' タブが存在するか確認してください。"
            f"（見本タブとは別に、複製元となる '{TEMPLATE_TAB}' タブが必要です）"
        )

    # 同名タブが既に存在する場合は連番サフィックスを付与
    existing_titles = {ws.title for ws in spreadsheet.worksheets()}
    unique_name = tab_name
    counter = 2
    while unique_name in existing_titles:
        unique_name = f"{tab_name}_{counter}"
        counter += 1

    new_sheet = spreadsheet.duplicate_sheet(
        source_sheet_id=template_sheet.id,
        new_sheet_name=unique_name,
    )

    # テンプレートがデフォルトで TEMPLATE_ROW を参照 → new_row に置換
    if new_row != TEMPLATE_ROW:
        _update_row_references(new_sheet, TEMPLATE_ROW, new_row)

    return new_sheet


def _update_row_references(
    worksheet: gspread.Worksheet,
    old_row: int,
    new_row: int,
) -> None:
    """
    シート内の数式で data_entry の old_row 参照を new_row に置換する。

    例: =data_entry!A2 → =data_entry!A3
    """
    all_values = worksheet.get_all_values(value_render_option="FORMULA")

    updates = []
    for row_idx, row in enumerate(all_values, start=1):
        for col_idx, cell_value in enumerate(row, start=1):
            if not isinstance(cell_value, str):
                continue
            if "data_entry!" not in cell_value:
                continue

            new_value = re.sub(
                rf"(data_entry![A-Z]{{1,3}}){old_row}(?!\d)",
                lambda m: f"{m.group(1)}{new_row}",
                cell_value,
            )

            if new_value != cell_value:
                col_letter = _col_num_to_letter(col_idx)
                updates.append({
                    "range": f"{col_letter}{row_idx}",
                    "values": [[new_value]],
                })

    if updates:
        worksheet.batch_update(updates, value_input_option="USER_ENTERED")


def _col_num_to_letter(col_num: int) -> str:
    """列番号（1-indexed）をアルファベット表記に変換する（例: 1→A, 27→AA）"""
    result = ""
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _generate_tab_name(data: dict, tab_name: str | None) -> str:
    """タブ名を生成する（住所+日付の自動生成 or 手動指定）"""
    if not tab_name:
        address = data.get("address") or "物件"
        # 都道府県名を除去して短縮
        short_address = re.sub(
            r"^(北海道|.{2,3}[都府県])", "", address
        )
        # 「字○○」「大字○○」を除去
        short_address = re.sub(r"[大字]+\S+\s*", "", short_address)
        short_address = short_address.replace("番", "-")
        if len(short_address) > 20:
            short_address = short_address[:20]
        date_str = datetime.now().strftime("%Y%m%d")
        tab_name = f"{short_address}_{date_str}"

    # Google Sheets のタブ名は100文字まで
    tab_name = tab_name[:100]

    return tab_name
