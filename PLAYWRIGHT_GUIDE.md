# Playwright 浏览器沙盒使用指南

## 概述

Playwright 浏览器沙盒是一个基于 Playwright 的实时浏览器控制系统，允许 AI 在真实的浏览器环境中执行操作。这是一个可选的前端类型，提供了比简单截图分析更强大的功能。

## 特性

- 🎭 **真实浏览器**: 使用 Playwright 控制真实的 Chromium 浏览器
- 🤖 **AI驱动**: 通过 Gemini AI 分析截图并生成操作指令
- 📸 **实时截图**: 自动截取浏览器当前状态
- 📊 **操作日志**: 详细记录所有操作和结果
- 🔄 **会话管理**: 支持多个浏览器会话同时运行
- ⚡ **自动执行**: AI 分析后自动在浏览器中执行操作

## 安装

### 1. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

这将下载并安装 Chromium 浏览器，大约需要 300MB 空间。

### 3. 配置环境变量

确保 `.env` 文件中配置了 Gemini API 密钥：

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3-pro-preview
```

## 使用步骤

### 1. 启动后端服务

```bash
cd backend
python main.py
```

服务将在 `http://localhost:5000` 启动。

### 2. 打开 Playwright 沙盒页面

在浏览器中打开 `frontend/playwright_sandbox.html`。

### 3. 配置浏览器参数

- **后端服务地址**: 默认 `http://localhost:5000`
- **目标网页URL**: 要访问的网页地址（如 `https://www.google.com`）
- **浏览器宽度**: 默认 1280 像素
- **浏览器高度**: 默认 720 像素

### 4. 启动浏览器

点击 "🚀 启动浏览器" 按钮。系统将：
1. 启动一个 Playwright 控制的 Chromium 浏览器
2. 访问指定的 URL
3. 自动截取初始截图
4. 返回会话 ID

### 5. 输入 AI 指令

在指令框中输入自然语言指令，例如：
- "点击搜索框"
- "在搜索框中输入'Playwright'"
- "点击搜索按钮"
- "向下滚动页面"

### 6. 执行指令

点击 "⚡ 执行指令" 按钮。系统将：
1. 截取当前浏览器状态
2. 发送截图和指令给 Gemini AI
3. AI 分析并返回操作建议
4. 在浏览器中自动执行操作
5. 显示执行结果和新的截图

### 7. 查看结果

- **浏览器预览**: 显示浏览器当前截图
- **操作日志**: 记录所有操作和结果
- **统计信息**: 显示执行次数、成功次数、错误次数

### 8. 关闭浏览器

完成操作后，点击 "❌ 关闭浏览器" 按钮关闭会话。

## API 接口

### 启动浏览器

```http
POST /playwright/launch
Content-Type: application/json

{
  "url": "https://www.google.com",
  "width": 1280,
  "height": 720,
  "headless": false
}
```

响应：
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://www.google.com",
  "viewport": {
    "width": 1280,
    "height": 720
  }
}
```

### 截取截图

```http
POST /playwright/screenshot
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

响应：
```json
{
  "success": true,
  "screenshot": "data:image/png;base64,...",
  "url": "https://www.google.com"
}
```

### 执行操作

```http
POST /playwright/execute
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": {
    "action": "click",
    "x": 640,
    "y": 360,
    "button": "left",
    "reasoning": "点击搜索框"
  }
}
```

响应：
```json
{
  "success": true,
  "message": "在坐标 (640, 360) 执行点击",
  "action": "click"
}
```

### 关闭会话

```http
POST /playwright/close
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 列出所有会话

```http
GET /playwright/sessions
```

响应：
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": 1234567890.123,
      "url": "https://www.google.com"
    }
  ],
  "count": 1
}
```

## 支持的操作类型

### 1. 鼠标点击 (mouse_click)

```json
{
  "action": "click",
  "x": 640,
  "y": 360,
  "button": "left",
  "duration": 0
}
```

- `x`, `y`: 点击坐标（像素）
- `button`: 按键类型（left/middle/right）
- `duration`: 按下时长（毫秒）

### 2. 鼠标悬停 (mouse_hover)

```json
{
  "action": "hover",
  "x": 640,
  "y": 360
}
```

### 3. 鼠标拖动 (mouse_drag)

```json
{
  "action": "drag",
  "start_x": 100,
  "start_y": 100,
  "end_x": 500,
  "end_y": 500,
  "button": "left"
}
```

### 4. 鼠标滚动 (mouse_scroll)

