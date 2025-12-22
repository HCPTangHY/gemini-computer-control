"""
计算机控制工具定义
包含鼠标点击、键盘输入等计算机操作的工具声明和实现
"""
from typing import Dict, Any, Callable
import logging
import pyautogui
import time
import pyperclip

# 设置 pyautogui 安全选项
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

logger = logging.getLogger(__name__)

# ============================================================================
# 工具实现函数
# ============================================================================

def mouse_click(x: int, y: int, button: str, duration: int = 0, reasoning: str = "") -> Dict[str, Any]:
    """
    在指定坐标位置执行鼠标点击操作
    
    Args:
        x: 点击位置的实际横坐标（像素）
        y: 点击位置的实际纵坐标（像素）
        button: 鼠标按键类型 ("left", "middle", "right")
        duration: 按下时长（毫秒），0表示普通点击
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: mouse_click(x={x}, y={y}, button={button}, duration={duration}ms)")
    
    if duration > 0:
        pyautogui.click(x, y, button=button, duration=duration/1000)
    else:
        pyautogui.click(x, y, button=button)
    
    return {
        "status": "success",
        "action": "mouse_click",
        "x": x,
        "y": y,
        "button": button,
        "duration": duration,
        "reasoning": reasoning,
        "message": f"已在坐标({x}, {y})执行{button}键点击，按下时长{duration}ms"
    }


def mouse_double_click(x: int, y: int, button: str = "left", reasoning: str = "") -> Dict[str, Any]:
    """
    在指定坐标位置执行鼠标双击操作
    
    Args:
        x: 点击位置的实际横坐标（像素）
        y: 点击位置的实际纵坐标（像素）
        button: 鼠标按键类型 ("left", "middle", "right")
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: mouse_double_click(x={x}, y={y}, button={button})")
    
    pyautogui.doubleClick(x, y, button=button)
    
    return {
        "status": "success",
        "action": "mouse_double_click",
        "x": x,
        "y": y,
        "button": button,
        "reasoning": reasoning,
        "message": f"已在坐标({x}, {y})执行{button}键双击"
    }


def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int, button: str, reasoning: str = "") -> Dict[str, Any]:
    """
    执行鼠标拖动操作
    
    Args:
        start_x: 起点横坐标（像素）
        start_y: 起点纵坐标（像素）
        end_x: 终点横坐标（像素）
        end_y: 终点纵坐标（像素）
        button: 鼠标按键类型 ("left", "middle", "right")
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: mouse_drag(from=({start_x}, {start_y}), to=({end_x}, {end_y}), button={button})")
    
    pyautogui.moveTo(start_x, start_y)
    pyautogui.dragTo(end_x, end_y, button=button, duration=0.5)
    
    return {
        "status": "success",
        "action": "mouse_drag",
        "start_x": start_x,
        "start_y": start_y,
        "end_x": end_x,
        "end_y": end_y,
        "button": button,
        "reasoning": reasoning,
        "message": f"已从({start_x}, {start_y})拖动到({end_x}, {end_y})，使用{button}键"
    }


def mouse_hover(x: int, y: int, reasoning: str = "") -> Dict[str, Any]:
    """
    将鼠标移动到指定坐标位置并悬停
    
    Args:
        x: 悬停位置的实际横坐标（像素）
        y: 悬停位置的实际纵坐标（像素）
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: mouse_hover(x={x}, y={y})")
    
    pyautogui.moveTo(x, y, duration=0.3)
    
    return {
        "status": "success",
        "action": "mouse_hover",
        "x": x,
        "y": y,
        "reasoning": reasoning,
        "message": f"已将鼠标移动到坐标({x}, {y})并悬停"
    }


