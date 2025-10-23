# main.py
import os
import sys
import base64
import re
import requests
from dotenv import load_dotenv

# 本文件会使用 lxml 来解析/美化模型返回的 XML
from lxml import etree as ET

# ==============================================================================
# 1. 加载 .env 并配置
# ==============================================================================
print("--- 步骤 1: 加载环境配置 ---")
load_dotenv()

# --- API 配置 ---
API_KEY = os.environ.get("ZHIPUAI_API_KEY")
# 根据新文档，更新模型名称为 GLM-4.5V
MODEL_NAME = "glm-4.5v"

if not API_KEY:
    print("  > 错误：未在 .env 文件中找到 ZHIPUAI_API_KEY")
    sys.exit(1)

print(f"  > 配置加载成功，将使用智谱AI模型: {MODEL_NAME}")

# --- 从 .env 文件加载提示词 ---
PERCEPTUAL_PROMPT = os.environ.get("PERCEPTUAL_PROMPT", "")
SEMANTIC_PROMPT_TEMPLATE = os.environ.get("SEMANTIC_PROMPT_TEMPLATE", "")
CODE_GENERATION_PROMPT_TEMPLATE = os.environ.get("CODE_GENERATION_PROMPT_TEMPLATE", "")

if not all([PERCEPTUAL_PROMPT, SEMANTIC_PROMPT_TEMPLATE, CODE_GENERATION_PROMPT_TEMPLATE]):
    print("  > 错误：一个或多个提示词环境变量未在 .env 文件中设置。")
    sys.exit(1)

print("  > 提示词加载完成。")
print("--- 配置加载完毕 ---\n")


# ==============================================================================
# 2. 辅助函数
# ==============================================================================
def encode_image_to_base64(image_path: str) -> str:
    """将图像文件编码为Base64字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"  > 错误：找不到图片文件 '{image_path}'")
        sys.exit(1)
    except Exception as e:
        print(f"  > 读取或编码图片时出错: {e}")
        sys.exit(1)

def clean_xml_output(xml_string: str) -> str:
    """清理模型可能返回的多余字符，如 markdown 代码块或思考过程。"""
    # 移除可能的思维链标签
    if "<think>" in xml_string and "</think>" in xml_string:
        # 假设思维链内容和代码是分开的，这里我们只取代码部分
        # 实际情况可能更复杂，但这是一个基础处理
        parts = xml_string.split("</think>")
        if len(parts) > 1:
            xml_string = parts[1] # 取思考过程之后的内容

    if "```xml" in xml_string:
        xml_string = xml_string.split("```xml", 1)[1]
    if "```" in xml_string:
        xml_string = xml_string.rsplit("```", 1)[0]
    return xml_string.strip()


def _escape_ampersands(s: str) -> str:
    """将未转义的 & 转为 &amp;，但保留已经是实体的部分。"""
    # 先暂时保护常见实体
    protected = {
        '&amp;': '__AMP__',
        '&lt;': '__LT__',
        '&gt;': '__GT__',
        '&quot;': '__QUOT__',
        "&apos;": '__APOS__',
    }
    for k, v in protected.items():
        s = s.replace(k, v)

    # 替换剩余的 &
    s = s.replace('&', '&amp;')

    # 恢复保护的实体
    for k, v in protected.items():
        s = s.replace(v, k)

    return s


def format_xml_string(xml_string: str) -> str:
    """尝试解析并美化模型返回的 XML 字符串。

    - 使用 recover 模式容错解析
    - 对无法解析的碎片尝试封装进根元素再解析
    - 返回带 XML 声明和缩进的 UTF-8 文本
    """
    if not xml_string or not xml_string.strip():
        return xml_string

    # 预处理：移除前后噪音并处理未转义的 &
    xml_candidate = xml_string.strip()
    xml_candidate = _escape_ampersands(xml_candidate)

    parser = ET.XMLParser(recover=True, encoding='utf-8')
    try:
        root = ET.fromstring(xml_candidate.encode('utf-8'), parser=parser)
        pretty = ET.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)
        return pretty.decode('utf-8')
    except Exception:
        # 如果直接解析失败，尝试将内容封装到一个根元素中
        try:
            wrapped = f"<root>{xml_candidate}</root>"
            root = ET.fromstring(wrapped.encode('utf-8'), parser=parser)
            # 如果包装后解析成功，取根下第一个子元素（如果存在）并输出
            children = list(root)
            if len(children) == 1:
                pretty = ET.tostring(children[0], pretty_print=True, encoding='utf-8', xml_declaration=True)
                return pretty.decode('utf-8')
            else:
                pretty = ET.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)
                return pretty.decode('utf-8')
        except Exception:
            # 最后退回到原始修剪文本（尽可能保证写入）
            return xml_string.strip()


# ==============================================================================
# 3. API 调用函数 (已根据 GLM-4.5V 文档更新)
# ==============================================================================
def get_xml_from_zhipuai(prompt: str, image_path: str, max_tokens: int = 8000) -> str | None:
    """
    调用智谱AI的 glm-4.5v 模型，发送合并后的提示词和图片，获取XML结果。
    """
    print(f"  > 正在调用智谱AI API (模型: {MODEL_NAME})...")
    try:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        base64_image = encode_image_to_base64(image_path)
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
            ]
        }]
        
        # 根据 GLM-4.5V 文档构建请求体
        data = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": max_tokens,
            # (新增) 开启思维链，强制模型思考，有助于复杂任务
            "thinking": {
                "type": "enabled"
            },
            # (新增) 根据文档建议，用于代码生成等确定性任务，设为 false
            "do_sample": False,
            # 当 do_sample 为 false 时，temperature 和 top_p 会被忽略，故注释掉
            # "temperature": 0.1,
            # "top_p": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=180)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content")
            if content:
                print("  > API 调用成功，已收到响应。")
                return content
            else:
                print(f"  > API 响应格式不正确: {result}")
                return None
        else:
            print(f"  > API 调用失败: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("  > API 请求超时，请检查网络连接或代理设置。")
        return None
    except Exception as e:
        print(f"  > API 调用时发生未知异常: {e}")
        return None

# ==============================================================================
# 4. 主程序入口
# ==============================================================================
if __name__ == "__main__":
    input_image_file = "transformer.jpg"

    if not os.path.exists(input_image_file):
        print(f"错误：找不到要处理的图片文件 '{input_image_file}'。")
        sys.exit(1)
        
    combined_prompt = (
        f"{PERCEPTUAL_PROMPT}\n\n"
        f"---\n\n"
        f"{SEMANTIC_PROMPT_TEMPLATE}\n\n"
        f"---\n\n"
        f"{CODE_GENERATION_PROMPT_TEMPLATE}"
    )
    
    print(f"--- 流程开始：使用图片 '{input_image_file}' 生成XML ---")
    
    final_xml = get_xml_from_zhipuai(combined_prompt, input_image_file)
    
    if final_xml:
        cleaned_xml = clean_xml_output(final_xml)
        output_filename = "output.xml"
        
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(cleaned_xml)
            print(f"\n--- 流程成功！---\nXML 文件已保存到: {output_filename}")
        except Exception as e:
            print(f"\n--- 流程失败 ---\n保存文件时出错: {e}")
            print("\n模型返回的原始数据如下:\n---")
            print(final_xml)

    else:
        print("\n--- 流程失败 ---\n未能从API获取有效的XML内容。")