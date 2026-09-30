import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from playwright.sync_api import (
    BrowserContext,
    Page,
    Response,
    sync_playwright,
)


# =========================================================
# 1. 基本設定
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
DEBUG_DIR = OUTPUT_DIR / "dcard_debug"
PROFILE_DIR = BASE_DIR / "dcard_browser_profile"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

PAGE_TIMEOUT_MS = 60_000


# =========================================================
# 2. 基本工具
# =========================================================
def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def extract_post_id(post_url_or_id: str) -> str:
    """
    從 Dcard 公開貼文網址或純文章 ID 取得文章 ID。
    """

    value = safe_text(post_url_or_id)

    if not value:
        raise ValueError("請輸入 Dcard 公開貼文網址或文章 ID。")

    if value.isdigit():
        return value

    parsed = urlparse(value)

    if "dcard.tw" not in parsed.netloc.lower():
        raise ValueError("這不是有效的 Dcard 網址。")

    match = re.search(r"/p/(\d+)", parsed.path)

    if not match:
        raise ValueError(
            "無法取得文章 ID。請使用公開貼文網址，例如："
            "https://www.dcard.tw/f/relationship/p/261898977"
        )

    return match.group(1)


def build_post_url(post_url_or_id: str, post_id: str) -> str:
    value = safe_text(post_url_or_id)

    if value.startswith(("http://", "https://")):
        return value

    return f"https://www.dcard.tw/f/all/p/{post_id}"


def get_author_name(comment: dict[str, Any]) -> str:
    if bool(comment.get("host")):
        return "原PO"

    nickname = safe_text(comment.get("nickname"))
    if nickname:
        return nickname

    school = safe_text(comment.get("school"))
    department = safe_text(comment.get("department"))

    if school and department:
        return f"{school}｜{department}"
    if school:
        return school

    gender = safe_text(comment.get("gender"))
    if gender:
        return f"匿名-{gender}"

    return "匿名"


# =========================================================
# 3. 遞迴搜尋 JSON 中的留言
# =========================================================
COMMENT_TEXT_KEYS = (
    "content",
    "text",
    "body",
    "message",
    "comment",
)

COMMENT_ID_KEYS = (
    "id",
    "commentId",
    "comment_id",
)

FLOOR_KEYS = (
    "floor",
    "floorNumber",
    "floor_number",
    "index",
)


