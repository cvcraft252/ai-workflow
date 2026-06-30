import os
import sys
import json
from dotenv import load_dotenv

# 确保控制台能正确输出 UTF-8 字符（如 emoji）而不崩溃
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

# 1. 验证环境变量
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
if not api_key or "你的" in api_key or "your_api_key" in api_key:
    print("错误: 请先在 .env 文件中配置好您真实的 OPENAI_API_KEY！")
    sys.exit(1)


# 2. 定义我们期望的数据结构
class ProjectInfo(BaseModel):
    project_name: str = Field(description="项目名称")
    location: str = Field(description="项目建设地点，精确到区或县")
    total_area_sqm: float = Field(description="总建筑面积，单位为平方米，只需提取数值")

    # 允许为 None，且默认值为 None
    floors_above_ground: int | None = Field(default=None, description="地上楼层数。若原文未提及，请输出 null")
    floors_underground: int | None = Field(default=None, description="地下楼层数。若原文未提及，请输出 null")

    structural_type: str = Field(description="结构形式，例如框架结构、剪力墙结构等")


# 3. 初始化客户端 (这里以 DeepSeek 官方为例)
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)


def run_extraction():
    raw_text = """
    本工程名为合肥高新区创新产业园三期A1栋研发楼建设项目，
    施工地点位于合肥市蜀山区创新大道与合欢路交口。
    该研发楼的主要用途为研发办公，配套有停车场和设备机房。
    总占地和建设规模方面，该研发楼的总建筑面积大约是 32500.50 平方米。
    承重结构采用的是目前主流的现浇钢筋混凝土剪力墙结构，抗震设防烈度为7度。
    """

    # 4. 获取 Pydantic 模型的 JSON Schema，用来塞进 Prompt 里告诉模型怎么输出
    schema_json = json.dumps(ProjectInfo.model_json_schema(), ensure_ascii=False)

    print("正在通过 DeepSeek 请求进行结构化提取...\n")

    try:
        # 5. 使用标准的 chat.completions.create 接口
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {
                    "role": "system",
                    "content": f"你是一个专业的建筑工程信息提取专家。请从用户的文本中提取关键的工程参数。\n"
                    f"你必须输出一个符合以下 JSON Schema 格式的 JSON 对象：\n"
                    f"{schema_json}\n"
                    f"🚨 【重要安全规则】:\n"
                    f"1. 如果文中完全没有提及某个参数（如楼层数），该字段必须输出为 null。防止逻辑漏洞。\n"
                    f"2. 绝对禁止猜测，绝对禁止自作聪明地用 0、-1 或空字符串 '' 来代替未提及的数据。",
                },
                {"role": "user", "content": raw_text},
            ],
            # 开启标准的 JSON 模式 (兼容绝大多数主流大模型)
            response_format={"type": "json_object"},
        )

        # 6. 获取模型返回的原始字符串
        raw_json_str = response.choices[0].message.content
        print(f"👉 模型返回的原始文本:\n{raw_json_str}\n")

        # 7. 手动用 Pydantic 在本地验证和解析
        extracted_data = ProjectInfo.model_validate_json(raw_json_str)

        print("🎉 --- 提取结果成功 ---")
        print(f"项目名称: {extracted_data.project_name}")
        print(f"建设地点: {extracted_data.location}")
        print(f"建筑面积: {extracted_data.total_area_sqm} ㎡")
        print(f"地上/地下层数: 地上{extracted_data.floors_above_ground}层 / 地下{extracted_data.floors_underground}层")
        print(f"结构形式: {extracted_data.structural_type}")

    except Exception as e:
        print(f"💥 运行中发生错误: {e}")


if __name__ == "__main__":
    run_extraction()
