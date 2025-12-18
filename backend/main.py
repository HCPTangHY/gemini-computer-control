"""
Gemini计算机控制后端服务
使用Gemini API分析截图并返回鼠标点击坐标
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import os
import logging
import asyncio
from dotenv import load_dotenv

# 导入自定义 Gemini 客户端
from gemini_client import GeminiClient

# 导入工具模块
from tools import ToolCallHandler
from tools.playwright_controller import PlaywrightController
from tools.agent_controller import AgentController
from tools.real_computer_controller import RealComputerController

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 获取配置参数
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3-pro-preview')
GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '1.0'))

# 初始化自定义 Gemini 客户端
client = GeminiClient(
    api_key=os.getenv('GEMINI_API_KEY'),
    model=GEMINI_MODEL
)

# 初始化工具调用处理器
tool_handler = ToolCallHandler(client=client, model=GEMINI_MODEL)

# 初始化 Playwright 控制器
playwright_controller = PlaywrightController()

# 初始化真实电脑控制器
real_computer_controller = RealComputerController()

# 初始化 Agent 控制器
agent_controller = AgentController(
    client=client,
    playwright_controller=playwright_controller,
    real_computer_controller=real_computer_controller,
    model=GEMINI_MODEL,
    temperature=GEMINI_TEMPERATURE
)

# 创建一个专用的事件循环用于 Playwright
import threading
from concurrent.futures import ThreadPoolExecutor

playwright_loop = None
playwright_thread = None
executor = ThreadPoolExecutor(max_workers=1)

def init_playwright_loop():
    """在单独的线程中初始化事件循环"""
    global playwright_loop
    playwright_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(playwright_loop)
    playwright_loop.run_forever()

def run_async(coro, timeout=300):
    """在专用事件循环中运行异步协程"""
    global playwright_loop, playwright_thread
    
    if playwright_loop is None or playwright_thread is None or not playwright_thread.is_alive():
        # 启动事件循环线程
        playwright_thread = threading.Thread(target=init_playwright_loop, daemon=True)
        playwright_thread.start()
        # 等待循环初始化
        import time
        time.sleep(0.1)
    
    # 在事件循环中运行协程
    future = asyncio.run_coroutine_threadsafe(coro, playwright_loop)
    try:
        return future.result(timeout=timeout)  # 默认300秒超时
    except Exception as e:
        logger.error(f"异步操作失败: {str(e)}")
        raise

logger.info(f"使用模型: {GEMINI_MODEL}")
logger.info(f"默认温度: {GEMINI_TEMPERATURE}")

# 系统提示词
SYSTEM_PROMPT = """你是一个计算机控制助手。用户会给你一张屏幕截图，你需要分析图像并使用工具来执行操作。

坐标系统：
- x: 横坐标（归一化到 0-1000 范围）
- y: 纵坐标（归一化到 0-1000 范围）

重要功能：
1. **并行函数调用**：你可以在一次响应中返回多个函数调用，系统会按顺序执行它们。
2. **重复使用工具**：你可以多次调用同一个工具，例如多次点击不同位置。
3. **等待UI刷新**：在需要等待页面加载或UI更新时，使用 wait 工具（1-30秒）。
4. **组合操作**：可以组合多个操作，例如：点击 → 等待 → 输入 → 等待 → 点击

