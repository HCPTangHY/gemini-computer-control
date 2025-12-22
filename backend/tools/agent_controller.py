
"""
Agent 控制器
实现自动化的 AI Agent 循环，自动执行任务直到完成
"""
from typing import Dict, Any, List, Optional
import logging
import base64
import sys
import os

# 添加父目录到路径以导入 gemini_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_client import GeminiClient, ConversationManager
from .playwright_controller import PlaywrightController
from .real_computer_controller import RealComputerController
from .background_controller import BackgroundComputerController
from .computer_control import (
    get_all_tool_declarations,
    execute_tool_call,
    denormalize_x,
    denormalize_y
)
from .tool_converter import convert_tools_to_rest_format
from .event_manager import event_manager

logger = logging.getLogger(__name__)


class AgentController:
    """
    Agent 控制器
    
    负责：
    1. 维护对话历史
    2. 自动循环调用 AI
    3. 执行工具并收集结果
    4. 自动截图并附加到对话
    5. 检测任务完成
    """
    
    def __init__(
        self,
        client: GeminiClient,
        playwright_controller: PlaywrightController,
        real_computer_controller: RealComputerController = None,
        background_controller: BackgroundComputerController = None,
        model: str = "gemini-3-pro-preview",
        temperature: float = 1.0
    ):
        """
        初始化 Agent 控制器
        
        Args:
            client: Gemini API 客户端
            playwright_controller: Playwright 控制器
            real_computer_controller: 真实电脑控制器
            background_controller: 后台窗口控制器
            model: 使用的模型名称
            temperature: 温度参数
        """
        self.client = client
        self.playwright = playwright_controller
        self.real_computer = real_computer_controller
        self.background = background_controller
        self.model = model
        self.temperature = temperature
        self.tool_declarations = get_all_tool_declarations()
        
        # 转换工具声明为 REST API 格式
        self.tools = convert_tools_to_rest_format(self.tool_declarations)
        
        # Agent 会话存储（每个会话有自己的 ConversationManager）
        self.sessions: Dict[str, Dict[str, Any]] = {}
        # 存储正在运行的会话 ID
        self.running_sessions: set = set()
        
        logger.info(f"Agent 控制器初始化完成，加载了 {len(self.tool_declarations)} 个工具")
    
    def create_session(
        self,
        session_id: str,
        initial_task: str,
        screen_width: int,
        screen_height: int,
        mode: str = "browser"
    ) -> Dict[str, Any]:
        """
        创建新的 Agent 会话
        
        Args:
            session_id: 会话 ID
            initial_task: 初始任务描述
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            mode: 模式 ("browser" 或 "real")
        
        Returns:
            会话信息
        """
        # 创建对话管理器
        conversation_manager = ConversationManager(self.client)
        
        self.sessions[session_id] = {
            "task": initial_task,
            "screen_width": screen_width,
            "screen_height": screen_height,
            "mode": mode,
            "conversation": conversation_manager,
            "step_count": 0,
            "completed": False,
            "summary": None,
            "notes": []  # 任务笔记本
        }
        
        logger.info(f"创建 Agent 会话: {session_id}")
        return {"success": True, "session_id": session_id}
    
    async def run_agent_step(
        self,
        session_id: str,
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行一步 Agent 操作
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息（首次调用时提供任务，后续为 None）
        
        Returns:
            执行结果
        """
        if session_id not in self.sessions:
            return {
                "success": False,
                "error": f"会话 {session_id} 不存在"
            }
        
        session = self.sessions[session_id]
        
        if session["completed"]:
            return {
                "success": False,
                "error": "任务已完成",
                "summary": session["summary"]
            }
        
        try:
            # 1. 截取当前状态（带重试机制）
            screenshot_result = None
            max_screenshot_retries = 3
            
            for retry in range(max_screenshot_retries):
                try:
                    if session.get("mode") == "real":
                        screenshot_result = await self.real_computer.take_screenshot()
                    elif session.get("mode") == "background":
                        if not self.background:
                            return {
                                "success": False,
                                "error": "后台控制器未初始化，请先设置目标窗口"
                            }
                        screenshot_result = await self.background.take_screenshot()
                    else:
                        screenshot_result = await self.playwright.take_screenshot(session_id)
                    
                    if screenshot_result.get("success"):
                        break
                    else:
                        logger.warning(f"截图尝试 {retry + 1}/{max_screenshot_retries} 失败: {screenshot_result.get('error')}")
                except Exception as e:
                    logger.warning(f"截图尝试 {retry + 1}/{max_screenshot_retries} 异常: {str(e)}")
                    screenshot_result = {"success": False, "error": str(e)}
                
                if retry < max_screenshot_retries - 1:
                    import asyncio
                    await asyncio.sleep(2)  # 等待2秒后重试
            
            if not screenshot_result or not screenshot_result.get("success"):
                error_msg = screenshot_result.get('error', '未知错误') if screenshot_result else '截图返回为空'
                logger.error(f"截图最终失败: {error_msg}")
                return {
                    "success": False,
                    "error": f"截图失败（已重试{max_screenshot_retries}次）: {error_msg}"
                }
            
            screenshot_data = screenshot_result["screenshot"]
            current_url = screenshot_result.get("url", "Desktop")
            
            # 发布截图事件到前端
            event_manager.publish_screenshot(
                session_id=session_id,
                screenshot=screenshot_data,
                step=session["step_count"] + 1,
                width=screenshot_result.get("width", session["screen_width"]),
                height=screenshot_result.get("height", session["screen_height"]),
                url=current_url,
                action=None  # 首次截图，还没执行操作
            )
            
            # 提取 base64 数据
            if ',' in screenshot_data:
                screenshot_base64 = screenshot_data.split(',')[1]
            else:
                screenshot_base64 = screenshot_data
            
            screenshot_bytes = base64.b64decode(screenshot_base64)
            
            # 2. 构建消息内容并添加到对话
            conversation = session["conversation"]
            
            if user_message:
                # 首次调用：用户任务 + 截图
                mode_names = {
                    "real": "真实电脑控制",
                    "background": "后台窗口控制",
                    "browser": "浏览器自动化"
                }
                mode_name = mode_names.get(session.get("mode"), "浏览器自动化")
                
                # 构建标签页信息（如果存在）
                tabs_info = ""
                if "tabs" in screenshot_result:
                    tabs_list = "\n".join([f"- [{t['index']}] {t['title']} ({t['url']}){' [当前活跃]' if t['is_active'] else ''}" for t in screenshot_result["tabs"]])
                    tabs_info = f"\n当前打开的标签页列表:\n{tabs_list}\n你可以使用 switch_tab(index) 切换标签页。\n"

                prompt = f"""你是一个{mode_name}助手。用户给你一个任务，你需要通过调用工具来完成它。

当前位置: {current_url}
屏幕尺寸: {session['screen_width']}x{session['screen_height']}{tabs_info}

用户任务: {user_message}

重要提示：
1. **并行函数调用**：你可以在一次响应中返回多个函数调用，系统会按顺序执行它们。
2. **重复使用工具**：你可以多次调用同一个工具，例如多次点击不同位置。
3. **等待UI刷新**：在需要等待页面加载或UI更新时，使用 wait 工具（1-30秒）。
4. **笔记功能**：使用 add_note 记录重要发现、进度、待办事项。使用 list_notes 查看已记录的内容。
5. **组合操作示例**：
   - 点击搜索框 → 输入文本 → 点击搜索按钮 → 等待3秒
   - 这些操作可以在一次响应中全部返回

请分析当前截图，决定下一步操作。当你认为任务完全完成时，调用 task_complete 工具。"""
            else:
                # 后续调用：继续提示 + 截图
                # 构建标签页信息（如果存在）
                tabs_info = ""
                if "tabs" in screenshot_result:
                    tabs_list = "\n".join([f"- [{t['index']}] {t['title']} ({t['url']}){' [当前活跃]' if t['is_active'] else ''}" for t in screenshot_result["tabs"]])
                    tabs_info = f"\n当前打开的标签页列表:\n{tabs_list}\n你可以使用 switch_tab(index) 切换标签页。\n"

                # 构建笔记摘要
                notes_summary = ""
                if session.get("notes"):
                    recent_notes = session["notes"][-5:]  # 最近5条笔记
                    notes_list = "\n".join([f"  - [{n['category']}] {n['content']}" for n in recent_notes])
                    notes_summary = f"\n\n你的笔记（最近{len(recent_notes)}条）:\n{notes_list}\n"

                prompt = f"""继续执行任务。

当前位置: {current_url}
已执行步骤: {session['step_count']}{tabs_info}{notes_summary}

提醒：
- 你可以一次返回多个函数调用来提高效率
- 在操作之间使用 wait 工具等待UI刷新（建议1-3秒）
- 可以重复使用同一个工具
- 使用 add_note 记录重要信息，使用 list_notes 查看所有笔记

请分析当前截图，决定下一步操作。如果任务已完成，调用 task_complete 工具。"""
            
            # 添加用户消息（包含截图）
            conversation.add_user_message(prompt, screenshot_bytes)
            
            # 3. 调用 AI（带重试机制）
            logger.info(f"会话 {session_id} 步骤 {session['step_count'] + 1}: 调用 AI")
            
            # 验证历史记录中的签名（Gemini 3 强制要求）
            if not conversation.validate_history_signatures():
                logger.warning("检测到历史记录中缺少必要的思考签名，可能会导致 400 错误")

            # 重试机制：最多重试3次，间隔10秒
            max_retries = 3
            retry_delay = 10
            response = None
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = conversation.generate_content(
                        tools=self.tools,
                        temperature=self.temperature,
                        thinking_level="low",
                        include_thoughts=True,
                        system_instruction=""
                    )
                    break  # 成功则跳出循环
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    
                    # 检查是否是可重试的错误
                    if '503' in error_msg or 'overloaded' in error_msg.lower() or 'UNAVAILABLE' in error_msg or 'Service Unavailable' in error_msg:
                        if attempt < max_retries - 1:
                            logger.warning(f"AI 调用失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                            logger.info(f"等待 {retry_delay} 秒后重试...")
                            # 使用异步 sleep
                            import asyncio
                            await asyncio.sleep(retry_delay)
                        else:
                            logger.error(f"AI 调用失败，已达最大重试次数: {error_msg}")
                            raise
                    else:
                        # 非可重试错误，直接抛出
                        logger.error(f"AI 调用失败（不可重试）: {error_msg}")
                        raise
            
            if response is None:
                raise last_error or Exception("AI 调用失败")
            
            # 4. 处理响应
            # 提取函数调用及其签名
            calls_with_sigs = self.client.extract_function_calls_with_signatures(response)
            
            # 检查并记录思考签名
            has_sigs = any(c.get("thought_signature") for c in calls_with_sigs)
            if has_sigs:
                logger.info(f"收到带思考签名的函数调用")
                for i, c in enumerate(calls_with_sigs):
                    if c.get("thought_signature"):
                        logger.debug(f"  FC {i+1} ({c['name']}) 签名: {c['thought_signature'][:30]}...")
            
            # 将模型响应添加到对话历史（包含思考签名）
            conversation.add_model_response(response)
            
            # 提取函数调用列表用于执行
            function_calls = [(c["name"], c["args"]) for c in calls_with_sigs]
            
            if not function_calls:
                # 提取思考摘要和文本
                thought_summary = self.client.extract_thought_summary(response)
                text_response = self.client.extract_text_from_response(response)
                
                logger.warning("AI 未返回函数调用")
                if thought_summary:
                    logger.info(f"思考摘要: {thought_summary[:200]}...")
                if text_response:
                    logger.info(f"文本响应: {text_response[:200]}...")
                
                return {
                    "success": False,
                    "error": "AI 未返回函数调用",
                    "thought_summary": thought_summary,
                    "text_response": text_response
                }
            
            # 5. 执行函数调用
            results = []
            task_completed = False
            
            for tool_name, args in function_calls:
                logger.info(f"执行工具: {tool_name}")
                logger.debug(f"参数: {args}")
                
                # 检查是否是任务完成
                if tool_name == "task_complete":
                    task_completed = True
                    session["completed"] = True
                    session["summary"] = args.get("summary", "任务已完成")
                    
                    result = {
                        "status": "completed",
                        "summary": session["summary"],
                        "success": args.get("success", True)
                    }
                else:
                    # 执行工具
                    if tool_name in ["mouse_click", "mouse_hover", "mouse_drag", "mouse_scroll", "keyboard_type", "keyboard_press", "clear_text", "click_and_type"]:
                        # 坐标转换（仅转换一次）
                        if tool_name in ["mouse_click", "mouse_hover", "click_and_type"]:
                            if "x" in args and "y" in args:
                                args["x"] = denormalize_x(args["x"], session["screen_width"])
                                args["y"] = denormalize_y(args["y"], session["screen_height"])
                        elif tool_name == "mouse_drag":
                            if "start_x" in args:
                                args["start_x"] = denormalize_x(args["start_x"], session["screen_width"])
                                args["start_y"] = denormalize_y(args["start_y"], session["screen_height"])
                                args["end_x"] = denormalize_x(args["end_x"], session["screen_width"])
                                args["end_y"] = denormalize_y(args["end_y"], session["screen_height"])
                        
                        action_data = {
                            "action": tool_name,
                            **args
                        }
                        
                        if session.get("mode") == "real":
                            # 在真实电脑中执行
                            exec_result = await self.real_computer.execute_action(action_data)
                        elif session.get("mode") == "background":
                            # 在后台窗口中执行
                            exec_result = await self.background.execute_action(action_data)
                        else:
                            # 在浏览器中执行
                            exec_result = await self.playwright.execute_action(session_id, action_data)
                        result = exec_result
                    elif tool_name in ["switch_tab", "list_tabs", "new_tab", "reset_browser", "clear_cookies", "navigate"]:
                        # 浏览器操作（仅在浏览器模式下有效）
                        if session.get("mode") == "browser":
                            action_data = {
                                "action": tool_name,
                                **args
                            }
                            exec_result = await self.playwright.execute_action(session_id, action_data)
                            result = exec_result
                        else:
                            result = {
                                "status": "error",
                                "message": f"工具 {tool_name} 仅在浏览器模式下可用"
                            }
                    elif tool_name == "add_note":
                        # 添加笔记
                        import datetime
                        note = {
                            "content": args.get("content", ""),
                            "category": args.get("category", "info"),
                            "timestamp": datetime.datetime.now().isoformat(),
                            "step": session["step_count"] + 1
                        }
                        session["notes"].append(note)
                        result = {
                            "status": "success",
                            "message": f"笔记已添加 [{note['category']}]: {note['content'][:50]}...",
                            "note_count": len(session["notes"])
                        }
                        logger.info(f"添加笔记 [{note['category']}]: {note['content'][:100]}")
                        # 发布笔记更新事件到前端
                        event_manager.publish_notes(session_id, session["notes"], "add")
                    elif tool_name == "list_notes":
                        # 列出笔记
                        category_filter = args.get("category", "all")
                        notes = session.get("notes", [])
                        if category_filter != "all":
                            notes = [n for n in notes if n.get("category") == category_filter]
                        
                        notes_summary = []
                        for i, note in enumerate(notes):
                            notes_summary.append({
                                "index": i + 1,
                                "category": note.get("category", "info"),
                                "content": note.get("content", ""),
                                "step": note.get("step", 0),
                                "time": note.get("timestamp", "")
                            })
                        
                        result = {
                            "status": "success",
                            "notes": notes_summary,
                            "total_count": len(session.get("notes", [])),
                            "filtered_count": len(notes_summary),
                            "filter": category_filter
                        }
                        logger.info(f"列出笔记: {len(notes_summary)} 条 (筛选: {category_filter})")
                        # 发布笔记事件到前端
                        event_manager.publish_notes(session_id, session.get("notes", []), "list")
                    elif tool_name == "clear_notes":
                        # 清空笔记
                        if not args.get("confirm", False):
                            result = {
                                "status": "error",
                                "message": "需要 confirm=true 才能清空笔记"
                            }
                        else:
                            category_filter = args.get("category", "all")
                            if category_filter == "all":
                                cleared_count = len(session.get("notes", []))
                                session["notes"] = []
                            else:
                                original_notes = session.get("notes", [])
                                session["notes"] = [n for n in original_notes if n.get("category") != category_filter]
                                cleared_count = len(original_notes) - len(session["notes"])
                            
                            result = {
                                "status": "success",
                                "message": f"已清空 {cleared_count} 条笔记",
                                "remaining_count": len(session["notes"])
                            }
                            logger.info(f"清空笔记: {cleared_count} 条 (筛选: {category_filter})")
                            # 发布笔记更新事件到前端
                            event_manager.publish_notes(session_id, session["notes"], "clear")
                    else:
                        # 本地执行
                        result = execute_tool_call(tool_name, args)
                
                results.append((tool_name, result))
            
            # 6. 如果任务未完成，准备下一轮
            if not task_completed:
                # 等待1秒让UI刷新
                import asyncio
                await asyncio.sleep(1)
                logger.info(f"等待1秒让UI刷新...")
                
                # 截取执行后的截图
                if session.get("mode") == "real":
                    after_screenshot = await self.real_computer.take_screenshot()
                elif session.get("mode") == "background":
                    after_screenshot = await self.background.take_screenshot()
                else:
                    after_screenshot = await self.playwright.take_screenshot(session_id)
                    
                if after_screenshot.get("success"):
                    after_screenshot_data = after_screenshot["screenshot"]
                    
                    # 发布操作后截图事件到前端
                    last_action = results[-1][0] if results else None
                    event_manager.publish_screenshot(
                        session_id=session_id,
                        screenshot=after_screenshot_data,
                        step=session["step_count"] + 1,
                        width=after_screenshot.get("width", session["screen_width"]),
                        height=after_screenshot.get("height", session["screen_height"]),
                        url=after_screenshot.get("url", current_url),
                        action=last_action
                    )
                    
                    if ',' in after_screenshot_data:
                        after_screenshot_base64 = after_screenshot_data.split(',')[1]
                    else:
                        after_screenshot_base64 = after_screenshot_data
                    after_screenshot_bytes = base64.b64decode(after_screenshot_base64)
                else:
                    after_screenshot_bytes = screenshot_bytes
                
                # 构建函数响应结果
                function_results = []
                for tool_name, result in results:
                    response_data = {
                        "url": current_url,
                        **result
                    }
                    function_results.append((tool_name, response_data))
                
                # 添加函数响应到对话历史（包含截图）
                conversation.add_function_responses(function_results, after_screenshot_bytes)
            
            session["step_count"] += 1
            
            # 7. 返回结果
            return {
                "success": True,
                "step": session["step_count"],
                "actions": [{"tool": name, "result": result} for name, result in results],
                "completed": task_completed,
                "summary": session.get("summary") if task_completed else None,
                "continue": not task_completed
            }
            
        except Exception as e:
            logger.exception(f"Agent 步骤执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def run_agent_loop(
        self,
        session_id: str,
        initial_task: str,
        max_steps: int = 20
    ) -> Dict[str, Any]:
        """
        运行完整的 Agent 循环直到任务完成
        
        Args:
            session_id: 会话 ID
            initial_task: 初始任务
            max_steps: 最大步骤数
        
        Returns:
            最终结果
        """
        all_steps = []
        consecutive_failures = 0
        max_consecutive_failures = 3  # 允许最多连续3次失败
        self.running_sessions.add(session_id)
        
        try:
            # 首次调用
            result = await self.run_agent_step(session_id, initial_task)
            all_steps.append(result)
            
            if not result.get("success"):
                consecutive_failures += 1
                logger.warning(f"首次步骤失败 ({consecutive_failures}/{max_consecutive_failures}): {result.get('error')}")
                # 首次失败也给机会重试
                if consecutive_failures >= max_consecutive_failures:
                    event_manager.publish_error(
                        session_id=session_id,
                        error=result.get("error", "首次步骤失败"),
                        step=len(all_steps)
                    )
                    return {
                        "success": False,
                        "error": result.get("error"),
                        "steps": all_steps
                    }
            else:
                consecutive_failures = 0
            
            # 循环执行直到完成或达到最大步骤
            while len(all_steps) < max_steps:
                # 检查是否被手动停止
                if session_id not in self.running_sessions:
                    logger.info(f"会话 {session_id} 已被手动停止")
                    return {
                        "success": True,
                        "completed": False,
                        "stopped": True,
                        "summary": "任务已被手动停止",
                        "total_steps": len(all_steps),
                        "steps": all_steps
                    }
                
                # 检查任务是否已完成
                session = self.sessions.get(session_id)
                if session and session.get("completed"):
                    break
                
                # 如果上一步不需要继续，则退出
                if not result.get("continue", True) and result.get("success"):
                    break

                result = await self.run_agent_step(session_id)
                all_steps.append(result)
                
                if not result.get("success"):
                    consecutive_failures += 1
                    logger.warning(f"步骤 {len(all_steps)} 失败 ({consecutive_failures}/{max_consecutive_failures}): {result.get('error')}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"连续失败 {consecutive_failures} 次，终止任务")
                        break
                    
                    # 等待一段时间后继续尝试
                    import asyncio
                    await asyncio.sleep(3)
                    continue
                else:
                    consecutive_failures = 0
                    
        finally:
            if session_id in self.running_sessions:
                self.running_sessions.remove(session_id)
        
        # 检查是否完成
        session = self.sessions.get(session_id)
        if session and session.get("completed"):
            # 发布完成事件
            event_manager.publish_complete(
                session_id=session_id,
                success=True,
                summary=session.get("summary", "任务已完成"),
                total_steps=len(all_steps)
            )
            return {
                "success": True,
                "completed": True,
                "summary": session.get("summary"),
                "total_steps": len(all_steps),
                "steps": all_steps
            }
        elif len(all_steps) >= max_steps:
            # 发布错误事件
            event_manager.publish_error(
                session_id=session_id,
                error=f"达到最大步骤数 {max_steps}",
                step=len(all_steps)
            )
            return {
                "success": False,
                "error": f"达到最大步骤数 {max_steps}",
                "completed": False,
                "total_steps": len(all_steps),
                "steps": all_steps
            }
        elif consecutive_failures >= max_consecutive_failures:
            # 连续失败导致终止
            last_error = all_steps[-1].get("error", "未知错误") if all_steps else "未知错误"
            event_manager.publish_error(
                session_id=session_id,
                error=f"连续失败 {consecutive_failures} 次: {last_error}",
                step=len(all_steps)
            )
            return {
                "success": False,
                "error": f"连续失败 {consecutive_failures} 次: {last_error}",
                "completed": False,
                "total_steps": len(all_steps),
                "steps": all_steps
            }
        else:
            # 其他情况（不应该到达这里）
            event_manager.publish_error(
                session_id=session_id,
                error="任务异常终止",
                step=len(all_steps)
            )
            return {
                "success": False,
                "error": "任务异常终止",
                "completed": False,
                "total_steps": len(all_steps),
                "steps": all_steps
            }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话 ID
        
        Returns:
            会话信息
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "task": session["task"],
            "step_count": session["step_count"],
            "completed": session["completed"],
            "summary": session.get("summary")
        }
    
    def stop_session(self, session_id: str) -> bool:
        """
        停止正在运行的会话
        
        Args:
            session_id: 会话 ID
        
        Returns:
            是否成功停止
        """
        if session_id in self.running_sessions:
            self.running_sessions.remove(session_id)
            logger.info(f"停止 Agent 会话: {session_id}")
            return True
        return False

    def clear_session(self, session_id: str):
        """
        清除会话
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self.running_sessions:
            self.running_sessions.remove(session_id)
            
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"清除 Agent 会话: {session_id}")