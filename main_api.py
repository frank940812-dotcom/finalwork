from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

import os
import ssl
import smtplib
import secrets
import json
import urllib.parse
import urllib.request
from email.message import EmailMessage
import pandas as pd

# 專題模組
import crawler
import boom_emotion
import topic
import my_db_import
import word_report
import dcard_search
import instagram_crawler


app = FastAPI(
    title="專題大數據分析 API 總部 - 完全體"
)


# =====================================================================
# 請求資料格式
# =====================================================================
class KeywordRequest(BaseModel):
    keyword: str


class VideoRequest(BaseModel):
    # 可以傳完整 YouTube 網址，也可以傳 video_id
    url: str


class DcardSearchRequest(BaseModel):
    forum: str
    keyword: str


class DcardAnalyzeRequest(BaseModel):
    article_id: str
    title: str = ""
    url: str = ""




class InstagramAnalyzeRequest(BaseModel):
    reel_id: str = ""
    url: str = ""
    caption: str = ""


class SendVerificationRequest(BaseModel):
    username: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    verification_code: str


class LoginRequest(BaseModel):
    username: str
    password: str


def extract_bearer_token(
    authorization: str | None
):
    if not authorization:
        return None

    authorization = authorization.strip()

    if not authorization.lower().startswith(
        "bearer "
    ):
        return None

    return authorization[7:].strip()


def get_optional_current_user(
    authorization: str | None
):
    token = extract_bearer_token(
        authorization
    )

    if not token:
        return None

    return my_db_import.get_user_by_token(
        token
    )


def require_current_user(
    authorization: str | None
):
    user = get_optional_current_user(
        authorization
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="請先登入後再使用此功能。"
        )

    return user


# =====================================================================
# API Key 設定
# =====================================================================
# 建議將 YouTube API Key 設定在 Windows 環境變數：
#
# setx YOUTUBE_API_KEY "你的 API Key"
#
# 設定完成後，要重新開啟終端機。
YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY"
)

if YOUTUBE_API_KEY:
    crawler.API_KEY = YOUTUBE_API_KEY


def send_verification_email(
    recipient_email: str,
    verification_code: str
):
    sender_email = os.getenv(
        "MAIL_SENDER",
        ""
    ).strip()

    app_password = os.getenv(
        "MAIL_APP_PASSWORD",
        ""
    ).strip()

    if not sender_email or not app_password:
        raise RuntimeError(
            "尚未設定寄件信箱。請先設定 MAIL_SENDER 與 MAIL_APP_PASSWORD。"
        )

    message = EmailMessage()
    message["Subject"] = "Social Insight 註冊驗證碼"
    message["From"] = sender_email
    message["To"] = recipient_email

    message.set_content(
        f"""你的 Social Insight 註冊驗證碼是：

{verification_code}

驗證碼 10 分鐘內有效。
若這不是你本人操作，可以忽略此信件。
"""
    )

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=context,
        timeout=20
    ) as smtp:
        smtp.login(
            sender_email,
            app_password
        )
        smtp.send_message(message)


# =====================================================================
# 🔐 帳號系統：寄送 6 位數 Email 驗證碼
# =====================================================================
@app.post("/api/auth/send-verification")
def send_registration_verification(
    req: SendVerificationRequest
):
    try:
        email = my_db_import.normalize_gmail(
            req.username
        )

        if my_db_import.user_exists(email):
            raise HTTPException(
                status_code=400,
                detail="此 Gmail 已經註冊過，請直接登入。"
            )

        verification_code = (
            f"{secrets.randbelow(1_000_000):06d}"
        )

        # 先建立驗證紀錄，這裡會檢查 60 秒冷卻
        record = (
            my_db_import.create_email_verification(
                email,
                verification_code
            )
        )

        try:
            send_verification_email(
                email,
                verification_code
            )

        except Exception:
            # 寄信失敗時，讓這筆驗證碼失效
            try:
                my_db_import.verify_email_code(
                    email,
                    "000000"
                )
            except Exception:
                pass
            raise

        return {
            "status": "success",
            "message": "6 位數驗證碼已寄到你的 Gmail。",
            "expires_in_minutes": 10
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"驗證碼寄送失敗：{str(error)}"
        )


