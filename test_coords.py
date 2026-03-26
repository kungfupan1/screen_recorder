# -*- coding: utf-8 -*-
"""
测试脚本 - 验证坐标系统
"""
import mss
import cv2
import numpy as np
import time

def test_coordinates():
    """测试坐标系统"""
    with mss.mss() as sct:
        print("=" * 50)
        print("显示器信息:")
        print("=" * 50)

        for i, mon in enumerate(sct.monitors):
            print("monitors[{}]: {}x{} at ({}, {})".format(
                i, mon['width'], mon['height'], mon['left'], mon['top']))

        print("\n" + "=" * 50)
        print("测试截图:")
        print("=" * 50)

        # 测试区域截图
        test_regions = [
            {"name": "虚拟桌面", "region": sct.monitors[0]},
            {"name": "主显示器", "region": sct.monitors[1]},
        ]

        # 询问用户要测试的区域
        print("\n请输入要测试的区域坐标 (格式: x y width height)")
        print("直接回车测试主显示器")
        user_input = input("> ").strip()

        if user_input:
            parts = user_input.split()
            if len(parts) == 4:
                x, y, w, h = map(int, parts)
                test_regions.append({
                    "name": "用户区域",
                    "region": {"left": x, "top": y, "width": w, "height": h}
                })

        for test in test_regions:
            region = test["region"]
            print("\n截图: {} - left={}, top={}, width={}, height={}".format(
                test["name"], region['left'], region['top'], region['width'], region['height']))

            screenshot = sct.grab(region)
            img = np.array(screenshot)[:, :, :3]

            # 显示截图
            cv2.imshow(test["name"], img)
            print("按任意键继续...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

if __name__ == "__main__":
    test_coordinates()