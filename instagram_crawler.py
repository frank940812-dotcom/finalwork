from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import instaloader

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / "instagram_session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_MAX_COMMENTS = 300


def extract_shortcode(instagram_url: str) -> str:
    instagram_url = str(instagram_url).strip()
    if not instagram_url:
        raise ValueError("請提供 Instagram 貼文或 Reels 網址。")

    clean_url = instagram_url.split("?")[0].split("#")[0]
    match = re.search(
        r"instagram\.com/(?:reel|reels|p|tv)/([^/?#]+)/?",
        clean_url,
        flags=re.IGNORECASE,
    )

    if not match:
        raise ValueError("無法解析 Instagram 網址。請貼上 /reel/、/p/ 或 /tv/ 格式的網址。")

    return match.group(1).strip("/")


def create_loader() -> instaloader.Instaloader:
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=False,
        max_connection_attempts=2,
        request_timeout=25.0,
    )
    loader.context._session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    return loader


def get_session_filename(username: str) -> Path:
    safe_username = re.sub(r"[^A-Za-z0-9_.-]", "_", username.strip())
    return SESSION_DIR / f"session-{safe_username}"


def load_login_session(loader: instaloader.Instaloader) -> str | None:
    username = os.getenv("IG_USERNAME", "").strip()
    if username:
        session_file = get_session_filename(username)
        if session_file.exists():
            try:
                loader.load_session_from_file(username=username, filename=str(session_file))
                return username
            except Exception as e:
                print(f"⚠️ 載入指定 Session 失敗: {e}")

    session_files = list(SESSION_DIR.glob("session-*"))
    if not session_files:
        return None

    target_session = session_files[0]
    session_user = target_session.name.replace("session-", "")

    try:
        loader.load_session_from_file(username=session_user, filename=str(target_session))
        return session_user
    except Exception as e:
        print(f"⚠️ 自動載入 Session 失敗: {e}")
        return None


def create_login_session(username: str) -> Path:
    username = str(username).strip()
    if not username:
        raise ValueError("請提供 Instagram 帳號名稱。")

    loader = create_loader()
    print("\n" + "=" * 62)
    print("建立 Instagram 登入 Session")
    print("密碼只會在目前終端機輸入，不會寫入程式碼。")
    print("=" * 62)

    loader.interactive_login(username)
    session_file = get_session_filename(username)
    loader.save_session_to_file(filename=str(session_file))
    print(f"\nSession 已儲存：{session_file}\n")
    return session_file


def normalize_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    try:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def fetch_reel_information(instagram_url: str) -> dict[str, Any]:
    shortcode = extract_shortcode(instagram_url)
    clean_url = f"https://www.instagram.com/p/{shortcode}/"
    return {
        "reel_id": shortcode,
        "shortcode": shortcode,
        "username": "",
        "caption": "",
        "url": clean_url,
        "created_at": normalize_datetime(datetime.now()),
        "like_count": 0,
        "comment_count": 0,
        "views": 0,
        "media_type": "Post",
        "logged_in_as": "System",
    }