# =====================================================================
# 🔐 帳號系統：註冊
# =====================================================================
@app.post("/api/auth/register")
def register_account(
    req: RegisterRequest
):
    try:
        email = my_db_import.normalize_gmail(
            req.username
        )

        if my_db_import.user_exists(email):
            raise HTTPException(
                status_code=400,
                detail="此 Gmail 已經註冊過，請直接登入。"
            )

        my_db_import.verify_email_code(
            email,
            req.verification_code
        )

        user = my_db_import.register_user(
            email,
            req.password
        )

        token = my_db_import.create_user_session(
            user["user_id"]
        )

        return {
            "status": "success",
            "token": token,
            "user": user,
            "message": "註冊成功。"
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"註冊失敗：{str(error)}"
        )


# =====================================================================
# 🔐 帳號系統：登入
# =====================================================================
@app.post("/api/auth/login")
def login_account(
    req: LoginRequest
):
    try:
        user = my_db_import.authenticate_user(
            req.username,
            req.password
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="帳號或密碼錯誤。"
            )

        token = my_db_import.create_user_session(
            user["user_id"]
        )

        return {
            "status": "success",
            "token": token,
            "user": user,
            "message": "登入成功。"
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"登入失敗：{str(error)}"
        )


# =====================================================================
# 🔐 帳號系統：目前登入者
# =====================================================================
@app.get("/api/auth/me")
def current_account(
    authorization: str | None = Header(
        default=None
    )
):
    user = require_current_user(
        authorization
    )

    return {
        "status": "success",
        "user": user
    }


# =====================================================================
# 🔐 帳號系統：登出
# =====================================================================
@app.post("/api/auth/logout")
def logout_account(
    authorization: str | None = Header(
        default=None
    )
):
    token = extract_bearer_token(
        authorization
    )

    if token:
        my_db_import.delete_user_session(
            token
        )

    return {
        "status": "success",
        "message": "已登出。"
    }


def get_youtube_video_title(video_id):
    """
    使用 YouTube Data API 取得影片真正標題。
    失敗時回傳 None，不影響主要分析流程。
    """
    video_id = str(video_id or "").strip()

    if not video_id or not crawler.API_KEY:
        return None

    try:
        query = urllib.parse.urlencode(
            {
                "part": "snippet",
                "id": video_id,
                "key": crawler.API_KEY
            }
        )

        api_url = (
            "https://www.googleapis.com/"
            "youtube/v3/videos?"
            + query
        )

        with urllib.request.urlopen(
            api_url,
            timeout=15
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

        items = payload.get("items", [])

        if not items:
            return None

        title = (
            items[0]
            .get("snippet", {})
            .get("title", "")
            .strip()
        )

        return title or None

    except Exception as error:
        print(
            f"⚠️ YouTube 影片標題取得失敗：{error}"
        )
        return None


def repair_youtube_history_titles(
    history_rows,
    user_id
):
    """
    舊版紀錄若仍是「YouTube 影片 + ID」，
    讀取歷史列表時自動向 YouTube API 查標題並回填資料庫。
    """
    repaired_rows = []

    for row in history_rows:
        row_copy = dict(row)

        if row_copy.get("platform") == "YouTube":
            target_id = str(
                row_copy.get("target_id") or ""
            ).strip()

            current_title = str(
                row_copy.get("target_title") or ""
            ).strip()

            looks_like_old_title = (
                not current_title
                or current_title == target_id
                or current_title.startswith(
                    "YouTube 影片 "
                )
            )

            if target_id and looks_like_old_title:
                real_title = get_youtube_video_title(
                    target_id
                )

                if real_title:
                    row_copy["target_title"] = real_title

                    try:
                        my_db_import.update_analysis_history_title(
                            analysis_id=row_copy["analysis_id"],
                            user_id=user_id,
                            target_title=real_title
                        )
                    except Exception as error:
                        print(
                            f"⚠️ 歷史影片標題回填失敗：{error}"
                        )

        repaired_rows.append(row_copy)

    return repaired_rows


# =====================================================================
# 🚪 窗口一：用關鍵字搜尋熱門影片清單
# =====================================================================
@app.post("/api/search_videos")
def search_videos(req: KeywordRequest):
    try:
        user_keyword = req.keyword.strip()

        if not user_keyword:
            raise ValueError(
                "請輸入搜尋關鍵字。"
            )

        if not crawler.API_KEY:
            raise ValueError(
                "尚未設定 YouTube API Key。"
            )

        print(
            "\n🔍 收到影片搜尋請求！"
        )

        print(
            f"正在搜尋關鍵字：{user_keyword}"
        )

        video_list = (
            crawler.search_videos_info_only(
                user_keyword,
                max_results=5
            )
        )

        if not video_list:
            return {
                "status": "success",
                "videos": [],
                "message": "沒有找到相關影片。"
            }

        print(
            f"✅ 成功找到 {len(video_list)} 支影片。"
        )

        return {
            "status": "success",
            "videos": video_list
        }

    except Exception as error:
        print(
            f"❌ 搜尋影片清單失敗：{error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"搜尋清單失敗：{str(error)}"
            )
        )


