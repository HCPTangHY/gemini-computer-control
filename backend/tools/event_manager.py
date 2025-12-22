"""
事件管理器
用于在 Agent 执行过程中发布截图等事件，供前端通过 SSE 订阅
"""
import queue
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventManager:
    """
    事件管理器
    
    支持：
    1. 发布事件到指定会话
    2. 订阅特定会话的事件流
    3. 多个订阅者同时订阅同一会话
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 每个会话的事件队列
        # session_id -> list of queues (多个订阅者)
        self.subscribers: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        self._initialized = True
        
        logger.info("事件管理器初始化完成")
    
    def subscribe(self, session_id: str) -> queue.Queue:
        """
        订阅指定会话的事件
        
        Args:
            session_id: 会话 ID
        
        Returns:
            事件队列，订阅者从此队列读取事件
        """
        q = queue.Queue(maxsize=100)
        with self._lock:
            self.subscribers[session_id].append(q)
        logger.info(f"新订阅者加入会话 {session_id}，当前订阅者数: {len(self.subscribers[session_id])}")
        return q
    
    def unsubscribe(self, session_id: str, q: queue.Queue):
        """
        取消订阅
        
        Args:
            session_id: 会话 ID
            q: 订阅时返回的队列
        """
        with self._lock:
            if session_id in self.subscribers:
                try:
                    self.subscribers[session_id].remove(q)
                    logger.info(f"订阅者离开会话 {session_id}，剩余订阅者数: {len(self.subscribers[session_id])}")
                except ValueError:
                    pass
    
    def publish(self, session_id: str, event_type: str, data: Dict[str, Any]):
        """
        发布事件到指定会话
        
        Args:
            session_id: 会话 ID
            event_type: 事件类型 (screenshot, action, complete, error)
            data: 事件数据
        """
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "session_id": session_id,
            "data": data
        }
        
        with self._lock:
            subscribers = self.subscribers.get(session_id, [])
            dead_queues = []
            
            for q in subscribers:
                try:
                    # 非阻塞放入，如果队列满则丢弃旧事件
                    if q.full():
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            pass
                    q.put_nowait(event)
                except Exception as e:
                    logger.warning(f"发布事件失败: {e}")
                    dead_queues.append(q)
            
            # 清理死亡的队列
            for q in dead_queues:
                try:
                    subscribers.remove(q)
                except ValueError:
                    pass
        
        if event_type == "screenshot":
            logger.debug(f"发布截图事件到会话 {session_id}，订阅者数: {len(subscribers)}")
        else:
            logger.info(f"发布 {event_type} 事件到会话 {session_id}")
    
    def publish_screenshot(
        self,
        session_id: str,
        screenshot: str,
        step: int,
        width: int,
        height: int,
        url: Optional[str] = None,
        action: Optional[str] = None
    ):
        """
        发布截图事件
        
        Args:
            session_id: 会话 ID
            screenshot: base64 编码的截图
            step: 当前步骤
            width: 截图宽度
            height: 截图高度
            url: 当前 URL（可选）
            action: 刚执行的操作（可选）
        """
        self.publish(session_id, "screenshot", {
            "screenshot": screenshot,
            "step": step,
            "width": width,
            "height": height,
            "url": url,
            "action": action
        })
    
    def publish_action(
        self,
        session_id: str,
        step: int,
        action: str,
        args: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """
        发布操作事件
        
        Args:
            session_id: 会话 ID
            step: 当前步骤
            action: 操作名称
            args: 操作参数
            result: 操作结果
        """
        self.publish(session_id, "action", {
            "step": step,
            "action": action,
            "args": args,
            "result": result
        })
    
    def publish_complete(
        self,
        session_id: str,
        success: bool,
        summary: str,
        total_steps: int
    ):
        """
        发布任务完成事件
        
        Args:
            session_id: 会话 ID
            success: 是否成功
            summary: 任务总结
            total_steps: 总步骤数
        """
        self.publish(session_id, "complete", {
            "success": success,
            "summary": summary,
            "total_steps": total_steps
        })
    
    def publish_error(
        self,
        session_id: str,
        error: str,
        step: Optional[int] = None
    ):
        """
        发布错误事件
        
        Args:
            session_id: 会话 ID
            error: 错误信息
            step: 发生错误的步骤（可选）
        """
        self.publish(session_id, "error", {
            "error": error,
            "step": step
        })
    
    def publish_notes(
        self,
        session_id: str,
        notes: list,
        action: str = "update"
    ):
        """
        发布笔记更新事件
        
        Args:
            session_id: 会话 ID
            notes: 笔记列表
            action: 操作类型 (add, list, clear, update)
        """
        self.publish(session_id, "notes", {
            "notes": notes,
            "action": action,
            "count": len(notes)
        })


# 全局单例
event_manager = EventManager()