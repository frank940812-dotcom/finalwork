import re
from pathlib import Path

import jieba
import pandas as pd
import torch
from transformers import pipeline


# ==========================================
# 1. 全域設定
# ==========================================
MODEL_NAME = (
    "lxyuan/"
    "distilbert-base-multilingual-cased-sentiments-student"
)

DEVICE = 0 if torch.cuda.is_available() else -1

print("🔌 正在載入 Transformer 情緒分析模型...")

try:
    sentiment_pipeline = pipeline(
        task="sentiment-analysis",
        model=MODEL_NAME,
        device=DEVICE
    )

    if DEVICE == 0:
        print("✅ 模型載入成功，目前使用 GPU。")
    else:
        print("✅ 模型載入成功，目前使用 CPU。")

except Exception as error:
    print(f"❌ 模型載入失敗：{error}")
    sentiment_pipeline = None


# ==========================================
# 2. 詞典與規則
# ==========================================

# 只保留明確、歧義較低的負面詞
NEGATIVE_WORDS = {
    "公沙小": 0.50,
    "攻殺小": 0.50,
    "供殺小": 0.50,
    "三小": 0.40,
    "靠北": 0.40,
    "靠夭": 0.40,
    "媽的": 0.45,
    "他媽的": 0.45,
    "爛透": 0.50,
    "廢物": 0.55,
    "垃圾": 0.50,
    "噁心": 0.50,
    "可悲": 0.40,
    "丟臉": 0.40,
    "吃相難看": 0.50,
    "浪費時間": 0.35,
    "退訂": 0.40,
    "拒看": 0.40,
    "智商稅": 0.45,
    "翻車": 0.30,
    "割韭菜": 0.45,
    "過氣": 0.35,
    "沒料": 0.40,
    "罐頭音效": 0.35,
    "難看": 0.35,
    "智障": 0.55,
    "白癡": 0.50,
    "可惡": 0.30,
    "抵制": 0.40,
    "難聽": 0.45,
    "走音": 0.35,
    "失望": 0.35,
    "退步": 0.35,
    "這什麼鬼": 0.45,
    "聽不下去": 0.50,
    "抄襲": 0.45,
    "難懂": 0.25,
    "毀了": 0.45,
    "太貴": 0.35,
    "很貴": 0.25,
    "CP值很低": 0.45,
    "無言": 0.30
}

# 只保留明確、歧義較低的正面詞
POSITIVE_WORDS = {
    "支持": 0.30,
    "好人": 0.25,
    "用心": 0.35,
    "超讚": 0.50,
    "期待": 0.25,
    "太神啦": 0.45,
    "真香": 0.35,
    "有料": 0.30,
    "優質": 0.40,
    "喜歡": 0.30,
    "感動": 0.40,
    "謝謝": 0.30,
    "感謝": 0.35,
    "神作": 0.45,
    "太棒了": 0.50,
    "辛苦了": 0.35,
    "加油": 0.30,
    "好聽": 0.40,
    "神曲": 0.45,
    "單曲循環": 0.40,
    "一直聽": 0.30,
    "還在聽": 0.30,
    "愛了": 0.45,
    "起雞皮疙瘩": 0.35,
    "寶藏": 0.40,
    "好聲音": 0.40,
    "這規格算不錯": 0.40
}

# 這些詞具有高度上下文依賴，不直接判斷正負
CONTEXT_WORDS = {
    "笑死",
    "呵呵",
    "ㄏㄏ",
    "崩潰",
    "玻璃心",
    "巨嬰",
    "護航",
    "洗地",
    "帶風向",
    "雙標",
    "水軍",
    "側翼",
    "下去",
    "社會實驗",
    "這咖",
    "推",
    "簽到",
    "按讚"
}

NEGATION_WORDS = {
    "不",
    "沒",
    "沒有",
    "不是",
    "並非",
    "不太",
    "不算",
    "未",
    "別"
}

