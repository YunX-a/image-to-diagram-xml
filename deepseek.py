# deepseek.py (最终版 - 集成图片缩放)
import os
import sys
import base64
import io
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image # 导入Pillow库用于图片处理

# ==============================================================================
# 1. 加载 .env 并配置
# ==============================================================================
print("--- 步骤 1: 加载环境配置 ---")
load_dotenv()

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
MODEL_NAME = "deepseek-chat"

if not DEEPSEEK_API_KEY:
    print("  > 错误：未在 .env 文件中找到 DEEPSEEK_API_KEY")
    sys.exit(1)

print(f"  > 配置加载成功，将使用模型: {MODEL_NAME}")

PERCEPTUAL_PROMPT = os.environ.get("PERCEPTUAL_PROMPT", "")
SEMANTIC_PROMPT_TEMPLATE = os.environ.get("SEMANTIC_PROMPT_TEMPLATE", "")
CODE_GENERATION_PROMPT_TEMPLATE = os.environ.get("CODE_GENERATION_PROMPT_TEMPLATE", "")

if not all([PERCEPTUAL_PROMPT, SEMANTIC_PROMPT_TEMPLATE, CODE_GENERATION_PROMPT_TEMPLATE]):
    print("  > 错误：请确保 .env 文件中已设置 PERCEPTUAL_PROMPT, SEMANTIC_PROMPT_TEMPLATE, 和 CODE_GENERATION_PROMPT_TEMPLATE")
    sys.exit(1)

COMBINED_PROMPT = f"""
{PERCEPTUAL_PROMPT}

{SEMANTIC_PROMPT_TEMPLATE}

{CODE_GENERATION_PROMPT_TEMPLATE}

请根据以上指令，分析提供的图片，并直接输出最终的 Draw.io XML 代码。
"""
print("  > 提示词加载并合并完成。")
print("--- 配置加载完毕 ---\n")


# ==============================================================================
# 2. 辅助函数
# ==============================================================================
def resize_and_encode_image(image_path: str, max_dimension: int = 1024) -> str:
    """
    读取图片，如果尺寸过大则进行缩放，然后编码为 Base64 字符串。
    """
    try:
        with Image.open(image_path) as img:
            # 检查图片尺寸
            if max(img.width, img.height) > max_dimension:
                print(f"  > 图片尺寸 ({img.width}x{img.height}) 过大，正在等比缩放至最长边为 {max_dimension} 像素...")
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                print(f"  > 图片已缩放至: {img.width}x{img.height}")

            # 将处理后的图片保存到内存中的字节流
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()

            # 对字节流进行 Base64 编码
            return base64.b64encode(image_bytes).decode('utf-8')

    except Exception as e:
        print(f"  > 错误：处理或编码图像文件失败: {e}")
        sys.exit(1)

def clean_xml_output(xml_string: str) -> str:
    """清理模型可能返回的多余字符，如 markdown 代码块。"""
    if "```xml" in xml_string:
        xml_string = xml_string.split("```xml", 1)[1]
    if "```" in xml_string:
        xml_string = xml_string.rsplit("```", 1)[0]
    return xml_string.strip()


# ==============================================================================
# 3. 核心流程：一步生成XML
# ==============================================================================
def generate_xml_from_image(image_path: str):
    """
    单次调用 DeepSeek Vision API，直接从图片生成 XML。
    """
    print(f"--- 步骤 2: 开始处理图片 '{image_path}' ---")

    if not os.path.exists(image_path):
        print(f"  > 错误：找不到图片文件 '{image_path}'")
        return None

    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
    except Exception as e:
        print(f"  > 错误：初始化 API 客户端失败: {e}")
        return None

    # ==================================================================
    # 调用新的函数，该函数会先处理图片尺寸再进行编码
    # ==================================================================
    print("  > 正在预处理图片并进行 Base64 编码...")
    base64_image = resize_and_encode_image(image_path)
    print("  > 图片预处理和编码完成。")

    print("  > 正在发送请求至 DeepSeek API，请稍候...")
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": f'{COMBINED_PROMPT}\n<img src="data:image/jpeg;base64,{base64_image}">'
                }
            ],
            max_tokens=4096,
            temperature=0.1,
            stream=False
        )
        
        xml_content = response.choices[0].message.content
        print("  > 成功接收到 API 响应。")
        return xml_content

    except Exception as e:
        print(f"  > 错误：API 调用失败: {e}")
        return None


# ==============================================================================
# 4. 主程序入口
# ==============================================================================
if __name__ == "__main__":
    input_image_file = "transformer.jpg"

    final_xml = generate_xml_from_image(input_image_file)

    if final_xml:
        print("\n--- 步骤 3: 清理并保存结果 ---")
        cleaned_xml = clean_xml_output(final_xml)
        
        output_filename = "output.xml"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(cleaned_xml)
        print(f"  > 流程完成！XML 文件已成功保存到: {output_filename}")
    else:
        print("\n流程失败：未能从 API 获取有效的 XML 内容。")