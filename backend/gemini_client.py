"""
自定义 Gemini REST API 客户端
支持思考签名的维护和对话上下文管理
"""
import requests
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import base64
import os

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    自定义 Gemini REST API 客户端
    
    功能：
    1. 使用 REST API 调用 Gemini 模型
    2. 自动维护思考签名（thought_signature）
    3. 管理对话历史上下文
    4. 支持函数调用
    """
    
    def __init__(self, api_key: str, model: str = "gemini-3-pro-preview", base_url: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            api_key: Gemini API 密钥
            model: 模型名称
            base_url: API 基础地址（可选，默认从环境变量 GEMINI_BASE_URL 读取）
        """
        self.api_key = api_key
        self.model = model
        
        # 优先使用传入的 base_url，其次从环境变量读取，最后使用默认地址
        self.base_url = base_url or os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
        
        logger.info(f"初始化 Gemini 客户端，模型: {model}, Base URL: {self.base_url}")
    
    def generate_content(
        self,
        contents: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 1.0,
        thinking_level: str = "low",
        include_thoughts: bool = True,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成内容
        
        Args:
            contents: 对话内容列表
            tools: 工具声明列表
            temperature: 温度参数
            thinking_level: 思考等级 ("low" 或 "high")
            include_thoughts: 是否包含思考摘要
            system_instruction: 系统指令文本
        
        Returns:
            API 响应
        """
        url = f"{self.base_url}/models/{self.model}:generateContent"
        
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "thinkingConfig": {
                    "thinkingLevel": thinking_level,
                    "includeThoughts": include_thoughts
                }
            }
        }
        
        # 添加系统指令
        if system_instruction:
            payload["system_instruction"] = {
                "parts": [
                    {
                        "text": system_instruction
                    }
                ]
            }
        
        # 添加工具配置
        if tools:
            payload["tools"] = tools
        
        logger.debug(f"发送请求到: {url}")
        logger.debug(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应内容: {e.response.text}")
            raise
    
    def extract_thought_signatures(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从响应中提取思考签名
        
        Args:
            response: API 响应
        
        Returns:
            包含思考签名的 parts 列表
        """
        signatures = []
        
        if "candidates" not in response:
            return signatures
        
        for candidate in response["candidates"]:
            if "content" not in candidate:
                continue
            
            content = candidate["content"]
            if "parts" not in content:
                continue
            
            for part in content["parts"]:
                # 检查是否包含思考签名
                if "thoughtSignature" in part:
                    signatures.append(part)
        
        return signatures
    
    def build_content_with_signature(
        self,
        role: str,
        parts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建包含签名的内容对象
        
        Args:
            role: 角色 ("user" 或 "model")
            parts: parts 列表
        
        Returns:
            内容对象
        """
        return {
            "role": role,
            "parts": parts
        }
    
    def create_text_part(self, text: str) -> Dict[str, Any]:
        """创建文本 part"""
        return {"text": text}
    
    def create_file_data_part(self, file_uri: str, mime_type: str) -> Dict[str, Any]:
        """创建文件数据 part（用于 File API 上传的文件）"""
        return {
            "fileData": {
                "mimeType": mime_type,
                "fileUri": file_uri
            }
        }
    
    def create_image_part(self, image_bytes: bytes, mime_type: str = "image/png") -> Dict[str, Any]:
        """创建图片 part"""
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return {
            "inlineData": {
                "mimeType": mime_type,
                "data": image_base64
            }
        }
    
    def create_function_call_part(self, name: str, args: Dict[str, Any], thought_signature: Optional[str] = None) -> Dict[str, Any]:
        """
        创建函数调用 part
        
        Args:
            name: 函数名
            args: 参数
            thought_signature: 思考签名（可选）
        """
        part = {
            "functionCall": {
                "name": name,
                "args": args
            }
        }
        if thought_signature:
            part["thoughtSignature"] = thought_signature
        return part
    
    def create_function_response_part(self, name: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """创建函数响应 part"""
        return {
            "functionResponse": {
                "name": name,
                "response": response
            }
        }
    
    def extract_function_calls_with_signatures(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从响应中提取函数调用及其思考签名
        
        Args:
            response: API 响应
        
        Returns:
            包含 name, args, thought_signature 的字典列表
        """
        results = []
        
        if "candidates" not in response:
            return results
        
        for candidate in response["candidates"]:
            if "content" not in candidate:
                continue
            
            content = candidate["content"]
            if "parts" not in content:
                continue
            
            for part in content["parts"]:
                fc = None
                if "functionCall" in part:
                    fc = part["functionCall"]
                elif "function_call" in part:
                    fc = part["function_call"]
                
                if fc:
                    results.append({
                        "name": fc["name"],
                        "args": fc.get("args", {}),
                        "thought_signature": part.get("thoughtSignature")
                    })
        
        return results

    def extract_function_calls(self, response: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        从响应中提取函数调用 (保持向后兼容)
        
        Args:
            response: API 响应
        
        Returns:
            (函数名, 参数) 元组列表
        """
        calls = self.extract_function_calls_with_signatures(response)
        return [(c["name"], c["args"]) for c in calls]
    
    def get_model_response_content(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        获取模型响应的完整内容（包含思考签名）
        
        Args:
            response: API 响应
        
        Returns:
            模型响应的 content 对象
        """
        if "candidates" not in response or not response["candidates"]:
            return None
        
        candidate = response["candidates"][0]
        if "content" not in candidate:
            return None
        
        return candidate["content"]
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        从响应中提取文本内容
        
        Args:
            response: API 响应
        
        Returns:
            文本内容
        """
        if "candidates" not in response:
            return ""
        
        texts = []
        for candidate in response["candidates"]:
            if "content" not in candidate:
                continue
            
            content = candidate["content"]
            if "parts" not in content:
                continue
            
            for part in content["parts"]:
                # 跳过思考摘要
                if part.get("thought", False):
                    continue
                
                if "text" in part:
                    texts.append(part["text"])
        
        return "\n".join(texts)
    
    def extract_thought_summary(self, response: Dict[str, Any]) -> str:
        """
        从响应中提取思考摘要
        
        Args:
            response: API 响应
        
        Returns:
            思考摘要文本
        """
        if "candidates" not in response:
            return ""
        
        thoughts = []
        for candidate in response["candidates"]:
            if "content" not in candidate:
                continue
            
            content = candidate["content"]
            if "parts" not in content:
                continue
            
            for part in content["parts"]:
                # 只提取思考摘要
                if part.get("thought", False) and "text" in part:
                    thoughts.append(part["text"])
        
        return "\n".join(thoughts)


class ConversationManager:
    """
    对话管理器
    
    负责维护对话历史和思考签名
    """
    
    def __init__(self, client: GeminiClient):
        """
        初始化对话管理器
        
        Args:
            client: Gemini 客户端
        """
        self.client = client
        self.history: List[Dict[str, Any]] = []
        
        logger.info("初始化对话管理器")
    
    def add_user_message(self, text: str, image_bytes: Optional[bytes] = None):
        """
        添加用户消息
        
        Args:
            text: 文本内容
            image_bytes: 图片数据（可选）
        """
        parts = [self.client.create_text_part(text)]
        
        if image_bytes:
            parts.append(self.client.create_image_part(image_bytes))
        
        content = self.client.build_content_with_signature("user", parts)
        self.history.append(content)
        
        logger.debug(f"添加用户消息，当前历史长度: {len(self.history)}")
    
    def add_model_response(self, response: Dict[str, Any]):
        """
        添加模型响应（包含思考签名）
        
        Args:
            response: API 响应
        """
        model_content = self.client.get_model_response_content(response)
        if model_content:
            self.history.append(model_content)
            logger.debug(f"添加模型响应，当前历史长度: {len(self.history)}")
    
    def add_function_responses(
        self,
        function_results: List[Tuple[str, Dict[str, Any]]],
        screenshot_bytes: Optional[bytes] = None
    ):
        """
        添加函数响应
        
        Args:
            function_results: (函数名, 结果) 元组列表
            screenshot_bytes: 截图数据（可选）
        """
        parts = []
        
        for func_name, result in function_results:
            parts.append(self.client.create_function_response_part(func_name, result))
        
        if screenshot_bytes:
            parts.append(self.client.create_image_part(screenshot_bytes))
        
        content = self.client.build_content_with_signature("user", parts)
        self.history.append(content)
        
        logger.debug(f"添加函数响应，当前历史长度: {len(self.history)}")

    def add_model_content(self, content: Dict[str, Any]):
        """
        直接添加模型内容对象（用于精确控制 parts）
        
        Args:
            content: 模型内容对象
        """
        if content and content.get("role") == "model":
            self.history.append(content)
            logger.debug(f"添加模型内容，当前历史长度: {len(self.history)}")
    
    def validate_history_signatures(self) -> bool:
        """
        验证历史记录中的思考签名是否符合 Gemini 3 要求
        
        根据文档：
        1. 每个包含 functionCall 的 step 的第一个 functionCall 必须有 thoughtSignature
        2. 并行调用中只有第一个有签名
        """
        # 查找当前 turn 的开始（最后一个包含 text 的 user 消息）
        current_turn_start = -1
        for i in range(len(self.history) - 1, -1, -1):
            msg = self.history[i]
            if msg["role"] == "user":
                has_text = any("text" in p for p in msg["parts"])
                if has_text:
                    current_turn_start = i
                    break
        
        if current_turn_start == -1:
            return True # 没有找到 user 消息，可能是初始状态
            
        # 检查从 current_turn_start 之后的所有 model 消息
        for i in range(current_turn_start + 1, len(self.history)):
            msg = self.history[i]
            if msg["role"] == "model":
                parts = msg["parts"]
                # 找到第一个 functionCall
                first_fc_index = -1
                for j, part in enumerate(parts):
                    if "functionCall" in part or "function_call" in part:
                        first_fc_index = j
                        break
                
                if first_fc_index != -1:
                    part = parts[first_fc_index]
                    if "thoughtSignature" not in part and "thought_signature" not in part:
                        logger.warning(f"历史记录验证失败: 索引 {i} 的模型响应中第一个函数调用缺少思考签名")
                        return False
        
        return True

    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.history
    
    def clear_history(self):
        """清空对话历史"""
        self.history = []
        logger.info("清空对话历史")
    
    def generate_content(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 1.0,
        thinking_level: str = "low",
        include_thoughts: bool = True,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成内容（使用当前历史）
        
        Args:
            tools: 工具声明列表
            temperature: 温度参数
            thinking_level: 思考等级
            include_thoughts: 是否包含思考摘要
            system_instruction: 系统指令文本
        
        Returns:
            API 响应
        """
        return self.client.generate_content(
            contents=self.history,
            tools=tools,
            temperature=temperature,
            thinking_level=thinking_level,
            include_thoughts=include_thoughts,
            system_instruction=system_instruction
        )