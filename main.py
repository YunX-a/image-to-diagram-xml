# main.py
import os
import sys
import base64
import requests
import json
from typing import Dict, Any, Optional, Callable
from lxml import etree  # type: ignore
from PIL import Image
from dotenv import load_dotenv
from enum import Enum

class APIProvider(Enum):
    ZHIPUAI = "zhipuai"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    OPENAI = "openai"

# ==============================================================================
# 1. 加载 .env 并配置
# ==============================================================================
print("--- 步骤 0: 加载环境配置 ---")
load_dotenv()

# --- API 配置 ---
API_PROVIDER = os.environ.get("API_PROVIDER", "zhipuai").lower()

# 根据选择的API提供商加载对应的配置
if API_PROVIDER == APIProvider.ZHIPUAI.value:
    API_KEY = os.environ.get("ZHIPUAI_API_KEY")
    MODEL_NAME = os.environ.get("ZHIPUAI_MODEL", "glm-4v")
    print(f"  > 使用智谱AI API，模型: {MODEL_NAME}")
elif API_PROVIDER == APIProvider.DEEPSEEK.value:
    API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    MODEL_NAME = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    print(f"  > 使用DeepSeek API，模型: {MODEL_NAME}")
elif API_PROVIDER == APIProvider.GEMINI.value:
    API_KEY = os.environ.get("GEMINI_API_KEY")
    MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-pro-vision")
    print(f"  > 使用Google Gemini API，模型: {MODEL_NAME}")
elif API_PROVIDER == APIProvider.OPENAI.value:
    API_KEY = os.environ.get("OPENAI_API_KEY")
    MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4-vision-preview")
    print(f"  > 使用OpenAI API，模型: {MODEL_NAME}")
else:
    print(f"  > 错误：不支持的API提供商: {API_PROVIDER}")
    sys.exit(1)

if not API_KEY:
    print(f"  > 错误：未找到 {API_PROVIDER.upper()} API Key")
    sys.exit(1)

if os.environ.get("HTTPS_PROXY"):
    print(f"  > 检测到代理环境变量: {os.environ.get('HTTPS_PROXY')}")
else:
    print("  > 未检测到代理环境变量。程序将尝试直接连接。")

# --- 从 .env 文件加载提示词 ---
PERCEPTUAL_PROMPT = os.environ.get("PERCEPTUAL_PROMPT", "")
SEMANTIC_PROMPT_TEMPLATE = os.environ.get("SEMANTIC_PROMPT_TEMPLATE", "")
CODE_GENERATION_PROMPT_TEMPLATE = os.environ.get("CODE_GENERATION_PROMPT_TEMPLATE", "")
REFINEMENT_PROMPT_TEMPLATE = os.environ.get("REFINEMENT_PROMPT_TEMPLATE", "")

# 检查必要的提示词是否存在
if not all([PERCEPTUAL_PROMPT, SEMANTIC_PROMPT_TEMPLATE, CODE_GENERATION_PROMPT_TEMPLATE, REFINEMENT_PROMPT_TEMPLATE]):
    print("  > 警告：某些提示词环境变量未设置，程序可能无法正常工作")

print("  > 提示词加载完成。")
print("--- 配置加载完毕 ---\n")

# ==============================================================================
# 2. 辅助函数
# ==============================================================================
def clean_xml_output(xml_string: str) -> str:
    """清理模型可能返回的多余字符，如 markdown 代码块。"""
    if "```xml" in xml_string:
        xml_string = xml_string.split("```xml", 1)[1]
    if "```" in xml_string:
        xml_string = xml_string.rsplit("```", 1)[0]
    return xml_string.strip()

