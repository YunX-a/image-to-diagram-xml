# main.py (已修正版本)
import os
import sys
import base64
import requests
import io
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# ==============================================================================
# 1. 加载 .env 并配置
# ==============================================================================
print("--- 步骤 1: 加载环境配置 ---")
load_dotenv()

# --- API 提供商选择 ---
API_PROVIDER = os.environ.get("API_PROVIDER", "zhipuai").lower()

# --- 根据选择加载特定配置 ---
if API_PROVIDER == "zhipuai":
    API_KEY = os.environ.get("ZHIPUAI_API_KEY")
    MODEL_NAME = os.environ.get("ZHIPUAI_MODEL", "glm-4.5v")
    if not API_KEY:
        print("  > 错误：未在 .env 文件中找到 ZHIPUAI_API_KEY")
        sys.exit(1)
    print(f"  > 已选择 API 提供商: 智谱AI (ZhipuAI)，模型: {MODEL_NAME}")
elif API_PROVIDER == "deepseek":
    API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    MODEL_NAME = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    if not API_KEY:
        print("  > 错误：未在 .env 文件中找到 DEEPSEEK_API_KEY")
        sys.exit(1)
    print(f"  > 已选择 API 提供商: 深度求索 (DeepSeek)，模型: {MODEL_NAME}")
else:
    print(f"  > 错误：不支持的 API_PROVIDER: '{API_PROVIDER}'。请在 .env 文件中设置为 'zhipuai' 或 'deepseek'。")
    sys.exit(1)

# --- 加载共用的提示词 ---
PERCEPTUAL_PROMPT = os.environ.get("PERCEPTUAL_PROMPT", "")
SEMANTIC_PROMPT_TEMPLATE = os.environ.get("SEMANTIC_PROMPT_TEMPLATE", "")
CODE_GENERATION_PROMPT_TEMPLATE = os.environ.get("CODE_GENERATION_PROMPT_TEMPLATE", "")

if not all([PERCEPTUAL_PROMPT, SEMANTIC_PROMPT_TEMPLATE, CODE_GENERATION_PROMPT_TEMPLATE]):
    print("  > 错误：一个或多个提示词环境变量未在 .env 文件中设置。")
    sys.exit(1)

# 将提示词合并为一个，供所有API使用
COMBINED_PROMPT = (
    f"{PERCEPTUAL_PROMPT}\n\n"
    f"---\n\n"
    f"{SEMANTIC_PROMPT_TEMPLATE}\n\n"
    f"---\n\n"
    f"{CODE_GENERATION_PROMPT_TEMPLATE}\n\n"
    "请根据以上指令，分析提供的图片，并直接输出最终的 Draw.io XML 代码。"
)
print("  > 提示词加载并合并完成。")
print("--- 配置加载完毕 ---\n")


# ==============================================================================
# 2. 辅助函数 (共用)
# ==============================================================================
def resize_and_encode_image(image_path: str, max_dimension: int = 1024) -> str:
    """
    读取图片，如果尺寸过大则进行缩放，然后编码为 Base64 字符串。
    """
    try:
        with Image.open(image_path) as img:
            if max(img.width, img.height) > max_dimension:
                print(f"  > 图片尺寸 ({img.width}x{img.height}) 过大，正在等比缩放至最长边为 {max_dimension} 像素...")
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                print(f"  > 图片已缩放至: {img.width}x{img.height}")
            
            buffer = io.BytesIO()
            # 确保保存为JPEG格式以兼容大多数API的base64数据头
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            
            return base64.b64encode(image_bytes).decode('utf-8')
    except FileNotFoundError:
        print(f"  > 错误：找不到图片文件 '{image_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"  > 错误：处理或编码图像文件失败: {e}")
        sys.exit(1)

def clean_xml_output(xml_string: str) -> str:
    """清理模型可能返回的多余字符，如 markdown 代码块或思考过程。"""
    # 移除 ZhipuAI 可能的思维链标签
    if xml_string and "<think>" in xml_string and "</think>" in xml_string:
        parts = xml_string.split("</think>")
        if len(parts) > 1:
            xml_string = parts[1]

    # 移除 Markdown 代码块
    if xml_string and "```xml" in xml_string:
        xml_string = xml_string.split("```xml", 1)[1]
    if xml_string and "```" in xml_string:
        xml_string = xml_string.rsplit("```", 1)[0]
    
    return xml_string.strip() if xml_string else ""


# ==============================================================================
# 3. API 调用函数
# ==============================================================================
def call_zhipuai_api(prompt: str, image_path: str, max_tokens: int = 8000) -> str | None:
    """调用智谱AI API"""
    print(f"  > 正在调用智谱AI API (模型: {MODEL_NAME})...")
    try:
        base64_image = resize_and_encode_image(image_path)
        
        response = requests.post(
            url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            },
            json={
                "model": MODEL_NAME,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                "max_tokens": max_tokens,
                "thinking": {"type": "enabled"},
                "do_sample": False
            },
            timeout=180
        )
        response.raise_for_status() # 检查HTTP请求错误
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content")
        print("  > 成功接收到 API 响应。")
        return content

    except requests.exceptions.RequestException as e:
        print(f"  > API 请求失败: {e}")
        return None
    except Exception as e:
        print(f"  > API 调用时发生未知异常: {e}")
        return None

def call_deepseek_api(prompt: str, image_path: str, max_tokens: int = 4096) -> str | None:
    """调用DeepSeek API"""
    print(f"  > 正在调用 DeepSeek API (模型: {MODEL_NAME})...")
    try:
        client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
        base64_image = resize_and_encode_image(image_path)
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{
                "role": "user", 
                "content": f'{prompt}\n<img src="data:image/jpeg;base64,{base64_image}">'
            }],
            max_tokens=max_tokens,
            temperature=0.1,
            stream=False
        )
        
        xml_content = response.choices[0].message.content
        print("  > 成功接收到 API 响应。")
        return xml_content
    except Exception as e:
        print(f"  > API 调用失败: {e}")
        return None


# ==============================================================================
# 4. 主程序入口
# ==============================================================================
if __name__ == "__main__":
    input_image_file = "transformer.jpg"
    
    print(f"--- 步骤 2: 开始使用 {API_PROVIDER.upper()} 处理图片 '{input_image_file}' ---")

    final_xml = None
    if API_PROVIDER == "zhipuai":
        final_xml = call_zhipuai_api(COMBINED_PROMPT, input_image_file)
    elif API_PROVIDER == "deepseek":
        final_xml = call_deepseek_api(COMBINED_PROMPT, input_image_file)

    if final_xml:
        print("\n--- 步骤 3: 清理并保存结果 ---")
        cleaned_xml = clean_xml_output(final_xml)
        
        output_filename = "output.xml"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(cleaned_xml)
        print(f"  > 流程完成！XML 文件已成功保存到: {output_filename}")
    else:
        print("\n--- 流程失败：未能从 API 获取有效的 XML 内容。 ---")