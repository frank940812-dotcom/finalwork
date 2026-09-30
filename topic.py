import os
import json
import re
import requests
import pandas as pd
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP
from sklearn.cluster import HDBSCAN, KMeans
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def clean_comment_text(text: str) -> str:
    """清理留言雜訊、網址、過多標點符號與多餘空白"""
    text = str(text or "")
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"@[a-zA-Z0-9_.]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_topic_label(label: str, max_chars: int = 10) -> str:
    """清理 LLM 主題名稱，確保適合 UI 與報表顯示"""
    label = str(label or "").strip()
    label = label.replace("\n", "").replace("\r", "")
    label = label.strip("「」『』【】[]()（）:：,.，。 \"'")

    banned_phrases = [
        "話題討論", "相關主題", "相關話題", "主題討論", "留言討論", "群體分析", "社群焦點"
    ]
    for phrase in banned_phrases:
        label = label.replace(phrase, "")

    label = label.strip()
    if len(label) > max_chars:
        label = label[:max_chars]

    return label if label else "綜合社群焦點"

def call_gemini_topic_naming(prompt: str, api_key: str) -> dict:
    """自動從 Google 獲取帳號可用的所有模型清單，並依序嘗試直到成功"""
    try:
        # 1. 詢問 Google 這把 Key 可以用哪些模型
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        list_resp = requests.get(list_url, timeout=10)
        
        available_models = []
        if list_resp.status_code == 200:
            models_data = list_resp.json().get("models", [])
            for m in models_data:
                # 篩選支援 generateContent 的模型
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    # 取出模型名稱 (例: models/gemini-pro -> gemini-pro)
                    m_name = m["name"].replace("models/", "")
                    available_models.append(m_name)
            print(f"📋 偵測到可用模型清單: {available_models[:4]}")
        else:
            print(f"⚠️ 獲取模型清單失敗: {list_resp.text[:100]}")
            available_models = ["gemini-pro", "gemini-1.0-pro"]

        # 2. 依序使用偵測到的模型進行推論
        for model_name in available_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                    return json.loads(text)
                else:
                    print(f"⚠️ 模型 [{model_name}] 回應 ({resp.status_code}): {resp.text[:80]}")
            except Exception as e:
                print(f"⚠️ 模型 [{model_name}] 異常: {e}")

    except Exception as overall_e:
        print(f"⚠️ API 連線發生錯誤: {overall_e}")

    return {}