def mouse_scroll(scroll_x: int, scroll_y: int, reasoning: str = "") -> Dict[str, Any]:
    """
    执行鼠标滚轮操作
    
    Args:
        scroll_x: 水平滚动量（正数向右，负数向左）
        scroll_y: 垂直滚动量（正数向下，负数向上）
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: mouse_scroll(scroll_x={scroll_x}, scroll_y={scroll_y})")
    
    if scroll_y != 0:
        # pyautogui.scroll 在 Windows 上正数向上，负数向下，与 Playwright 相反
        # 这里我们统一逻辑：正数向下，负数向上
        pyautogui.scroll(-scroll_y)
    if scroll_x != 0:
        pyautogui.hscroll(scroll_x)
    
    direction = []
    if scroll_y > 0:
        direction.append("向下")
    elif scroll_y < 0:
        direction.append("向上")
    if scroll_x > 0:
        direction.append("向右")
    elif scroll_x < 0:
        direction.append("向左")
    
    direction_str = "、".join(direction) if direction else "无滚动"
    
    return {
        "status": "success",
        "action": "mouse_scroll",
        "scroll_x": scroll_x,
        "scroll_y": scroll_y,
        "reasoning": reasoning,
        "message": f"已执行滚轮操作：{direction_str}，向量({scroll_x}, {scroll_y})"
    }


def keyboard_type(text: str, clear_existing: bool = False, reasoning: str = "") -> Dict[str, Any]:
    """
    输入文本内容
    
    Args:
        text: 要输入的文本内容
        clear_existing: 是否先清除现有文本（默认False）
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: keyboard_type(text='{text[:50]}...', clear_existing={clear_existing})")
    
    if clear_existing:
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
    
    # 使用剪贴板支持中文输入
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    
    return {
        "status": "success",
        "action": "keyboard_type",
        "text": text,
        "text_length": len(text),
        "clear_existing": clear_existing,
        "reasoning": reasoning,
        "message": f"{'清除后' if clear_existing else ''}已输入文本，长度{len(text)}字符"
    }


def clear_text(reasoning: str = "") -> Dict[str, Any]:
    """
    清除当前输入框的文本（全选后删除）
    
    Args:
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: clear_text()")
    
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('delete')
    
    return {
        "status": "success",
        "action": "clear_text",
        "reasoning": reasoning,
        "message": "已清除文本"
    }


def click_and_type(
    x: int,
    y: int,
    text: str = "",
    clear_existing: bool = True,
    reasoning: str = ""
) -> Dict[str, Any]:
    """
    点击指定位置后输入文本（组合操作）
    
    Args:
        x: 点击位置的实际横坐标（像素）
        y: 点击位置的实际纵坐标（像素）
        text: 要输入的文本内容（为空则只清除不输入）
        clear_existing: 是否先清除现有文本（默认True）
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: click_and_type(x={x}, y={y}, text='{text[:30]}...', clear={clear_existing})")
    
    pyautogui.click(x, y)
    time.sleep(0.2)
    if clear_existing:
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
    if text:
        # 使用剪贴板支持中文输入
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
    
    operation = []
    if clear_existing:
        operation.append("清除文本")
    if text:
        operation.append(f"输入'{text[:30]}{'...' if len(text) > 30 else ''}'")
    
    operation_str = "、".join(operation) if operation else "仅点击"
    
    return {
        "status": "success",
        "action": "click_and_type",
        "x": x,
        "y": y,
        "text": text,
        "text_length": len(text),
        "clear_existing": clear_existing,
        "reasoning": reasoning,
        "message": f"已在坐标({x}, {y})点击并{operation_str}"
    }


def keyboard_press(keys: list, reasoning: str = "") -> Dict[str, Any]:
    """
    执行键盘按键操作，支持单个按键或组合键
    
    Args:
        keys: 按键列表。单个按键时列表只有一个元素，组合键时包含多个元素（同时按下）
              例如: ["enter"] 表示按Enter键
                   ["ctrl", "c"] 表示按Ctrl+C组合键
                   ["ctrl", "shift", "esc"] 表示按Ctrl+Shift+Esc
        reasoning: 选择此操作的原因说明
    
    Returns:
        包含执行状态的字典
    """
    keys_str = "+".join(keys)
    logger.info(f"工具调用: keyboard_press(keys={keys_str})")
    
    if len(keys) == 1:
        pyautogui.press(keys[0])
    else:
        pyautogui.hotkey(*keys)
    
    operation_type = "组合键" if len(keys) > 1 else "单键"
    
    return {
        "status": "success",
        "action": "keyboard_press",
        "keys": keys,
        "keys_str": keys_str,
        "operation_type": operation_type,
        "reasoning": reasoning,
        "message": f"已执行{operation_type}操作：{keys_str}"
    }