def encode_image_to_base64(image_path: str) -> str:
    """将图像编码为base64字符串"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_mime_type(image_path: str) -> str:
    """获取图像的MIME类型"""
    _, ext = os.path.splitext(image_path)
    ext = ext.lower()
    if ext in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    elif ext == '.png':
        return 'image/png'
    elif ext == '.gif':
        return 'image/gif'
    elif ext == '.webp':
        return 'image/webp'
    else:
        return 'image/jpeg'  # 默认

# ==============================================================================
# 3. API 调用函数
# ==============================================================================
def call_zhipuai_api(prompt: str, image_path: Optional[str] = None, max_tokens: int = 2000) -> Optional[str]:
    """调用智谱AI API"""
    try:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        messages = []
        
        if image_path:
            base64_image = encode_image_to_base64(image_path)
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            })
            model = "glm-4v"
        else:
            messages.append({
                "role": "user",
                "content": prompt
            })
            model = "glm-4"
        
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"  > 智谱AI API 调用失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"  > 智谱AI API 调用异常: {e}")
        return None

def call_deepseek_api(prompt: str, image_path: Optional[str] = None, max_tokens: int = 2000) -> Optional[str]:
    """调用DeepSeek API"""
    try:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        # DeepSeek目前主要支持文本，如果需要图像支持可能需要特定模型
        data = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.7,
            "stream": False
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"  > DeepSeek API 调用失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"  > DeepSeek API 调用异常: {e}")
        return None

def call_gemini_api(prompt: str, image_path: Optional[str] = None, max_tokens: int = 2000) -> Optional[str]:
    """调用Google Gemini API"""
    try:
        # 确保token数量足够
        actual_max_tokens = max(max_tokens, 8000)
        print(f"  > 使用 max_tokens: {actual_max_tokens}")
        
        if image_path:
            # 多模态调用
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
            
            base64_image = encode_image_to_base64(image_path)
            mime_type = get_image_mime_type(image_path)
            
            contents = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": actual_max_tokens,
                    "temperature": 0.1,
                    "topP": 0.7
                }
            }
        else:
            # 纯文本调用 - 使用相同的模型
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
            contents = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": actual_max_tokens,
                    "temperature": 0.1,
                    "topP": 0.7
                }
            }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=contents, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate:
                    content = candidate["content"]
                    # 检查content是否有parts字段
                    if "parts" in content and len(content["parts"]) > 0:
                        return content["parts"][0]["text"]
                    # 如果没有parts，可能是新的API格式，尝试直接获取text
                    elif "text" in content:
                        return content["text"]
                    else:
                        print(f"  > Gemini API 返回格式不完整: {candidate}")
                        return None
            return None
        else:
            print(f"  > Gemini API 调用失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"  > Gemini API 调用异常: {e}")
        return None

def call_openai_api(prompt: str, image_path: Optional[str] = None, max_tokens: int = 2000) -> Optional[str]:
    """调用OpenAI API"""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        messages = []
        
        if image_path:
            base64_image = encode_image_to_base64(image_path)
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        data = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"  > OpenAI API 调用失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"  > OpenAI API 调用异常: {e}")
        return None

# API 调用函数映射
API_FUNCTIONS = {
    APIProvider.ZHIPUAI.value: call_zhipuai_api,
    APIProvider.DEEPSEEK.value: call_deepseek_api,
    APIProvider.GEMINI.value: call_gemini_api,
    APIProvider.OPENAI.value: call_openai_api
}

def call_api(prompt: str, image_path: Optional[str] = None, max_tokens: int = 2000) -> Optional[str]:
    """通用API调用函数，根据配置选择对应的API提供商"""
    if API_PROVIDER not in API_FUNCTIONS:
        print(f"  > 错误：不支持的API提供商: {API_PROVIDER}")
        return None
    
    api_function = API_FUNCTIONS[API_PROVIDER]
    return api_function(prompt, image_path, max_tokens)

# ==============================================================================
# 4. 核心流程
# ==============================================================================
def run_planning_stage(image_path: str):
    """执行从粗到细的规划阶段"""
    print("--- 阶段 1: 规划开始 ---")
    
    try:
        if not os.path.exists(image_path):
            print(f"  > 错误：无法找到图像文件 '{image_path}'")
            return None
    except Exception as e:
        print(f"  > 图像文件检查错误: {e}")
        return None

    # 第一次请求：感知分析
    print("  > 步骤 1.1: 发送包含图像的感知结构化提示...")
    try:
        perceptual_analysis = call_api(PERCEPTUAL_PROMPT, image_path, max_tokens=2000)
        if not perceptual_analysis:
            print("  > 感知分析失败")
            return None
        print("  > 感知分析完成。")
    except Exception as e:
        print(f"\n  > 错误：在感知分析阶段调用 API 失败: {e}")
        return None

    # 第二次请求：语义规划
    full_semantic_prompt = f"{SEMANTIC_PROMPT_TEMPLATE}\n\n---\nThe result of the perception analysis is below:\n{perceptual_analysis}"
    print("  > 步骤 1.2: 发送语义规范化提示...")
    try:
        semantic_plan = call_api(full_semantic_prompt, max_tokens=2000)
        if not semantic_plan:
            print("  > 语义规划失败")
            return None
        print("--- 阶段 1: 规划完成。 ---\n")
        return semantic_plan
    except Exception as e:
        print(f"\n  > 错误：在语义规划阶段调用 API 失败: {e}")
        return None

def validate_xml(xml_string: str):
    """验证 XML 字符串的语法正确性"""
    try:
        etree.fromstring(xml_string.encode('utf-8'))
        return True, ""
    except etree.XMLSyntaxError as e:
        return False, str(e)

def run_generation_stage(semantic_plan: str, max_refinements: int = 5):
    """执行代码生成与循环修正阶段"""
    print("--- 阶段 2: 生成与修正开始 ---")
    
    full_code_gen_prompt = f"{CODE_GENERATION_PROMPT_TEMPLATE}\n\n---\nThe semantic plan to implement is below:\n{semantic_plan}"
    print("  > 步骤 2.1: 生成初始 XML...")
    try:
        current_xml = call_api(full_code_gen_prompt, max_tokens=8000)
        if not current_xml:
            print("  > 初始 XML 生成失败")
            return None
        current_xml = clean_xml_output(current_xml)
    except Exception as e:
        print(f"\n  > 错误：在初始 XML 生成阶段调用 API 失败: {e}")
        return None

    for i in range(max_refinements):
        print(f"\n  > --- 修正循环第 {i+1}/{max_refinements} 轮 ---")
        is_valid, error_message = validate_xml(current_xml)
        
        if is_valid and '<mxCell id="0" parent="0"/>' in current_xml:
            is_valid = False
            error_message = "Logical Error: Root cell with id='0' cannot have a parent."

        if is_valid:
            print("  >  XML 验证通过！")
            print("--- 阶段 2: 代码生成成功。 ---")
            return current_xml
        
        print(f"  >  XML 验证失败: {error_message}")
        print("  > 发送修正提示...")
        
        try:
            full_refinement_prompt = f"{REFINEMENT_PROMPT_TEMPLATE}\n\n[INPUT]\nXML Code:\n{current_xml}\n\nError Message: '{error_message}'"
            refinement_response = call_api(full_refinement_prompt, max_tokens=4000)
            if not refinement_response:
                print("  > 修正请求失败")
                break
            current_xml = clean_xml_output(refinement_response)
        except Exception as e:
            print(f"\n  > 错误：在 XML 修正阶段调用 API 失败: {e}")
            return current_xml
    
    print("--- 阶段 2: 已达到最大修正次数，应用最终修复。 ---")
    if current_xml and '<mxCell id="0" parent="0"/>' in current_xml:
        current_xml = current_xml.replace('<mxCell id="0" parent="0"/>', '<mxCell id="0"/>')
        
    return current_xml

# ==============================================================================
# 5. 主程序入口
# ==============================================================================
if __name__ == "__main__":
    if not API_KEY:
        print(f"错误：请在 .env 文件中设置您的 {API_PROVIDER.upper()}_API_KEY。")
        sys.exit(1)
        
    input_image_file = "transformer.jpg" 

    if not os.path.exists(input_image_file):
        print(f"错误：找不到要处理的图片文件 '{input_image_file}'。")
        sys.exit(1)

    print(f"开始使用 {API_PROVIDER.upper()} 模型 '{MODEL_NAME}' 处理图片 '{input_image_file}'...")
    plan = run_planning_stage(input_image_file)
    if plan:
        final_xml = run_generation_stage(plan)
        if final_xml:
            output_filename = "output.xml"
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(final_xml)
            print(f"\n流程完成！XML 文件已保存到 {output_filename}")
        else:
            print("\n流程失败：代码生成阶段未能生成有效 XML。")
    else:
        print("\n流程失败：规划阶段未能生成有效计划。")