# =====================================================================
# 🚪 窗口二：執行完整分析管線
# =====================================================================
@app.post("/api/run_pipeline")
def run_full_system(
    req: VideoRequest,
    authorization: str | None = Header(
        default=None
    )
):
    try:
        current_user = get_optional_current_user(
            authorization
        )

        user_input = req.url.strip()

        if not user_input:
            raise ValueError(
                "請提供 YouTube 影片網址或影片 ID。"
            )

        if not crawler.API_KEY:
            raise ValueError(
                "尚未設定 YouTube API Key。"
            )

        print(
            "\n🚀 核心分析管線啟動！"
        )

        print(
            f"分析目標：{user_input}"
        )

        # =============================================================
        # 判斷輸入是網址還是影片 ID
        # =============================================================
        if (
            "http://" in user_input
            or "https://" in user_input
            or "youtu.be" in user_input
            or "youtube.com" in user_input
        ):
            video_id = crawler.extract_video_id(
                user_input
            )

        else:
            video_id = user_input

        if not video_id:
            raise ValueError(
                "無法解析 YouTube 影片 ID。"
            )

        print(
            f"🎬 影片 ID：{video_id}"
        )

        video_title = (
            get_youtube_video_title(
                video_id
            )
            or f"YouTube 影片 {video_id}"
        )

        print(
            f"📝 影片標題：{video_title}"
        )

        # =============================================================
        # 建立 outputs 資料夾
        # =============================================================
        current_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        output_dir = os.path.join(
            current_dir,
            "outputs"
        )

        os.makedirs(
            output_dir,
            exist_ok=True
        )

        # =============================================================
        # 第 1 站：抓取原始留言
        # =============================================================
        print(
            "▶️ [步驟 1] 正在抓取影片留言……"
        )

        raw_comments = (
            crawler.fetch_comments_and_replies(
                video_id
            )
        )

        if not raw_comments:
            raise RuntimeError(
                "該影片沒有可取得的留言，"
                "或 YouTube API 已達到今日配額上限。"
            )

        raw_file = os.path.join(
            output_dir,
            f"raw_{video_id}.csv"
        )

        df_raw = pd.DataFrame(
            raw_comments
        )

        if df_raw.empty:
            raise RuntimeError(
                "留言資料為空。"
            )

        df_raw["video_id"] = video_id

        # 移除作者與留言內容完全相同的重複資料
        if (
            "author" in df_raw.columns
            and "comment" in df_raw.columns
        ):
            df_raw = (
                df_raw
                .drop_duplicates(
                    subset=[
                        "author",
                        "comment"
                    ]
                )
                .reset_index(drop=True)
            )

        df_raw.to_csv(
            raw_file,
            index=False,
            encoding="utf-8-sig"
        )

        print(
            f"✅ 原始留言已儲存：{raw_file}"
        )

        print(
            f"✅ 去重後留言數：{len(df_raw)}"
        )

        # =============================================================
        # 第 2 站：情緒分析
        # =============================================================
        print(
            "▶️ [步驟 2] 啟動 AI 情緒分析……"
        )

        emotion_file = (
            boom_emotion.analyze_emotions(
                raw_file
            )
        )

        if not emotion_file:
            raise RuntimeError(
                "情緒分析沒有回傳結果檔案。"
            )

        if not os.path.exists(
            emotion_file
        ):
            raise FileNotFoundError(
                f"找不到情緒分析結果：{emotion_file}"
            )

        print(
            f"✅ 情緒分析完成：{emotion_file}"
        )

        # =============================================================
        # 第 3 站：BERTopic 主題建模
        # =============================================================
        print(
            "▶️ [步驟 3] 啟動 BERTopic 主題探勘……"
        )

        topic_result = (
            topic.run_topic_modeling(
                emotion_file
            )
        )

        if not isinstance(
            topic_result,
            dict
        ):
            raise RuntimeError(
                "BERTopic 回傳格式錯誤，"
                "應該回傳 dictionary。"
            )

        final_file = topic_result.get(
            "final_csv"
        )

        chart_html = topic_result.get(
            "barchart_html"
        )

        if not final_file:
            raise RuntimeError(
                "BERTopic 沒有回傳 final_csv。"
            )

        if not os.path.exists(
            final_file
        ):
            raise FileNotFoundError(
                f"找不到最終分析 CSV：{final_file}"
            )

        print(
            f"✅ 主題分析完成：{final_file}"
        )

        # =============================================================
        # 第 4 站：存入 MySQL
        # =============================================================
        print(
            "▶️ [步驟 4] 將結果存入 MySQL……"
        )

        try:
            my_db_import.save_to_database(
                final_file,
                video_id
            )

            print(
                "✅ MySQL 資料庫儲存完成。"
            )

        except Exception as database_error:
            # 資料庫失敗不阻止 Word 報告產生
            print(
                "⚠️ MySQL 儲存失敗，"
                "但系統會繼續產生 Word 報告。"
            )

            print(
                f"資料庫錯誤：{database_error}"
            )

        # =============================================================
        # 第 5 站：產生精緻 Word 報告
        # =============================================================
        print(
            "▶️ [步驟 5] 正在產生精緻 Word 報告……"
        )

        word_file = (
            word_report.generate_word_report(
                csv_path=final_file,
                target_url=user_input,
                platform="YouTube"
            )
        )

        if not word_file:
            raise RuntimeError(
                "Word 報告模組沒有回傳檔案路徑。"
            )

        if not os.path.exists(
            word_file
        ):
            raise FileNotFoundError(
                f"Word 報告產生後找不到檔案：{word_file}"
            )

        print(
            f"✅ Word 報告產生完成：{word_file}"
        )

        # =============================================================
        # 第 6 站：建立歷史紀錄
        # =============================================================
        analysis_id = None

        if current_user:
            try:
                analysis_id = my_db_import.save_analysis_history(
                    csv_path=final_file,
                    platform="YouTube",
                    target_title=video_title,
                    target_url=user_input,
                    target_id=video_id,
                    word_report_path=word_file,
                    user_id=current_user["user_id"]
                )

                print(
                    f"✅ 歷史紀錄建立完成：analysis_id={analysis_id}"
                )

            except Exception as history_error:
                print(
                    "⚠️ 歷史紀錄建立失敗，但不影響本次分析結果。"
                )
                print(
                    f"歷史紀錄錯誤：{history_error}"
                )

        else:
            print(
                "ℹ️ 目前未登入，本次分析不保存歷史紀錄。"
            )

        # =============================================================
        # 全部完成，回傳 Streamlit
        # =============================================================
        print(
            "🎉 該影片完整分析流程完成！"
        )

        return {
            "status": "success",
            "video_id": video_id,
            "video_title": video_title,
            "final_csv": final_file,
            "topic_chart": chart_html,
            "word_report": word_file,
            "analysis_id": analysis_id
        }

    except Exception as error:
        print(
            f"❌ 系統發生錯誤：{error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"系統發生錯誤：{str(error)}"
            )
        )


