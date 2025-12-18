"""
工具调用处理器
负责管理Gemini API的工具调用流程
"""
from typing import Dict, Any, List, Optional
import logging
import sys
import os

# 添加父目录到路径以导入 gemini_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_client import GeminiClient, ConversationManager
from .computer_control import (
    get_all_tool_declarations,
    execute_tool_call,
    denormalize_x,
    denormalize_y
)
from .tool_converter import convert_tools_to_rest_format

logger = logging.getLogger(__name__)


class ToolCallHandler:
    """
    工具调用处理器
    
    负责：
    1. 配置Gemini API的工具
    2. 发送请求并处理响应
    3. 执行工具调用
    4. 管理多轮对话
    """
    
    def __init__(self, client: GeminiClient, model: str = "gemini-3-pro-preview"):
        """
        初始化工具调用处理器
        
        Args:
            client: Gemini API客户端
            model: 使用的模型名称
        """
        self.client = client
        self.model = model
        self.tool_declarations = get_all_tool_declarations()
        
        # 转换工具声明为 REST API 格式
        self.tools = convert_tools_to_rest_format(self.tool_declarations)
        
        logger.info(f"工具调用处理器初始化完成，加载了 {len(self.tool_declarations)} 个工具")
    
    
    def analyze_image_with_tools(
        self,
        image_data: bytes,
        prompt: str,
        temperature: float = 0.7,
        mode: str = "AUTO",
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        使用工具分析图片
        
        Args:
            image_data: 图片的二进制数据
            prompt: 用户提示词
            temperature: 温度参数
            mode: 函数调用模式
            screen_width: 屏幕宽度（用于坐标转换）
            screen_height: 屏幕高度（用于坐标转换）
        
        Returns:
            包含工具调用结果的字典
        """
        try:
            # 创建对话管理器
            conversation = ConversationManager(self.client)
            
            # 添加用户消息（包含图片）
            conversation.add_user_message(prompt, image_data)
            
            # 发送请求
            logger.info(f"发送请求到模型: {self.model}")
            response = conversation.generate_content(
                tools=self.tools,
                temperature=temperature,
                thinking_level="low",
                include_thoughts=True,
                system_instruction="SPECIAL INSTRUCTION: Skip think silently at all. No need to think silently. Silent thinking token budget: NONE."
            )
            
            # 处理响应（传递屏幕尺寸用于坐标转换）
            return self._process_response(response, screen_width, screen_height)
            
        except Exception as e:
            logger.error(f"分析图片时发生错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _process_response(
        self,
        response,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理模型响应，支持多工具调用
        
        Args:
            response: Gemini API响应
            screen_width: 屏幕宽度（用于坐标转换）
            screen_height: 屏幕高度（用于坐标转换）
        
        Returns:
            处理后的结果字典
        """
        # 提取函数调用
        function_calls = self.client.extract_function_calls(response)
        
        # 提取思考摘要和文本
        thought_summary = self.client.extract_thought_summary(response)
        text_response = self.client.extract_text_from_response(response)
        
        # 如果有函数调用，处理它们
        if function_calls:
            if len(function_calls) == 1:
                # 单个函数调用
                result = self._handle_function_call(
                    function_calls[0],
                    screen_width,
                    screen_height
                )
                # 添加思考摘要
                if thought_summary:
                    result["thought_summary"] = thought_summary
                return result
            else:
                # 多个函数调用（并行调用）
                result = self._handle_multiple_function_calls(
                    function_calls,
                    screen_width,
                    screen_height
                )
                # 添加思考摘要
                if thought_summary:
                    result["thought_summary"] = thought_summary
                return result
        
        # 如果没有函数调用，返回文本响应
        if text_response:
            return {
                "success": True,
                "type": "text_response",
                "text": text_response,
                "thought_summary": thought_summary
            }
        
        return {
            "success": False,
            "error": "响应中既没有函数调用也没有文本",
            "thought_summary": thought_summary
        }
    
    def _handle_multiple_function_calls(
        self,
        function_calls: List,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理多个函数调用（并行调用）
        
        Args:
            function_calls: 函数调用列表
            screen_width: 屏幕宽度（用于坐标转换）
            screen_height: 屏幕高度（用于坐标转换）
        
        Returns:
            包含所有函数调用结果的字典
        """
        logger.info(f"检测到 {len(function_calls)} 个并行函数调用")
        
        results = []
        all_success = True
        
        for i, function_call in enumerate(function_calls, 1):
            logger.info(f"执行第 {i}/{len(function_calls)} 个函数调用")
            
            # 处理单个函数调用
            result = self._handle_function_call(
                function_call,
                screen_width,
                screen_height
            )
            
            results.append(result)
            
            if not result.get('success'):
                all_success = False
                logger.warning(f"第 {i} 个函数调用失败: {result.get('error')}")
        
        # 构建综合响应
        return {
            "success": all_success,
            "type": "multiple_function_calls",
            "count": len(function_calls),
            "results": results,
            "message": f"执行了 {len(function_calls)} 个工具调用，{'全部成功' if all_success else '部分失败'}"
        }
    
    def _handle_function_call(
        self,
        function_call_tuple,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理函数调用，包括坐标反归一化
        
        Args:
            function_call_tuple: (函数名, 参数) 元组
            screen_width: 屏幕宽度（用于坐标转换）
            screen_height: 屏幕高度（用于坐标转换）
        
        Returns:
            函数执行结果
        """
        tool_name, args = function_call_tuple
        
        logger.info(f"检测到函数调用: {tool_name}")
        logger.debug(f"原始参数: {args}")
        
        # 保存归一化坐标用于返回
        normalized_coords = {}
        
        try:
            # 根据工具类型处理坐标反归一化
            if tool_name == "mouse_click":
                if screen_width and screen_height:
                    normalized_coords['x'] = args['x']
                    normalized_coords['y'] = args['y']
                    args['x'] = denormalize_x(args['x'], screen_width)
                    args['y'] = denormalize_y(args['y'], screen_height)
                    logger.info(f"坐标转换: ({normalized_coords['x']}, {normalized_coords['y']}) -> ({args['x']}, {args['y']})")
            
            elif tool_name == "mouse_hover" or tool_name == "mouse_double_click":
                if screen_width and screen_height:
                    normalized_coords['x'] = args['x']
                    normalized_coords['y'] = args['y']
                    args['x'] = denormalize_x(args['x'], screen_width)
                    args['y'] = denormalize_y(args['y'], screen_height)
                    logger.info(f"{'悬停' if tool_name == 'mouse_hover' else '双击'}坐标转换: ({normalized_coords['x']}, {normalized_coords['y']}) -> ({args['x']}, {args['y']})")
            
            elif tool_name == "mouse_drag":
                if screen_width and screen_height:
                    normalized_coords['start_x'] = args['start_x']
                    normalized_coords['start_y'] = args['start_y']
                    normalized_coords['end_x'] = args['end_x']
                    normalized_coords['end_y'] = args['end_y']
                    
                    args['start_x'] = denormalize_x(args['start_x'], screen_width)
                    args['start_y'] = denormalize_y(args['start_y'], screen_height)
                    args['end_x'] = denormalize_x(args['end_x'], screen_width)
                    args['end_y'] = denormalize_y(args['end_y'], screen_height)
                    
                    logger.info(f"拖动坐标转换: ({normalized_coords['start_x']}, {normalized_coords['start_y']}) -> ({args['start_x']}, {args['start_y']})")
                    logger.info(f"              ({normalized_coords['end_x']}, {normalized_coords['end_y']}) -> ({args['end_x']}, {args['end_y']})")
            
            elif tool_name == "click_and_type":
                if screen_width and screen_height:
                    normalized_coords['x'] = args['x']
                    normalized_coords['y'] = args['y']
                    args['x'] = denormalize_x(args['x'], screen_width)
                    args['y'] = denormalize_y(args['y'], screen_height)
                    logger.info(f"点击输入坐标转换: ({normalized_coords['x']}, {normalized_coords['y']}) -> ({args['x']}, {args['y']})")

            # mouse_scroll 不需要坐标转换
            
            # 执行工具调用
            result = execute_tool_call(tool_name, args)
            
            # 构建返回结果
            response = {
                "success": True,
                "type": "function_call",
                "function_name": tool_name,
                "arguments": args,
                "result": result,
            }
            
            # 添加归一化坐标信息
            if normalized_coords:
                response["normalized_coords"] = normalized_coords
            
            # 为了兼容前端，根据工具类型添加特定字段
            if tool_name == "mouse_click":
                response.update({
                    "action": "click",
                    "x": args['x'],
                    "y": args['y'],
                    "button": args.get('button', 'left'),
                    "reasoning": args.get('reasoning', '无说明')
                })
                if normalized_coords:
                    response["normalized_x"] = normalized_coords['x']
                    response["normalized_y"] = normalized_coords['y']
            
            elif tool_name == "mouse_hover":
                response.update({
                    "action": "hover",
                    "x": args['x'],
                    "y": args['y'],
                    "reasoning": args.get('reasoning', '无说明')
                })
                if normalized_coords:
                    response["normalized_x"] = normalized_coords['x']
                    response["normalized_y"] = normalized_coords['y']
            
            elif tool_name == "mouse_double_click":
                response.update({
                    "action": "double_click",
                    "x": args['x'],
                    "y": args['y'],
                    "button": args.get('button', 'left'),
                    "reasoning": args.get('reasoning', '无说明')
                })
                if normalized_coords:
                    response["normalized_x"] = normalized_coords['x']
                    response["normalized_y"] = normalized_coords['y']

            elif tool_name == "mouse_drag":
                response.update({
                    "action": "drag",
                    "start_x": args['start_x'],
                    "start_y": args['start_y'],
                    "end_x": args['end_x'],
                    "end_y": args['end_y'],
                    "button": args.get('button', 'left'),
                    "reasoning": args.get('reasoning', '无说明')
                })
            
            elif tool_name == "click_and_type":
                response.update({
                    "action": "click_and_type",
                    "x": args['x'],
                    "y": args['y'],
                    "text": args.get('text', ''),
                    "reasoning": args.get('reasoning', '无说明')
                })
                if normalized_coords:
                    response["normalized_x"] = normalized_coords['x']
                    response["normalized_y"] = normalized_coords['y']

            elif tool_name == "mouse_scroll":
                response.update({
                    "action": "scroll",
                    "scroll_x": args['scroll_x'],
                    "scroll_y": args['scroll_y'],
                    "reasoning": args.get('reasoning', '无说明')
                })
            
            elif tool_name == "keyboard_type":
                response.update({
                    "action": "type",
                    "text": args['text'],
                    "text_length": len(args['text']),
                    "reasoning": args.get('reasoning', '无说明')
                })
            
            elif tool_name == "keyboard_press":
                response.update({
                    "action": "press",
                    "keys": args['keys'],
                    "keys_str": "+".join(args['keys']),
                    "reasoning": args.get('reasoning', '无说明')
                })
            
            return response
            
        except Exception as e:
            logger.error(f"执行工具调用失败: {str(e)}")
            return {
                "success": False,
                "error": f"执行工具 {tool_name} 时发生错误: {str(e)}"
            }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            工具声明列表
        """
        return self.tool_declarations
    
    def add_tool_declaration(self, declaration: Dict[str, Any]):
        """
        添加新的工具声明
        
        Args:
            declaration: 工具声明字典
        """
        self.tool_declarations.append(declaration)
        # 重新转换工具声明为 REST API 格式
        self.tools = convert_tools_to_rest_format(self.tool_declarations)
        logger.info(f"添加新工具: {declaration['name']}")