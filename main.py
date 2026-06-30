"""
AI 提取服务 FastAPI 入口程序
----------------------------
使用 FastAPI 框架将 AI 提取服务封装为 Web API 接口，并自动支持 Swagger UI API 文档。
"""

import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Windows 控制台 UTF-8 输出重配置（防止打印 Emoji 或特殊 Unicode 字符时崩溃）
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from extractor import ProjectInfo, extract_project_info, api_key

# 初始化 FastAPI 应用程序，配置 Swagger 文档信息
app = FastAPI(
    title="AI 工程数据提取 API 服务",
    description="利用大语言模型 (LLM) 和 Pydantic 解析非结构化建筑描述文本，输出强类型的结构化工程数据。",
    version="0.1.0",
    docs_url="/docs",      # Swagger 页面路径
    redoc_url="/redoc",    # ReDoc 页面路径
)


# 定义 API 请求体数据结构
class ExtractRequest(BaseModel):
    text: str = Field(
        description="待解析和提取关键工程参数的原始自然语言文本",
        examples=[
            "本工程名为合肥高新区创新产业园三期A1栋研发楼建设项目，施工地点位于合肥市蜀山区创新大道与合欢路交口。总建筑面积大约是 32500.50 平方米。承重结构采用的是现浇钢筋混凝土剪力墙结构。"
        ]
    )


@app.post(
    "/api/v1/extract", 
    response_model=ProjectInfo, 
    summary="异步工程参数结构化提取", 
    description="上传一段包含建筑描述的原始文本，模型将对其进行解析并返回符合 ProjectInfo 模式的强类型 JSON 结果。"
)
async def api_extract_project_info(request: ExtractRequest):
    # 服务端密钥预检查，未配置时给出 500 报错提示
    if not api_key or "your_api_key" in api_key or "你的" in api_key:
        raise HTTPException(
            status_code=500, 
            detail="OpenAI API Key is not configured on the server. Please check the server's .env file."
        )
    
    try:
        # 异步调用核心提取逻辑
        result = await extract_project_info(request.text)
        return result
    except Exception as e:
        # 返回详细的错误提示给客户端
        raise HTTPException(status_code=500, detail=f"LLM Extraction failed: {str(e)}")


@app.get(
    "/health", 
    summary="服务健康状况检查", 
    description="检查 API 服务的当前运行状态。"
)
async def api_health_check():
    return {"status": "ok", "message": "AI Extraction Service is running smoothly."}


# 本地直接运行启动（可执行: python main.py 启动开发服务器）
if __name__ == "__main__":
    import uvicorn
    # 启动 ASGI 服务
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