```json
{
  "action": "scroll",
  "scroll_x": 0,
  "scroll_y": 100
}
```

- 正值：向下/向右滚动
- 负值：向上/向左滚动

### 5. 键盘输入 (keyboard_type)

```json
{
  "action": "type",
  "text": "Hello, World!"
}
```

### 6. 键盘按键 (keyboard_press)

```json
{
  "action": "press",
  "keys": ["ctrl", "c"]
}
```

支持的按键：
- 修饰键：ctrl, shift, alt, win/meta
- 功能键：enter, esc, tab, space, backspace, delete
- 方向键：up, down, left, right
- 其他：home, end, pageup, pagedown, f1-f12

## 工作流程

```
用户输入指令
    ↓
截取浏览器截图
    ↓
发送截图和指令给 Gemini AI
    ↓
AI 分析并返回操作建议
    ↓
Playwright 在浏览器中执行操作
    ↓
截取新的截图
    ↓
显示结果
```

## 坐标系统

系统使用两种坐标系统：

### 1. 归一化坐标（0-1000）

AI 返回的坐标使用归一化系统，范围为 0-1000：
- x: 0（最左）到 1000（最右）
- y: 0（最顶）到 1000（最底）

### 2. 实际像素坐标

后端自动将归一化坐标转换为实际像素坐标：
```python
actual_x = (normalized_x / 1000) * screen_width
actual_y = (normalized_y / 1000) * screen_height
```

## 最佳实践

### 1. 清晰的指令

使用清晰、具体的指令：
- ✅ "点击页面顶部的搜索框"
- ✅ "在输入框中输入'Playwright'"
- ❌ "做点什么"

### 2. 分步执行

对于复杂任务，分步执行：
1. "点击搜索框"
2. "输入'Playwright'"
3. "点击搜索按钮"

### 3. 等待页面加载

在执行下一步之前，确保页面已加载完成。系统会自动等待 0.5 秒。

### 4. 检查结果

每次操作后查看截图，确认操作是否成功。

## 故障排除

### 浏览器无法启动

**问题**: 点击启动按钮后没有反应

**解决方案**:
1. 检查后端服务是否运行
2. 确认已安装 Playwright 浏览器：`playwright install chromium`
3. 查看后端日志的错误信息

### 操作执行失败

**问题**: AI 返回了操作，但执行失败

**解决方案**:
1. 检查坐标是否在屏幕范围内
2. 确认目标元素是否可见
3. 尝试使用更具体的指令

### 截图显示空白

**问题**: 浏览器截图显示空白页面

**解决方案**:
1. 等待页面完全加载
2. 检查目标 URL 是否可访问
3. 尝试刷新页面

### 会话丢失

**问题**: 提示会话不存在

**解决方案**:
1. 重新启动浏览器
2. 检查会话是否已超时
3. 使用 `/playwright/sessions` 接口查看活动会话

## 安全注意事项

1. **不要在生产环境使用**: 这是一个开发工具，不适合生产环境
2. **保护 API 密钥**: 不要在公共代码中暴露 Gemini API 密钥
3. **限制访问**: 确保后端服务只在本地网络访问
4. **监控使用**: 注意 Gemini API 的使用配额

## 限制

1. **浏览器支持**: 目前只支持 Chromium
2. **并发限制**: 建议不要同时运行太多会话
3. **性能**: 截图和 AI 分析需要时间
4. **准确性**: AI 的操作建议可能不总是准确

## 示例场景

### 场景 1: Google 搜索

1. 启动浏览器，URL: `https://www.google.com`
2. 指令: "点击搜索框"
3. 指令: "输入'Playwright automation'"
4. 指令: "点击搜索按钮"

### 场景 2: 表单填写

1. 启动浏览器，访问表单页面
2. 指令: "点击姓名输入框"
3. 指令: "输入'张三'"
4. 指令: "点击邮箱输入框"
5. 指令: "输入'zhangsan@example.com'"
6. 指令: "点击提交按钮"

### 场景 3: 页面导航

1. 启动浏览器
2. 指令: "点击导航栏的'关于'链接"
3. 指令: "向下滚动查看更多内容"
4. 指令: "点击返回顶部按钮"

## 技术架构

```
前端 (playwright_sandbox.html)
    ↓ HTTP
后端 Flask API (main.py)
    ↓
PlaywrightController (playwright_controller.py)
    ↓
Playwright Browser
    ↓
Gemini AI (分析截图)
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License