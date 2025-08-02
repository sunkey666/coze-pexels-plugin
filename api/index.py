# 文件路径: api/index.py

from fastapi import FastAPI, Request, HTTPException
import httpx
import math
import random
from typing import Dict, List, Any

# 1. 创建一个FastAPI应用实例，这是我们Web服务的核心
app = FastAPI()

# 2. 这是我们插件的核心逻辑函数，负责与Pexels API交互
#    它被设计成一个独立的、可复用的函数
async def search_pexels_videos(query: str, api_key: str, count: int, randomize: bool) -> Dict[str, Any]:
    """
    根据关键词在Pexels上搜索视频，并返回精炼后的数据。
    """
    search_url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    page_to_fetch = 1

    # 随机化逻辑
    if randomize:
        try:
            scout_params = {"query": query, "per_page": 1, "page": 1}
            async with httpx.AsyncClient() as client:
                scout_response = await client.get(search_url, headers=headers, params=scout_params, timeout=20.0)
                scout_response.raise_for_status()
                scout_data = scout_response.json()
                total_results = scout_data.get("total_results", 0)

            if total_results > 0:
                items_per_page = 80 
                total_pages = math.ceil(total_results / items_per_page)
                max_page_limit = min(total_pages, 200)
                if max_page_limit > 1:
                    page_to_fetch = random.randint(1, max_page_limit)
        except Exception as e:
            # 如果随机化失败，静默处理，继续使用第一页
            print(f"Randomization scout failed: {e}")
            page_to_fetch = 1
            
    # 最终请求参数
    final_params = {
        "query": query, 
        "per_page": count, 
        "orientation": "landscape", 
        "page": page_to_fetch
    }

    # 主API请求
    async with httpx.AsyncClient() as client:
        response = await client.get(search_url, headers=headers, params=final_params, timeout=30.0)
        # 无论成功失败，都先确保能处理响应
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Pexels API Error: {response.text}")
        
        data = response.json()

    # 解析并精炼结果
    video_list: List[Dict[str, Any]] = []
    if "videos" in data:
        for video in data["videos"]:
            download_link = ""
            for file_info in video.get("video_files", []):
                if file_info.get("quality") == "sd" and "link" in file_info:
                    download_link = file_info["link"]
                    break
            if download_link:
                video_list.append({
                    "id": video.get("id"),
                    "photographer": video.get("user", {}).get("name"),
                    "download_url": download_link
                })
    
    return {"status": "success", "videos": video_list}

# 3. 创建一个API端点(Endpoint)，这是Vercel将会运行的“入口”
#    它负责接收Coze的请求，并调用上面的核心逻辑函数
@app.post("/api")
async def handler(request: Request):
    """
    这是API的主处理函数，接收来自Coze的POST请求。
    """
    try:
        # 从请求体中异步读取JSON数据
        body = await request.json()

        # 从JSON中安全地获取参数
        query = body.get("query")
        api_key = body.get("apiKey")
        count = body.get("count", 3) # 提供默认值
        randomize = body.get("randomize", False) # 提供默认值

        # 验证必需的参数是否存在
        if not query or not api_key:
            raise HTTPException(status_code=400, detail="必需的输入参数 'query' 和 'apiKey' 未提供。")

        # 调用我们的核心搜索逻辑
        results = await search_pexels_videos(query, api_key, count, randomize)
        
        # 将结果作为JSON响应返回
        return results

    except Exception as e:
        # 捕获所有可能的异常，并返回一个标准的HTTP错误
        # 这样Coze就能知道调用失败了
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# Vercel 需要一个顶级的 'app' 变量来识别FastAPI应用
# 我们在文件开头已经定义好了 app = FastAPI()