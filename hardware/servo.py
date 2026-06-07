# servo_control.py
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Servo

class ServoControl:
    """极简舵机控制类"""
    
    def __init__(self, 
                 horizontal_pin=24, 
                 vertical_pin=23,
                 step=0.1,
                 min_pulse=0.5/1000,
                 max_pulse=2.5/1000):
        """
        初始化舵机
        
        Args:
            horizontal_pin: 水平舵机GPIO引脚
            vertical_pin: 垂直舵机GPIO引脚
            step: 每次移动的步长（0-1之间）
            min_pulse: 最小脉冲宽度
            max_pulse: 最大脉冲宽度
        """
        self.horizontal_pin = horizontal_pin
        self.vertical_pin = vertical_pin
        self.step = step
        
        # 创建GPIO工厂
        factory = PiGPIOFactory()
        
        # 初始化舵机
        self.servo_h = Servo(
            horizontal_pin,
            pin_factory=factory,
            min_pulse_width=min_pulse,
            max_pulse_width=max_pulse
        )
        
        self.servo_v = Servo(
            vertical_pin,
            pin_factory=factory,
            min_pulse_width=min_pulse,
            max_pulse_width=max_pulse
        )
        
        # 当前位置（范围 -1 到 1）
        self.current_h = 0.0
        self.current_v = 0.0
        
        # 设置初始位置
        self.servo_h.value = self.current_h
        self.servo_v.value = self.current_v
    
    def set_position(self, horizontal, vertical):
        """设置指定位置"""
        self.current_h = max(-1, min(1, horizontal))
        self.current_v = max(-1, min(1, vertical))
        self.servo_h.value = self.current_h
        self.servo_v.value = self.current_v
    
    def move(self, direction):
        """
        移动舵机
        
        Args:
            direction: 'up', 'down', 'left', 'right'
        
        Returns:
            bool: 是否成功移动
        """
        if direction == "up":
            new_v = max(-1, self.current_v - self.step)
            if new_v != self.current_v:
                self.current_v = new_v
                self.servo_v.value = self.current_v
                return True
        
        elif direction == "down":
            new_v = min(1, self.current_v + self.step)
            if new_v != self.current_v:
                self.current_v = new_v
                self.servo_v.value = self.current_v
                return True
        
        elif direction == "left":
            new_h = min(1, self.current_h + self.step)
            if new_h != self.current_h:
                self.current_h = new_h
                self.servo_h.value = self.current_h
                return True
        
        elif direction == "right":
            new_h = max(-1, self.current_h - self.step)
            if new_h != self.current_h:
                self.current_h = new_h
                self.servo_h.value = self.current_h
                return True
        
        return False
    
    def get_position(self):
        """获取当前位置"""
        return {
            'horizontal': self.current_h,
            'vertical': self.current_v
        }
    
    def center(self):
        """归中"""
        self.current_h = 0.0
        self.current_v = 0.0
        self.servo_h.value = self.current_h
        self.servo_v.value = self.current_v
    
    def home(self):
        """归位（同center）"""
        self.center()
    
    def close(self):
        """清理资源"""
        self.servo_h.close()
        self.servo_v.close()
    
    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except:
            pass