# =====================================================================
# 🚪 窗口三：搜尋 Dcard 文章
# =====================================================================
@app.post("/api/dcard/search_articles")
def search_dcard_articles(req: DcardSearchRequest):
    try:
        forum = req.forum.strip()
        keyword = req.keyword.strip()

        if not forum:
            raise ValueError("請選擇 Dcard 看板。")

        if not keyword:
            raise ValueError("請輸入 Dcard 搜尋關鍵字。")

        print("\n🔍 收到 Dcard 文章搜尋請求！")
        print(f"看板代碼：{forum}")
        print(f"搜尋關鍵字：{keyword}")

        articles = dcard_search.search_dcard_articles(
            forum_alias=forum,
            keyword=keyword,
            max_results=10,
            headless=False
        )

        print(f"✅ 共找到 {len(articles)} 篇文章。")

        return {
            "status": "success",
            "forum": forum,
            "keyword": keyword,
            "articles": articles,
            "message": f"已找到 {len(articles)} 篇相關文章。"
        }

    except Exception as error:
        print(f"❌ Dcard 文章搜尋失敗：{error}")

        raise HTTPException(
            status_code=500,
            detail=f"Dcard 搜尋失敗：{str(error)}"
        )


# =====================================================================
# 🚪 窗口四：分析 Dcard 文章留言
# =====================================================================
@app.post("/api/dcard/analyze_article")
def analyze_dcard_article(
    req: DcardAnalyzeRequest,
    authorization: str | None = Header(
        default=None
    )
):
    try:
        current_user = get_optional_current_user(
            authorization
        )

        article_id = req.article_id.strip()
        article_title = req.title.strip() or f"Dcard 文章 {article_id}"
        article_url = req.url.strip() or f"dcard://article/{article_id}"

        if not article_id:
            raise ValueError("請提供 Dcard 文章 ID。")

        print("\n🚀 Dcard 留言分析管線啟動！")
        print(f"文章 ID：{article_id}")
        print(f"文章標題：{article_title}")

        current_dir = os.path.dirname(
            os.path.abspath(__file__)
        )
        output_dir = os.path.join(
            current_dir,
            "outputs"
        )
        os.makedirs(
            output_dir,
            exist_ok=True
        )

        # =============================================================
        # 第 1 站：讀取本機 Dcard 留言
        # =============================================================
        print("▶️ [步驟 1] 正在讀取本機 Dcard 留言……")

        comments = dcard_search.get_dcard_comments(
            article_id=article_id
        )

        if not comments:
            raise RuntimeError(
                "這篇文章在 dcard_comments.csv 中沒有留言資料。"
            )

        df_raw = pd.DataFrame(comments)

        required_columns = ["author", "comment"]
        missing_columns = [
            column
            for column in required_columns
            if column not in df_raw.columns
        ]

        if missing_columns:
            raise ValueError(
                "Dcard 留言資料缺少必要欄位："
                + ", ".join(missing_columns)
            )

        df_raw["article_id"] = str(article_id)
        df_raw["platform"] = "Dcard"

        df_raw = (
            df_raw
            .drop_duplicates(
                subset=["author", "comment"]
            )
            .reset_index(drop=True)
        )

        safe_article_id = "".join(
            character
            for character in article_id
            if character.isalnum() or character in ("-", "_")
        ) or "unknown"

        raw_file = os.path.join(
            output_dir,
            f"raw_dcard_{safe_article_id}.csv"
        )

        df_raw.to_csv(
            raw_file,
            index=False,
            encoding="utf-8-sig"
        )

        print(f"✅ Dcard 原始留言已儲存：{raw_file}")
        print(f"✅ 去重後留言數：{len(df_raw)}")

        # =============================================================
        # 第 2 站：情緒分析
        # =============================================================
        print("▶️ [步驟 2] 啟動 AI 情緒分析……")

        emotion_file = boom_emotion.analyze_emotions(
            raw_file
        )

        if not emotion_file or not os.path.exists(emotion_file):
            raise FileNotFoundError(
                f"找不到情緒分析結果：{emotion_file}"
            )

        print(f"✅ 情緒分析完成：{emotion_file}")

        # =============================================================
        # 第 3 站：BERTopic 主題建模
        # 樣本太少時使用備援主題，避免整個流程失敗
        # =============================================================
        print("▶️ [步驟 3] 啟動 BERTopic 主題探勘……")

        final_file = None
        chart_html = None

        try:
            topic_result = topic.run_topic_modeling(
                emotion_file
            )

            if isinstance(topic_result, dict):
                final_file = topic_result.get("final_csv")
                chart_html = topic_result.get("barchart_html")

            if not final_file or not os.path.exists(final_file):
                raise RuntimeError(
                    "BERTopic 沒有產生有效的 final_csv。"
                )

            print(f"✅ 主題分析完成：{final_file}")

        except Exception as topic_error:
            print(
                "⚠️ Dcard 留言樣本較少，BERTopic 無法正常分群。"
            )
            print(f"BERTopic 錯誤：{topic_error}")

            fallback_df = pd.read_csv(
                emotion_file,
                encoding="utf-8-sig"
            )

            fallback_df["topic_name"] = "樣本不足－未進行主題分群"
            fallback_df["topic"] = -1

            final_file = os.path.join(
                output_dir,
                f"final_dcard_{safe_article_id}.csv"
            )

            fallback_df.to_csv(
                final_file,
                index=False,
                encoding="utf-8-sig"
            )

            chart_html = None

            print(
                f"✅ 已改用情緒分析結果作為最終檔案：{final_file}"
            )

        # =============================================================
        # 第 4 站：存入 MySQL
        # =============================================================
        print("▶️ [步驟 4] 將 Dcard 結果存入 MySQL……")

        try:
            my_db_import.save_to_database(
                final_file,
                f"dcard_{article_id}"
            )
            print("✅ MySQL 資料庫儲存完成。")

        except Exception as database_error:
            print(
                "⚠️ MySQL 儲存失敗，但不會中斷分析結果顯示。"
            )
            print(f"資料庫錯誤：{database_error}")

        # =============================================================
        # 第 5 站：產生 Word 報告
        # =============================================================
        print("▶️ [步驟 5] 正在產生 Dcard Word 報告……")

        word_file = None

        try:
            word_file = word_report.generate_word_report(
                csv_path=final_file,
                target_url=article_url,
                platform="Dcard"
            )

            if word_file and os.path.exists(word_file):
                print(f"✅ Word 報告產生完成：{word_file}")
            else:
                word_file = None
                print("⚠️ Word 報告模組未產生有效檔案。")

        except Exception as report_error:
            print(
                "⚠️ Word 報告產生失敗，但分析結果仍可顯示。"
            )
            print(f"報告錯誤：{report_error}")
            word_file = None

        # =============================================================
        # 第 6 站：建立歷史紀錄
        # =============================================================
        analysis_id = None

        if current_user:
            try:
                analysis_id = my_db_import.save_analysis_history(
                    csv_path=final_file,
                    platform="Dcard",
                    target_title=article_title,
                    target_url=article_url,
                    target_id=article_id,
                    word_report_path=word_file or "",
                    user_id=current_user["user_id"]
                )

                print(
                    f"✅ 歷史紀錄建立完成：analysis_id={analysis_id}"
                )

            except Exception as history_error:
                print(
                    "⚠️ Dcard 歷史紀錄建立失敗，但不影響分析結果。"
                )
                print(
                    f"歷史紀錄錯誤：{history_error}"
                )

        else:
            print(
                "ℹ️ 目前未登入，本次分析不保存歷史紀錄。"
            )

        print("🎉 Dcard 文章留言分析完成！")

        return {
            "status": "success",
            "platform": "Dcard",
            "article_id": article_id,
            "article_title": article_title,
            "comment_count": len(df_raw),
            "final_csv": final_file,
            "topic_chart": chart_html,
            "word_report": word_file,
            "analysis_id": analysis_id,
            "message": (
                f"已完成「{article_title}」的 "
                f"{len(df_raw)} 則留言分析。"
            )
        }

    except Exception as error:
        print(f"❌ Dcard 留言分析失敗：{error}")

        raise HTTPException(
            status_code=500,
            detail=f"Dcard 留言分析失敗：{str(error)}"
        )




