from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

class FeedMotor:
    """投喂舵机控制类"""
    
    def __init__(self, 
                 feed_servo_pin: int = 17,
                 feed_duration: float = 1.0,
                 feed_angle: float = 0.5,
                 min_pulse: float = 0.5,
                 max_pulse: float = 2.5):
        """
        初始化投喂电机
        
        Args:
            feed_servo_pin: 舵机GPIO引脚
            feed_duration: 投喂持续时间（秒）
            feed_angle: 投喂角度（0-1之间，0.5约45度）
            min_pulse: 最小脉冲宽度(ms)
            max_pulse: 最大脉冲宽度(ms)
        """
        self.feed_duration = feed_duration
        self.feed_angle = feed_angle
        
        factory = PiGPIOFactory()
        self.feed_servo = Servo(
            feed_servo_pin,
            pin_factory=factory,
            min_pulse_width=min_pulse/1000,
            max_pulse_width=max_pulse/1000
        )
    
    def feed(self):
        """执行投喂"""
        self.feed_servo.value = self.feed_angle
        sleep(self.feed_duration)
        self.feed_servo.value = 0

    
    def stop(self):
        """停止舵机"""
        self.feed_servo.value = 0