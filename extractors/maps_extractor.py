import os
import re
import googlemaps


def _get_client() -> googlemaps.Client | None:
    """Google Maps クライアントを取得する。APIキー未設定時は None を返す。"""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    return googlemaps.Client(key=api_key)


def get_nearest_station(address: str) -> tuple[str | None, str | None]:
    """
    物件住所から最寄り駅を検索して路線・駅名と徒歩分数を返す。

    Returns:
        (transport_line, walk_minutes) のタプル。取得失敗時は (None, None)
    """
    client = _get_client()
    if not client:
        return None, None

    try:
        # 住所から座標を取得
        geocode_result = client.geocode(address, language="ja")
        if not geocode_result:
            return None, None

        location = geocode_result[0]["geometry"]["location"]

        # 周辺の駅を検索（train_station / transit_station）
        places_result = client.places_nearby(
            location=location,
            radius=5000,
            type="train_station",
            language="ja",
        )

        results = places_result.get("results", [])
        if not results:
            # transit_station でも試す
            places_result = client.places_nearby(
                location=location,
                radius=5000,
                type="transit_station",
                language="ja",
            )
            results = places_result.get("results", [])

        if not results:
            return None, None

        nearest = results[0]
        station_name = nearest["name"]
        station_location = nearest["geometry"]["location"]

        # 徒歩時間と距離を取得
        dm_result = client.distance_matrix(
            origins=[address],
            destinations=[f"{station_location['lat']},{station_location['lng']}"],
            mode="walking",
            language="ja",
        )
        rows = dm_result.get("rows", [])
        walk_minutes = None
        if rows and rows[0]["elements"][0]["status"] == "OK":
            duration_seconds = rows[0]["elements"][0]["duration"]["value"]
            walk_minutes = f"{round(duration_seconds / 60)}分"

        transport_line = station_name
        return transport_line, walk_minutes

    except Exception as e:
        raise RuntimeError(f"最寄り駅の検索に失敗しました: {e}")


def get_walk_minutes(address: str, station_name: str) -> str | None:
    """
    物件住所から指定駅までの徒歩分数を取得する。

    Args:
        address: 物件住所
        station_name: 駅名（例: "茂林寺駅"）

    Returns:
        "XX分" 形式の文字列、または取得失敗時は None
    """
    client = _get_client()
    if not client:
        return None

    try:
        result = client.distance_matrix(
            origins=[address],
            destinations=[f"{station_name} 群馬県"],
            mode="walking",
            language="ja",
        )
        rows = result.get("rows", [])
        if rows and rows[0]["elements"][0]["status"] == "OK":
            duration_seconds = rows[0]["elements"][0]["duration"]["value"]
            minutes = round(duration_seconds / 60)
            return f"{minutes}分"
    except Exception:
        pass
    return None


def get_nearest_school(address: str, school_type: str) -> str | None:
    """
    物件住所から最寄りの学校を検索して名称と距離を返す。

    Args:
        address: 物件住所
        school_type: "小学校" または "中学校"

    Returns:
        "○○小学校 約XXXm" 形式の文字列、または取得失敗時は None
    """
    client = _get_client()
    if not client:
        return None

    try:
        # 住所から座標を取得
        geocode_result = client.geocode(address, language="ja")
        if not geocode_result:
            return None

        location = geocode_result[0]["geometry"]["location"]

        # 周辺の学校を検索
        places_result = client.places_nearby(
            location=location,
            radius=3000,
            keyword=school_type,
            language="ja",
            type="school",
        )

        results = places_result.get("results", [])
        if not results:
            return None

        # 最初の結果（最も近い）を使用
        nearest = results[0]
        school_name = nearest["name"]
        school_location = nearest["geometry"]["location"]

        # 距離を計算
        dm_result = client.distance_matrix(
            origins=[address],
            destinations=[f"{school_location['lat']},{school_location['lng']}"],
            mode="walking",
            language="ja",
        )
        rows = dm_result.get("rows", [])
        if rows and rows[0]["elements"][0]["status"] == "OK":
            distance_m = rows[0]["elements"][0]["distance"]["value"]
            return f"{school_name} 約{distance_m}m"
        else:
            return school_name

    except Exception as e:
        raise RuntimeError(f"{school_type}の検索に失敗しました: {e}")