请确保返回的坐标在有效范围内（0-1000），并且是可操作的有效位置。
"""

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "message": "服务运行正常",
        "model": GEMINI_MODEL,
        "temperature": GEMINI_TEMPERATURE,
        "tools_loaded": len(tool_handler.get_available_tools())
    })

@app.route('/tools', methods=['GET'])
def list_tools():
    """列出所有可用工具"""
    tools = tool_handler.get_available_tools()
    return jsonify({
        "success": True,
        "tools": tools,
        "count": len(tools)
    })

@app.route('/analyze', methods=['POST'])
def analyze_screenshot():
    """
    分析截图并返回操作指令
    
    请求体：
    {
        "image": "base64编码的图片数据",
        "screen_width": 1920 (必需),
        "screen_height": 1080 (必需),
        "instruction": "用户指令（可选）",
        "temperature": 1.0 (可选),
        "mode": "AUTO" (可选, AUTO/ANY/NONE)
    }
    
    返回：
    {
        "success": true,
        "action": "click",
        "x": 960,  // 实际像素坐标
        "y": 540,  // 实际像素坐标
        "normalized_x": 500,  // 归一化坐标(0-1000)
        "normalized_y": 500,  // 归一化坐标(0-1000)
        "reasoning": "点击原因"
    }
    """
    try:
        data = request.json
        
        if not data or 'image' not in data:
            logger.warning("请求缺少图片数据")
            return jsonify({
                "success": False,
                "error": "缺少图片数据"
            }), 400
        
        # 获取屏幕尺寸（必需）
        if 'screen_width' not in data or 'screen_height' not in data:
            logger.warning("请求缺少屏幕尺寸信息")
            return jsonify({
                "success": False,
                "error": "缺少screen_width或screen_height参数"
            }), 400
        
        screen_width = int(data['screen_width'])
        screen_height = int(data['screen_height'])
        
        logger.info(f"屏幕尺寸: {screen_width}x{screen_height}")
        
        # 获取base64图片数据
        image_data = data['image']
        
        # 如果包含data:image前缀，去除它
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # 解码base64数据
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            logger.error(f"Base64解码失败: {str(e)}")
            return jsonify({
                "success": False,
                "error": "图片数据格式错误"
            }), 400
        
        # 获取参数
        user_instruction = data.get('instruction', '请分析这张截图，找到一个合适的位置进行点击。')
        temperature = float(data.get('temperature', GEMINI_TEMPERATURE))
        mode = data.get('mode', 'AUTO')
        
        # 构建完整的提示词
        full_prompt = f"{SYSTEM_PROMPT}\n\n用户指令：{user_instruction}"
        
        logger.info(f"开始分析截图，指令: {user_instruction[:50]}...")
        
        # 使用工具处理器分析图片（传递屏幕尺寸用于坐标转换）
        result = tool_handler.analyze_image_with_tools(
            image_data=image_bytes,
            prompt=full_prompt,
            temperature=temperature,
            mode=mode,
            screen_width=screen_width,
            screen_height=screen_height
        )
        
        # 添加屏幕尺寸信息到结果中
        if result.get('success'):
            result['screen_width'] = screen_width
            result['screen_height'] = screen_height
            logger.info(f"分析成功: {result.get('function_name', 'N/A')}")
            return jsonify(result)
        else:
            logger.error(f"分析失败: {result.get('error', 'Unknown error')}")
            return jsonify(result), 500
        
    except Exception as e:
        logger.exception(f"处理请求时发生异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500

# ============================================================================
# 真实电脑控制接口
# ============================================================================

@app.route('/real/screenshot', methods=['GET', 'POST'])
def real_screenshot():
    """截取真实屏幕截图"""
    try:
        result = run_async(real_computer_controller.take_screenshot())
        return jsonify(result)
    except Exception as e:
        logger.exception(f"真实截图失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/real/execute', methods=['POST'])
def real_execute():
    """执行真实电脑操作"""
    try:
        data = request.json or {}
        action = data.get('action')
        if not action:
            return jsonify({"success": False, "error": "缺少action参数"}), 400
        
        result = run_async(real_computer_controller.execute_action(action))
        return jsonify(result)
    except Exception as e:
        logger.exception(f"执行真实操作失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/real/info', methods=['GET'])
def real_info():
    """获取真实屏幕信息"""
    return jsonify({
        "success": True,
        **real_computer_controller.get_screen_info()
    })

# ============================================================================
# Playwright 浏览器控制接口
# ============================================================================

@app.route('/playwright/launch', methods=['POST'])
def playwright_launch():
    """
    启动 Playwright 浏览器
    
    请求体：
    {
        "url": "https://example.com",
        "width": 1280,
        "height": 720,
        "headless": false
    }
    
    返回：
    {
        "success": true,
        "session_id": "uuid",
        "url": "https://example.com",
        "viewport": {"width": 1280, "height": 720}
    }
    """
    try:
        data = request.json or {}
        
        url = data.get('url', 'https://www.google.com')
        width = int(data.get('width', 1280))
        height = int(data.get('height', 720))
        headless = data.get('headless', False)
        
        logger.info(f"启动浏览器: {url}, {width}x{height}, headless={headless}")
        
        result = run_async(playwright_controller.launch_browser(
            url=url,
            width=width,
            height=height,
            headless=headless
        ))
        
        if result.get('success'):
            logger.info(f"浏览器启动成功: {result['session_id']}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"启动浏览器失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/playwright/screenshot', methods=['POST'])
def playwright_screenshot():
    """
    截取浏览器截图
    
    请求体：
    {
        "session_id": "uuid"
    }
    
    返回：
    {
        "success": true,
        "screenshot": "data:image/png;base64,...",
        "url": "https://example.com"
    }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        logger.info(f"截图: {session_id}")
        
        result = run_async(playwright_controller.take_screenshot(session_id))
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"截图失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/playwright/execute', methods=['POST'])
def playwright_execute():
    """
    执行浏览器操作
    
    请求体：
    {
        "session_id": "uuid",
        "action": {
            "action": "click",
            "x": 100,
            "y": 200,
            ...
        }
    }
    
    返回：
    {
        "success": true,
        "message": "操作执行成功",
        "action": "click"
    }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        action = data.get('action')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        if not action:
            return jsonify({
                "success": False,
                "error": "缺少action参数"
            }), 400
        
        logger.info(f"执行操作: {session_id}, {action.get('action', 'unknown')}")
        
        result = run_async(playwright_controller.execute_action(session_id, action))
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"执行操作失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/playwright/close', methods=['POST'])
def playwright_close():
    """
    关闭浏览器会话
    
    请求体：
    {
        "session_id": "uuid"
    }
    
    返回：
    {
        "success": true,
        "message": "会话已关闭"
    }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        logger.info(f"关闭会话: {session_id}")
        
        result = run_async(playwright_controller.close_session(session_id))
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"关闭会话失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/playwright/sessions', methods=['GET'])
def playwright_sessions():
    """
    列出所有活动的浏览器会话
    
    返回：
    {
        "success": true,
        "sessions": [...],
        "count": 1
    }
    """
    try:
        sessions = playwright_controller.list_sessions()
        
        return jsonify({
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        })
        
    except Exception as e:
        logger.exception(f"列出会话失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============================================================================
# Agent 自动化接口
# ============================================================================

@app.route('/agent/start', methods=['POST'])
def agent_start():
    """
    启动 Agent 自动化任务
    
    请求体：
    {
        "session_id": "uuid",
        "task": "用户任务描述",
        "screen_width": 1280,
        "screen_height": 720,
        "mode": "step" 或 "auto"
    }
    
    返回：
    {
        "success": true,
        "session_id": "uuid",
        "step": 1,
        "actions": [...],
        "completed": false,
        "continue": true
    }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        task = data.get('task')
        screen_width = int(data.get('screen_width', 1280))
        screen_height = int(data.get('screen_height', 720))
        mode = data.get('mode', 'step')  # step: 单步执行, auto: 自动循环
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        if not task:
            return jsonify({
                "success": False,
                "error": "缺少task参数"
            }), 400
        
        logger.info(f"启动 Agent 任务: {session_id}, 模式: {mode}")
        
        # 创建 Agent 会话
        # 如果 session_id 是 'real'，则使用真实电脑模式
        controller_mode = 'real' if session_id == 'real' else 'browser'
        agent_controller.create_session(session_id, task, screen_width, screen_height, mode=controller_mode)
        
        if mode == 'auto':
            # 自动循环模式（需要更长超时）
            result = run_async(
                agent_controller.run_agent_loop(
                    session_id=session_id,
                    initial_task=task,
                    max_steps=20
                ),
                timeout=600  # 10分钟超时
            )
        else:
            # 单步模式
            result = run_async(
                agent_controller.run_agent_step(
                    session_id=session_id,
                    user_message=task
                ),
                timeout=120  # 2分钟超时
            )
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"启动 Agent 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/agent/continue', methods=['POST'])
def agent_continue():
    """
    继续执行 Agent 任务（单步模式）
    
    请求体：
    {
        "session_id": "uuid"
    }
    
    返回：
    {
        "success": true,
        "step": 2,
        "actions": [...],
        "completed": false,
        "continue": true
    }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        logger.info(f"继续 Agent 任务: {session_id}")
        
        result = run_async(agent_controller.run_agent_step(session_id))
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"继续 Agent 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/agent/status', methods=['GET'])
def agent_status():
    """
    获取 Agent 任务状态
    
    参数：
    - session_id: 会话ID
    
    返回：
    {
        "success": true,
        "session_id": "uuid",
        "task": "任务描述",
        "step_count": 5,
        "completed": false,
        "summary": null
    }
    """
    try:
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        info = agent_controller.get_session_info(session_id)
        
        if not info:
            return jsonify({
                "success": False,
                "error": f"会话 {session_id} 不存在"
            }), 404
        
        return jsonify({
            "success": True,
            **info
        })
        
    except Exception as e:
        logger.exception(f"获取 Agent 状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/agent/clear', methods=['POST'])
def agent_clear():
    """
    清除 Agent 会话
    
    请求体：
    {
        "session_id": "uuid"
    }
    
    返回：
    {
        "success": true,
        "message": "会话已清除"
    }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        agent_controller.clear_session(session_id)
        
        return jsonify({
            "success": True,
            "message": f"会话 {session_id} 已清除"
        })
    except Exception as e:
        logger.exception(f"清除 Agent 会话失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/agent/stop', methods=['POST'])
def agent_stop():
    """
    停止正在运行的 Agent 任务
    
    请求体：
    {
        "session_id": "uuid"
    }
    
    返回：
    {
        "success": true,
        "message": "任务已停止"
    }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少session_id参数"
            }), 400
        
        success = agent_controller.stop_session(session_id)
        
        return jsonify({
            "success": True,
            "message": f"会话 {session_id} 已停止" if success else f"会话 {session_id} 未在运行"
        })
        
    except Exception as e:
        logger.exception(f"停止 Agent 失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # 检查API密钥
    if not os.getenv('GEMINI_API_KEY'):
        logger.warning("未设置GEMINI_API_KEY环境变量")
        logger.warning("请在.env文件中设置: GEMINI_API_KEY=your_api_key")
    else:
        logger.info("✓ API密钥已配置")
    
    # 显示配置信息
    logger.info("=" * 60)
    logger.info("配置信息:")
    logger.info(f"  模型: {GEMINI_MODEL}")
    logger.info(f"  默认温度: {GEMINI_TEMPERATURE}")
    logger.info("=" * 60)
    
    # 显示加载的工具
    tools = tool_handler.get_available_tools()
    logger.info(f"已加载 {len(tools)} 个工具:")
    for tool in tools:
        logger.info(f"  - {tool['name']}: {tool['description']}")
    
    logger.info("=" * 60)
    logger.info("启动Gemini计算机控制后端服务...")
    logger.info("访问 http://localhost:5000/health 检查服务状态")
    logger.info("访问 http://localhost:5000/tools 查看可用工具")
    logger.info("访问 http://localhost:5000/playwright/sessions 查看浏览器会话")
    logger.info("访问 http://localhost:5000/agent/status 查看 Agent 状态")
    logger.info("=" * 60)
    
    # 注册清理函数
    import atexit
    
    def cleanup_playwright():
        """清理 Playwright 资源"""
        global playwright_loop, playwright_thread
        try:
            logger.info("清理 Playwright 资源...")
            if playwright_controller.playwright:
                try:
                    run_async(playwright_controller.cleanup())
                except Exception as e:
                    logger.error(f"清理失败: {e}")
            
            # 停止事件循环
            if playwright_loop and playwright_loop.is_running():
                playwright_loop.call_soon_threadsafe(playwright_loop.stop)
                if playwright_thread:
                    playwright_thread.join(timeout=2)
        except Exception as e:
            logger.error(f"清理过程出错: {e}")
    
    atexit.register(cleanup_playwright)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
        cleanup_playwright()