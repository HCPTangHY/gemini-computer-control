"""
真实电脑控制器
负责管理真实屏幕截图和执行本地操作
"""
from typing import Dict, Any, Optional
import logging
import base64
import io
import pyautogui
from PIL import Image
from .computer_control import execute_tool_call

logger = logging.getLogger(__name__)

class RealComputerController:
    """
    真实电脑控制器
    提供与 PlaywrightController 类似的接口，但操作真实电脑
    """
    
    def __init__(self):
        # 获取屏幕尺寸
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"真实电脑控制器初始化，屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
    async def take_screenshot(self) -> Dict[str, Any]:
        """
        截取真实屏幕截图
        
        Returns:
            包含base64编码截图的字典
        """
        try:
            # 截取全屏
            screenshot = pyautogui.screenshot()
            
            # 转换为 base64
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            screenshot_base64 = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
            
            logger.info("真实屏幕截图成功")
            
            return {
                "success": True,
                "screenshot": screenshot_base64,
                "url": "Desktop",
                "width": self.screen_width,
                "height": self.screen_height
            }
            
        except Exception as e:
            logger.error(f"真实屏幕截图失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行真实电脑操作
        
        Args:
            action: 操作数据
        
        Returns:
            执行结果
        """
        try:
            action_type = action.get('action') or action.get('function_name', '')
            args = {k: v for k, v in action.items() if k not in ['action', 'function_name']}
            
            logger.info(f"执行真实电脑操作: {action_type}")
            
            # 直接调用 computer_control 中的实现
            result = execute_tool_call(action_type, args)
            
            return {
                "success": result.get("status") != "error",
                "message": result.get("message", ""),
                "action": action_type,
                **result
            }
            
        except Exception as e:
            logger.error(f"执行真实电脑操作失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_screen_info(self) -> Dict[str, int]:
        """获取屏幕信息"""
        return {
            "width": self.screen_width,
            "height": self.screen_height
        }