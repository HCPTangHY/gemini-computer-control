"""
工具声明格式转换器
将内部工具声明格式转换为 Gemini REST API 格式
"""
from typing import Dict, Any, List


def convert_tool_declaration_to_rest_format(declaration: Dict[str, Any]) -> Dict[str, Any]:
    """
    将工具声明转换为 REST API 格式
    
    Args:
        declaration: 内部工具声明格式
    
    Returns:
        REST API 格式的工具声明
    """
    # 转换参数类型
    def convert_type(type_str: str) -> str:
        type_mapping = {
            "OBJECT": "object",
            "STRING": "string",
            "INTEGER": "integer",
            "NUMBER": "number",
            "BOOLEAN": "boolean",
            "ARRAY": "array"
        }
        return type_mapping.get(type_str, type_str.lower())
    
    # 递归转换 properties
    def convert_properties(props: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in props.items():
            converted = {}
            if "type" in value:
                converted["type"] = convert_type(value["type"])
            if "description" in value:
                converted["description"] = value["description"]
            if "enum" in value:
                converted["enum"] = value["enum"]
            if "items" in value:
                converted["items"] = convert_properties({"item": value["items"]})["item"]
            result[key] = converted
        return result
    
    # 构建 REST API 格式
    rest_declaration = {
        "name": declaration["name"],
        "description": declaration["description"]
    }
    
    if "parameters" in declaration:
        params = declaration["parameters"]
        rest_params = {
            "type": convert_type(params.get("type", "OBJECT"))
        }
        
        if "properties" in params:
            rest_params["properties"] = convert_properties(params["properties"])
        
        if "required" in params:
            rest_params["required"] = params["required"]
        
        rest_declaration["parameters"] = rest_params
    
    return rest_declaration


def convert_tools_to_rest_format(declarations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量转换工具声明为 REST API 格式
    
    Args:
        declarations: 工具声明列表
    
    Returns:
        REST API 格式的工具列表
    """
    return [
        {
            "functionDeclarations": [
                convert_tool_declaration_to_rest_format(decl)
                for decl in declarations
            ]
        }
    ]