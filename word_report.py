from pathlib import Path
from datetime import datetime
import math

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


# ==========================================
# Pillow 中文字型工具 (100% 避開 C-Extension 封鎖)
# ==========================================
def get_pillow_font(size=18):
    """
    尋找系統中的中文字型並載入，避免觸發 Matplotlib 的 DLL 封鎖。
    """
    candidate_paths = [
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\msjhbd.ttc",
        r"C:\Windows\Fonts\mingliu.ttc",
        r"C:\Windows\Fonts\kaiu.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]

    for font_path in candidate_paths:
        path = Path(font_path)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue

    # 若找不到則使用預設字型
    return ImageFont.load_default()


# ==========================================
# 基本工具
# ==========================================
def set_chinese_font(run, font_name="Microsoft JhengHei"):
    """設定 Word 中文字型。"""
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)


def set_cell_background(cell, fill):
    """設定 Word 表格儲存格底色。"""
    cell_properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    cell_properties.append(shading)


def add_heading(document, text, level=1):
    """加入統一格式的標題。"""
    heading = document.add_heading(text, level=level)
    for run in heading.runs:
        set_chinese_font(run)
    return heading


def find_column(dataframe, possible_names):
    """尋找資料中實際存在的欄位。"""
    for column_name in possible_names:
        if column_name in dataframe.columns:
            return column_name
    return None


def safe_text(value, default="-"):
    """避免空值造成錯誤。"""
    if pd.isna(value):
        return default
    text = str(value).strip()
    if not text:
        return default
    return text