def first_existing(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def normalize_comment_candidate(
    data: dict[str, Any]
) -> dict[str, Any] | None:
    """
    將可能的留言物件統一成 Dcard 欄位格式。

    判斷比舊版寬鬆：
    - 必須有文字
    - 並且至少有樓層、留言 ID、作者資訊或時間其中一項
    """

    content = first_existing(data, COMMENT_TEXT_KEYS)

    if not isinstance(content, str):
        return None

    content = content.strip()

    if len(content) < 1:
        return None

    comment_id = first_existing(data, COMMENT_ID_KEYS)
    floor = first_existing(data, FLOOR_KEYS)

    has_comment_signal = any([
        comment_id is not None,
        floor is not None,
        data.get("createdAt") is not None,
        data.get("updatedAt") is not None,
        data.get("likeCount") is not None,
        data.get("host") is not None,
        data.get("school") is not None,
        data.get("department") is not None,
    ])

    if not has_comment_signal:
        return None

    normalized = dict(data)
    normalized["content"] = content

    if normalized.get("id") is None and comment_id is not None:
        normalized["id"] = comment_id

    if normalized.get("floor") is None and floor is not None:
        normalized["floor"] = floor

    return normalized


def collect_comment_dicts(data: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    if isinstance(data, dict):
        candidate = normalize_comment_candidate(data)

        if candidate is not None:
            found.append(candidate)

        for value in data.values():
            found.extend(collect_comment_dicts(value))

    elif isinstance(data, list):
        for item in data:
            found.extend(collect_comment_dicts(item))

    return found


def find_post_info(data: Any, post_id: str) -> dict[str, Any] | None:
    if isinstance(data, dict):
        candidate_id = safe_text(
            data.get("id")
            or data.get("postId")
            or data.get("post_id")
        )

        if candidate_id == post_id and (
            "title" in data
            or "forumAlias" in data
            or "forumName" in data
        ):
            return data

        for value in data.values():
            found = find_post_info(value, post_id)
            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = find_post_info(item, post_id)
            if found:
                return found

    return None


# =========================================================
# 4. 收集瀏覽器實際收到的回應
# =========================================================
class DcardCollector:
    def __init__(self, post_id: str):
        self.post_id = post_id
        self.post_info: dict[str, Any] = {}
        self.comments: dict[str, dict[str, Any]] = {}
        self.response_number = 0
        self.last_error = ""

    def add_comment(self, comment: dict[str, Any]) -> None:
        content = safe_text(comment.get("content"))

        if not content:
            return

        comment_id = safe_text(
            comment.get("id")
            or comment.get("commentId")
            or comment.get("comment_id")
        )
        floor = safe_text(
            comment.get("floor")
            or comment.get("floorNumber")
        )

        key = comment_id or f"{floor}|{content}"

        if key and key != "|":
            self.comments[key] = comment

    def save_debug_response(
        self,
        response: Response,
        data: Any
    ) -> None:
        self.response_number += 1

        url_name = re.sub(
            r"[^a-zA-Z0-9_-]",
            "_",
            response.url
        )[-120:]

        file_path = (
            DEBUG_DIR
            / f"{self.response_number:04d}_{response.status}_{url_name}.json"
        )

        file_path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    def handle_response(self, response: Response) -> None:
        try:
            lower_url = response.url.lower()

            if "dcard.tw" not in lower_url:
                return

            resource_type = response.request.resource_type
            content_type = response.headers.get(
                "content-type",
                ""
            ).lower()

            interesting = (
                resource_type in {"xhr", "fetch"}
                or any(
                    word in lower_url
                    for word in (
                        "comment",
                        "post",
                        "graphql",
                        "api",
                        "service",
                    )
                )
            )

            if interesting:
                print(
                    f"🌐 {response.status}｜{resource_type}｜{response.url}"
                )

            if response.status >= 400:
                return

            # 先嘗試依 content-type 判定，再直接嘗試 response.json()
            if (
                "json" not in content_type
                and resource_type not in {"xhr", "fetch"}
            ):
                return

            try:
                data = response.json()
            except Exception:
                return

            self.save_debug_response(response, data)

            post_info = find_post_info(data, self.post_id)
            if post_info:
                self.post_info.update(post_info)

            candidates = collect_comment_dicts(data)

            if candidates:
                print(
                    f"💬 這筆回應辨識到 {len(candidates)} 個留言候選"
                )

            for candidate in candidates:
                self.add_comment(candidate)

        except Exception as error:
            self.last_error = str(error)


# =========================================================
# 5. DOM 備援
# =========================================================
def collect_visible_dom_comments(page: Page) -> list[dict[str, Any]]:
    """
    從頁面可見元素取文字。

    這是備援，因此輸出的作者、時間與按讚數可能不完整。
    """

    print("\n🔎 開始使用頁面元素備援方式...")

    selectors = [
        "[data-testid*='comment' i]",
        "[aria-label*='留言']",
        "[class*='comment' i]",
        "article",
        "main section",
    ]

    excluded_exact = {
        "登入",
        "註冊",
        "分享",
        "收藏",
        "追蹤",
        "回覆",
        "更多",
        "顯示更多",
        "查看留言",
        "載入更多",
    }

    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = min(locator.count(), 3000)

            print(f"🔎 {selector}：找到 {count} 個元素")

            for index in range(count):
                item = locator.nth(index)

                try:
                    if not item.is_visible():
                        continue

                    text = item.inner_text(timeout=1500).strip()
                except Exception:
                    continue

                if not text:
                    continue
                if text in seen:
                    continue
                if text in excluded_exact:
                    continue
                if len(text) < 2 or len(text) > 800:
                    continue

                # 過濾明顯的整篇頁面內容
                newline_count = text.count("\n")
                if newline_count > 20:
                    continue

                seen.add(text)

                results.append({
                    "id": f"dom-{len(results) + 1}",
                    "floor": len(results) + 1,
                    "content": text,
                    "createdAt": "",
                    "likeCount": 0,
                    "host": False,
                    "school": "",
                    "department": "",
                    "gender": "",
                })

            if len(results) >= 2:
                break

        except Exception as error:
            print(f"⚠️ {selector} 讀取失敗：{error}")

    return results


# =========================================================
# 6. 轉成 CSV
# =========================================================
def build_dataframe(
    post_info: dict[str, Any],
    comments: list[dict[str, Any]],
    post_id: str,
    post_url: str,
) -> pd.DataFrame:
    post_title = safe_text(post_info.get("title"))
    forum = safe_text(
        post_info.get("forumAlias")
        or post_info.get("forumName")
        or post_info.get("forum")
    )

    rows: list[dict[str, Any]] = []

    for item in comments:
        content = safe_text(item.get("content"))

        if not content:
            continue

        rows.append({
            "platform": "Dcard",
            "post_id": post_id,
            "post_url": post_url,
            "post_title": post_title,
            "forum": forum,
            "comment_id": safe_text(
                item.get("id")
                or item.get("commentId")
                or item.get("comment_id")
            ),
            "floor": (
                item.get("floor")
                or item.get("floorNumber")
                or item.get("floor_number")
            ),
            "author": get_author_name(item),
            "comment": content,
            "time": safe_text(
                item.get("createdAt")
                or item.get("updatedAt")
                or item.get("time")
            ),
            "like_count": safe_int(
                item.get("likeCount")
                or item.get("like_count")
                or item.get("likes")
            ),
            "is_host": bool(item.get("host", False)),
            "gender": safe_text(item.get("gender")),
            "school": safe_text(item.get("school")),
            "department": safe_text(item.get("department")),
        })

    columns = [
        "platform",
        "post_id",
        "post_url",
        "post_title",
        "forum",
        "comment_id",
        "floor",
        "author",
        "comment",
        "time",
        "like_count",
        "is_host",
        "gender",
        "school",
        "department",
    ]

    df = pd.DataFrame(rows, columns=columns)

    if df.empty:
        return df

    df = df.drop_duplicates(
        subset=["comment_id", "floor", "comment"],
        keep="first"
    ).reset_index(drop=True)

    df["_floor"] = pd.to_numeric(
        df["floor"],
        errors="coerce"
    )

    df = (
        df.sort_values("_floor", na_position="last")
        .drop(columns=["_floor"])
        .reset_index(drop=True)
    )

    return df


# =========================================================
# 7. 瀏覽器設定
# =========================================================
def prepare_page(context: BrowserContext) -> Page:
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(PAGE_TIMEOUT_MS)
    return page


def crawl_dcard_comments(
    post_url_or_id: str,
    headless: bool = False
) -> str:
    """
    開啟 Dcard 公開貼文，讓使用者手動把留言載入完成，
    再從瀏覽器網路回應及頁面元素擷取留言。
    """

    post_id = extract_post_id(post_url_or_id)
    post_url = build_post_url(post_url_or_id, post_id)

    # 每次執行先清掉舊的 debug JSON，避免混在一起
    for old_file in DEBUG_DIR.glob("*.json"):
        try:
            old_file.unlink()
        except OSError:
            pass

    collector = DcardCollector(post_id)

    print("\n==================================")
    print("🚀 Dcard 留言擷取程式")
    print("==================================")
    print(f"📌 文章 ID：{post_id}")
    print(f"🔗 網址：{post_url}")
    print("\n接下來會打開 Chromium 視窗。")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR.resolve()),
            headless=headless,
            viewport={"width": 1440, "height": 960},
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            args=["--start-maximized"],
        )

        try:
            page = prepare_page(context)
            page.on("response", collector.handle_response)

            page.goto(
                post_url,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT_MS
            )

            print("\n請在 Chromium 視窗中完成以下動作：")
            print("1. 確認頁面已顯示正確貼文。")
            print("2. 網站要求登入或驗證時，請手動完成。")
            print("3. 慢慢往下滑，讓留言全部載入。")
            print("4. 有『查看更多留言』時請點開。")
            print("5. 完成後不要關閉 Chromium。")

            input(
                "\n完成以上操作後，回到 PowerShell 按 Enter："
            )

            # 使用者按 Enter 後再等兩秒，讓最後請求處理完成
            page.wait_for_timeout(2000)

            comments = list(collector.comments.values())

            print(
                f"\n📦 網路回應共取得 {len(comments)} 則留言候選。"
            )

            if not comments:
                comments = collect_visible_dom_comments(page)

            if not collector.post_info:
                try:
                    collector.post_info["title"] = page.title()
                except Exception:
                    collector.post_info["title"] = ""

            df = build_dataframe(
                post_info=collector.post_info,
                comments=comments,
                post_id=post_id,
                post_url=post_url,
            )

            if df.empty:
                print("\n❌ 仍然沒有辨識到留言。")
                print(
                    "除錯 JSON 已保存到："
                    f"{DEBUG_DIR.resolve()}"
                )
                raise ValueError(
                    "沒有抓到可分析的留言。"
                    "請把 PowerShell 中所有「🌐」開頭的內容，"
                    "以及 outputs\\dcard_debug 資料夾中的 JSON 提供給我。"
                )

            output_path = OUTPUT_DIR / f"raw_dcard_{post_id}.csv"

            df.to_csv(
                output_path,
                index=False,
                encoding="utf-8-sig"
            )

            print("\n==================================")
            print("🎉 Dcard 留言輸出完成")
            print("==================================")
            print(f"✅ 有效資料數：{len(df)}")
            print(f"📄 CSV：{output_path.resolve()}")

            if collector.last_error:
                print(f"ℹ️ 部分回應略過：{collector.last_error}")

            return str(output_path.resolve())

        finally:
            context.close()


# =========================================================
# 8. 單獨測試
# =========================================================
if __name__ == "__main__":
    target = input(
        "\n請貼上 Dcard 公開貼文網址或文章 ID："
    ).strip()

    try:
        csv_path = crawl_dcard_comments(
            target,
            headless=False
        )

        print("\n✅ 測試成功。")
        print("這個 CSV 已包含 comment 欄位：")
        print(csv_path)

    except KeyboardInterrupt:
        print("\n⚠️ 使用者中止程式。")

    except Exception as error:
        print(f"\n❌ 執行失敗：{error}")