QUESTION_PATTERNS = [
    r"[？?]",
    r"^(請問|想問|求問|有人知道|誰知道)",
    r"(為什麼|怎麼|如何|哪裡|哪個|多少|何時|是不是|可以嗎|有嗎|好嗎)$"
]


# ==========================================
# 3. 文字清理與特徵函式
# ==========================================
def clean_text(text: object) -> str:
    """清理網址、換行與多餘空白，保留表情符號。"""

    if pd.isna(text):
        return ""

    cleaned = str(text)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def is_question(text: str) -> bool:
    """判斷留言是否具有提問特徵。"""

    return any(
        re.search(pattern, text)
        for pattern in QUESTION_PATTERNS
    )


def contains_negation_before_word(
    text: str,
    target_word: str,
    window_size: int = 4
) -> bool:
    """
    檢查情緒詞前方是否有否定詞。

    例如：
    不難聽
    沒有失望
    """

    position = text.find(target_word)

    if position < 0:
        return False

    prefix_start = max(0, position - window_size)
    prefix = text[prefix_start:position]

    return any(
        negation in prefix
        for negation in NEGATION_WORDS
    )


def calculate_lexicon_score(text: str) -> float:
    """
    計算詞典分數。

    正數代表正面，負數代表負面。
    """

    score = 0.0

    for word, weight in POSITIVE_WORDS.items():
        if word in text:
            if contains_negation_before_word(text, word):
                score -= weight
            else:
                score += weight

    for word, weight in NEGATIVE_WORDS.items():
        if word in text:
            if contains_negation_before_word(text, word):
                score += weight
            else:
                score -= weight

    return max(-1.0, min(1.0, score))


def normalize_model_result(
    result: dict
) -> tuple[str, float]:
    """把 Transformer 模型標籤轉成中文。"""

    label = str(result.get("label", "")).lower()
    score = float(result.get("score", 0.0))

    if "positive" in label:
        return "正面", score

    if "negative" in label:
        return "負面", score

    return "中立", score


def combine_predictions(
    text: str,
    model_label: str,
    model_score: float,
    lexicon_score: float
) -> tuple[str, float, str]:
    """
    融合 Transformer 與詞典分數。

    Transformer 權重 75%
    詞典權重 25%
    """

    if model_label == "正面":
        model_direction_score = model_score
    elif model_label == "負面":
        model_direction_score = -model_score
    else:
        model_direction_score = 0.0

    combined_score = (
        model_direction_score * 0.75
        + lexicon_score * 0.25
    )

    if model_direction_score * lexicon_score < 0:
        source = "transformer+lexicon_conflict"
        confidence = abs(combined_score) * 0.80
    else:
        source = "transformer+lexicon"
        confidence = abs(combined_score)

    if combined_score >= 0.25:
        final_label = "正面"
    elif combined_score <= -0.25:
        final_label = "負面"
    else:
        final_label = "中立"

    # 提問不再搶走明確的正負面情緒
    # 只有當情緒接近中立時才歸類為提問
    if is_question(text) and final_label == "中立":
        final_label = "提問"
        confidence = max(confidence, 0.70)
        source = f"{source}+question_rule"

    confidence = max(0.0, min(1.0, confidence))

    return (
        final_label,
        round(confidence, 4),
        source
    )