# ==========================================
# 純 Pillow 繪製情緒圓餅圖 (避開 Matplotlib DLL 封鎖)
# ==========================================
def create_sentiment_chart(dataframe, output_path):
    if "sentiment" not in dataframe.columns:
        return False

    sentiment_order = ["正面", "中立", "負面", "提問"]
    counts = (
        dataframe["sentiment"]
        .fillna("未分類")
        .astype(str)
        .value_counts()
        .reindex(sentiment_order, fill_value=0)
    )
    counts = counts[counts > 0]

    if counts.empty:
        return False

    total = counts.sum()
    
    # 畫布尺寸與顏色
    width, height = 800, 500
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    color_map = {
        "正面": (46, 204, 113),   # 綠
        "中立": (149, 165, 166),  # 灰
        "負面": (231, 76, 60),    # 紅
        "提問": (52, 152, 219)    # 藍
    }

    font_title = get_pillow_font(24)
    font_label = get_pillow_font(18)

    # 標題
    draw.text((width // 2, 30), "留言情緒分布", fill="black", font=font_title, anchor="mm")

    # 繪製圓餅圖
    center_x, center_y, radius = 300, 270, 160
    bbox = [center_x - radius, center_y - radius, center_x + radius, center_y + radius]
    
    start_angle = -90.0
    legend_y = 180

    for label, count in counts.items():
        extent = (count / total) * 360.0
        color = color_map.get(label, (100, 100, 100))

        # 扇形
       
        draw.pieslice(bbox, start=start_angle, end=start_angle + extent, fill=color, outline="white")
        # 圖例
        pct = (count / total) * 100
        legend_text = f"{label}: {count} ({pct:.1f}%)"
        
        draw.rectangle([520, legend_y, 545, legend_y + 20], fill=color)
        draw.text((560, legend_y - 2), legend_text, fill="black", font=font_label)
        legend_y += 40

        start_angle += extent

    img.save(output_path)
    return True


# ==========================================
# 純 Pillow 繪製主題橫向長條圖 (避開 Matplotlib DLL 封鎖)
# ==========================================
def create_topic_chart(dataframe, output_path):
    topic_column = find_column(dataframe, ["topic_name", "topic"])

    if topic_column is None:
        return False

    topic_counts = (
        dataframe[topic_column]
        .fillna("未分類")
        .astype(str)
        .value_counts()
        .head(10)
    )

    if topic_counts.empty:
        return False

    width, height = 900, 550
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    font_title = get_pillow_font(24)
    font_label = get_pillow_font(16)

    # 標題
    draw.text((width // 2, 30), "前十大討論主題聲量", fill="black", font=font_title, anchor="mm")

    max_val = max(topic_counts.values) if max(topic_counts.values) > 0 else 1
    items = list(topic_counts.items())
    
    start_y = 80
    bar_height = 32
    gap = 12
    margin_left = 220
    max_bar_width = 580

    for i, (label, count) in enumerate(items):
        y = start_y + i * (bar_height + gap)

        # 主題名稱
        draw.text((margin_left - 15, y + bar_height // 2), label, fill="black", font=font_label, anchor="rm")

        # 長條
        bar_w = int((count / max_val) * max_bar_width)
        bar_w = max(bar_w, 4) # 確保極小值仍可看見
        
        draw.rectangle([margin_left, y, margin_left + bar_w, y + bar_height], fill=(52, 152, 219))

        # 數值
        draw.text((margin_left + bar_w + 10, y + bar_height // 2), str(count), fill="black", font=font_label, anchor="lm")

    img.save(output_path)
    return True


# ==========================================
# 建立摘要表格
# ==========================================
def add_summary_table(document, rows):
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"

    header_cells = table.rows[0].cells
    header_cells[0].text = "監測指標"
    header_cells[1].text = "分析結果"

    for cell in header_cells:
        set_cell_background(cell, "D9EAF7")
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                set_chinese_font(run)

    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = str(label)
        cells[1].text = str(value)
        for cell in cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_chinese_font(run)

    return table


# ==========================================
# 加入代表性留言
# ==========================================
def add_comment_table(document, dataframe, title, sentiment_label, limit=5):
    add_heading(document, title, level=2)

    if "sentiment" not in dataframe.columns:
        document.add_paragraph("資料中沒有 sentiment 欄位。")
        return

    comment_column = find_column(dataframe, ["comment", "text", "content", "jieba_cut"])
    author_column = find_column(dataframe, ["author", "username", "user"])
    score_column = find_column(dataframe, ["sentiment_score", "confidence", "score"])

    if comment_column is None:
        document.add_paragraph("找不到留言內容欄位。")
        return

    filtered_dataframe = dataframe[
        dataframe["sentiment"].astype(str) == sentiment_label
    ].copy()

    if score_column:
        filtered_dataframe[score_column] = pd.to_numeric(
            filtered_dataframe[score_column], errors="coerce"
        )
        filtered_dataframe = filtered_dataframe.sort_values(
            score_column, ascending=False, na_position="last"
        )

    filtered_dataframe = filtered_dataframe.head(limit)

    if filtered_dataframe.empty:
        document.add_paragraph(f"目前沒有「{sentiment_label}」留言。")
        return

    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"

    header_names = ["帳號", "留言內容", "信心度"]

    for index, header_name in enumerate(header_names):
        cell = table.rows[0].cells[index]
        cell.text = header_name
        set_cell_background(cell, "EAF2F8")
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                set_chinese_font(run)

    for _, row in filtered_dataframe.iterrows():
        cells = table.add_row().cells

        author = safe_text(row.get(author_column), "匿名使用者") if author_column else "匿名使用者"
        comment = safe_text(row.get(comment_column))

        if score_column:
            score_value = row.get(score_column)
            if pd.isna(score_value):
                score = "-"
            else:
                try:
                    score = f"{float(score_value):.2f}"
                except (TypeError, ValueError):
                    score = safe_text(score_value)
        else:
            score = "-"

        cells[0].text = author
        cells[1].text = comment
        cells[2].text = score

        for cell in cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_chinese_font(run)


# ==========================================
# 主要函式：產生 Word 報告
# ==========================================
def generate_word_report(csv_path, target_url="", platform="YouTube"):
    csv_path = Path(csv_path).resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"找不到分析 CSV：{csv_path}")

    dataframe = pd.read_csv(csv_path, encoding="utf-8-sig")

    if dataframe.empty:
        raise ValueError("分析 CSV 裡沒有任何資料。")

    output_directory = csv_path.parent
    assets_directory = output_directory / f"{csv_path.stem}_report_assets"
    assets_directory.mkdir(parents=True, exist_ok=True)

    sentiment_chart_path = assets_directory / "sentiment_chart.png"
    topic_chart_path = assets_directory / "topic_chart.png"

    has_sentiment_chart = create_sentiment_chart(dataframe, sentiment_chart_path)
    has_topic_chart = create_topic_chart(dataframe, topic_chart_path)

    total_count = len(dataframe)

    if "sentiment" in dataframe.columns:
        sentiment_counts = dataframe["sentiment"].fillna("未分類").astype(str).value_counts()
    else:
        sentiment_counts = pd.Series(dtype="int64")

    positive_count = int(sentiment_counts.get("正面", 0))
    neutral_count = int(sentiment_counts.get("中立", 0))
    negative_count = int(sentiment_counts.get("負面", 0))
    question_count = int(sentiment_counts.get("提問", 0))

    positive_rate = (positive_count / total_count * 100) if total_count > 0 else 0
    negative_rate = (negative_count / total_count * 100) if total_count > 0 else 0

    if negative_rate > 30:
        risk_status = "危機型預警"
        risk_description = "負面留言比例高於 30%，建議立即檢視主要負面主題，並準備危機回應策略。"
    elif negative_rate > 15:
        risk_status = "輕度風險"
        risk_description = "負面留言比例介於 15% 至 30%，建議持續追蹤負面聲量與高頻議題。"
    else:
        risk_status = "正常"
        risk_description = "目前負面留言比例低於或等於 15%，整體輿情相對穩定。"

    document = Document()

    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    normal_style = document.styles["Normal"]
    normal_style.font.name = "Microsoft JhengHei"
    normal_style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    normal_style.font.size = Pt(10.5)

    for style_name in ["Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"]:
        if style_name in document.styles:
            style = document.styles[style_name]
            style.font.name = "Microsoft JhengHei"
            style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")

    # 封面
    title_paragraph = document.add_paragraph()
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_paragraph.add_run("社群媒體輿情分析報告")
    title_run.bold = True
    title_run.font.size = Pt(24)
    set_chinese_font(title_run)

    subtitle_paragraph = document.add_paragraph()
    subtitle_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle_paragraph.add_run("情緒分析、主題建模與決策支援")
    subtitle_run.font.size = Pt(14)
    set_chinese_font(subtitle_run)

    document.add_paragraph("")

    add_summary_table(
        document,
        [
            ("監測平台", platform),
            ("監測目標", target_url or "未提供"),
            ("總留言數", total_count),
            ("報告產出時間", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ],
    )

    document.add_page_break()

    # 執行摘要
    add_heading(document, "一、執行摘要", level=1)
    add_summary_table(
        document,
        [
            ("正面留言", f"{positive_count} 則（{positive_rate:.1f}%）"),
            ("中立留言", f"{neutral_count} 則"),
            ("負面留言", f"{negative_count} 則（{negative_rate:.1f}%）"),
            ("提問留言", f"{question_count} 則"),
            ("系統預警狀態", risk_status),
        ],
    )

    summary_paragraph = document.add_paragraph()
    summary_label = summary_paragraph.add_run("整體判斷：")
    summary_label.bold = True
    summary_paragraph.add_run(risk_description)
    for run in summary_paragraph.runs:
        set_chinese_font(run)

    # 情緒分布圖
    add_heading(document, "二、情緒分布分析", level=1)
    if has_sentiment_chart:
        chart_paragraph = document.add_paragraph()
        chart_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        chart_run = chart_paragraph.add_run()
        chart_run.add_picture(str(sentiment_chart_path), width=Inches(6.3))

        caption = document.add_paragraph("圖 1 留言情緒分布")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in caption.runs:
            set_chinese_font(run)
    else:
        document.add_paragraph("目前資料不足，無法建立情緒分布圖。")

    # 主題圖表
    add_heading(document, "三、主要討論主題", level=1)
    if has_topic_chart:
        chart_paragraph = document.add_paragraph()
        chart_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        chart_run = chart_paragraph.add_run()
        chart_run.add_picture(str(topic_chart_path), width=Inches(6.5))

        caption = document.add_paragraph("圖 2 前十大討論主題聲量")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in caption.runs:
            set_chinese_font(run)
    else:
        document.add_paragraph("目前資料缺少 topic 或 topic_name 欄位，因此沒有建立主題圖表。")

    # 代表性留言
    add_heading(document, "四、代表性留言", level=1)
    add_comment_table(document, dataframe, "4.1 代表性正面留言", "正面")
    document.add_paragraph("")
    add_comment_table(document, dataframe, "4.2 代表性負面留言", "負面")
    document.add_paragraph("")
    add_comment_table(document, dataframe, "4.3 代表性提問留言", "提問")

    # 決策建議
    add_heading(document, "五、決策建議", level=1)
    if negative_rate > 30:
        recommendations = [
            "優先檢視負面聲量最高的討論主題。",
            "整理重複出現的不滿原因，建立統一回應內容。",
            "每日追蹤負面比例與高互動留言的變化。",
            "必要時啟動危機溝通與公關回應流程。",
        ]
    elif negative_rate > 15:
        recommendations = [
            "持續追蹤負面比例是否上升。",
            "整理常見不滿與提問，建立回覆範本。",
            "觀察主要討論主題是否出現負面集中現象。",
        ]
    else:
        recommendations = [
            "維持目前的社群互動與內容策略。",
            "整理正面留言中的高頻優點。",
            "持續監測可能形成風險的新主題。",
        ]

    for recommendation in recommendations:
        paragraph = document.add_paragraph(recommendation, style="List Bullet")
        for run in paragraph.runs:
            set_chinese_font(run)

    output_path = csv_path.with_name(f"{csv_path.stem}_輿情分析報告.docx")
    document.save(output_path)
    return str(output_path.resolve())


if __name__ == "__main__":
    print("word_report.py 是提供 main_api.py 匯入使用的報告模組。")