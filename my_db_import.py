import os
import re
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import pandas as pd
import pymysql


DB_CONFIG = {
    "host": "120.125.83.49",
    "port": 3306,
    "user": "root",
    "password": "Aa12131213",
    "database": "project_db",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def save_to_database(csv_path, video_url="https://youtube.com/"):
    print(f"\n📦 倉管員啟動！準備將 {csv_path} 存入 MySQL 資料庫...")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            sample_video_id = (
                str(df["video_id"].iloc[0])
                if "video_id" in df.columns
                else "unknown_video"
            )

            actual_url = (
                f"https://youtube.com/watch?v={sample_video_id}"
                if video_url == "https://youtube.com/"
                else video_url
            )

            cursor.execute(
                """
                INSERT IGNORE INTO platformcontent
                (content_id, platform, content_title, content_url)
                VALUES (1, 'YouTube', 'YouTube專案輿情分析影片', %s);
                """,
                (actual_url,),
            )

            valid_count = 0
            ignored_count = 0

            for _, row in df.iterrows():
                raw_comment = (
                    row.get("clean_comment")
                    or row.get("comment")
                    or ""
                )

                if pd.isna(raw_comment) or not isinstance(raw_comment, str):
                    ignored_count += 1
                    continue

                comment_clean = raw_comment.strip()

                if len(comment_clean) < 2:
                    ignored_count += 1
                    continue

                valid_count += 1
                current_comment_id = valid_count

                author_name = (
                    row["author"]
                    if "author" in df.columns and pd.notna(row["author"])
                    else "匿名使用者"
                )
                sentiment_tag = (
                    row["sentiment"]
                    if "sentiment" in df.columns and pd.notna(row["sentiment"])
                    else "中立"
                )
                sentiment_score = (
                    float(row["sentiment_score"])
                    if "sentiment_score" in df.columns
                    and pd.notna(row["sentiment_score"])
                    else 0.0
                )

                cursor.execute(
                    """
                    INSERT IGNORE INTO comment
                    (comment_id, content_id, user_name, comment_text, cleaned_text)
                    VALUES (%s, 1, %s, %s, %s);
                    """,
                    (
                        current_comment_id,
                        author_name,
                        comment_clean,
                        comment_clean,
                    ),
                )

                cursor.execute(
                    """
                    INSERT IGNORE INTO sentimentresult
                    (comment_id, sentiment_label, confidence_score)
                    VALUES (%s, %s, %s);
                    """,
                    (
                        current_comment_id,
                        sentiment_tag,
                        sentiment_score,
                    ),
                )

        connection.commit()
        print("\n🎉 【資料庫歸位報告】")
        print(f"✅ 成功寫入資料庫：{valid_count} 筆")
        print(f"❌ 剔除垃圾資料：{ignored_count} 筆")
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
        print("🔌 資料庫連線已安全關閉。")


def ensure_history_tables():
    """
    建立登入、Session、歷史分析與歷史留言資料表。
    舊資料表若已存在，會自動補上 user_id 欄位。
    """
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(80) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_users_username (username)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS email_verifications (
                    verification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    code_hash VARCHAR(255) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    used TINYINT(1) NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_verification_email (email),
                    INDEX idx_verification_created_at (created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    token_hash CHAR(64) NOT NULL UNIQUE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_sessions_user_id (user_id),
                    CONSTRAINT fk_session_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_history (
                    analysis_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NULL,
                    platform VARCHAR(30) NOT NULL,
                    target_id VARCHAR(255) NULL,
                    target_title TEXT NULL,
                    target_url TEXT NULL,
                    analyzed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    total_comments INT NOT NULL DEFAULT 0,
                    positive_count INT NOT NULL DEFAULT 0,
                    neutral_count INT NOT NULL DEFAULT 0,
                    negative_count INT NOT NULL DEFAULT 0,
                    question_count INT NOT NULL DEFAULT 0,
                    positive_rate DECIMAL(6,2) NOT NULL DEFAULT 0,
                    negative_rate DECIMAL(6,2) NOT NULL DEFAULT 0,
                    top_topic VARCHAR(255) NULL,
                    final_csv_path TEXT NULL,
                    word_report_path TEXT NULL,
                    INDEX idx_history_user (user_id),
                    INDEX idx_history_platform (platform),
                    INDEX idx_history_analyzed_at (analyzed_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """
            )

            # 舊版 analysis_history 沒有 user_id 時自動補欄位
            cursor.execute(
                """
                SELECT COUNT(*) AS column_count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'analysis_history'
                  AND COLUMN_NAME = 'user_id';
                """,
                (DB_CONFIG["database"],)
            )

            column_info = cursor.fetchone()

            if not column_info or int(column_info["column_count"]) == 0:
                cursor.execute(
                    """
                    ALTER TABLE analysis_history
                    ADD COLUMN user_id BIGINT NULL AFTER analysis_id;
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX idx_history_user
                    ON analysis_history(user_id);
                    """
                )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_comment_history (
                    history_comment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    analysis_id BIGINT NOT NULL,
                    author VARCHAR(255) NULL,
                    comment_text TEXT NULL,
                    sentiment_label VARCHAR(30) NULL,
                    confidence_score DECIMAL(10,6) NULL,
                    topic_id INT NULL,
                    topic_name VARCHAR(255) NULL,
                    topic_keywords TEXT NULL,
                    comment_time VARCHAR(100) NULL,
                    INDEX idx_comment_analysis_id (analysis_id),
                    CONSTRAINT fk_history_analysis
                        FOREIGN KEY (analysis_id)
                        REFERENCES analysis_history(analysis_id)
                        ON DELETE CASCADE
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """
            )

        connection.commit()

    finally:
        connection.close()


# ==========================================
# 帳號 / 登入系統
# ==========================================
def _hash_password(password, salt_hex=None):
    if salt_hex is None:
        salt = secrets.token_bytes(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000
    ).hex()

    return f"{salt_hex}${digest}"


def normalize_gmail(username):
    """只接受 Gmail 信箱作為登入帳號。"""
    gmail = str(username or "").strip().lower()

    gmail_pattern = r"^[a-z0-9][a-z0-9._%+-]*@gmail\.com$"

    if not re.fullmatch(gmail_pattern, gmail):
        raise ValueError(
            "帳號必須使用有效的 Gmail 信箱，例如：example@gmail.com"
        )

    return gmail


def user_exists(username):
    ensure_history_tables()

    username = normalize_gmail(username)
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE username = %s
                LIMIT 1;
                """,
                (username,)
            )

            return cursor.fetchone() is not None

    finally:
        connection.close()


def create_email_verification(email, code):
    """
    建立 6 位數 Email 驗證碼。
    60 秒內不可重複寄送；驗證碼 10 分鐘失效。
    """
    ensure_history_tables()

    email = normalize_gmail(email)
    code = str(code).strip()
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT created_at
                FROM email_verifications
                WHERE email = %s
                ORDER BY verification_id DESC
                LIMIT 1;
                """,
                (email,)
            )

            latest = cursor.fetchone()

            if latest and latest.get("created_at"):
                seconds_since_last = (
                    datetime.now() - latest["created_at"]
                ).total_seconds()

                if seconds_since_last < 60:
                    wait_seconds = max(
                        1,
                        int(60 - seconds_since_last)
                    )
                    raise ValueError(
                        f"請等待 {wait_seconds} 秒後再重新寄送驗證碼。"
                    )

            # 讓舊驗證碼失效
            cursor.execute(
                """
                UPDATE email_verifications
                SET used = 1
                WHERE email = %s
                  AND used = 0;
                """,
                (email,)
            )

            code_hash = _hash_password(code)
            expires_at = datetime.now() + timedelta(
                minutes=10
            )

            cursor.execute(
                """
                INSERT INTO email_verifications (
                    email,
                    code_hash,
                    expires_at,
                    used
                )
                VALUES (%s, %s, %s, 0);
                """,
                (
                    email,
                    code_hash,
                    expires_at
                )
            )

            verification_id = cursor.lastrowid

        connection.commit()

        return {
            "verification_id": verification_id,
            "email": email,
            "expires_at": expires_at
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def verify_email_code(email, code):
    """
    驗證最新一筆尚未使用且未過期的驗證碼。
    驗證成功後立即標記為已使用。
    """
    ensure_history_tables()

    email = normalize_gmail(email)
    code = str(code or "").strip()

    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("驗證碼必須是 6 位數字。")

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    verification_id,
                    code_hash,
                    expires_at
                FROM email_verifications
                WHERE email = %s
                  AND used = 0
                ORDER BY verification_id DESC
                LIMIT 1;
                """,
                (email,)
            )

            record = cursor.fetchone()

            if not record:
                raise ValueError(
                    "找不到可使用的驗證碼，請重新取得驗證碼。"
                )

            if datetime.now() > record["expires_at"]:
                cursor.execute(
                    """
                    UPDATE email_verifications
                    SET used = 1
                    WHERE verification_id = %s;
                    """,
                    (record["verification_id"],)
                )
                connection.commit()

                raise ValueError(
                    "驗證碼已失效，請重新取得驗證碼。"
                )

            stored_hash = str(record["code_hash"])

            if "$" not in stored_hash:
                raise ValueError(
                    "驗證碼資料格式錯誤，請重新取得驗證碼。"
                )

            salt_hex, _ = stored_hash.split("$", 1)
            candidate_hash = _hash_password(
                code,
                salt_hex=salt_hex
            )

            if not hmac.compare_digest(
                stored_hash,
                candidate_hash
            ):
                raise ValueError("驗證碼錯誤。")

            cursor.execute(
                """
                UPDATE email_verifications
                SET used = 1
                WHERE verification_id = %s;
                """,
                (record["verification_id"],)
            )

        connection.commit()
        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def register_user(username, password):
    ensure_history_tables()

    username = normalize_gmail(username)
    password = str(password or "")

    if len(password) < 6:
        raise ValueError("密碼至少需要 6 位字元。")

    password_hash = _hash_password(password)
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s);
                """,
                (username, password_hash)
            )

            user_id = cursor.lastrowid

        connection.commit()

        return {
            "user_id": user_id,
            "username": username
        }

    except pymysql.err.IntegrityError:
        connection.rollback()
        raise ValueError("這個帳號已經被使用。")

    finally:
        connection.close()


def authenticate_user(username, password):
    ensure_history_tables()

    username = str(username or "").strip().lower()
    password = str(password or "")

    try:
        username = normalize_gmail(username)
    except ValueError:
        return None

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, password_hash
                FROM users
                WHERE username = %s
                LIMIT 1;
                """,
                (username,)
            )

            user = cursor.fetchone()

        if not user:
            return None

        stored_hash = str(user["password_hash"])

        if "$" not in stored_hash:
            return None

        salt_hex, _ = stored_hash.split("$", 1)
        candidate_hash = _hash_password(
            password,
            salt_hex=salt_hex
        )

        if not hmac.compare_digest(
            stored_hash,
            candidate_hash
        ):
            return None

        return {
            "user_id": int(user["user_id"]),
            "username": user["username"]
        }

    finally:
        connection.close()


def create_user_session(user_id):
    ensure_history_tables()

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_sessions (
                    user_id,
                    token_hash
                )
                VALUES (%s, %s);
                """,
                (user_id, token_hash)
            )

        connection.commit()
        return raw_token

    finally:
        connection.close()


def get_user_by_token(raw_token):
    ensure_history_tables()

    raw_token = str(raw_token or "").strip()

    if not raw_token:
        return None

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.user_id,
                    u.username,
                    u.created_at
                FROM user_sessions AS s
                INNER JOIN users AS u
                    ON u.user_id = s.user_id
                WHERE s.token_hash = %s
                LIMIT 1;
                """,
                (token_hash,)
            )

            user = cursor.fetchone()

        if not user:
            return None

        if user.get("created_at"):
            user["created_at"] = user[
                "created_at"
            ].isoformat(
                sep=" ",
                timespec="seconds"
            )

        return user

    finally:
        connection.close()


def delete_user_session(raw_token):
    ensure_history_tables()

    raw_token = str(raw_token or "").strip()

    if not raw_token:
        return False

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM user_sessions
                WHERE token_hash = %s;
                """,
                (token_hash,)
            )

            deleted = cursor.rowcount > 0

        connection.commit()
        return deleted

    finally:
        connection.close()


def _safe_text(value, default=""):
    if value is None or pd.isna(value):
        return default
    return str(value).strip()


def _safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=None):
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def save_analysis_history(
    csv_path,
    platform,
    target_title="",
    target_url="",
    target_id="",
    word_report_path="",
    user_id=None,
):
    ensure_history_tables()
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    if df.empty:
        raise ValueError("歷史紀錄 CSV 沒有任何資料。")

    total_comments = len(df)

    if "sentiment" in df.columns:
        sentiment_counts = (
            df["sentiment"]
            .fillna("未分類")
            .astype(str)
            .value_counts()
        )
    else:
        sentiment_counts = pd.Series(dtype="int64")

    positive_count = int(sentiment_counts.get("正面", 0))
    neutral_count = int(sentiment_counts.get("中立", 0))
    negative_count = int(sentiment_counts.get("負面", 0))
    question_count = int(sentiment_counts.get("提問", 0))

    positive_rate = (
        positive_count / total_comments * 100
        if total_comments else 0
    )
    negative_rate = (
        negative_count / total_comments * 100
        if total_comments else 0
    )

    top_topic = ""

    if "topic_name" in df.columns:
        topic_series = (
            df["topic_name"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        topic_series = topic_series[
            ~topic_series.isin(
                [
                    "",
                    "其他未分類",
                    "樣本不足－未進行主題分群",
                ]
            )
        ]
        if not topic_series.empty:
            top_topic = topic_series.value_counts().index[0]

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analysis_history (
                    user_id,
                    platform, target_id, target_title, target_url,
                    analyzed_at, total_comments,
                    positive_count, neutral_count,
                    negative_count, question_count,
                    positive_rate, negative_rate,
                    top_topic, final_csv_path, word_report_path
                )
                VALUES (
                    %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                );
                """,
                (
                    user_id,
                    platform,
                    target_id,
                    target_title,
                    target_url,
                    datetime.now(),
                    total_comments,
                    positive_count,
                    neutral_count,
                    negative_count,
                    question_count,
                    round(positive_rate, 2),
                    round(negative_rate, 2),
                    top_topic,
                    str(csv_path),
                    str(word_report_path or ""),
                ),
            )

            analysis_id = cursor.lastrowid
            comment_rows = []

            for _, row in df.iterrows():
                comment_text = _safe_text(
                    row.get("comment")
                    or row.get("clean_comment")
                    or row.get("text")
                    or row.get("content")
                    or ""
                )

                if not comment_text:
                    continue

                author = _safe_text(
                    row.get("author")
                    or row.get("username")
                    or row.get("user")
                    or "匿名使用者"
                )

                sentiment = _safe_text(
                    row.get("sentiment"),
                    "未分類"
                )

                confidence = _safe_float(
                    row.get("sentiment_score")
                    if "sentiment_score" in row.index
                    else row.get("confidence"),
                    0.0,
                )

                topic_id = _safe_int(
                    row.get("topic"),
                    None
                )

                topic_name = _safe_text(
                    row.get("topic_name")
                )

                topic_keywords = _safe_text(
                    row.get("topic_keywords")
                )

                comment_time = _safe_text(
                    row.get("time")
                    or row.get("created_at")
                    or row.get("published_at")
                    or ""
                )

                comment_rows.append(
                    (
                        analysis_id,
                        author,
                        comment_text,
                        sentiment,
                        confidence,
                        topic_id,
                        topic_name,
                        topic_keywords,
                        comment_time,
                    )
                )

            if comment_rows:
                cursor.executemany(
                    """
                    INSERT INTO analysis_comment_history (
                        analysis_id, author, comment_text,
                        sentiment_label, confidence_score,
                        topic_id, topic_name, topic_keywords,
                        comment_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    comment_rows,
                )

        connection.commit()

        print(
            f"🕘 歷史紀錄已建立：analysis_id={analysis_id}，"
            f"共 {len(comment_rows)} 則留言"
        )

        return analysis_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_analysis_history_title(
    analysis_id,
    user_id,
    target_title
):
    """
    更新指定使用者某筆歷史分析的顯示標題。
    """
    ensure_history_tables()

    target_title = str(target_title or "").strip()

    if not target_title:
        return False

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE analysis_history
                SET target_title = %s
                WHERE analysis_id = %s
                  AND user_id = %s;
                """,
                (
                    target_title,
                    analysis_id,
                    user_id
                )
            )

            updated = cursor.rowcount > 0

        connection.commit()
        return updated

    finally:
        connection.close()


def get_analysis_history(user_id, limit=50, platform=""):
    """
    只取得指定登入使用者自己的歷史分析。
    """
    ensure_history_tables()

    limit = max(1, min(int(limit), 200))
    platform = str(platform or "").strip()
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            if platform:
                cursor.execute(
                    """
                    SELECT *
                    FROM analysis_history
                    WHERE user_id = %s
                      AND platform = %s
                    ORDER BY analyzed_at DESC, analysis_id DESC
                    LIMIT %s;
                    """,
                    (user_id, platform, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM analysis_history
                    WHERE user_id = %s
                    ORDER BY analyzed_at DESC, analysis_id DESC
                    LIMIT %s;
                    """,
                    (user_id, limit)
                )

            rows = cursor.fetchall()

        for row in rows:
            if row.get("analyzed_at"):
                row["analyzed_at"] = row[
                    "analyzed_at"
                ].isoformat(
                    sep=" ",
                    timespec="seconds"
                )

            if row.get("positive_rate") is not None:
                row["positive_rate"] = float(
                    row["positive_rate"]
                )

            if row.get("negative_rate") is not None:
                row["negative_rate"] = float(
                    row["negative_rate"]
                )

        return rows

    finally:
        connection.close()


def get_analysis_history_detail(
    analysis_id,
    user_id
):
    """
    只允許讀取屬於目前登入者的歷史紀錄。
    """
    ensure_history_tables()
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM analysis_history
                WHERE analysis_id = %s
                  AND user_id = %s;
                """,
                (analysis_id, user_id)
            )

            history = cursor.fetchone()

            if not history:
                return None

            cursor.execute(
                """
                SELECT
                    history_comment_id,
                    analysis_id,
                    author,
                    comment_text,
                    sentiment_label,
                    confidence_score,
                    topic_id,
                    topic_name,
                    topic_keywords,
                    comment_time
                FROM analysis_comment_history
                WHERE analysis_id = %s
                ORDER BY history_comment_id ASC;
                """,
                (analysis_id,)
            )

            comments = cursor.fetchall()

        if history.get("analyzed_at"):
            history["analyzed_at"] = history[
                "analyzed_at"
            ].isoformat(
                sep=" ",
                timespec="seconds"
            )

        if history.get("positive_rate") is not None:
            history["positive_rate"] = float(
                history["positive_rate"]
            )

        if history.get("negative_rate") is not None:
            history["negative_rate"] = float(
                history["negative_rate"]
            )

        for comment in comments:
            if comment.get("confidence_score") is not None:
                comment["confidence_score"] = float(
                    comment["confidence_score"]
                )

        history["comments"] = comments
        return history

    finally:
        connection.close()


if __name__ == "__main__":
    ensure_history_tables()
    print("✅ 歷史紀錄資料表檢查完成。")