# ==========================================
# 4. 主分析函式
# ==========================================
def analyze_emotions(
    input_csv: str,
    batch_size: int = 16
) -> str:
    """讀取留言 CSV，執行情緒分析並輸出結果。"""

    print(f"\n🚀 開始分析留言：{input_csv}")

    input_path = Path(input_csv)

    if not input_path.exists():
        raise FileNotFoundError(
            f"找不到輸入檔案：{input_path}"
        )

    try:
        df = pd.read_csv(
            input_path,
            encoding="utf-8-sig"
        )
    except Exception as error:
        raise RuntimeError(
            f"讀取 CSV 失敗：{error}"
        ) from error

    if "comment" not in df.columns:
        raise ValueError(
            "找不到 comment 欄位，"
            "請確認爬蟲輸出格式。"
        )

    print("🧹 正在清理留言...")

    df["clean_comment"] = (
        df["comment"]
        .apply(clean_text)
    )

    # 移除空白留言
    df = df[
        df["clean_comment"] != ""
    ].copy()

    df.reset_index(
        drop=True,
        inplace=True
    )

    if df.empty:
        raise ValueError(
            "清理後沒有可分析的有效留言。"
        )

    print(f"📄 有效留言數：{len(df)}")

    print("✂️ 正在執行 Jieba 斷詞...")

    df["jieba_cut"] = (
        df["clean_comment"]
        .apply(
            lambda text: " ".join(
                jieba.cut(text)
            ).strip()
        )
    )

    texts = df["clean_comment"].tolist()

    print("📚 正在計算詞典情緒分數...")

    lexicon_scores = [
        calculate_lexicon_score(text)
        for text in texts
    ]

    if sentiment_pipeline is None:
        raise RuntimeError(
            "Transformer 模型沒有成功載入，"
            "請先查看程式啟動時的錯誤訊息。"
        )

    print(
        f"🧠 正在批次執行 Transformer 推論，"
        f"batch_size={batch_size}..."
    )

    try:
        model_results = sentiment_pipeline(
            texts,
            batch_size=batch_size,
            truncation=True,
            max_length=512
        )
    except Exception as error:
        raise RuntimeError(
            f"Transformer 推論失敗：{error}"
        ) from error

    sentiments = []
    confidence_scores = []
    prediction_sources = []
    question_flags = []
    model_labels = []
    model_scores = []

    for text, model_result, lexicon_score in zip(
        texts,
        model_results,
        lexicon_scores
    ):
        model_label, model_score = (
            normalize_model_result(model_result)
        )

        (
            final_label,
            confidence,
            prediction_source
        ) = combine_predictions(
            text=text,
            model_label=model_label,
            model_score=model_score,
            lexicon_score=lexicon_score
        )

        sentiments.append(final_label)
        confidence_scores.append(confidence)
        prediction_sources.append(
            prediction_source
        )
        question_flags.append(
            is_question(text)
        )
        model_labels.append(model_label)
        model_scores.append(
            round(model_score, 4)
        )

    df["sentiment"] = sentiments
    df["sentiment_score"] = confidence_scores
    df["sentiment_source"] = prediction_sources
    df["is_question"] = question_flags
    df["model_sentiment"] = model_labels
    df["model_score"] = model_scores
    df["lexicon_score"] = lexicon_scores

    output_file = input_path.with_name(
        f"{input_path.stem}"
        "_hybrid_predicted.csv"
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n==================================")
    print("🎉 情緒分析完成")
    print("==================================")

    sentiment_order = [
        "正面",
        "中立",
        "負面",
        "提問"
    ]

    counts = df["sentiment"].value_counts()
    total = len(df)

    for emotion in sentiment_order:
        count = int(
            counts.get(emotion, 0)
        )

        ratio = (
            count / total * 100
            if total > 0
            else 0
        )

        print(
            f"📌 {emotion:<4}："
            f"{count:>5} 筆 "
            f"({ratio:.1f}%)"
        )

    average_confidence = (
        df["sentiment_score"].mean()
    )

    print(
        f"📊 平均判斷信心度："
        f"{average_confidence:.3f}"
    )

    print(f"📄 輸出檔案：{output_file}")

    return str(output_file)


# ==========================================
# 5. 單獨測試入口
# ==========================================
if __name__ == "__main__":
    test_file = input(
        "\n請輸入尚未分析情緒的 CSV 檔案："
    ).strip()

    try:
        result = analyze_emotions(test_file)

        print(
            f"✅ 測試完成，檔案存於：{result}"
        )

    except Exception as error:
        print(f"❌ 分析失敗：{error}")