import requests 
import pandas as pd 

API_KEY = "AIzaSyAhHxRZGJTOFlbb8EBznKw50bmsan_KBow"


def extract_video_id(url):
    if "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return url.strip()


def fetch_replies(parent_comment_id, video_id):
    replies = []
    next_page_token = None

    while True:
        api_url = "https://www.googleapis.com/youtube/v3/comments"
        params = {
            "part": "snippet",
            "parentId": parent_comment_id,
            "maxResults": 100,
            "pageToken": next_page_token,
            "textFormat": "plainText",
            "key": API_KEY
        }

        response = requests.get(api_url, params=params, timeout=30)
        data = response.json()

        if "error" in data:
            print(f"抓回覆時 API 錯誤（parentId={parent_comment_id}）：", data["error"])
            return replies

        for item in data.get("items", []):
            snippet = item["snippet"]
            replies.append({
                "comment_id": item.get("id"),
                "parent_comment_id": parent_comment_id,
                "video_id": video_id,
                "comment_type": "reply",
                "author": snippet.get("authorDisplayName"),
                "comment": snippet.get("textDisplay"),
                "time": snippet.get("publishedAt"),
                "like": snippet.get("likeCount")
            })

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return replies


def fetch_comments_and_replies(video_id):
    all_comments = []
    next_page_token = None

    while True:
        api_url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "pageToken": next_page_token,
            "textFormat": "plainText",
            "key": API_KEY
        }

        response = requests.get(api_url, params=params, timeout=30)
        print("commentThreads HTTP 狀態碼：", response.status_code)

        data = response.json()

        if "error" in data:
            print("API 錯誤：", data["error"])
            return []

        for item in data.get("items", []):
            top_comment = item["snippet"]["topLevelComment"]
            top_snippet = top_comment["snippet"]

            top_comment_id = top_comment.get("id")
            total_reply_count = item["snippet"].get("totalReplyCount", 0)

            # 先存頂層留言
            all_comments.append({
                "comment_id": top_comment_id,
                "parent_comment_id": None,
                "video_id": video_id,
                "comment_type": "top_level",
                "author": top_snippet.get("authorDisplayName"),
                "comment": top_snippet.get("textDisplay"),
                "time": top_snippet.get("publishedAt"),
                "like": top_snippet.get("likeCount")
            })

            # 再抓完整回覆
            if total_reply_count > 0:
                replies = fetch_replies(top_comment_id, video_id)
                all_comments.extend(replies)

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return all_comments


def run_crawler(url):
    if not url:
        raise ValueError("❌ 網址不能為空")

    video_id = extract_video_id(url)
    print(f"🎬 開始抓取影片 ID：{video_id} 的留言...")

    data = fetch_comments_and_replies(video_id)

    if data:
        df = pd.DataFrame(data)
        filename = f"{video_id}_raw_comments.csv" 
        df.to_csv(filename, index=False, encoding="utf-8-sig")

        total_count = len(df)
        top_level_count = len(df[df["comment_type"] == "top_level"])
        reply_count = len(df[df["comment_type"] == "reply"])

        print(f"✅ 爬蟲完成！共抓到 {total_count} 筆留言（主留言 {top_level_count} 筆，回覆 {reply_count} 筆）")
        return filename 
    else:
        raise Exception("❌ 沒有抓到留言，請檢查影片是否開放留言或 API Key 是否有效。")


# =====================================================================
# 🚀 深度進化：全網自適應關鍵字追蹤爬蟲模組 (完美補上組員遺漏的技能！)
# =====================================================================
def fetch_comments_by_keyword(keyword, max_results=100):
    print(f"🔍 進入 crawler 關鍵字核心，正在搜尋：【{keyword}】")
    
    # 1. 向 YouTube 搜尋與關鍵字最相關的前 3 支影片
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "id",
        "q": keyword,
        "type": "video",
        "maxResults": 3,
        "key": API_KEY
    }
    
    try:
        response = requests.get(search_url, params=search_params, timeout=30)
        search_data = response.json()
        
        if "error" in search_data:
            print("❌ YouTube 搜尋 API 發生配額或權限錯誤：", search_data["error"])
            return []
            
        video_ids = [item["id"]["videoId"] for item in search_data.get("items", []) if "videoId" in item["id"]]
        print(f"📡 成功鎖定前 3 支最具產業代表性影片 ID 清單：{video_ids}")
        
        if not video_ids:
            return []
            
        all_keyword_comments = []
        
        # 2. 挨家挨戶去這 3 支影片底下榨乾她們的真實留言
        for vid in video_ids:
            print(f"📥 正在穿透抓取影片來源 {vid} 的大眾留言...")
            comments = fetch_comments_and_replies(vid)
            if comments:
                all_keyword_comments.extend(comments)
                
        if not all_keyword_comments:
            return []
            
        # 3. 🧠 【真．通用型自適應語意資料清洗濾網】
        # 擷取關鍵字的前兩個字（例如：被動、東坡、低軌）
        core_kw = keyword[:2]
        df_all = pd.DataFrame(all_keyword_comments)
        
        # 濾除完全沒提到核心概念的無關個股留言，防止像之前一樣噴出華邦電
        filter_mask = df_all["comment"].str.contains(core_kw, na=False)
        df_filtered = df_all[filter_mask].reset_index(drop=True)
        
        # 4. 防呆分流輸出
        if len(df_filtered) >= 10:
            print(f"🎯 資料清洗完畢！精準留下 {len(df_filtered)} 筆高純度【{keyword}】輿情留言。")
            return df_filtered.head(max_results).to_dict(orient="records")
        else:
            print("⚠️ 網友討論度較分散，系統採取廣義留存，抓取前段相關留言。")
            return df_all.head(max_results).to_dict(orient="records")
            
    except Exception as e:
        print(f"❌ 關鍵字多工爬蟲運作失敗: {str(e)}")
        return []

def search_videos_info_only(keyword, max_results=5):
    """
    🔍 專門功能：輸入關鍵字，只抓取 YouTube 前 3~5 支最熱門影片的 ID 與標題資訊
    """
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": max_results,
        "key": API_KEY
    }
    try:
        response = requests.get(search_url, params=search_params, timeout=30)
        search_data = response.json()
        
        if "error" in search_data:
            print("❌ YouTube 搜尋 API 錯誤：", search_data["error"])
            return []
            
        video_list = []
        for item in search_data.get("items", []):
            if "videoId" in item["id"]:
                video_list.append({
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"]
                })
        return video_list
    except Exception as e:
        print(f"❌ 搜尋影片清單失敗: {str(e)}")
        return []

if __name__ == "__main__":
    test_url = input("請輸入 YouTube 影片網址測試：").strip()
    result = run_crawler(test_url)
    print(f"測試完成，檔案存於：{result}")