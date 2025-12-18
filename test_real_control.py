import requests
import time
import base64
import os

BASE_URL = "http://localhost:5000"

def test_real_control():
    print("开始测试真实电脑控制功能...")
    
    # 1. 检查健康状态
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"健康检查: {resp.json()}")
    except Exception as e:
        print(f"无法连接到服务器: {e}")
        print("请确保后端服务已启动 (python backend/main.py)")
        return

    # 2. 获取屏幕信息
    resp = requests.get(f"{BASE_URL}/real/info")
    screen_info = resp.json()
    print(f"屏幕信息: {screen_info}")
    
    # 3. 测试截图
    print("正在测试截图...")
    resp = requests.get(f"{BASE_URL}/real/screenshot")
    screenshot_result = resp.json()
    if screenshot_result.get("success"):
        print(f"截图成功，数据长度: {len(screenshot_result['screenshot'])}")
    else:
        print(f"截图失败: {screenshot_result.get('error')}")

    # 4. 测试鼠标移动 (移动到屏幕中心)
    print("正在测试鼠标移动到中心...")
    center_x = 500 # 归一化坐标
    center_y = 500
    action = {
        "action": "mouse_hover",
        "x": center_x,
        "y": center_y,
        "reasoning": "测试移动到屏幕中心"
    }
    resp = requests.post(f"{BASE_URL}/real/execute", json={"action": action})
    print(f"操作结果: {resp.json()}")

if __name__ == "__main__":
    test_real_control()