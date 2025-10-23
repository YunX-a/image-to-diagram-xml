# DWT Project - 图像到XML转换工具

一个基于多模态AI的图像分析和XML代码生成工具。

## 项目简介

DWT Project 是一个基于多种AI模型的图像分析和XML代码生成工具。通过多模态AI技术，它能够理解图像中的结构、关系和语义信息，然后生成高质量的XML代码。

## 快速复现指南

本项目提供了详细的手动复现流程，具体操作步骤请参考 `复现流程.md` 文件。通过四个阶段的AI对话：

1. **感知分析阶段**：让AI"看懂"图片的视觉结构
2. **语义规划阶段**：制定详细的绘图蓝图
3. **代码生成阶段**：生成完整的mxGraph XML代码
4. **验证修正阶段**：在draw.io中验证并优化结果

**实测效果**：直接使用 Gemini 2.5 Pro 进行对话，最终生成的图表与原图相似度可达95%。生成的XML文件可直接导入draw.io，图表将在画布右下角显示。

> **提示**：如果遇到XML渲染问题，建议将生成的XML代码和原图片一起提供给大模型进行优化，通常能显著提升渲染效果。

## 核心功能

- 多AI模型支持：支持智谱AI、DeepSeek、Google Gemini和OpenAI等多种AI服务
- 智能分析：采用"从粗到细"的分析策略，确保输出质量
- 自动修正：内置XML验证和智能错误修正机制
- 高度可配置：支持自定义提示词和模型参数

## 支持的AI服务

- 智谱AI (ZhipuAI)：强大的中文多模态模型
- DeepSeek：高性能的推理模型
- Google Gemini：先进的多模态AI
- OpenAI：业界领先的GPT模型

## 处理流程

- 图像分析：深度理解图像内容和结构
- 语义规划：多阶段提示工程策略
- 代码生成：自动生成高质量XML代码
- 质量检验：实时XML语法和逻辑验证
- 智能修正：最多5轮自动错误修正

## 环境要求

- Python 3.8+（推荐3.9+）
- AI服务API密钥（至少一个）
- 2GB+内存用于图像处理

附加依赖说明：项目会对模型返回的 XML 进行后处理（纠正未转义字符、容错解析并美化缩进），因此额外依赖 `lxml` 和 `defusedxml`，安装时会一并处理。

## 快速开始

### 安装步骤

1. 克隆项目
   ```bash
   git clone <repository-url>
   cd DWT_Project
   ```

2. 创建虚拟环境（推荐）
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 安装依赖包
   ```powershell
   pip install -r requirements.txt
   ```

### 环境配置

创建 `.env` 文件并配置AI服务：

```env
# API 提供商选择
API_PROVIDER=zhipuai

# 智谱AI配置
ZHIPUAI_API_KEY=your_zhipuai_api_key_here
ZHIPUAI_MODEL=glm-4v

# 网络代理（可选）
HTTPS_PROXY=http://your_proxy:port

# 提示词配置（必需）
PERCEPTUAL_PROMPT=请分析这张图像的内容和结构...
SEMANTIC_PROMPT_TEMPLATE=基于分析结果，请生成语义规划...
CODE_GENERATION_PROMPT_TEMPLATE=请根据语义规划生成XML代码...
REFINEMENT_PROMPT_TEMPLATE=请修正以下XML代码中的错误...
```

其他AI服务配置方式类似，只需修改对应的API_PROVIDER和相关密钥即可。

## 使用方法

### 基本使用

1. 准备图像文件
   将图像文件重命名为 `transformer.jpg` 并放在项目根目录
   支持格式：JPG, PNG, GIF, WebP

2. 运行程序
   ```powershell
   .\.venv\Scripts\Activate.ps1
   python main.py
   ```

3. 查看结果
   生成的XML代码保存在 `output.xml` 文件中

注意：程序会自动尝试清理和美化模型返回的 XML（移除代码块标记、修复未转义的 &、增加 XML 声明并规范缩进）。如果最终文件仍有渲染问题，请将 `output.xml` 与原图一并提交给模型进行进一步修正。

### 代码调用

```python
from main import run_planning_stage, run_generation_stage

plan = run_planning_stage("your_image.jpg")
if plan:
    xml_output = run_generation_stage(plan)
    if xml_output:
        print("XML生成成功！")
```

## 项目结构

```text
DWT_Project/
├── main.py               # 主程序入口
├── requirements.txt      # Python依赖包列表
├── README.md            # 项目文档
├── .env                 # 环境变量配置文件（需创建）
├── transformer.jpg      # 输入图像文件
├── output.xml           # 输出XML文件（程序生成）
├── .venv/               # Python虚拟环境
└── __pycache__/         # Python缓存文件
```

## 技术栈

- Python 3.8+
- 多模态AI：图像理解和代码生成
- lxml：XML处理和验证
- Pillow：图像处理和编码
- python-dotenv：环境变量管理
- requests：HTTP API调用

## 故障排除

### 常见问题

1. **API Key错误**
   - 检查 `.env` 文件中的API Key设置
   - 确认API_PROVIDER与API Key匹配
   - 验证API Key有效性和配额

2. **网络连接问题**
   - 检查网络连接
   - 配置代理：设置 `HTTPS_PROXY` 环境变量
   - 测试API连接

3. **图像处理失败**
   - 确认图像文件存在且格式正确
   - 支持格式：JPG, PNG, GIF, WebP
   - 检查图像文件大小

4. **XML生成失败**
   - 检查提示词配置是否完整
   - 验证AI模型响应
   - 检查生成的XML语法



## 许可证

本项目采用 MIT License 开源协议。

## 贡献

欢迎贡献代码、报告问题或提出改进建议。
