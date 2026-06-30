"""
AI 结构化数据提取工作流示例
----------------------------
本示例展示了如何结合大语言模型（如 DeepSeek、OpenAI 等）与 Pydantic，
从无结构的自然语言文本中提取标准、结构化的 JSON 数据，并在本地进行类型验证。

核心学习目标:
1. 学习如何通过环境变量安全配置 LLM 客户端，避免密钥泄漏。
2. 学习使用 Pydantic 声明强类型数据模型。
3. 学习将 Pydantic 生成的 JSON Schema 注入 System Prompt，精准定义模型的输出格式。
4. 学习启用大模型的 JSON Mode（JSON 对象格式限制）。
5. 学习在本地使用 Pydantic 校验和解析大模型输出，确保数据可靠性。
"""

import json
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# 解决 Windows 控制台 UTF-8 编码报错问题：
# 在 Windows 环境下，默认控制台编码通常为 GBK。如果 Python 尝试打印 Emoji 或特定 Unicode 字符，
# 会抛出 UnicodeEncodeError。通过显式重置输出流的编码为 UTF-8 可以完美解决此崩溃。
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 第一步：加载 `.env` 环境变量文件
# 这是开发中的最佳实践。避免将敏感 API 密钥硬编码在代码中，以防止上传至 GitHub 等公开平台。
load_dotenv()

# 从环境变量中安全地检索 API 密钥和 Base URL
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 基本参数校验：如果用户未配置 API 密钥或仍然使用占位符，给出友好提示并终止程序
if not api_key or "your_api_key" in api_key or "你的" in api_key:
    print("错误: 请先在 .env 文件中配置好您真实的 OPENAI_API_KEY！")
    sys.exit(1)


# 第二步：使用 Pydantic 定义期望提取的强类型目标数据结构
# 1. 继承 `BaseModel` 以获得强大的自动校验、解析和序列化能力。
# 2. 通过 `Field` 的 `description` 属性为每个字段添加业务解释，大模型将阅读这些解释进行精准提取。
class ProjectInfo(BaseModel):
    project_name: str = Field(description="项目名称，例如某某研发楼建设项目")
    location: str = Field(description="项目建设地点，要求精确到区或县，若有具体路口也可包含")
    total_area_sqm: float = Field(description="总建筑面积，单位为平方米。模型必须只提取数值，不带单位")

    # 允许字段为 None（在 Python 3.10+ 中推荐使用 `int | None` 语法）
    # 设置 default=None。这样即使模型输出中缺失该字段，Pydantic 也会赋予默认值 None，而不会引发校验报错。
    floors_above_ground: int | None = Field(
        default=None, 
        description="地上楼层数。若原文未提及，请输出 null。绝对不能猜测"
    )
    floors_underground: int | None = Field(
        default=None, 
        description="地下楼层数。若原文未提及，请输出 null。绝对不能猜测"
    )

    structural_type: str = Field(description="结构形式，例如框架结构、剪力墙结构、钢结构等")


# 第三步：初始化大模型客户端
# 由于绝大多数国产大模型（如 DeepSeek、阿里云通义灵积、智谱等）都提供了 OpenAI 兼容接口，
# 我们可以直接使用标准库 `openai.OpenAI`，只需传入定制的 `api_key` 和 `base_url` 即可。
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)


def run_extraction():
    # 待提取的非结构化工程描述文本
    raw_text = """
    本工程名为合肥高新区创新产业园三期A1栋研发楼建设项目，
    施工地点位于合肥市蜀山区创新大道与合欢路交口。
    该研发楼的主要用途为研发办公，配套有停车场和设备机房。
    总占地和建设规模方面，该研发楼的总建筑面积大约是 32500.50 平方米。
    承重结构采用的是目前主流的现浇钢筋混凝土剪力墙结构，抗震设防烈度为7度。
    """

    # 第四步：自动将 Pydantic 转换为标准 JSON Schema
    # 大模型对标准 JSON Schema 的理解力远优于人类编写的模棱两成自然语言格式说明。
    # 这样可以彻底免除手写“请输出格式如下：{...}”之类 Prompt 的痛苦。
    schema_json = json.dumps(ProjectInfo.model_json_schema(), ensure_ascii=False)

    print("正在向大语言模型请求结构化提取数据...\n")

    try:
        # 第五步：使用标准的 chat.completions.create 接口与大模型通信
        response = client.chat.completions.create(
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
            # 开启标准的 JSON 模式
            # 作用是强制 LLM 的底层输出语法必须是合法的 JSON 字符串。
            # 注意：使用 response_format={"type": "json_object"} 时，
            # 系统 Prompt 提示词中也必须包含 "json" 或 "JSON" 字样，否则部分 API 会报错。
            response_format={"type": "json_object"},
        )

        # 第六步：获取大模型返回的原始 JSON 格式字符串
        raw_json_str = response.choices[0].message.content
        print(f"👉 大模型返回的原始 JSON 字符串:\n{raw_json_str}\n")

        # 第七步：在本地使用 Pydantic 进行运行时严格验证和数据解析
        # 即使大模型生成了合法的 JSON，由于幻觉，数据类型（如将 area 输出了带有 "平方米" 字符串的值）仍可能出错。
        # model_validate_json 会进行本地校验：如果校验通过，会返回一个类型安全的 Python 对象；
        # 如果类型不符或缺失必需字段，将抛出 ValidationError 异常，防止脏数据流入下游业务系统。
        extracted_data = ProjectInfo.model_validate_json(raw_json_str)

        # 打印成功提取并经验证的类型安全数据
        print("🎉 --- 提取结果校验成功 ---")
        print(f"项目名称: {extracted_data.project_name}")
        print(f"建设地点: {extracted_data.location}")
        print(f"建筑面积: {extracted_data.total_area_sqm} ㎡")
        print(f"地上/地下层数: 地上 {extracted_data.floors_above_ground} 层 / 地下 {extracted_data.floors_underground} 层")
        print(f"结构形式: {extracted_data.structural_type}")

    except Exception as e:
        print(f"💥 运行过程中发生错误: {e}")


if __name__ == "__main__":
    run_extraction()
