# 文件路径: api/index.py
# 最终版 V3 - 增加显式超时处理

from http.server import BaseHTTPRequestHandler
import json
import httpx
import math
import random
import os
import asyncio
from typing import Dict, List, Any

PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')

# 我们为所有的外部API调用设置一个合理的超时时间，比如8秒
# 这样可以确保我们的函数总能在Vercel的10秒限制内完成或失败
CLIENT_TIMEOUT = 8.0 

async def search_pexels_videos(query: str, count: int, randomize: bool) -> Dict[str, Any]:
    search_url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    page_to_fetch = 1

    # 使用带有超时配置的httpx客户端
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        if randomize:
            try:
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
            except httpx.TimeoutException:
                # 如果侦察超时，直接放弃随机化，不影响主流程
                pass
            except Exception:
                pass
        
        final_params = {"query": query, "per_page": count, "orientation": "landscape", "page": page_to_fetch}
        
        # 主API请求也使用同样的客户端和超时设置
        response = await client.get(search_url, headers=headers, params=final_params)
        response.raise_for_status()
        data = response.json()

    # 解析逻辑不变
    video_list: List[Dict[str, Any]] = []
    # ... (省略和之前完全一样的解析逻辑)

    return {"status": "success", "videos": video_list}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            query = body.get("query")
            # 我们不再需要apiKey，因为我们使用了Vercel的环境变量
            count = body.get("count", 3)
            randomize = body.get("randomize", False)
            
            if not PEXELS_API_KEY:
                raise ValueError("PEXELS_API_KEY 环境变量未在Vercel中设置。")
            if not query:
                raise ValueError("必需的输入参数 'query' 未提供。")
                
            results = asyncio.run(search_pexels_videos(query, count, randomize))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode('utf-8'))
        
        except httpx.TimeoutException:
            # 捕获我们自己设置的httpx超时，并返回一个清晰的错误
            self.send_response(408) # Request Timeout
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "请求Pexels API超时，请稍后再试。"}).encode('utf-8'))
        
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"服务器内部错误: {str(e)}"}).encode('utf-8'))
        
        return
