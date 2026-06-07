# button.py
from gpiozero import Button

class SimpleButton:
    """极简按钮类"""
    
    def __init__(self, pin=25, pull_up=False, bounce_time=0.1):
        self.pin = pin
        self._callback = None
        
        # 创建按钮
        self._button = Button(
            pin,
            pull_up=None if pull_up else False,  # 简化：默认上拉电阻
            bounce_time=bounce_time
        )
        
        # 绑定内部处理
        self._button.when_pressed = self._on_press
    
    def _on_press(self):
        """按下时调用"""
        if self._callback:
            self._callback()
    
    def set_callback(self, callback):
        """设置回调函数"""
        self._callback = callback
    
    def close(self):
        """清理资源"""
        self._button.close()