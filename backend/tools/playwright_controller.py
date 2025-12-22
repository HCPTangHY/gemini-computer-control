"""
Playwright 浏览器控制器
负责管理 Playwright 浏览器会话和执行操作
"""
from typing import Dict, Any, Optional
import asyncio
import base64
import logging
import uuid
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)


class PlaywrightSession:
    """
    Playwright 浏览器会话
    管理单个浏览器实例的生命周期，支持多标签页
    """
    
    def __init__(self, session_id: str, browser: Browser, context: BrowserContext):
        self.session_id = session_id
        self.browser = browser
        self.context = context
        self.active_page_index = 0
        self.created_at = asyncio.get_event_loop().time()
        
    @property
    def page(self) -> Page:
        """获取当前活跃页面"""
        pages = self.context.pages
        if not pages:
            return None
        # 确保索引不越界
        if self.active_page_index >= len(pages):
            self.active_page_index = len(pages) - 1
        return pages[self.active_page_index]
        
    async def close(self):
        """关闭浏览器会话"""
        try:
            await self.context.close()
            await self.browser.close()
            logger.info(f"会话 {self.session_id} 已关闭")
        except Exception as e:
            logger.error(f"关闭会话 {self.session_id} 时出错: {str(e)}")


class PlaywrightController:
    """
    Playwright 控制器
    管理多个浏览器会话并提供操作接口
    """
    
    def __init__(self):
        self.sessions: Dict[str, PlaywrightSession] = {}
        self.playwright = None
        self._playwright_context = None
        self._lock = None
        
    async def initialize(self):
        """初始化 Playwright"""
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        if self.playwright is None:
            self._playwright_context = async_playwright()
            self.playwright = await self._playwright_context.start()
            logger.info("Playwright 已初始化")
    
    async def launch_browser(
        self,
        url: str,
        width: int = 1280,
        height: int = 720,
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        启动新的浏览器会话
        
        Args:
            url: 要访问的URL
            width: 浏览器窗口宽度
            height: 浏览器窗口高度
            headless: 是否无头模式
        
        Returns:
            包含会话ID和状态的字典
        """
        try:
            await self.initialize()
            
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 启动浏览器
            browser = await self.playwright.chromium.launch(
                headless=headless,
                args=['--start-maximized'] if not headless else []
            )
            
            # 创建上下文
            context = await browser.new_context(
                viewport={'width': width, 'height': height},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # 创建页面
            page = await context.new_page()
            
            # 访问URL
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 保存会话
            session = PlaywrightSession(session_id, browser, context)
            async with self._lock:
                self.sessions[session_id] = session
            
            logger.info(f"浏览器会话 {session_id} 已启动，访问 {url}")
            
            return {
                "success": True,
                "session_id": session_id,
                "url": url,
                "viewport": {"width": width, "height": height}
            }
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def take_screenshot(self, session_id: str) -> Dict[str, Any]:
        """
        截取浏览器截图并获取标签页列表
        
        Args:
            session_id: 会话ID
        
        Returns:
            包含base64编码截图和标签页信息的字典
        """
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"会话 {session_id} 不存在"
                }
            
            page = session.page
            if not page:
                return {
                    "success": False,
                    "error": "当前没有活跃页面"
                }
            
            # 截图（设置较短的超时时间，避免长时间阻塞）
            try:
                screenshot_bytes = await page.screenshot(type='png', full_page=False, timeout=10000)
            except Exception as screenshot_error:
                logger.warning(f"截图超时，尝试强制截图: {screenshot_error}")
                # 尝试不等待页面稳定直接截图
                try:
                    screenshot_bytes = await page.screenshot(type='png', full_page=False, timeout=5000)
                except:
                    return {
                        "success": False,
                        "error": f"截图失败: {str(screenshot_error)}"
                    }
            
            screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot_bytes).decode()}"
            
            # 获取所有标签页信息
            pages = session.context.pages
            tabs = []
            for i, p in enumerate(pages):
                try:
                    tabs.append({
                        "index": i,
                        "title": await p.title(),
                        "url": p.url,
                        "is_active": i == session.active_page_index
                    })
                except:
                    continue
            
            logger.info(f"会话 {session_id} 截图成功，当前共有 {len(tabs)} 个标签页")
            
            return {
                "success": True,
                "screenshot": screenshot_base64,
                "url": session.page.url,
                "tabs": tabs,
                "active_index": session.active_page_index
            }
            
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_action(self, session_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行浏览器操作
        
        Args:
            session_id: 会话ID
            action: 操作数据（来自AI分析结果）
        
        Returns:
            执行结果
        """
        try:
            session = self.sessions.get(session_id)
            if not session:
                return {
                    "success": False,
                    "error": f"会话 {session_id} 不存在"
                }
            
            page = session.page
            action_type = action.get('action') or action.get('function_name', '')
            
            # 根据操作类型执行相应的操作
            if action_type == 'click' or action_type == 'mouse_click':
                x = action.get('x', 0)
                y = action.get('y', 0)
                await page.mouse.click(x, y)
                message = f"在坐标 ({x}, {y}) 执行点击"
                
            elif action_type == 'hover' or action_type == 'mouse_hover':
                x = action.get('x', 0)
                y = action.get('y', 0)
                await page.mouse.move(x, y)
                message = f"鼠标移动到坐标 ({x}, {y})"
                
            elif action_type == 'drag' or action_type == 'mouse_drag':
                start_x = action.get('start_x', 0)
                start_y = action.get('start_y', 0)
                end_x = action.get('end_x', 0)
                end_y = action.get('end_y', 0)
                await page.mouse.move(start_x, start_y)
                await page.mouse.down()
                await page.mouse.move(end_x, end_y)
                await page.mouse.up()
                message = f"从 ({start_x}, {start_y}) 拖动到 ({end_x}, {end_y})"
                
            elif action_type == 'scroll' or action_type == 'mouse_scroll':
                scroll_x = action.get('scroll_x', 0)
                scroll_y = action.get('scroll_y', 0)
                # Playwright 使用 wheel 事件进行滚动
                await page.mouse.wheel(scroll_x, scroll_y)
                message = f"滚动 ({scroll_x}, {scroll_y})"
                
            elif action_type == 'type' or action_type == 'keyboard_type':
                text = action.get('text', '')
                clear_existing = action.get('clear_existing', False)
                
                if clear_existing:
                    # 全选并删除现有文本
                    await page.keyboard.press('Control+A')
                    await page.keyboard.press('Delete')
                    await asyncio.sleep(0.1)
                
                await page.keyboard.type(text)
                message = f"{'清除后' if clear_existing else ''}输入文本: {text[:50]}{'...' if len(text) > 50 else ''}"
            
            elif action_type == 'clear_text':
                # 全选并删除
                await page.keyboard.press('Control+A')
                await page.keyboard.press('Delete')
                message = "已清除文本"
            
            elif action_type == 'click_and_type':
                x = action.get('x', 0)
                y = action.get('y', 0)
                text = action.get('text', '')
                clear_existing = action.get('clear_existing', True)
                
                # 先点击
                await page.mouse.click(x, y)
                await asyncio.sleep(0.2)
                
                # 清除现有文本（如果需要）
                if clear_existing:
                    await page.keyboard.press('Control+A')
                    await page.keyboard.press('Delete')
                    await asyncio.sleep(0.1)
                
                # 输入文本（如果有）
                if text:
                    await page.keyboard.type(text)
                
                operation = []
                if clear_existing:
                    operation.append("清除")
                if text:
                    operation.append(f"输入'{text[:30]}{'...' if len(text) > 30 else ''}'")
                operation_str = "、".join(operation) if operation else "仅点击"
                
                message = f"在坐标 ({x}, {y}) 点击并{operation_str}"
                
            elif action_type == 'press' or action_type == 'keyboard_press':
                keys = action.get('keys', [])
                if isinstance(keys, list):
                    # 组合键
                    for key in keys[:-1]:
                        await page.keyboard.down(self._normalize_key(key))
                    await page.keyboard.press(self._normalize_key(keys[-1]))
                    for key in reversed(keys[:-1]):
                        await page.keyboard.up(self._normalize_key(key))
                    message = f"按键: {'+'.join(keys)}"
                else:
                    await page.keyboard.press(self._normalize_key(keys))
                    message = f"按键: {keys}"
            
            elif action_type == 'switch_tab':
                index = action.get('index', 0)
                pages = session.context.pages
                if 0 <= index < len(pages):
                    session.active_page_index = index
                    await pages[index].bring_to_front()
                    message = f"切换到标签页 {index}: {pages[index].url}"
                else:
                    return {"success": False, "error": f"无效的标签页索引: {index}"}

            elif action_type == 'list_tabs':
                pages = session.context.pages
                tabs = [{"index": i, "title": await p.title(), "url": p.url} for i, p in enumerate(pages)]
                return {
                    "success": True,
                    "tabs": tabs,
                    "active_index": session.active_page_index,
                    "message": f"当前共有 {len(pages)} 个标签页"
                }

            elif action_type == 'new_tab':
                url = action.get('url', 'about:blank')
                # 创建新页面
                new_page = await session.context.new_page()
                # 访问URL
                await new_page.goto(url, wait_until='networkidle', timeout=30000)
                # 更新活跃页面索引为新页面
                session.active_page_index = len(session.context.pages) - 1
                message = f"新建标签页并访问: {url}"

            elif action_type == 'navigate':
                url = action.get('url', 'about:blank')
                # 在当前页面导航
                await page.goto(url, wait_until='networkidle', timeout=30000)
                message = f"导航到: {url}"

            elif action_type == 'clear_cookies':
                # 清除所有Cookies
                await session.context.clear_cookies()
                # 清除本地存储（通过在页面执行脚本）
                try:
                    await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
                except:
                    pass  # 某些页面可能无法执行脚本
                message = "已清除Cookies和本地存储"

            elif action_type == 'reset_browser':
                url = action.get('url', 'about:blank')
                # 重置浏览器：创建全新的上下文
                # 1. 获取当前浏览器实例
                browser = session.browser
                old_context = session.context
                
                # 2. 创建新的浏览器上下文（全新的指纹和缓存）
                new_context = await browser.new_context(
                    viewport={'width': page.viewport_size['width'], 'height': page.viewport_size['height']},
                    user_agent=f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{120 + (hash(str(asyncio.get_event_loop().time())) % 10)}.0.0.0 Safari/537.36'
                )
                
                # 3. 创建新页面并访问URL
                new_page = await new_context.new_page()
                await new_page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 4. 更新会话
                session.context = new_context
                session.active_page_index = 0
                
                # 5. 关闭旧上下文
                try:
                    await old_context.close()
                except:
                    pass
                
                message = f"浏览器环境已重置，导航到: {url}"

            else:
                return {
                    "success": False,
                    "error": f"未知的操作类型: {action_type}"
                }
            
            # 等待页面稳定
            await asyncio.sleep(0.5)
            
            logger.info(f"会话 {session_id} 执行操作: {message}")
            
            # 额外等待3秒让UI刷新（所有模式都生效）
            logger.info(f"等待1秒让UI刷新...")
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "message": message,
                "action": action_type
            }
            
        except Exception as e:
            logger.error(f"执行操作失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _normalize_key(self, key: str) -> str:
        """
        标准化按键名称
        将常见的按键名称转换为 Playwright 识别的格式
        """
        key_map = {
            'ctrl': 'Control',
            'control': 'Control',
            'alt': 'Alt',
            'shift': 'Shift',
            'win': 'Meta',
            'meta': 'Meta',
            'cmd': 'Meta',
            'enter': 'Enter',
            'return': 'Enter',
            'esc': 'Escape',
            'escape': 'Escape',
            'space': ' ',
            'tab': 'Tab',
            'backspace': 'Backspace',
            'delete': 'Delete',
            'up': 'ArrowUp',
            'down': 'ArrowDown',
            'left': 'ArrowLeft',
            'right': 'ArrowRight',
            'home': 'Home',
            'end': 'End',
            'pageup': 'PageUp',
            'pagedown': 'PageDown',
        }
        
        normalized = key_map.get(key.lower(), key)
        return normalized
    
    async def close_session(self, session_id: str) -> Dict[str, Any]:
        """
        关闭浏览器会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            关闭结果
        """
        try:
            async with self._lock:
                session = self.sessions.pop(session_id, None)
            
            if not session:
                return {
                    "success": False,
                    "error": f"会话 {session_id} 不存在"
                }
            
            await session.close()
            
            return {
                "success": True,
                "message": f"会话 {session_id} 已关闭"
            }
            
        except Exception as e:
            logger.error(f"关闭会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_all_sessions(self):
        """关闭所有会话"""
        async with self._lock:
            session_ids = list(self.sessions.keys())
        
        for session_id in session_ids:
            await self.close_session(session_id)
        
        logger.info("所有会话已关闭")
    
    async def cleanup(self):
        """清理资源"""
        await self.close_all_sessions()
        
        if self.playwright and self._playwright_context:
            try:
                await self._playwright_context.__aexit__(None, None, None)
                self.playwright = None
                self._playwright_context = None
                logger.info("Playwright 已停止")
            except Exception as e:
                logger.error(f"停止 Playwright 时出错: {e}")
                self.playwright = None
                self._playwright_context = None
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话信息字典，如果会话不存在则返回None
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "url": session.page.url if session.page else None
        }
    
    def list_sessions(self) -> list:
        """
        列出所有活动会话
        
        Returns:
            会话信息列表
        """
        return [
            self.get_session_info(session_id)
            for session_id in self.sessions.keys()
        ]