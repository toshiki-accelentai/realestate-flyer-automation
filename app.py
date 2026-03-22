import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv(override=True)

from extractors.claude_extractor import extract_property_data
from extractors.maps_extractor import enrich_with_maps
from sheets.sheets_writer import write_to_sheet
from config.field_mapping import FIELD_DEFINITIONS

# ページ設定
st.set_page_config(
    page_title="不動産物件情報 自動抽出",
    page_icon="🏠",
    layout="centered",
)

st.title("🏠 不動産物件情報 自動抽出")
st.caption("PDF資料をアップロードして、物件情報を自動的にスプレッドシートへ記録します。")

# ---- Step 1: ファイルアップロード ----
st.markdown("---")
st.subheader("① PDFファイルのアップロード")
st.markdown(
    "登記情報・建築計画概要書・上水道配管図・道路台帳など、"
    "物件に関するPDFファイルをすべて選択してください。"
)

uploaded_files = st.file_uploader(
    "PDFファイルを選択（複数可）",
    type=["pdf"],
    accept_multiple_files=True,
    help="複数ファイルを一度に選択できます。Ctrl+クリックで複数選択。",
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} 件のファイルが選択されました。")
    for f in uploaded_files:
        st.caption(f"📄 {f.name}")

# ---- Step 2: 抽出ボタン ----
st.markdown("---")
st.subheader("② 情報の抽出")

extract_btn = st.button(
    "🔍 物件情報を抽出する",
    disabled=not uploaded_files,
    use_container_width=True,
    type="primary",
)

if extract_btn:
    if not uploaded_files:
        st.error("PDFファイルをアップロードしてください。")
    else:
        # APIキーチェック
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("⚠️ ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。")
            st.stop()

        pdf_files = [
            {"name": f.name, "bytes": f.read()}
            for f in uploaded_files
        ]

        with st.spinner("AIがPDFを解析中です。少々お待ちください..."):
            try:
                extracted = extract_property_data(pdf_files)
                st.session_state["extracted_data"] = extracted
                st.success("✅ 抽出が完了しました！")
            except ValueError as e:
                st.error(f"抽出エラー: {e}")
                st.stop()
            except Exception as e:
                st.error(f"予期しないエラーが発生しました: {e}")
                st.stop()

        # Google Maps で補完
        address = extracted.get("address") or ""
        if address and os.getenv("GOOGLE_MAPS_API_KEY"):
            with st.spinner("Google Mapsで交通・学校情報を取得中..."):
                try:
                    enriched, maps_errors = enrich_with_maps(extracted, address)
                    st.session_state["extracted_data"] = enriched
                    if maps_errors:
                        for err in maps_errors:
                            st.warning(f"⚠️ Maps API: {err}")
                    else:
                        st.success("✅ Google Maps情報を取得しました。")
                except Exception as e:
                    st.warning(f"⚠️ Google Maps処理でエラーが発生しました: {e}")
        elif not os.getenv("GOOGLE_MAPS_API_KEY"):
            st.info(
                "ℹ️ Google Maps API キーが未設定のため、交通・学校距離は自動取得されません。"
                "手動で入力してください。"
            )

# ---- Step 3: 結果プレビュー・編集 ----
if "extracted_data" in st.session_state:
    st.markdown("---")
    st.subheader("③ 抽出結果の確認・修正")
    st.caption("内容を確認し、必要であれば手動で修正してください。")

    data = st.session_state["extracted_data"]
    edited_data = {}

    # フィールドを表形式で表示・編集
    for field in FIELD_DEFINITIONS:
        key = field["key"]
        label = field["label"]
        current_value = data.get(key) or ""
        if current_value == "null":
            current_value = ""

        edited_value = st.text_input(
            label=label,
            value=str(current_value),
            key=f"field_{key}",
        )
        edited_data[key] = edited_value

    # 編集済みデータをセッションに保存
    st.session_state["edited_data"] = edited_data

    # ---- Step 4: Sheetsへ保存 ----
    st.markdown("---")
    st.subheader("④ スプレッドシートへ記録")

    tab_name_input = st.text_input(
        "タブ名（省略可）",
        value="",
        placeholder="例: 館林市下三林町1334-3_20240708　← 空欄の場合は自動生成",
        help="スプレッドシートに追加するタブの名前。空欄の場合は住所+日付で自動生成されます。",
    )

    save_btn = st.button(
        "💾 スプレッドシートに保存",
        use_container_width=True,
        type="primary",
    )

    if save_btn:
        save_data = st.session_state.get("edited_data", data)

        with st.spinner("スプレッドシートに書き込み中..."):
            try:
                url = write_to_sheet(
                    data=save_data,
                    tab_name=tab_name_input if tab_name_input.strip() else None,
                )
                st.session_state["last_sheet_url"] = url
                st.session_state["save_done"] = True
            except FileNotFoundError as e:
                st.error(f"認証エラー: {e}")
            except Exception as e:
                st.error(f"保存エラー: {e}")

    if st.session_state.get("save_done"):
        url = st.session_state.get("last_sheet_url", "")
        st.success("✅ スプレッドシートへの記録が完了しました！")
        if url:
            st.markdown(f"[📊 スプレッドシートを開く]({url})", unsafe_allow_html=False)
        if st.button("🔄 新しい物件を処理する", use_container_width=True):
            # フィールド・抽出データ・保存状態をすべてリセット
            keys_to_clear = [k for k in st.session_state if k.startswith("field_")]
            keys_to_clear += ["extracted_data", "edited_data", "save_done", "last_sheet_url"]
            for k in keys_to_clear:
                st.session_state.pop(k, None)
            # ページ先頭にスクロール
            components.html("<script>window.parent.scrollTo(0, 0);</script>", height=0)
            st.rerun()

# ---- フッター ----
st.markdown("---")
st.caption("© Real Estate Automation | Powered by Claude AI")
