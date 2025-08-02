# 文件路径: api/index.py
# 最终版 - 原生Python Serverless函数格式

# 引入Python处理HTTP请求和JSON的标准库
from http.server import BaseHTTPRequestHandler
import json
import httpx
import math
import random
from typing import Dict, List, Any

# 这是我们插件的核心逻辑函数，保持不变
async def search_pexels_videos(query: str, api_key: str, count: int, randomize: bool) -> Dict[str, Any]:
    # ... (这部分核心搜索逻辑和之前完全一样)
    search_url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    page_to_fetch = 1

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
        except Exception:
            page_to_fetch = 1
            
    final_params = {
        "query": query, "per_page": count, "orientation": "landscape", "page": page_to_fetch
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(search_url, headers=headers, params=final_params, timeout=30.0)
        response.raise_for_status()
        data = response.json()

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

# 这是Vercel Python运行时的标准入口处理类
class handler(BaseHTTPRequestHandler):

    # 它只处理POST请求，这正是我们需要的
    def do_POST(self):
        try:
            # 1. 读取请求体中的JSON数据
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            # 2. 从JSON中安全地获取参数
            query = body.get("query")
            api_key = body.get("apiKey")
            count = body.get("count", 3)
            randomize = body.get("randomize", False)

            if not query or not api_key:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "必需参数 'query' 和 'apiKey' 未提供。"}).encode('utf-8'))
                return

            # 3. Vercel的原生Python环境不支持顶层await，所以我们需要一个方法来运行异步函数
            import asyncio
            results = asyncio.run(search_pexels_videos(query, api_key, count, randomize))
            
            # 4. 成功后，返回200状态码和JSON结果
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode('utf-8'))

        except Exception as e:
            # 5. 如果过程中出现任何错误，返回500状态码和错误信息
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"服务器内部错误: {str(e)}"}).encode('utf-8'))
        
        return
