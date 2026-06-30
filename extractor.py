"""
AI 结构化数据异步提取核心模块
----------------------------
本模块包含核心的 Pydantic 数据模型定义，以及使用 AsyncOpenAI 异步客户端与大模型交互的提取逻辑。
"""

import json
import os
import sys
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

# 第一步：定义期望提取的强类型目标数据结构
class ProjectInfo(BaseModel):
    project_name: str = Field(description="项目名称，例如某某研发楼建设项目")
    location: str = Field(description="项目建设地点，要求精确到区或县，若有具体路口也可包含")
    total_area_sqm: float = Field(description="总建筑面积，单位为平方米。模型必须只提取数值，不带单位")

    # 允许字段为 None
    floors_above_ground: int | None = Field(
        default=None, 
        description="地上楼层数。若原文未提及，请输出 null。绝对不能猜测"
    )
    floors_underground: int | None = Field(
        default=None, 
        description="地下楼层数。若原文未提及，请输出 null。绝对不能猜测"
    )

    structural_type: str = Field(description="结构形式，例如框架结构、剪力墙结构、钢结构等")


# 第二步：获取 API 环境变量并初始化异步大模型客户端
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 初始化异步客户端 (AsyncOpenAI)
# 这样在 FastAPI 这样的异步 Web 服务中调用大模型时，不会阻塞其他并发请求。
client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url,
)


async def extract_project_info(raw_text: str) -> ProjectInfo:
    """
    异步提取接口：接受原始非结构化描述文本，调用大语言模型进行提取，并在本地进行类型校验。
    """
    # 自动将 Pydantic 转换为标准 JSON Schema，作为提示词的一部分注入给大模型
    schema_json = json.dumps(ProjectInfo.model_json_schema(), ensure_ascii=False)

    # 异步调用 chat.completions.create 并使用 await 挂起，释放事件循环以允许其他并发请求
    response = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {
                "role": "system",
                "content": (
                    f"你是一个专业的建筑工程信息提取专家。请从用户的文本中提取关键的工程参数。\n"
                    f"你必须输出一个符合以下 JSON Schema 格式的 JSON 对象：\n"
                    f"{schema_json}\n\n"
                    f"🚨 【重要安全规则】:\n"
                    f"1. 如果文中完全没有提及某个参数（如楼层数），该字段必须输出为 null，以防逻辑漏洞。\n"
                    f"2. 绝对禁止猜测，绝对禁止自作聪明地用 0、-1 或空字符串 '' 来代替未提及的数据。"
                ),
            },
            {"role": "user", "content": raw_text},
        ],
        # 启用 JSON 模式强制大模型只输出标准 JSON 字符串
        response_format={"type": "json_object"},
    )

    # 提取生成的 JSON 字符串
    raw_json_str = response.choices[0].message.content

    # 本地 Pydantic 严格校验并转换为强类型对象
    extracted_data = ProjectInfo.model_validate_json(raw_json_str)
    
    return extracted_data