def wait(seconds: int, reasoning: str = "") -> Dict[str, Any]:
    """
    等待指定的时间
    
    Args:
        seconds: 等待时长（秒），范围1-30
        reasoning: 等待的原因说明
    
    Returns:
        包含执行状态的字典
    """
    # 限制等待时间在1-30秒之间
    seconds = max(1, min(30, seconds))
    
    logger.info(f"工具调用: wait(seconds={seconds})")
    
    import time
    time.sleep(seconds)
    
    return {
        "status": "success",
        "action": "wait",
        "seconds": seconds,
        "reasoning": reasoning,
        "message": f"已等待 {seconds} 秒"
    }


def task_complete(summary: str, success: bool = True) -> Dict[str, Any]:
    """
    标记任务完成
    
    Args:
        summary: 任务完成总结
        success: 任务是否成功完成
    
    Returns:
        包含执行状态的字典
    """
    logger.info(f"工具调用: task_complete(success={success})")
    logger.info(f"任务总结: {summary}")
    
    return {
        "status": "completed",
        "action": "task_complete",
        "summary": summary,
        "success": success,
        "message": "任务已完成"
    }


# ============================================================================
# 工具声明（OpenAPI Schema格式）
# ============================================================================

MOUSE_CLICK_DECLARATION = {
    "name": "mouse_click",
    "description": "在屏幕上的指定坐标位置执行鼠标点击操作。支持左键、中键、右键点击，可选择按下时长。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "x": {
                "type": "INTEGER",
                "description": "点击位置的归一化横坐标（0-1000范围）。0表示最左侧，1000表示最右侧。"
            },
            "y": {
                "type": "INTEGER",
                "description": "点击位置的归一化纵坐标（0-1000范围）。0表示最顶部，1000表示最底部。"
            },
            "button": {
                "type": "STRING",
                "enum": ["left", "middle", "right"],
                "description": "鼠标按键类型。left=左键，middle=中键，right=右键。"
            },
            "duration": {
                "type": "INTEGER",
                "description": "按下时长（毫秒）。0表示普通点击，大于0表示长按指定时长。默认为0。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择此操作的原因说明。应该清晰地解释为什么选择这个坐标和操作。"
            }
        },
        "required": ["x", "y", "button"]
    }
}

MOUSE_DOUBLE_CLICK_DECLARATION = {
    "name": "mouse_double_click",
    "description": "在屏幕上的指定坐标位置执行鼠标双击操作。常用于打开文件、启动程序或选择文本。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "x": {
                "type": "INTEGER",
                "description": "点击位置的归一化横坐标（0-1000范围）。"
            },
            "y": {
                "type": "INTEGER",
                "description": "点击位置的归一化纵坐标（0-1000范围）。"
            },
            "button": {
                "type": "STRING",
                "enum": ["left", "middle", "right"],
                "description": "鼠标按键类型。默认为 left。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择此操作的原因说明。"
            }
        },
        "required": ["x", "y"]
    }
}

MOUSE_HOVER_DECLARATION = {
    "name": "mouse_hover",
    "description": "将鼠标移动到屏幕上的指定坐标位置并悬停。常用于触发悬停效果、显示工具提示、展开下拉菜单等场景。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "x": {
                "type": "INTEGER",
                "description": "悬停位置的归一化横坐标（0-1000范围）。0表示最左侧，1000表示最右侧。"
            },
            "y": {
                "type": "INTEGER",
                "description": "悬停位置的归一化纵坐标（0-1000范围）。0表示最顶部，1000表示最底部。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择此悬停操作的原因说明。应该清晰地解释为什么需要在此位置悬停。"
            }
        },
        "required": ["x", "y"]
    }
}

