# 文件路径: api/index.py
# 最终版 V2 - 原生Python Serverless函数格式 - 读取Vercel环境变量

from http.server import BaseHTTPRequestHandler
import json
import httpx
import math
import random
import os # <--- 新增导入 os 库
from typing import Dict, List, Any

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
#   新的变化：我们在函数外部，一次性地从Vercel的环境变量中读取密钥
# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')

async def search_pexels_videos(query: str, count: int, randomize: bool) -> Dict[str, Any]:
    # 核心搜索逻辑保持不变
    # ... (省略)
    
    # 我们在这里使用从环境变量中读取的 PEXELS_API_KEY
    headers = {"Authorization": PEXELS_API_KEY}
    
    # ... (省略剩余的搜索、解析逻辑)
    # ... 请确保这部分和我们上一版代码完全一致

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
            #   新的变化：我们不再需要从请求体中获取apiKey
            # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            query = body.get("query")
            # api_key = body.get("apiKey") # <--- 删掉这一行
            count = body.get("count", 3)
            randomize = body.get("randomize", False)

            if not PEXELS_API_KEY:
                # 检查环境变量是否设置成功
                raise ValueError("PEXELS_API_KEY 环境变量未在Vercel中设置。")
            
            if not query:
                raise ValueError("必需的输入参数 'query' 未提供。")

            import asyncio
            results = asyncio.run(search_pexels_videos(query, count, randomize))
            
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
