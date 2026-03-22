# フィールド定義
# key: アプリ内部で使うフィールドID（Claude抽出JSONのキー名）
# label: 表示ラベル
# source: データの取得元

FIELD_DEFINITIONS = [
    {"key": "address",           "label": "所在地",              "source": "claude"},
    {"key": "property_type",     "label": "物件種別",             "source": "claude"},
    {"key": "rights",            "label": "権利",                "source": "claude"},
    {"key": "transport_line",    "label": "交通（路線・駅）",      "source": "claude"},
    {"key": "walk_minutes",      "label": "徒歩分数",             "source": "maps"},
    {"key": "lease_period",      "label": "借地期間",             "source": "claude"},
    {"key": "lease_fee",         "label": "借地料",              "source": "claude"},
    {"key": "land_area",         "label": "土地面積",             "source": "claude"},
    {"key": "building_area",     "label": "建物面積",             "source": "claude"},
    {"key": "city_plan",         "label": "都市計画",             "source": "claude"},
    {"key": "zoning",            "label": "用途地域",             "source": "claude"},
    {"key": "coverage_ratio",    "label": "建ぺい率",             "source": "claude"},
    {"key": "floor_ratio",       "label": "容積率",              "source": "claude"},
    {"key": "structure",         "label": "建物構造",             "source": "claude"},
    {"key": "built_date",        "label": "建築年月",             "source": "claude"},
    {"key": "road",              "label": "道路（方位・幅員・種別）", "source": "claude"},
    {"key": "water_supply",      "label": "水道",                "source": "claude"},
    {"key": "sewage",            "label": "排水",                "source": "claude"},
    {"key": "gas",               "label": "ガス",                "source": "claude"},
    {"key": "parking",           "label": "駐車台数",             "source": "claude"},
    {"key": "current_status",    "label": "現況",                "source": "claude"},
    {"key": "elementary_school", "label": "小学校（名称・距離）",   "source": "maps"},
    {"key": "middle_school",     "label": "中学校（名称・距離）",   "source": "maps"},
    {"key": "supermarket",       "label": "スーパー（名称・距離）",  "source": "maps"},
    {"key": "convenience",       "label": "コンビニ（名称・距離）",  "source": "maps"},
    {"key": "hospital",          "label": "病院（名称・距離）",      "source": "maps"},
    {"key": "bank",              "label": "銀行（名称・距離）",      "source": "maps"},
]

# data_entry タブの列マッピング
# key → data_entry タブのヘッダー列アルファベット
# ※ data_entry の1行目ヘッダーと一致させること
# ※ スクショ確認後に右側の列を追加してください
DATA_ENTRY_COLUMNS = {
    "address":           "A",   # 所在地番
    "property_type":     "B",   # 物件種別
    "rights":            "C",   # 権利
    # "owner":           "D",   # 所有権者（現在未抽出）
    "transport_line":    "E",   # 交通
    "zoning":            "F",   # 用途地域
    "land_area":         "G",   # 土地面積
    "building_area":     "H",   # 建物面積
    "city_plan":         "I",   # 都市計画
    "coverage_ratio":    "J",   # 建蔽率
    "floor_ratio":       "K",   # 容積率
    "structure":         "L",   # 建築構造
    "built_date":        "M",   # 建築年月
    "road":              "N",   # 道路種別
    # "road_width":      "O",   # 道路幅員（road フィールドに含まれるため未分割）
    # "road_direction":  "P",   # 接道方向（同上）
    # "transaction_type":"Q",   # 取引形態（現在未抽出）
    "parking":           "R",   # 駐車台数
    "water_supply":      "S",   # 水道
    "sewage":            "T",   # 排水
    "gas":               "U",   # ガス
    "current_status":    "V",   # 現況
    # "handover":        "W",   # 引渡（現在未抽出）
    "elementary_school": "X",   # 小学校
    "middle_school":     "Y",   # 中学校
    "supermarket":       "Z",   # スーパー
    "convenience":       "AA",  # コンビニ
    "hospital":          "AB",  # 病院
    "bank":              "AC",  # 銀行
}

# フィールドIDのリスト（Claude抽出JSONのキー名として使用）
ALL_FIELD_KEYS = [f["key"] for f in FIELD_DEFINITIONS]

# Claudeが抽出する項目のみ
CLAUDE_FIELD_KEYS = [f["key"] for f in FIELD_DEFINITIONS if f["source"] == "claude"]

# Google Mapsが取得する項目のみ
MAPS_FIELD_KEYS = [f["key"] for f in FIELD_DEFINITIONS if f["source"] == "maps"]