MOUSE_DRAG_DECLARATION = {
    "name": "mouse_drag",
    "description": "执行鼠标拖动操作，从起点拖动到终点。支持左键、中键、右键拖动。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "start_x": {
                "type": "INTEGER",
                "description": "起点的归一化横坐标（0-1000范围）。"
            },
            "start_y": {
                "type": "INTEGER",
                "description": "起点的归一化纵坐标（0-1000范围）。"
            },
            "end_x": {
                "type": "INTEGER",
                "description": "终点的归一化横坐标（0-1000范围）。"
            },
            "end_y": {
                "type": "INTEGER",
                "description": "终点的归一化纵坐标（0-1000范围）。"
            },
            "button": {
                "type": "STRING",
                "enum": ["left", "middle", "right"],
                "description": "拖动时使用的鼠标按键类型。left=左键，middle=中键，right=右键。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择此拖动操作的原因说明。"
            }
        },
        "required": ["start_x", "start_y", "end_x", "end_y", "button"]
    }
}

MOUSE_SCROLL_DECLARATION = {
    "name": "mouse_scroll",
    "description": "执行鼠标滚轮操作。通过滚动向量控制滚动方向和距离。正值表示向下/向右，负值表示向上/向左。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "scroll_x": {
                "type": "INTEGER",
                "description": "水平滚动量。正数表示向右滚动，负数表示向左滚动，0表示不水平滚动。"
            },
            "scroll_y": {
                "type": "INTEGER",
                "description": "垂直滚动量。正数表示向下滚动，负数表示向上滚动，0表示不垂直滚动。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择此滚动操作的原因说明。"
            }
        },
        "required": ["scroll_x", "scroll_y"]
    }
}

KEYBOARD_TYPE_DECLARATION = {
    "name": "keyboard_type",
    "description": "输入文本内容。用于在文本框、编辑器等位置输入文字。可选择是否先清除现有文本。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {
                "type": "STRING",
                "description": "要输入的文本内容。可以是任意长度的字符串。"
            },
            "clear_existing": {
                "type": "BOOLEAN",
                "description": "是否先清除输入框中的现有文本。true=先全选删除再输入，false=直接输入。默认为false。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择输入此文本的原因说明。"
            }
        },
        "required": ["text"]
    }
}

CLEAR_TEXT_DECLARATION = {
    "name": "clear_text",
    "description": "清除当前输入框的文本。通过全选（Ctrl+A）后删除来清空文本内容。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "reasoning": {
                "type": "STRING",
                "description": "选择清除文本的原因说明。"
            }
        },
        "required": []
    }
}

CLICK_AND_TYPE_DECLARATION = {
    "name": "click_and_type",
    "description": "组合操作：先点击指定位置，然后可选择清除现有文本，最后输入新文本。适用于需要先聚焦输入框再输入的场景。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "x": {
                "type": "INTEGER",
                "description": "点击位置的归一化横坐标（0-1000范围）。0表示最左侧，1000表示最右侧。"
            },
            "y": {
                "type": "INTEGER",
                "description": "点击位置的归一化纵坐标（0-1000范围）。0表示最顶部，1000表示最底部。"
            },
            "text": {
                "type": "STRING",
                "description": "要输入的文本内容。如果为空字符串，则只执行点击和清除操作（如果启用）。"
            },
            "clear_existing": {
                "type": "BOOLEAN",
                "description": "是否先清除输入框中的现有文本。true=点击后先全选删除再输入，false=点击后直接输入。默认为true。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择此操作的原因说明。"
            }
        },
        "required": ["x", "y"]
    }
}

KEYBOARD_PRESS_DECLARATION = {
    "name": "keyboard_press",
    "description": "执行键盘按键操作。支持单个按键或组合键（多个按键同时按下）。常用于快捷键操作、特殊按键等。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "keys": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                },
                "description": "按键列表。单个按键时只包含一个元素，组合键时包含多个元素。常用按键：enter, esc, tab, space, backspace, delete, ctrl, shift, alt, win, up, down, left, right, home, end, pageup, pagedown, f1-f12等。示例：['enter']表示回车，['ctrl','c']表示复制，['ctrl','shift','esc']表示任务管理器。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "选择此按键操作的原因说明。"
            }
        },
        "required": ["keys"]
    }
}

