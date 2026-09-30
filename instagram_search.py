from pathlib import Path
from typing import Any
import re

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "ig_data"
REELS_FILE = DATA_DIR / "instagram_reels.csv"
COMMENTS_FILE = DATA_DIR / "instagram_comments.csv"


def _read_csv(path: Path) -> pd.DataFrame:
    for encoding in ["utf-8-sig", "utf-8", "cp950", "big5"]:
        try:
            return pd.read_csv(path, encoding=encoding, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"無法讀取檔案編碼：{path}")


def _check_files() -> None:
    missing = [str(p) for p in [REELS_FILE, COMMENTS_FILE] if not p.exists()]
    if missing:
        raise FileNotFoundError("找不到 Instagram 資料檔：\n" + "\n".join(missing))


def search_instagram_reels(keyword: str, max_results: int = 5) -> list[dict[str, Any]]:
    _check_files()
    keyword = str(keyword).strip()

    if not keyword:
        raise ValueError("請輸入 Instagram 搜尋關鍵字。")

    df = _read_csv(REELS_FILE)

    required = {
        "reel_id","shortcode","username","caption","topic","tags","url",
        "created_at","views","like_count","comment_count"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError("instagram_reels.csv 缺少欄位：" + ", ".join(sorted(missing)))

    tokens = [
        token.casefold()
        for token in re.split(r"[\s,，、/|]+", keyword)
        if token.strip()
    ]

    df["_search_text"] = (
        df[["caption", "topic", "tags"]]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.casefold()
    )

    def score(row) -> int:
        caption = str(row["caption"]).casefold()
        topic = str(row["topic"]).casefold()
        tags = str(row["tags"]).casefold()
        total = 0
        for token in tokens:
            if token in caption:
                total += 10
            if token in topic:
                total += 8
            if token in tags:
                total += 5
        return total

    df["_score"] = df.apply(score, axis=1)
    df = df[df["_score"] > 0].copy()

    if df.empty:
        return []

    for col in ["views", "like_count", "comment_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df = df.sort_values(
        by=["views", "_score"],
        ascending=[False, False]
    ).head(max_results)

    return [
        {
            "reel_id": str(row["reel_id"]),
            "shortcode": str(row["shortcode"]),
            "username": str(row["username"]),
            "caption": str(row["caption"]),
            "topic": str(row["topic"]),
            "url": str(row["url"]),
            "created_at": str(row["created_at"]),
            "views": int(row["views"]),
            "like_count": int(row["like_count"]),
            "comment_count": int(row["comment_count"]),
        }
        for _, row in df.iterrows()
    ]


def find_reel_by_url(url: str) -> dict[str, Any] | None:
    _check_files()
    url = str(url).strip().rstrip("/") + "/"
    df = _read_csv(REELS_FILE)
    df["_normalized_url"] = df["url"].astype(str).str.rstrip("/") + "/"
    matched = df[df["_normalized_url"] == url]

    if matched.empty:
        return None

    row = matched.iloc[0]
    return {
        "reel_id": str(row["reel_id"]),
        "shortcode": str(row["shortcode"]),
        "username": str(row["username"]),
        "caption": str(row["caption"]),
        "topic": str(row["topic"]),
        "url": str(row["url"]),
        "created_at": str(row["created_at"]),
        "views": int(float(row["views"])),
        "like_count": int(float(row["like_count"])),
        "comment_count": int(float(row["comment_count"])),
    }


def get_instagram_comments(reel_id: str) -> list[dict[str, Any]]:
    _check_files()
    reel_id = str(reel_id).strip()
    df = _read_csv(COMMENTS_FILE)
    result = df[df["reel_id"].astype(str) == reel_id].copy()

    return [
        {
            "reel_id": str(row["reel_id"]),
            "author": str(row["author"]),
            "comment": str(row["comment"]),
            "time": str(row["time"]),
            "like_count": int(float(row["like_count"])),
            "platform": "Instagram",
        }
        for _, row in result.iterrows()
    ]