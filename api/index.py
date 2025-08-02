# 文件路径: api/index.py
# 最终版 V4 - 纯粹的API代理/搬运工模式

from http.server import BaseHTTPRequestHandler
import json
import httpx
import math
import random
import os
import asyncio
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs

PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')

# 这个函数现在只负责调用API并直接返回原始数据
async def search_pexels_videos_raw(query: str, count: int, randomize: bool, orientation: str) -> Dict[str, Any]:
    search_url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    page_to_fetch = 1
    
    async with httpx.AsyncClient(timeout=8.0) as client:
        if randomize:
            try:
                # 随机化逻辑保持不变
                scout_params = {"query": query, "per_page": 1, "page": 1}
                scout_response = await client.get(search_url, headers=headers, params=scout_params)
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
            "query": query, "per_page": count, "orientation": orientation, "page": page_to_fetch
        }
        
        response = await client.get(search_url, headers=headers, params=final_params)
        response.raise_for_status()
        
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        #   最关键的修改：不再解析和精炼，直接返回API的原始JSON响应！
        # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
        return response.json()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 解析URL参数的逻辑不变
            parsed_path = urlparse(self.path)
            params = parse_qs(parsed_path.query)
            query = params.get("query", [None])[0]
            count = int(params.get("count", [3])[0])
            randomize = params.get("randomize", ["false"])[0].lower() == 'true'
            orientation = params.get("orientation", ["landscape"])[0]

            if not PEXELS_API_KEY:
                raise ValueError("PEXELS_API_KEY 环境变量未设置。")
            if not query:
                raise ValueError("必需参数 'query' 未提供。")

            results = asyncio.run(search_pexels_videos_raw(query, count, randomize, orientation))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"服务器内部错误: {str(e)}"}).encode('utf-8'))
        return
