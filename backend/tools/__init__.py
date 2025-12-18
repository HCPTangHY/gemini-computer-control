"""
Gemini函数调用工具模块
提供计算机控制相关的工具声明和实现
"""
from .computer_control import (
    mouse_click,
    mouse_drag,
    mouse_scroll,
    keyboard_type,
    keyboard_press,
    MOUSE_CLICK_DECLARATION,
    MOUSE_DRAG_DECLARATION,
    MOUSE_SCROLL_DECLARATION,
    KEYBOARD_TYPE_DECLARATION,
    KEYBOARD_PRESS_DECLARATION,
    get_all_tool_declarations,
    execute_tool_call,
    denormalize_x,
    denormalize_y
)
from .handler import ToolCallHandler

__all__ = [
    'mouse_click',
    'mouse_drag',
    'mouse_scroll',
    'keyboard_type',
    'keyboard_press',
    'MOUSE_CLICK_DECLARATION',
    'MOUSE_DRAG_DECLARATION',
    'MOUSE_SCROLL_DECLARATION',
    'KEYBOARD_TYPE_DECLARATION',
    'KEYBOARD_PRESS_DECLARATION',
    'get_all_tool_declarations',
    'execute_tool_call',
    'denormalize_x',
    'denormalize_y',
    'ToolCallHandler'
]