WAIT_DECLARATION = {
    "name": "wait",
    "description": "等待指定的时间。用于等待页面加载、动画完成、或其他需要时间的操作。等待时间范围为1-30秒。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "seconds": {
                "type": "INTEGER",
                "description": "等待时长（秒）。必须在1-30之间。常见用法：等待页面加载3-5秒，等待动画1-2秒，等待长时间操作10-30秒。"
            },
            "reasoning": {
                "type": "STRING",
                "description": "等待的原因说明。例如：等待页面加载完成、等待搜索结果显示、等待动画结束等。"
            }
        },
        "required": ["seconds"]
    }
}

TASK_COMPLETE_DECLARATION = {
    "name": "task_complete",
    "description": "当你认为用户的任务已经完全完成时，调用此工具来结束任务。你必须提供详细的任务总结，说明你执行了哪些操作以及达到了什么结果。",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "summary": {
                "type": "STRING",
                "description": "任务完成总结。详细描述你执行的所有操作步骤和最终达到的结果。"
            },
            "success": {
                "type": "BOOLEAN",
                "description": "任务是否成功完成。true表示成功，false表示失败或部分完成。"
            }
        },
        "required": ["summary", "success"]
    }
}

# ============================================================================
# 工具注册表
# ============================================================================

# 工具名称到实现函数的映射
TOOL_IMPLEMENTATIONS: Dict[str, Callable] = {
    "mouse_click": mouse_click,
    "mouse_double_click": mouse_double_click,
    "mouse_hover": mouse_hover,
    "mouse_drag": mouse_drag,
    "mouse_scroll": mouse_scroll,
    "keyboard_type": keyboard_type,
    "keyboard_press": keyboard_press,
    "clear_text": clear_text,
    "click_and_type": click_and_type,
    "wait": wait,
    "task_complete": task_complete,
    "switch_tab": lambda **kwargs: {"status": "success", "message": "正在切换标签页"},
    "list_tabs": lambda **kwargs: {"status": "success", "message": "正在获取标签页列表"},
    "new_tab": lambda **kwargs: {"status": "success", "message": "正在新建标签页"},
    "reset_browser": lambda **kwargs: {"status": "success", "message": "正在重置浏览器环境"},
    "clear_cookies": lambda **kwargs: {"status": "success", "message": "正在清除Cookies"},
    "navigate": lambda **kwargs: {"status": "success", "message": "正在导航到新页面"},
    "add_note": lambda **kwargs: {"status": "success", "message": "笔记已添加"},
    "list_notes": lambda **kwargs: {"status": "success", "message": "获取笔记列表"},
    "clear_notes": lambda **kwargs: {"status": "success", "message": "笔记已清空"},
}