# =====================================================================
# 🚪 窗口五：分析 Instagram 貼文或 Reels 留言
# =====================================================================
@app.post("/api/instagram/analyze_reel")
def analyze_instagram_reel(
    req: InstagramAnalyzeRequest,
    authorization: str | None = Header(
        default=None
    )
):
    try:
        current_user = get_optional_current_user(
            authorization
        )

        reel_url = req.url.strip()

        if not reel_url:
            raise ValueError(
                "請提供 Instagram 貼文或 Reels 網址。"
            )

        print("\n🌐 收到真實 Instagram 網址分析請求！")
        print(f"網址：{reel_url}")

        crawler_result = instagram_crawler.fetch_reel_comments(
            instagram_url=reel_url,
            max_comments=300
        )

        reel_info = crawler_result.get("reel", {})
        comments = crawler_result.get("comments", [])

        reel_id = str(
            reel_info.get("reel_id", "")
        ).strip()

        caption = (
            str(reel_info.get("caption", "")).strip()
            or f"Instagram 貼文 {reel_id}"
        )

        reel_url = (
            str(reel_info.get("url", reel_url)).strip()
            or reel_url
        )

        source_mode = "real_crawler"

        if not comments:
            raise RuntimeError(
                "這則 Instagram 貼文沒有取得任何留言。"
            )

        print("\n🚀 Instagram 留言分析管線啟動！")
        print(f"Reel ID：{reel_id}")
        print(f"貼文標題：{caption}")
        print(f"資料來源模式：{source_mode}")

        current_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        output_dir = os.path.join(
            current_dir,
            "outputs"
        )

        os.makedirs(
            output_dir,
            exist_ok=True
        )

        # =============================================================
        # 第 1 站：整理原始留言
        # =============================================================
        print("▶️ [步驟 1] 正在整理 Instagram 留言……")

        df_raw = pd.DataFrame(
            comments
        )

        required_columns = [
            "author",
            "comment"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df_raw.columns
        ]

        if missing_columns:
            raise ValueError(
                "Instagram 留言資料缺少必要欄位："
                + ", ".join(missing_columns)
            )

        df_raw["reel_id"] = reel_id
        df_raw["platform"] = "Instagram"
        df_raw["source_mode"] = source_mode

        df_raw = (
            df_raw
            .drop_duplicates(
                subset=["author", "comment"]
            )
            .reset_index(drop=True)
        )

        safe_reel_id = "".join(
            character
            for character in reel_id
            if character.isalnum()
            or character in ("-", "_")
        ) or "unknown"

        raw_file = os.path.join(
            output_dir,
            f"raw_instagram_{safe_reel_id}.csv"
        )

        df_raw.to_csv(
            raw_file,
            index=False,
            encoding="utf-8-sig"
        )

        print(f"✅ Instagram 原始留言已儲存：{raw_file}")
        print(f"✅ 去重後留言數：{len(df_raw)}")

        # =============================================================
        # 第 2 站：情緒分析
        # =============================================================
        print("▶️ [步驟 2] 啟動 AI 情緒分析……")

        emotion_file = boom_emotion.analyze_emotions(
            raw_file
        )

        if not emotion_file or not os.path.exists(
            emotion_file
        ):
            raise FileNotFoundError(
                f"找不到情緒分析結果：{emotion_file}"
            )

        print(f"✅ 情緒分析完成：{emotion_file}")

        # =============================================================
        # 第 3 站：BERTopic 主題建模
        # =============================================================
        print("▶️ [步驟 3] 啟動 BERTopic 主題探勘……")

        final_file = None
        chart_html = None

        try:
            topic_result = topic.run_topic_modeling(
                emotion_file
            )

            if isinstance(topic_result, dict):
                final_file = topic_result.get(
                    "final_csv"
                )

                chart_html = topic_result.get(
                    "barchart_html"
                )

            if not final_file or not os.path.exists(
                final_file
            ):
                raise RuntimeError(
                    "BERTopic 沒有產生有效的 final_csv。"
                )

            print(f"✅ 主題分析完成：{final_file}")

        except Exception as topic_error:
            print(
                "⚠️ Instagram 留言樣本較少，"
                "BERTopic 無法正常分群。"
            )
            print(f"BERTopic 錯誤：{topic_error}")

            fallback_df = pd.read_csv(
                emotion_file,
                encoding="utf-8-sig"
            )

            fallback_df["topic_name"] = (
                "樣本不足－未進行主題分群"
            )
            fallback_df["topic"] = -1

            final_file = os.path.join(
                output_dir,
                f"final_instagram_{safe_reel_id}.csv"
            )

            fallback_df.to_csv(
                final_file,
                index=False,
                encoding="utf-8-sig"
            )

            chart_html = None

            print(
                f"✅ 已建立 Instagram 備援結果：{final_file}"
            )

        # =============================================================
        # 第 4 站：存入 MySQL
        # =============================================================
        print("▶️ [步驟 4] 將 Instagram 結果存入 MySQL……")

        try:
            my_db_import.save_to_database(
                final_file,
                f"instagram_{reel_id}"
            )

            print("✅ MySQL 資料庫儲存完成。")

        except Exception as database_error:
            print(
                "⚠️ MySQL 儲存失敗，"
                "但不會中斷分析結果顯示。"
            )
            print(f"資料庫錯誤：{database_error}")

        # =============================================================
        # 第 5 站：產生 Word 報告
        # =============================================================
        print("▶️ [步驟 5] 正在產生 Instagram Word 報告……")

        word_file = None

        try:
            word_file = word_report.generate_word_report(
                csv_path=final_file,
                target_url=reel_url,
                platform="Instagram"
            )

            if word_file and os.path.exists(
                word_file
            ):
                print(f"✅ Word 報告產生完成：{word_file}")
            else:
                word_file = None
                print("⚠️ Word 報告模組未產生有效檔案。")

        except Exception as report_error:
            word_file = None

            print(
                "⚠️ Word 報告產生失敗，"
                "但分析結果仍可顯示。"
            )
            print(f"報告錯誤：{report_error}")

        # =============================================================
        # 第 6 站：建立歷史紀錄
        # =============================================================
        analysis_id = None

        if current_user:
            try:
                analysis_id = my_db_import.save_analysis_history(
                    csv_path=final_file,
                    platform="Instagram",
                    target_title=caption,
                    target_url=reel_url,
                    target_id=reel_id,
                    word_report_path=word_file or "",
                    user_id=current_user["user_id"]
                )

                print(
                    f"✅ 歷史紀錄建立完成：analysis_id={analysis_id}"
                )

            except Exception as history_error:
                print(
                    "⚠️ Instagram 歷史紀錄建立失敗，但不影響分析結果。"
                )
                print(
                    f"歷史紀錄錯誤：{history_error}"
                )

        else:
            print(
                "ℹ️ 目前未登入，本次分析不保存歷史紀錄。"
            )

        print("🎉 Instagram 貼文留言分析完成！")

        return {
            "status": "success",
            "platform": "Instagram",
            "source_mode": source_mode,
            "reel_id": reel_id,
            "caption": caption,
            "comment_count": len(df_raw),
            "final_csv": final_file,
            "topic_chart": chart_html,
            "word_report": word_file,
            "analysis_id": analysis_id,
            "message": (
                f"已完成「{caption}」的 "
                f"{len(df_raw)} 則留言分析。"
            )
        }

    except Exception as error:
        print(f"❌ Instagram 留言分析失敗：{error}")

        raise HTTPException(
            status_code=500,
            detail=f"Instagram 留言分析失敗：{str(error)}"
        )


