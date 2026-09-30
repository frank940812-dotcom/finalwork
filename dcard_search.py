from pathlib import Path
from typing import Any

import pandas as pd


# =========================================================
# 1. 基本路徑
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "dcard_data"

ARTICLES_FILE = DATA_DIR / "dcard_articles.csv"
COMMENTS_FILE = DATA_DIR / "dcard_comments.csv"


# =========================================================
# 2. 共用工具
# =========================================================
def _check_files() -> None:
    """確認本機 Dcard 資料檔存在。"""

    missing_files = []

    if not ARTICLES_FILE.exists():
        missing_files.append(str(ARTICLES_FILE))

    if not COMMENTS_FILE.exists():
        missing_files.append(str(COMMENTS_FILE))

    if missing_files:
        raise FileNotFoundError(
            "找不到以下 Dcard 本機資料檔：\n"
            + "\n".join(missing_files)
        )


def _read_articles() -> pd.DataFrame:
    """讀取文章資料。"""

    _check_files()

    df = pd.read_csv(
        ARTICLES_FILE,
        encoding="utf-8-sig"
    )

    required_columns = {
        "article_id",
        "forum",
        "forum_name",
        "title",
        "url",
        "created_at",
        "like_count",
        "comment_count",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "dcard_articles.csv 缺少欄位："
            + ", ".join(sorted(missing_columns))
        )

    df["article_id"] = df["article_id"].astype(str)

    return df


def _read_comments() -> pd.DataFrame:
    """讀取留言資料。"""

    _check_files()

    df = pd.read_csv(
        COMMENTS_FILE,
        encoding="utf-8-sig"
    )

    required_columns = {
        "article_id",
        "author",
        "comment",
        "time",
        "like_count",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "dcard_comments.csv 缺少欄位："
            + ", ".join(sorted(missing_columns))
        )

    df["article_id"] = df["article_id"].astype(str)

    return df


# =========================================================
# 3. 搜尋文章
# =========================================================
def search_dcard_articles(
    forum_alias: str,
    keyword: str,
    max_results: int = 10,
    headless: bool = False,
) -> list[dict[str, Any]]:
    """
    從本機 dcard_articles.csv 搜尋文章。

    參數：
    forum_alias：
        例如 relationship、money、mood

    keyword：
        例如 出軌、遠距離、台積電

    max_results：
        最多回傳幾篇

    headless：
        為了相容原本 main_api.py 保留此參數，
        但本機 CSV 版本不會使用瀏覽器。
    """

    del headless

    forum_alias = str(forum_alias).strip()
    keyword = str(keyword).strip()

    if not forum_alias:
        raise ValueError("請提供 Dcard 看板代碼。")

    if not keyword:
        raise ValueError("請輸入 Dcard 搜尋關鍵字。")

    if max_results < 1:
        raise ValueError("max_results 必須大於 0。")

    df = _read_articles()

    forum_mask = (
        df["forum"]
        .astype(str)
        .str.casefold()
        .eq(forum_alias.casefold())
    )

    keyword_mask = (
        df["title"]
        .astype(str)
        .str.contains(
            keyword,
            case=False,
            na=False,
            regex=False
        )
    )

    result_df = (
        df[forum_mask & keyword_mask]
        .copy()
    )

    if "created_at" in result_df.columns:
        result_df["created_at"] = pd.to_datetime(
            result_df["created_at"],
            errors="coerce"
        )

        result_df = result_df.sort_values(
            by="created_at",
            ascending=False,
            na_position="last"
        )

        result_df["created_at"] = (
            result_df["created_at"]
            .dt.strftime("%Y-%m-%d")
            .fillna("")
        )

    result_df = result_df.head(max_results)

    articles = []

    for _, row in result_df.iterrows():
        articles.append({
            "id": str(row["article_id"]),
            "title": str(row["title"]),
            "url": str(row["url"]),
            "forum": str(row["forum"]),
            "forum_name": str(row["forum_name"]),
            "created_at": str(row["created_at"]),
            "like_count": int(row["like_count"]),
            "comment_count": int(row["comment_count"]),
        })

    return articles


# =========================================================
# 4. 取得指定文章留言
# =========================================================
def get_dcard_comments(
    article_id: str
) -> list[dict[str, Any]]:
    """
    從本機 dcard_comments.csv 取得指定文章留言。
    """

    article_id = str(article_id).strip()

    if not article_id:
        raise ValueError("請提供 Dcard 文章 ID。")

    df = _read_comments()

    result_df = (
        df[
            df["article_id"]
            .astype(str)
            .eq(article_id)
        ]
        .copy()
    )

    comments = []

    for _, row in result_df.iterrows():
        comments.append({
            "article_id": str(row["article_id"]),
            "author": str(row["author"]),
            "comment": str(row["comment"]),
            "time": str(row["time"]),
            "like_count": int(row["like_count"]),
            "platform": "Dcard",
        })

    return comments


# =========================================================
# 5. 單獨測試
# =========================================================
if __name__ == "__main__":
    print("\nDcard 本機資料搜尋測試")

    forum = input(
        "請輸入看板代碼，例如 relationship："
    ).strip()

    keyword = input(
        "請輸入關鍵字，例如 出軌："
    ).strip()

    try:
        results = search_dcard_articles(
            forum_alias=forum,
            keyword=keyword,
            max_results=10,
        )

        if not results:
            print("\n沒有找到符合條件的文章。")

        else:
            print(f"\n找到 {len(results)} 篇文章：")

            for index, article in enumerate(
                results,
                start=1
            ):
                print(
                    f"\n{index}. {article['title']}"
                )
                print(
                    f"   文章 ID：{article['id']}"
                )
                print(
                    f"   看板：{article['forum_name']}"
                )
                print(
                    f"   日期：{article['created_at']}"
                )
                print(
                    f"   愛心：{article['like_count']}"
                )
                print(
                    f"   留言：{article['comment_count']}"
                )

            selected_id = input(
                "\n輸入要查看留言的文章 ID，"
                "直接按 Enter 可略過："
            ).strip()

            if selected_id:
                comments = get_dcard_comments(
                    selected_id
                )

                print(
                    f"\n文章 {selected_id} "
                    f"共有 {len(comments)} 則留言："
                )

                for comment in comments:
                    print(
                        f"- {comment['author']}："
                        f"{comment['comment']}"
                    )

    except Exception as error:
        print(f"\n執行失敗：{error}")