def _fetch_comments_via_playwright(shortcode: str, max_comments: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    透過 Playwright 注入 Session，並於背景攔截 GraphQL/API 網路封包串流，精準抓取百則留言與回覆
    """
    clean_url = f"https://www.instagram.com/p/{shortcode}/"
    comments: list[dict[str, Any]] = []
    reel_info = fetch_reel_information(clean_url)

    if sync_playwright is None:
        raise RuntimeError("未安裝 playwright 套件。")

    intercepted_raw_comments: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="zh-TW",
        )

        try:
            loader = create_loader()
            session_user = load_login_session(loader)
            if session_user and loader.context._session.cookies:
                pw_cookies = []
                for c in loader.context._session.cookies:
                    pw_cookies.append({
                        "name": c.name,
                        "value": c.value,
                        "domain": ".instagram.com",
                        "path": "/",
                    })
                context.add_cookies(pw_cookies)
                print(f"🔑 [Playwright] 成功注入 Instagram 憑證：{session_user}")
        except Exception as e:
            print(f"⚠️ [Playwright] Cookie 注入略過: {e}")

        page = context.new_page()

        # 🚨【核心：直接監聽 Instagram 後端回傳的所有留言封包】
        def handle_response(response):
            try:
                url = response.url
                if ("/comments" in url or "graphql" in url or "api/v1" in url) and response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type:
                        data = response.json()
                        # 解析頂層留言與子回覆
                        items_to_process = []
                        if "comments" in data and isinstance(data["comments"], list):
                            items_to_process.extend(data["comments"])
                        elif "data" in data:
                            conn = data.get("data", {}).get("xdt_api__v1__media__comments__connection", {})
                            edges = conn.get("edges", []) if isinstance(conn, dict) else []
                            for edge in edges:
                                node = edge.get("node", {})
                                if node:
                                    items_to_process.append(node)

                        for item in items_to_process:
                            txt = item.get("text", "") or ""
                            user_obj = item.get("user", {}) or item.get("owner", {})
                            username = user_obj.get("username", "") or "ig_user"
                            created_time = item.get("created_at_utc", None) or item.get("created_at", None)
                            formatted_time = normalize_datetime(datetime.fromtimestamp(created_time)) if created_time else normalize_datetime(datetime.now())

                            if txt.strip():
                                intercepted_raw_comments.append({
                                    "reel_id": shortcode,
                                    "author": username,
                                    "comment": txt.strip(),
                                    "time": formatted_time,
                                    "like_count": int(item.get("comment_like_count", 0) or item.get("like_count", 0) or 0),
                                    "platform": "Instagram",
                                })

                            # 解析子回覆 (child comments)
                            child_list = item.get("child_comments", []) or []
                            for child in child_list:
                                c_txt = child.get("text", "") or ""
                                c_user = child.get("user", {}).get("username", "") or "ig_user"
                                if c_txt.strip():
                                    intercepted_raw_comments.append({
                                        "reel_id": shortcode,
                                        "author": c_user,
                                        "comment": c_txt.strip(),
                                        "time": formatted_time,
                                        "like_count": int(child.get("comment_like_count", 0) or 0),
                                        "platform": "Instagram",
                                    })
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"🌐 [Playwright] 正在載入頁面：{clean_url}")
        page.goto(clean_url, wait_until="domcontentloaded", timeout=35000)
        time.sleep(3.5)

        # 抓取作者與標題
        try:
            author_el = page.query_selector("header h2, header a, span._ap3a")
            if author_el:
                reel_info["username"] = author_el.inner_text().strip()
            title_el = page.query_selector("h1, div._a9zs span")
            if title_el:
                reel_info["caption"] = title_el.inner_text().strip()
        except Exception:
            pass

        print(f"📜 [Playwright] 正在深度滾動觸發封包加載（目標最多 {max_comments} 則）...")
        for loop in range(30):
            if len(intercepted_raw_comments) >= max_comments:
                break

            # 點擊加載與展開回覆
            try:
                page.evaluate("""
                    const buttons = Array.from(document.querySelectorAll('span, button, div[role="button"], svg[aria-label="載入更多留言"]'));
                    buttons.forEach(el => {
                        const t = el.innerText || '';
                        if (t.includes('載入更多留言') || t.includes('查看回覆') || t.includes('View replies') || t.includes('Load more') || t.includes('查看全部')) {
                            el.click();
                        }
                    });
                    const scrollables = Array.from(document.querySelectorAll('div, ul')).filter(el => {
                        return el.scrollHeight > el.clientHeight && el.clientHeight > 150;
                    });
                    if (scrollables.length > 0) {
                        scrollables.forEach(s => { s.scrollTop += 2500; });
                    }
                """)
                page.keyboard.press("PageDown")
                page.mouse.wheel(0, 3000)
            except Exception:
                pass

            time.sleep(1.2)

        # 彙整攔截到的封包資料
        seen_keys = set()
        for item in intercepted_raw_comments:
            if len(comments) >= max_comments:
                break
            key = f"{item['author']}_{item['comment']}"
            if key not in seen_keys:
                seen_keys.add(key)
                comments.append(item)

        # 若封包攔截筆數較少，輔以 DOM 補充
        if len(comments) < 20:
            raw_blocks = page.evaluate("""
                () => {
                    const results = [];
                    const elements = document.querySelectorAll('ul > li, ul > div, div.x78zum5.xdt5ytf.x1iyjqo2, div.x9f619');
                    elements.forEach(el => {
                        const txt = el.innerText ? el.innerText.trim() : '';
                        if (txt && (txt.includes('回覆') || txt.includes('讚') || txt.includes('Reply') || txt.includes('Like') || txt.includes('分鐘') || txt.includes('小時') || txt.includes('天'))) {
                            results.push(txt);
                        }
                    });
                    return results;
                }
            """)
            for block in raw_blocks:
                if len(comments) >= max_comments:
                    break
                lines = [l.strip() for l in block.split("\n") if l.strip()]
                if len(lines) >= 2:
                    user = lines[0]
                    if any(g in user for g in ["登入", "註冊", "•", "Meta", "人"]) or len(user) > 30:
                        continue
                    content_parts = [
                        l for l in lines[1:]
                        if l not in ["讚", "回覆", "Like", "Reply", "•", "翻譯年糕", "已編輯", "隱藏回覆"]
                        and not re.match(r"^\d+\s*(個讚|小時|天|週|分|秒|分鐘)$", l)
                        and not re.search(r"^\d+[小時天週分秒分鐘前]+$", l)
                        and not ("查看全部" in l and "則回覆" in l)
                    ]
                    content = " ".join(content_parts).strip()
                    content = re.sub(r"^\d+\s*(分鐘|小時|天|週|分|秒|m|h|d|w)\s*", "", content).strip()
                    content = re.sub(r"(翻譯年糕|已編輯|回覆|讚|隱藏回覆)$", "", content).strip()
                    if content and len(content) >= 1:
                        key = f"{user}_{content}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            comments.append({
                                "reel_id": shortcode,
                                "author": user,
                                "comment": content,
                                "time": normalize_datetime(datetime.now()),
                                "like_count": 0,
                                "platform": "Instagram",
                            })

        browser.close()

    return reel_info, comments


def fetch_reel_comments(
    instagram_url: str,
    max_comments: int = DEFAULT_MAX_COMMENTS,
) -> dict[str, Any]:
    shortcode = extract_shortcode(instagram_url)
    max_comments = int(max_comments)

    if max_comments < 1:
        raise ValueError("max_comments 必須大於 0。")

    errors = []

    # 先用 Instaloader + 登入 Session 抓真實留言
    try:
        loader = create_loader()
        session_user = load_login_session(loader)

        if session_user:
            print(f"🔑 [Instaloader] 已登入：{session_user}")
            post = instaloader.Post.from_shortcode(
                loader.context,
                shortcode
            )

            reel_info = {
                "reel_id": shortcode,
                "shortcode": shortcode,
                "username": post.owner_username or "",
                "caption": post.caption or "",
                "url": str(instagram_url).strip(),
                "created_at": normalize_datetime(post.date_local),
                "like_count": int(post.likes or 0),
                "comment_count": int(post.comments or 0),
                "views": int(getattr(post, "video_view_count", 0) or 0),
                "media_type": "Reel/Video" if getattr(post, "is_video", False) else "Post",
                "logged_in_as": session_user,
            }

            comments = []
            seen = set()

            for comment in post.get_comments():
                if len(comments) >= max_comments:
                    break

                author = getattr(getattr(comment, "owner", None), "username", "") or "instagram_user"
                text = str(getattr(comment, "text", "") or "").strip()

                if text:
                    key = (author, text)
                    if key not in seen:
                        seen.add(key)
                        comments.append({
                            "reel_id": shortcode,
                            "author": author,
                            "comment": text,
                            "time": normalize_datetime(getattr(comment, "created_at_utc", None)),
                            "like_count": int(getattr(comment, "likes_count", 0) or 0),
                            "platform": "Instagram",
                        })

                answers = getattr(comment, "answers", None)
                if answers:
                    for answer in answers:
                        if len(comments) >= max_comments:
                            break
                        a_author = getattr(getattr(answer, "owner", None), "username", "") or "instagram_user"
                        a_text = str(getattr(answer, "text", "") or "").strip()
                        if not a_text:
                            continue
                        key = (a_author, a_text)
                        if key in seen:
                            continue
                        seen.add(key)
                        comments.append({
                            "reel_id": shortcode,
                            "author": a_author,
                            "comment": a_text,
                            "time": normalize_datetime(getattr(answer, "created_at_utc", None)),
                            "like_count": int(getattr(answer, "likes_count", 0) or 0),
                            "platform": "Instagram",
                        })

            if comments:
                reel_info["comment_count"] = len(comments)
                print(f"✅ [Instaloader] 共抓到 {len(comments)} 則留言")
                return {"reel": reel_info, "comments": comments}

            errors.append("Instaloader 沒有取得任何留言")
        else:
            errors.append("找不到有效的 Instagram Session")

    except Exception as err:
        errors.append(f"Instaloader：{err}")
        print(f"⚠️ Instaloader 抓取失敗：{err}")

    # 再用 Playwright 當備援
    try:
        reel_info, comments = _fetch_comments_via_playwright(shortcode, max_comments)
        if comments:
            reel_info["comment_count"] = len(comments)
            print(f"✅ [Playwright] 共抓到 {len(comments)} 則留言")
            return {"reel": reel_info, "comments": comments}

        errors.append("Playwright 沒有取得任何留言")

    except Exception as err:
        errors.append(f"Playwright：{err}")
        print(f"⚠️ Playwright 抓取失敗：{err}")

    # 重要：不要再塞一則假的『貼文分析完成』
    raise RuntimeError(
        "Instagram 真實留言抓取失敗。\n"
        "這次不會再用假的 1 則留言代替。\n\n"
        "請先確認 Instagram Session 是否有效，並重新登入後再測試。\n"
        "詳細錯誤：\n- " + "\n- ".join(errors)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Instagram 真實留言擷取工具")
    parser.add_argument("--login", type=str, help="建立 Instagram 登入 Session")
    parser.add_argument("--url", type=str, help="測試擷取指定 Instagram 網址")
    parser.add_argument("--max-comments", type=int, default=300, help="測試時最多取得的留言數")
    args = parser.parse_args()

    if args.login:
        create_login_session(args.login)
        return

    if args.url:
        result = fetch_reel_comments(instagram_url=args.url, max_comments=args.max_comments)
        reel = result["reel"]
        comments = result["comments"]

        print("\n" + "=" * 62)
        print("Instagram 留言擷取完成")
        print(f"Shortcode：{reel['shortcode']}")
        print(f"帳號：@{reel['username']}")
        print(f"共擷取留言：{len(comments)} 則")
        print("=" * 62)

        for index, comment in enumerate(comments[:15], start=1):
            print(f"{index}. @{comment['author']}：{comment['comment']}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()