# =====================================================================
# 🚪 窗口六：歷史紀錄清單
# =====================================================================
@app.get("/api/history")
def list_analysis_history(
    platform: str = "",
    limit: int = 50,
    authorization: str | None = Header(
        default=None
    )
):
    try:
        user = require_current_user(
            authorization
        )

        rows = my_db_import.get_analysis_history(
            user_id=user["user_id"],
            limit=limit,
            platform=platform
        )

        if platform == "YouTube":
            rows = repair_youtube_history_titles(
                rows,
                user["user_id"]
            )

        return {
            "status": "success",
            "count": len(rows),
            "history": rows
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            f"❌ 歷史紀錄讀取失敗：{error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"歷史紀錄讀取失敗：{str(error)}"
            )
        )


# =====================================================================
# 🚪 窗口七：單次歷史紀錄詳情
# =====================================================================
@app.get("/api/history/{analysis_id}")
def analysis_history_detail(
    analysis_id: int,
    authorization: str | None = Header(
        default=None
    )
):
    try:
        user = require_current_user(
            authorization
        )

        result = (
            my_db_import.get_analysis_history_detail(
                analysis_id=analysis_id,
                user_id=user["user_id"]
            )
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="找不到這筆歷史分析紀錄。"
            )

        if result.get("platform") == "YouTube":
            repaired = repair_youtube_history_titles(
                [result],
                user["user_id"]
            )
            result = repaired[0]

        return {
            "status": "success",
            "history": result
        }

    except HTTPException:
        raise

    except Exception as error:
        print(
            f"❌ 歷史紀錄詳情讀取失敗：{error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"歷史紀錄詳情讀取失敗：{str(error)}"
            )
        )


# =====================================================================
# 健康檢查
# =====================================================================
@app.get("/")
def root():
    return {
        "status": "online",
        "message": "社群輿情分析 API 正常運作"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "youtube_api_key": (
            "configured"
            if crawler.API_KEY
            else "missing"
        )
    }