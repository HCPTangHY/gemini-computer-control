# Gemini计算机控制系统

基于Gemini AI的屏幕分析与自动点击系统。通过截图分析，AI会返回建议的鼠标点击坐标。

## 项目结构

```
gemini-computer-use/
├── backend/                      # Python后端服务
│   ├── main.py                  # Flask服务器
│   ├── requirements.txt         # Python依赖
│   ├── .env.example             # 环境变量示例
│   └── tools/                   # 工具模块
│       ├── computer_control.py  # 计算机控制工具
│       ├── handler.py           # 工具调用处理器
│       └── playwright_controller.py  # Playwright控制器
├── frontend/                    # 前端页面
│   ├── index.html              # 截图和控制界面
│   └── playwright_sandbox.html # Playwright浏览器沙盒
└── README.md                    # 项目说明
```

## 功能特性

- 🖼️ **屏幕截图**: 使用浏览器原生API进行屏幕截取
- 🤖 **AI分析**: 使用Gemini 3.0 Pro模型分析截图
- 🎯 **多种操作**: 支持鼠标点击、悬停、拖动、滚动和键盘输入
- 🎭 **Playwright沙盒**: 在真实浏览器中执行AI建议的操作
- 🤖 **Agent模式**: 自动化执行复杂任务，无需人工干预
- 🔄 **实时状态**: 显示后端服务连接状态
- 📊 **结果展示**: 美观的结果展示界面
- 🔧 **工具系统**: 基于函数调用的可扩展工具架构

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt

# 安装 Playwright 浏览器（用于浏览器沙盒功能）
playwright install chromium
```

### 2. 配置API密钥

复制环境变量示例文件并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的Gemini API密钥：

```
GEMINI_API_KEY=your_actual_api_key_here
```

> 💡 从 [Google AI Studio](https://aistudio.google.com/app/apikey) 获取API密钥

### 3. 启动后端服务

```bash
python main.py
```

服务将在 `http://localhost:5000` 启动

### 4. 打开前端页面

直接在浏览器中打开 `frontend/index.html` 文件，或使用本地服务器：

```bash
# 使用Python内置服务器
cd frontend
python -m http.server 8080
```

然后访问 `http://localhost:8080`

## 使用说明

### 方式一：截图分析模式（index.html）

1. **检查连接**: 确保页面左上角的状态指示灯为绿色（在线）
2. **截取屏幕**: 点击"📸 截取屏幕"按钮，选择要截取的屏幕或窗口
3. **输入指令**: （可选）在文本框中输入AI指令，例如"点击屏幕中央的按钮"
4. **AI分析**: 点击"🚀 发送给AI分析"按钮
5. **查看结果**: AI将返回建议的点击坐标和原因

### 方式二：Playwright浏览器沙盒（playwright_sandbox.html）

支持三种执行模式：

#### 手动模式
1. 打开 `frontend/playwright_sandbox.html`
2. 选择"手动模式"
3. 启动浏览器
4. 输入单个指令并执行
5. 查看结果

#### Agent单步模式
1. 选择"Agent单步模式"
2. 启动浏览器
3. 输入完整任务描述
4. 点击"执行任务"，AI执行一步
5. 点击"继续"按钮，AI继续执行下一步
6. 重复直到任务完成

#### Agent自动模式（推荐）
1. 选择"Agent自动模式"
2. 启动浏览器
3. 输入完整任务描述（如"在Google搜索Playwright并打开第一个结果"）
4. 点击"执行任务"
5. AI自动循环执行直到任务完成
6. 查看任务总结

## API接口

### 基础接口

#### 健康检查
```
GET /health
```

#### 列出可用工具
```
GET /tools
```

#### 分析截图
```
POST /analyze
```

请求体：
```json
{
  "image": "base64编码的图片数据",
  "screen_width": 1920,
  "screen_height": 1080,
  "instruction": "用户指令（可选）",
  "temperature": 1.0,
  "mode": "AUTO"
}
```

返回：
```json
{
  "success": true,
  "action": "click",
  "x": 960,
  "y": 540,
  "normalized_x": 500,
  "normalized_y": 500,
  "reasoning": "点击原因的简短说明"
}
```

### Playwright浏览器控制接口

#### 启动浏览器
```
POST /playwright/launch
```

请求体：
```json
{
  "url": "https://example.com",
  "width": 1280,
  "height": 720,
  "headless": false
}
```

#### 截取浏览器截图
```
POST /playwright/screenshot
```

请求体：
```json
{
  "session_id": "uuid"
}
```