def run_topic_modeling(input_csv: str):
    print(f"\n🤖 啟動高階 BERTopic + LLM 智慧主題聚類專家！正在分析：{input_csv}")
    
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    df = pd.read_csv(input_csv, encoding="utf-8-sig")

    comment_col = "comment" if "comment" in df.columns else "jieba_cut"
    df = df.dropna(subset=[comment_col])
    
    # 清理留言文本
    df["clean_doc"] = df[comment_col].apply(clean_comment_text)
    df = df[df["clean_doc"].str.len() >= 2].copy()

    final_chart_path = os.path.join(output_dir, "topic_sentiment_barchart.html")
    output_file = input_csv.replace(".csv", "_FINAL.csv")

    if len(df) < 15:
        print(f"⚠️ 留言樣本較少 ({len(df)} 筆)，直接聚合為單一核心主題。")
        df['topic'] = 0
        df['topic_name'] = "社群熱議核心焦點"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        return {"final_csv": output_file, "barchart_html": final_chart_path}

    print("🚀 啟動 BERTopic 語意向量分群...")
    docs = df["clean_doc"].tolist()

    custom_stopwords = {
        "可以", "非常", "這是", "一路", "提示", "相關", "這個", "那個", "因為", "所以", 
        "就是", "什麼", "覺得", "知道", "已經", "感覺", "真的", "好像", "看到", "出來",
        "感謝", "謝謝", "分享", "這集", "話題討論", "影片", "頻道", "大家", "支持", "哈哈",
        "笑死", "怎麼", "不是", "還有", "一個", "現在", "沒有", "也是"
    }
    
    stopwords_path = os.path.join(current_dir, "stopwords.txt")
    stopwords = list(custom_stopwords)
    if os.path.exists(stopwords_path):
        with open(stopwords_path, encoding="utf-8") as f:
            stopwords.extend([line.strip() for line in f.readlines()])
    stopwords = list(set(stopwords))

    vectorizer_model = CountVectorizer(
        stop_words=stopwords,
        min_df=2
    )

    umap_model = UMAP(
        n_neighbors=15,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42
    )

    # 主題數量控制：資料足夠時固定切成 10 個主題
    if len(df) >= 300:
        target_topics = 10
    elif len(df) >= 150:
        target_topics = 8
    elif len(df) >= 80:
        target_topics = 6
    else:
        target_topics = 4

    target_topics = min(
        target_topics,
        max(2, len(df) // 5)
    )

    print(f"🎯 本次預計建立 {target_topics} 個主題")

    cluster_model = KMeans(
        n_clusters=target_topics,
        random_state=42,
        n_init="auto"
    )

    topic_model = BERTopic(
        embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
        vectorizer_model=vectorizer_model,
        umap_model=umap_model,
        hdbscan_model=cluster_model,
        language="multilingual",
        nr_topics=None
    )

    topics, probs = topic_model.fit_transform(docs)

    # KMeans 會將每筆留言分配到固定群組，因此不需要 reduce_outliers。
    try:
        topic_model.update_topics(docs, topics=topics)
    except Exception as e:
        print(f"⚠️ 主題詞更新略過：{e}")

    df['topic'] = topics
    topic_info = topic_model.get_topic_info()

    topic_context_prompt = ""
    topic_summary_dict = {}

    for index, row in topic_info.iterrows():
        t_id = int(row['Topic'])
        if t_id != -1: 
            top_words = [
                word for word, _ in topic_model.get_topic(t_id)[:10]
                if word not in custom_stopwords and not re.match(r"^[a-zA-Z0-9_.]+$", word)
            ]
            sample_comments = df[df['topic'] == t_id][comment_col].head(5).tolist()
            clean_samples = [clean_comment_text(s)[:50] for s in sample_comments]

            topic_summary_dict[t_id] = {
                "keywords": ", ".join(top_words[:6]),
                "samples": sample_comments
            }

            samples_str = "\n  - ".join(clean_samples)
            topic_context_prompt += (
                f"【群聚編號 {t_id}】\n"
                f"高頻關鍵字：{', '.join(top_words[:6])}\n"
                f"代表留言範例：\n  - {samples_str}\n\n"
            )

    prompt = f"""
你是一位專業的社群大數據輿情分析專家。
以下是從社群留言中聚類出的民眾討論族群。請根據每個族群的「代表留言範例」與「關鍵字」，
替每個群聚產生：主題名稱、上層分類，以及一句淺顯易懂的重點摘要。

{topic_context_prompt}

【命名規則】
1. name：繁體中文，4 到 8 個中文字，要清楚指出核心議題。
2. category：只能從以下 8 類擇一：
   - 內容與功能
   - 使用體驗
   - 價格與價值
   - 品牌與服務
   - 事件與爭議
   - 情緒與互動
   - 問題與求助
   - 其他
3. summary：20 到 45 個中文字，用一般人看得懂的方式解釋這群留言主要在談什麼。
4. 禁止使用「相關主題」「心得分享」「留言討論」等空泛名稱。
5. 僅輸出標準 JSON，不要加 Markdown。

JSON 格式範例：
{{
  "0": {{
    "name": "訓練強度質疑",
    "category": "事件與爭議",
    "summary": "多數留言聚焦在訓練方式是否過度，以及實際效果是否符合預期。"
  }},
  "1": {{
    "name": "幽默調侃反應",
    "category": "情緒與互動",
    "summary": "留言主要以玩笑、迷因與輕鬆吐槽回應內容，互動氣氛偏娛樂性。"
  }}
}}
"""

    topic_label_dict = {}
    topic_category_dict = {}
    topic_insight_dict = {}

    # 從環境變數讀取 Gemini API Key
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if gemini_api_key:
        print("🚀 呼叫 Gemini 進行主題命名、分類與摘要...")
        ai_labels = call_gemini_topic_naming(
            prompt,
            gemini_api_key
        )
    else:
        print("⚠️ 尚未設定 GEMINI_API_KEY，主題名稱將使用備援規則。")
        ai_labels = {}

    allowed_categories = {
        "內容與功能",
        "使用體驗",
        "價格與價值",
        "品牌與服務",
        "事件與爭議",
        "情緒與互動",
        "問題與求助",
        "其他"
    }

    if ai_labels:
        for t_id in topic_info['Topic']:
            str_id = str(t_id)

            if str_id not in ai_labels:
                continue

            ai_item = ai_labels[str_id]

            # 相容舊格式
            if isinstance(ai_item, str):
                name = ai_item
                category = "其他"
                summary = ""
            else:
                name = ai_item.get("name", "")
                category = ai_item.get("category", "其他")
                summary = ai_item.get("summary", "")

            normalized = normalize_topic_label(
                name,
                max_chars=8
            )

            if normalized:
                topic_label_dict[int(t_id)] = normalized
                topic_category_dict[int(t_id)] = (
                    category
                    if category in allowed_categories
                    else "其他"
                )
                topic_insight_dict[int(t_id)] = (
                    str(summary).strip()
                )

        print("✅ Gemini 主題智慧命名與分類成功！")

        for topic_id in sorted(topic_label_dict.keys()):
            if topic_id != -1:
                print(
                    f"🏷️ Topic {topic_id} → "
                    f"【{topic_label_dict[topic_id]}】 / "
                    f"{topic_category_dict.get(topic_id, '其他')}"
                )

    else:
        print("⚠️ Gemini 命名未返回有效標籤，啟動備援規則...")

    topic_label_dict[-1] = "其他未分類"
    topic_category_dict[-1] = "其他"
    topic_insight_dict[-1] = "無法明確歸入主要群聚的零散留言。"

    for index, row in topic_info.iterrows():
        t_id = int(row['Topic'])

        if t_id not in topic_label_dict:
            sample_text = "".join(
                topic_summary_dict.get(
                    t_id,
                    {}
                ).get(
                    "samples",
                    []
                )
            )

            chinese_words = re.findall(
                r"[\u4e00-\u9fa5]{2,4}",
                sample_text
            )

            chinese_words = [
                word
                for word in chinese_words
                if word not in custom_stopwords
            ]

            if chinese_words:
                fallback_label = (
                    f"{chinese_words[0]}焦點"
                )
            else:
                fallback_label = (
                    f"焦點議題{t_id + 1}"
                )

            topic_label_dict[t_id] = normalize_topic_label(
                fallback_label,
                max_chars=8
            )

        if t_id not in topic_category_dict:
            topic_category_dict[t_id] = "其他"

        if not topic_insight_dict.get(t_id):
            keywords_text = topic_summary_dict.get(
                t_id,
                {}
            ).get(
                "keywords",
                ""
            )

            if keywords_text:
                topic_insight_dict[t_id] = (
                    f"此群留言主要圍繞「{keywords_text}」"
                    "等核心詞形成共同焦點。"
                )
            else:
                topic_insight_dict[t_id] = (
                    "此群留言具有相近語意，"
                    "建議搭配代表留言與情緒比例進一步解讀。"
                )

    df['topic'] = df['topic'].astype(int)
    df['topic_name'] = (
        df['topic']
        .map(topic_label_dict)
        .fillna("其他未分類")
    )

    df['topic_category'] = (
        df['topic']
        .map(topic_category_dict)
        .fillna("其他")
    )

    df['topic_summary'] = (
        df['topic']
        .map(topic_insight_dict)
        .fillna(
            "此群留言具有相近語意，"
            "建議搭配代表留言與情緒比例進一步解讀。"
        )
    )

    topic_keywords_dict = {
        int(topic_id): info.get(
            "keywords",
            ""
        )
        for topic_id, info in topic_summary_dict.items()
    }

    df['topic_keywords'] = (
        df['topic']
        .map(topic_keywords_dict)
        .fillna("")
    )

    # =====================================================
    # 主題層級統計資料
    # =====================================================
    total_rows = max(
        len(df),
        1
    )

    topic_volume_map = (
        df['topic']
        .value_counts()
        .to_dict()
    )

    topic_rank_map = {
        topic_id: rank
        for rank, topic_id in enumerate(
            df['topic']
            .value_counts()
            .index
            .tolist(),
            start=1
        )
    }

    df['topic_volume'] = (
        df['topic']
        .map(topic_volume_map)
        .fillna(0)
        .astype(int)
    )

    df['topic_share_pct'] = (
        df['topic_volume']
        / total_rows
        * 100
    ).round(2)

    df['topic_rank'] = (
        df['topic']
        .map(topic_rank_map)
        .fillna(0)
        .astype(int)
    )

    if "sentiment" in df.columns:
        sentiment_stats = (
            df.groupby(
                ['topic', 'sentiment']
            )
            .size()
            .unstack(
                fill_value=0
            )
        )

        sentiment_total = (
            sentiment_stats
            .sum(axis=1)
            .replace(0, 1)
        )

        sentiment_mapping = [
            ("正面", "topic_positive_rate"),
            ("中立", "topic_neutral_rate"),
            ("負面", "topic_negative_rate"),
            ("提問", "topic_question_rate"),
        ]

        for sentiment_name, output_column in sentiment_mapping:
            if sentiment_name not in sentiment_stats.columns:
                sentiment_stats[
                    sentiment_name
                ] = 0

            rate_map = (
                sentiment_stats[
                    sentiment_name
                ]
                / sentiment_total
                * 100
            ).round(2).to_dict()

            df[output_column] = (
                df['topic']
                .map(rate_map)
                .fillna(0.0)
            )

        def classify_topic_risk(
            negative_rate
        ):
            if negative_rate >= 30:
                return "高風險"

            if negative_rate >= 15:
                return "需關注"

            return "穩定"

        df['topic_risk_level'] = (
            df['topic_negative_rate']
            .apply(
                classify_topic_risk
            )
        )

    else:
        df['topic_positive_rate'] = 0.0
        df['topic_neutral_rate'] = 0.0
        df['topic_negative_rate'] = 0.0
        df['topic_question_rate'] = 0.0
        df['topic_risk_level'] = "穩定"

    if "clean_doc" in df.columns:
        df = df.drop(
            columns=["clean_doc"]
        )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ==========================================
    # 📊 生成雙維度圖表
    # ==========================================
    try:
        print("📈 繪製主題與情緒分析圖表...")
        if "sentiment" not in df.columns:
            df["sentiment"] = "中立"

        df_grouped = df.groupby(['topic', 'topic_name', 'sentiment']).size().reset_index(name='count')
        topic_totals = df_grouped.groupby('topic_name')['count'].sum().reset_index(name='total')
        topic_totals = topic_totals.sort_values(by='total', ascending=True) 
        sorted_topics = topic_totals['topic_name'].tolist()

        fig = make_subplots(
            rows=1, cols=2, 
            subplot_titles=("🔥 各話題討論總筆數 (聲量)", "🎭 各話題民眾情緒佔比 (%)"),
            shared_yaxes=True,
            horizontal_spacing=0.08
        )

        colors = {'正面': '#2ecc71', '中立': '#95a5a6', '負面': '#e74c3c', '提問': '#3498db'}

        for sentiment in ['正面', '中立', '負面', '提問']:
            sub_df = df_grouped[df_grouped['sentiment'] == sentiment].copy()
            if not sub_df.empty:
                hover_texts = []
                for _, r in sub_df.iterrows():
                    t_id = r['topic']
                    summary = topic_summary_dict.get(t_id, {"keywords": "無", "samples": []})
                    kw = summary["keywords"]
                    samples_formatted = "<br>".join([f"• {clean_comment_text(s)[:30]}..." for s in summary["samples"][:2]])
                    
                    ht = (
                        f"<b>【{r['topic_name']}】</b><br>"
                        f"情緒: {sentiment} | 筆數: {r['count']} 筆<br>"
                        f"<b>🔑 核心詞:</b> {kw}<br>"
                        f"<b>💬 代表留言:</b><br>{samples_formatted}"
                    )
                    hover_texts.append(ht)

                fig.add_trace(
                    go.Bar(
                        y=sub_df['topic_name'], 
                        x=sub_df['count'], 
                        name=sentiment,
                        orientation='h',
                        marker_color=colors.get(sentiment, '#3498db'),
                        legendgroup=sentiment,
                        hoverinfo="text",
                        hovertext=hover_texts
                    ),
                    row=1, col=1
                )

        df_pivot = df_grouped.pivot(index='topic_name', columns='sentiment', values='count').fillna(0)
        df_pct = df_pivot.div(df_pivot.sum(axis=1), axis=0) * 100
        df_pct = df_pct.reset_index()

        for sentiment in ['正面', '中立', '負面', '提問']:
            if sentiment in df_pct.columns:
                fig.add_trace(
                    go.Bar(
                        y=df_pct['topic_name'], 
                        x=df_pct[sentiment], 
                        name=sentiment,
                        orientation='h',
                        marker_color=colors.get(sentiment, '#3498db'),
                        legendgroup=sentiment,
                        showlegend=False,
                        hovertemplate="話題: %{y}<br>情緒: " + sentiment + "<br>比例: %{x:.1f}%<extra></extra>"
                    ),
                    row=1, col=2
                )

        chart_height = max(520, len(sorted_topics) * 55)

        fig.update_layout(
            title_text="<b>社群媒體焦點話題與情緒傾向分析總覽</b>",
            title_font_size=18,
            barmode='stack',
            height=chart_height,
            margin=dict(l=260, r=40, t=70, b=40),
            plot_bgcolor='#F9FAFB',
            paper_bgcolor='white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_xaxes(title_text="留言筆數", row=1, col=1, showgrid=True, gridcolor='#E5E7EB')
        fig.update_xaxes(title_text="佔比 (%)", range=[0, 100], row=1, col=2, showgrid=True, gridcolor='#E5E7EB')
        fig.update_yaxes(categoryorder="array", categoryarray=sorted_topics, tickfont=dict(size=12))

        fig.write_html(final_chart_path)
        print(f"🎉 成功產出雙維度高階圖表：{final_chart_path}")

    except Exception as chart_error:
        print(f"❌ 圖表繪製錯誤: {chart_error}")

    return {"final_csv": output_file, "barchart_html": final_chart_path}

if __name__ == "__main__":
    test_file = input("請輸入測試檔名：").strip()
    run_topic_modeling(test_file)