# 所有工具声明的列表
TOOL_DECLARATIONS = [
    MOUSE_CLICK_DECLARATION,
    MOUSE_DOUBLE_CLICK_DECLARATION,
    MOUSE_HOVER_DECLARATION,
    MOUSE_DRAG_DECLARATION,
    MOUSE_SCROLL_DECLARATION,
    KEYBOARD_TYPE_DECLARATION,
    KEYBOARD_PRESS_DECLARATION,
    CLEAR_TEXT_DECLARATION,
    CLICK_AND_TYPE_DECLARATION,
    WAIT_DECLARATION,
    TASK_COMPLETE_DECLARATION,
    {
        "name": "switch_tab",
        "description": "在浏览器的多个标签页之间切换。仅在浏览器自动化模式下有效。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "index": {
                    "type": "INTEGER",
                    "description": "目标标签页的索引（从0开始）。"
                }
            },
            "required": ["index"]
        }
    },
    {
        "name": "list_tabs",
        "description": "列出浏览器当前所有打开的标签页及其标题和URL。仅在浏览器自动化模式下有效。",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "new_tab",
        "description": "在浏览器中新建一个标签页并访问指定的网址。仅在浏览器自动化模式下有效。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "要在新标签页中打开的网址。"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "reset_browser",
        "description": "重置浏览器环境，创建全新的浏览器上下文（新的指纹、清空缓存和Cookies）。适用于需要全新浏览器状态的场景，如规避检测、清除登录状态等。仅在浏览器自动化模式下有效。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "重置后要访问的网址。如果不提供则访问 about:blank。"
                },
                "reasoning": {
                    "type": "STRING",
                    "description": "重置浏览器的原因说明。"
                }
            },
            "required": []
        }
    },
    {
        "name": "clear_cookies",
        "description": "清除当前浏览器上下文的所有Cookies和本地存储，但保留当前页面。适用于需要清除登录状态但不需要完全重置浏览器的场景。仅在浏览器自动化模式下有效。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "reasoning": {
                    "type": "STRING",
                    "description": "清除Cookies的原因说明。"
                }
            },
            "required": []
        }
    },
    {
        "name": "navigate",
        "description": "在当前标签页导航到指定的网址。与new_tab不同，这会在当前页面进行跳转而不是新建标签页。仅在浏览器自动化模式下有效。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "要导航到的网址。"
                },
                "reasoning": {
                    "type": "STRING",
                    "description": "导航的原因说明。"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "add_note",
        "description": "添加一条笔记到任务笔记本。用于记录重要信息、发现、进度、待办事项等。笔记会在整个任务期间保留，帮助你追踪任务状态和记住关键信息。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "content": {
                    "type": "STRING",
                    "description": "笔记内容。"
                },
                "category": {
                    "type": "STRING",
                    "enum": ["info", "progress", "todo", "important", "error"],
                    "description": "笔记分类。info=一般信息，progress=进度记录，todo=待办事项，important=重要发现，error=错误记录。"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "list_notes",
        "description": "列出当前任务的所有笔记。用于回顾之前记录的信息、检查进度、查看待办事项等。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "enum": ["info", "progress", "todo", "important", "error", "all"],
                    "description": "要筛选的笔记分类。默认为 all（所有分类）。"
                }
            },
            "required": []
        }
    },
    {
        "name": "clear_notes",
        "description": "清空当前任务的所有笔记。谨慎使用，清空后无法恢复。",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "enum": ["info", "progress", "todo", "important", "error", "all"],
                    "description": "要清空的笔记分类。默认为 all（清空所有）。"
                },
                "confirm": {
                    "type": "BOOLEAN",
                    "description": "确认清空。必须为 true 才会执行清空操作。"
                }
            },
            "required": ["confirm"]
        }
    }
]


# ============================================================================
# 坐标转换函数
# ============================================================================

def denormalize_x(x: int, screen_width: int) -> int:
    """
    将归一化的x坐标(0-1000)转换为实际像素坐标
    
    Args:
        x: 归一化的x坐标 (0-1000)
        screen_width: 屏幕宽度（像素）
    
    Returns:
        实际的x坐标（像素）
    """
    return int(x / 1000 * screen_width)


def denormalize_y(y: int, screen_height: int) -> int:
    """
    将归一化的y坐标(0-1000)转换为实际像素坐标
    
    Args:
        y: 归一化的y坐标 (0-1000)
        screen_height: 屏幕高度（像素）
    
    Returns:
        实际的y坐标（像素）
    """
    return int(y / 1000 * screen_height)


# ============================================================================
# 辅助函数
# ============================================================================

def get_all_tool_declarations() -> list:
    """
    获取所有工具声明
    
    Returns:
        工具声明列表
    """
    return TOOL_DECLARATIONS


def execute_tool_call(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行工具调用
    
    Args:
        tool_name: 工具名称
        args: 工具参数
    
    Returns:
        工具执行结果
    
    Raises:
        ValueError: 如果工具不存在
    """
    if tool_name not in TOOL_IMPLEMENTATIONS:
        raise ValueError(f"未知的工具: {tool_name}")
    
    tool_func = TOOL_IMPLEMENTATIONS[tool_name]
    
    try:
        result = tool_func(**args)
        logger.info(f"工具执行成功: {tool_name}")
        return result
    except Exception as e:
        logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"执行工具 {tool_name} 时发生错误"
        }