#### 执行浏览器操作
```
POST /playwright/execute
```

请求体：
```json
{
  "session_id": "uuid",
  "action": {
    "action": "click",
    "x": 100,
    "y": 200
  }
}
```

#### 关闭浏览器会话
```
POST /playwright/close
```

#### 列出所有会话
```
GET /playwright/sessions
```

## 技术栈

### 后端
- **Flask**: Web框架
- **Google GenAI**: Gemini API客户端
- **Playwright**: 浏览器自动化
- **Flask-CORS**: 跨域支持
- **python-dotenv**: 环境变量管理

### 前端
- **原生HTML/CSS/JavaScript**: 无框架依赖
- **Screen Capture API**: 浏览器截图功能
- **Fetch API**: HTTP请求

### AI工具系统
- **函数调用**: 基于Gemini函数调用的工具系统
- **坐标归一化**: 0-1000范围的归一化坐标系统
- **多工具支持**: 鼠标操作、键盘操作等6种工具

## 注意事项

1. **浏览器兼容性**: 需要支持Screen Capture API的现代浏览器（Chrome、Edge等）
2. **HTTPS要求**: 某些浏览器可能要求HTTPS才能使用截图功能
3. **API配额**: 注意Gemini API的使用配额限制
4. **图片大小**: 建议截图不要过大，以免影响处理速度

## 故障排除

### 后端服务无法启动
- 检查Python版本（建议3.8+）
- 确认已安装所有依赖
- 检查端口5000是否被占用

### 前端无法连接后端
- 确认后端服务已启动
- 检查后端URL配置是否正确
- 查看浏览器控制台的错误信息

### AI分析失败
- 确认API密钥配置正确
- 检查网络连接
- 查看后端日志的错误信息

## 可用工具

系统支持以下11种计算机控制工具：

### 鼠标操作
1. **mouse_click**: 鼠标点击（支持左键、中键、右键）
2. **mouse_hover**: 鼠标悬停
3. **mouse_drag**: 鼠标拖动
4. **mouse_scroll**: 鼠标滚轮

### 键盘操作
5. **keyboard_type**: 键盘输入文本（支持可选的清除现有文本）
6. **keyboard_press**: 键盘按键（支持组合键）
7. **clear_text**: 清除当前输入框文本（全选+删除）

### 组合操作
8. **click_and_type**: 点击后输入文本（可选清除现有文本）

### 时间控制
9. **wait**: 等待指定时间（1-30秒）

### 任务控制
10. **task_complete**: 任务完成标记（Agent模式专用）

所有坐标使用归一化系统（0-1000范围），自动转换为实际像素坐标。

### 新增功能说明

**keyboard_type** 增强：
- 新增 `clear_existing` 参数（默认false）
- 设为true时会先全选删除现有文本再输入

**clear_text** 工具：
- 清除当前聚焦输入框的所有文本
- 通过 Ctrl+A 全选后删除实现

**click_and_type** 组合工具：
- 先点击指定坐标
- 可选择是否清除现有文本（默认true）
- 然后输入新文本（可为空）
- 适用于需要先聚焦输入框的场景

**wait** 等待工具：
- 等待指定的时间（1-30秒）
- 用于等待页面加载、动画完成等
- AI 可以根据需要自主决定等待时长
- 系统会在每次操作后自动等待3秒让UI刷新

## Agent 模式

Agent 模式允许 AI 自动执行复杂的多步骤任务：

### 工作原理
1. 用户提供任务描述
2. AI 分析当前截图
3. AI 决定并执行下一步操作
4. 系统自动截图并附加到对话历史
5. AI 继续分析和执行
6. 重复直到 AI 调用 `task_complete` 工具

### 特点
- ✅ 自动循环执行
- ✅ 维护完整对话历史
- ✅ 每步自动截图
- ✅ 智能任务完成检测
- ✅ 详细的任务总结

### API 接口
- `POST /agent/start` - 启动 Agent 任务
- `POST /agent/continue` - 继续执行（单步模式）
- `GET /agent/status` - 查询任务状态
- `POST /agent/clear` - 清除会话

## 开发计划

- [x] 添加鼠标自动点击功能
- [x] 支持更多操作类型（拖拽、输入等）
- [x] Playwright浏览器沙盒
- [x] Agent 自动化模式
- [x] 任务完成检测
- [ ] 添加操作历史记录
- [ ] 支持批量操作
- [ ] 添加操作录制和回放功能
- [ ] 支持更多浏览器（Firefox、Safari）
- [ ] Agent 错误恢复机制

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！