def get_nearest_facility(address: str, place_type: str, label: str) -> str | None:
    """
    物件住所から最寄りの施設を検索して名称と距離を返す。

    Args:
        address: 物件住所
        place_type: Google Maps の place type（例: "supermarket", "convenience_store"）
        label: エラーメッセージ用ラベル（例: "スーパー"）

    Returns:
        "○○店 約XXXm" 形式の文字列、または取得失敗時は None
    """
    client = _get_client()
    if not client:
        return None

    try:
        geocode_result = client.geocode(address, language="ja")
        if not geocode_result:
            return None

        location = geocode_result[0]["geometry"]["location"]

        places_result = client.places_nearby(
            location=location,
            radius=3000,
            type=place_type,
            language="ja",
        )

        results = places_result.get("results", [])
        if not results:
            return None

        nearest = results[0]
        name = nearest["name"]
        loc = nearest["geometry"]["location"]

        dm_result = client.distance_matrix(
            origins=[address],
            destinations=[f"{loc['lat']},{loc['lng']}"],
            mode="walking",
            language="ja",
        )
        rows = dm_result.get("rows", [])
        if rows and rows[0]["elements"][0]["status"] == "OK":
            distance_m = rows[0]["elements"][0]["distance"]["value"]
            return f"{name} 約{distance_m}m"
        return name

    except Exception as e:
        raise RuntimeError(f"{label}の検索に失敗しました: {e}")


def enrich_with_maps(data: dict, address: str) -> tuple[dict, list[str]]:
    """
    Google Maps APIを使って距離情報をデータに追加する。
    APIキーが未設定の場合は元のデータをそのまま返す。

    Args:
        data: Claude抽出済みの物件データ辞書
        address: 物件住所

    Returns:
        (Maps情報を追加したデータ辞書, エラーメッセージのリスト)
    """
    errors = []
    client = _get_client()
    if not client:
        return data, errors

    enriched = dict(data)

    # 交通：Claudeが抽出できなかった場合はGoogle Mapsで最寄り駅を検索
    transport_line = data.get("transport_line") or ""
    if not transport_line or transport_line == "null":
        try:
            station, walk = get_nearest_station(address)
            if station:
                enriched["transport_line"] = station
                if walk:
                    enriched["walk_minutes"] = walk
        except RuntimeError as e:
            errors.append(str(e))
    else:
        # Claudeが駅名を抽出済みの場合は徒歩分数だけ計算
        station_match = re.search(r"「(.+?駅)」|(\S+駅)", transport_line)
        if station_match:
            station_name = station_match.group(1) or station_match.group(2)
            try:
                walk = get_walk_minutes(address, station_name)
                if walk:
                    enriched["walk_minutes"] = walk
            except Exception as e:
                errors.append(f"徒歩分数の取得に失敗しました: {e}")

    # 小学校
    try:
        elementary = get_nearest_school(address, "小学校")
        if elementary:
            enriched["elementary_school"] = elementary
    except RuntimeError as e:
        errors.append(str(e))

    # 中学校
    try:
        middle = get_nearest_school(address, "中学校")
        if middle:
            enriched["middle_school"] = middle
    except RuntimeError as e:
        errors.append(str(e))

    # 周辺施設（スーパー・コンビニ・病院・銀行）
    facilities = [
        ("supermarket",  "supermarket",      "スーパー"),
        ("convenience",  "convenience_store","コンビニ"),
        ("hospital",     "hospital",         "病院"),
        ("bank",              "bank",            "銀行"),
    ]
    for field_key, place_type, label in facilities:
        try:
            result = get_nearest_facility(address, place_type, label)
            if result:
                enriched[field_key] = result
        except RuntimeError as e:
            errors.append(str(e))

    return enriched, errors
