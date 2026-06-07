from hardware import VideoStream, SimpleButton, ServoControl, Hx711, FeedMotor
from data import maoDB
from service import AutoFeed, PetRecognizer
from web.app import App
import json
import os

class InitTool:
    def __init__(self, config_path: str = None) -> None:
        # 如果没给路径，自动找同目录下的 config.json
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "config.json")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    # ========== Hardware 初始化 ==========
    def init_Hx711(self):
        cfg = self.config.get("Hx711", {})
        return Hx711(**cfg) if cfg else Hx711()
    
    def init_camera(self):
        """初始化摄像头"""
        cfg = self.config.get("camera", {})
        return VideoStream(**cfg) if cfg else VideoStream()
    
    def init_button(self):
        """初始化按钮"""
        cfg = self.config.get("button", {})
        return SimpleButton(**cfg) if cfg else SimpleButton()
    
    def init_servo(self):
        """初始化舵机"""
        cfg = self.config.get("servo", {})
        return ServoControl(**cfg) if cfg else ServoControl()
    
    def init_feed_motor(self):
        """初始化投食电机"""
        cfg = self.config.get("feed_motor", {})
        return FeedMotor(**cfg) if cfg else FeedMotor()
    
    def init_all_hardware(self):
        """初始化所有硬件"""
        return {
            'hx711': self.init_Hx711(),
            'camera': self.init_camera(),
            'button': self.init_button(),
            'servo': self.init_servo(),
            'feed_motor': self.init_feed_motor()
        }
    
    # ========== Data 初始化 ==========
    def init_db(self):
        """初始化数据库"""
        cfg = self.config.get("database", {})
        return maoDB(**cfg) if cfg else maoDB()
    
    # ========== Service 初始化 ==========
    def init_auto_feed(self, feed_callback=None):
        """初始化自动投喂服务"""
        cfg = self.config.get("auto_feed", {})
        if feed_callback:
            return AutoFeed(**cfg) if cfg else AutoFeed()
        return AutoFeed(**cfg) if cfg else AutoFeed()
    
    def init_pet_recognizer(self):
        """初始化宠物识别服务"""
        cfg = self.config.get("pet_recognizer", {})
        return PetRecognizer(**cfg) if cfg else PetRecognizer()
    
    def init_all_services(self):
        """初始化所有服务"""
        return {
            'auto_feed': self.init_auto_feed(),
            'pet_recognizer': self.init_pet_recognizer()
        }
    
    # ========== Web 初始化 ==========
    def init_web(self):
        """初始化Web应用"""
        cfg = self.config.get("web", {})
        return App(**cfg) if cfg else App()
    
    # ========== 全量初始化 ==========
    def init_all(self):
        """初始化所有模块"""
        return {
            'hardware': self.init_all_hardware(),
            'data': {
                'db': self.init_db()
            },
            'service': self.init_all_services(),
            'web': self.init_web()
        }