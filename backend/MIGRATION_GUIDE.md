# Gemini API 迁移指南

## 概述

本项目已从 Google GenAI Python SDK 迁移到自定义的 REST API 实现。

## 主要变更

### 1. 新增文件

- **`backend/gemini_client.py`**: 自定义 Gemini REST API 客户端
  - `GeminiClient`: 核心客户端类，处理 API 请求
  - `ConversationManager`: 对话管理器，维护对话历史和思考签名

- **`backend/tools/tool_converter.py`**: 工具声明格式转换器
  - 将内部工具声明格式转换为 Gemini REST API 格式

### 2. 修改的文件

- **`backend/main.py`**: 
  - 移除 `from google import genai`
  - 使用 `GeminiClient` 替代 `genai.Client`

- **`backend/tools/agent_controller.py`**:
  - 使用 `ConversationManager` 管理对话历史
  - 自动维护思考签名
  - 使用 REST API 格式的工具声明

- **`backend/tools/handler.py`**:
  - 使用 `GeminiClient` 和 `ConversationManager`
  - 提取思考摘要并返回

- **`backend/requirements.txt`**:
  - 移除 `google-genai==0.2.2`
  - 添加 `requests==2.31.0`

### 3. 新功能

#### 思考签名维护

系统现在自动维护 Gemini 3 系列模型的思考签名（thought_signature），确保多轮对话中的上下文连续性。

#### 思考等级配置

- **思考等级**: 设置为 `"low"`（适合快速响应的任务）
- **包含思考摘要**: `include_thoughts=True`（可查看模型的推理过程）

#### 配置参数

```python
response = client.generate_content(
    contents=contents,
    tools=tools,
    temperature=1.0,
    thinking_level="low",      # 思考等级
    include_thoughts=True      # 包含思考摘要
)
```

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 环境配置

确保 `.env` 文件中配置了正确的参数：

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3-pro-preview
GEMINI_TEMPERATURE=1.0
```

## 测试步骤

### 1. 基础功能测试

启动服务：

```bash
cd backend
python main.py
```

访问健康检查接口：

```bash
curl http://localhost:5000/health
```

预期响应：

```json
{
  "status": "ok",
  "message": "服务运行正常",
  "model": "gemini-3-pro-preview",
  "temperature": 1.0,
  "tools_loaded": 10
}
```

### 2. 工具列表测试

```bash
curl http://localhost:5000/tools
```

应该返回所有可用工具的列表。

### 3. 图片分析测试

准备一张 base64 编码的截图，然后：

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/png;base64,iVBORw0KG...",
    "screen_width": 1920,
    "screen_height": 1080,
    "instruction": "点击屏幕中央的按钮"
  }'
```

预期响应应包含：
- `success`: true
- `function_name`: 工具名称
- `thought_summary`: 思考摘要（如果有）
- 其他工具相关参数

### 4. Agent 自动化测试

#### 启动浏览器会话

```bash
curl -X POST http://localhost:5000/playwright/launch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.google.com",
    "width": 1280,
    "height": 720
  }'
```

记录返回的 `session_id`。

#### 启动 Agent 任务

```bash
curl -X POST http://localhost:5000/agent/start \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "task": "搜索 Python 教程",
    "screen_width": 1280,
    "screen_height": 720,
    "mode": "step"
  }'
```

预期响应应包含：
- `success`: true
- `step`: 步骤编号
- `actions`: 执行的操作列表
- `completed`: 是否完成
- `thought_summary`: 思考摘要（如果有）

## 关键特性

### 1. 思考签名自动维护

`ConversationManager` 自动处理思考签名：

```python
# 添加模型响应（包含思考签名）
conversation.add_model_response(response)

# 添加函数响应
conversation.add_function_responses(function_results, screenshot_bytes)
```

### 2. 思考摘要提取

可以从响应中提取思考摘要：

```python
thought_summary = client.extract_thought_summary(response)
text_response = client.extract_text_from_response(response)
```

### 3. 函数调用提取

简化的函数调用提取：

```python
function_calls = client.extract_function_calls(response)
# 返回: [(函数名, 参数), ...]
```

## 故障排查

### 问题 1: API 密钥错误

**症状**: 401 Unauthorized 错误

**解决方案**: 检查 `.env` 文件中的 `GEMINI_API_KEY` 是否正确

### 问题 2: 模型不支持

**症状**: 400 Bad Request，模型不存在

**解决方案**: 确认使用的是 Gemini 3 系列模型（如 `gemini-3-pro-preview`）

### 问题 3: 思考签名丢失

**症状**: 多轮对话中上下文丢失

**解决方案**: 确保使用 `ConversationManager` 管理对话，并且调用 `add_model_response()` 添加模型响应

### 问题 4: 导入错误

**症状**: `ModuleNotFoundError: No module named 'google'`

**解决方案**: 
1. 确认已卸载旧的 `google-genai` 包：`pip uninstall google-genai`
2. 安装新的依赖：`pip install -r requirements.txt`

## API 参考

### GeminiClient

```python
from gemini_client import GeminiClient

client = GeminiClient(
    api_key="your_api_key",
    model="gemini-3-pro-preview"
)

response = client.generate_content(
    contents=[...],
    tools=[...],
    temperature=1.0,
    thinking_level="low",
    include_thoughts=True
)
```

### ConversationManager

```python
from gemini_client import ConversationManager

conversation = ConversationManager(client)

# 添加用户消息
conversation.add_user_message("你好", image_bytes=None)

# 生成响应
response = conversation.generate_content(
    tools=tools,
    temperature=1.0,
    thinking_level="low",
    include_thoughts=True
)

# 添加模型响应（自动维护思考签名）
conversation.add_model_response(response)

# 添加函数响应
conversation.add_function_responses(
    [("tool_name", {"result": "success"})],
    screenshot_bytes=None
)
```

## 性能优化建议

1. **思考等级**: 对于简单任务使用 `"low"`，复杂任务使用 `"high"`
2. **温度参数**: Gemini 3 建议保持默认值 `1.0`
3. **批量操作**: 尽可能在单次请求中处理多个操作

## 向后兼容性

此迁移保持了与前端的完全兼容性。所有 API 端点的请求和响应格式保持不变，只是内部实现改为使用 REST API。

## 未来改进

- [ ] 添加请求重试机制的配置选项
- [ ] 支持流式响应
- [ ] 添加更详细的错误处理
- [ ] 性能监控和日志记录增强