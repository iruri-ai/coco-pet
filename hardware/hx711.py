# hx711.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import RPi.GPIO as GPIO
import time
from datetime import datetime
from collections import deque
from typing import Optional, Callable, Dict, List, Tuple


class Hx711:
    def __init__(self, 
                 sck_pin: int = 40,
                 dt_pin: int = 38, 
                 reference_unit: float = 413,
                 tare_offset: int = -139388,
                 garmmar: int = 2,
                 expect_times: int = 2,
                 normal_times: int = 3,
                 measure_interval: float = 2.0,
                ):
        
        # 基础参数
        self.SCK = sck_pin 
        self.DT = dt_pin 
        self.reference_unit = reference_unit 
        self.tare_offset = tare_offset
        self.current_weight: float = 0.0

        # 异常检测参数
        self.garmmar = garmmar
        self.expect_times = expect_times
        self.expect_happen_times = 0
        self.normal_times = normal_times
        self.normal_happen_times = 0
        self.measure_interval = measure_interval
        self._is_in_anomaly = False 
        self.last_normal = 0
        self.last_normal_time = datetime.now()

        # 状态变量
        self.gpio_initialized = False
        self.scheduler = None
        self._on_measure = None
        self._on_except = None
        self._on_normal = None
        
        # 暂停控制
        self._paused = False
        self.admit = False  # 是否允许测量，外部控制

        # 初始化硬件
        self.setup()
        self._start_scheduler()

    def set_callback(self, measured, excepted, normalized):
        self._on_measure = measured
        self._on_except = excepted
        self._on_normal = normalized

    def _start_scheduler(self) -> bool:
        """启动定时器"""
        if self.scheduler is not None:
            return False       
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self._auto_measure,
            trigger=IntervalTrigger(seconds=self.measure_interval),
            misfire_grace_time=1,
            coalesce=True,
            max_instances=1
        )
        self.scheduler.start()
        return True
    
    def pause(self):
        """
        暂停测量
        清空异常检测参数，重置计数
        """
        self._paused = True
        # 清空异常检测参数
        self.expect_happen_times = 0
        self.normal_happen_times = 0
        self._is_in_anomaly = False
        print("Hx711 已暂停，异常计数已重置")
    
    def resume(self):
        """
        恢复测量
        """
        self._paused = False
        self.admit = True  # 恢复后允许测量
        print("Hx711 已恢复")
    
    def is_paused(self):
        """检查是否暂停"""
        return self._paused

    def __del__(self):
        try:
            if hasattr(self, 'scheduler') and self.scheduler is not None:
                try:
                    if self.scheduler.running:
                        self.scheduler.shutdown(wait=False)
                except:
                    pass
        except:
            pass
        
        try:
            if self.gpio_initialized:
                GPIO.cleanup()
                self.gpio_initialized = False
        except:
            pass
    
    def setup(self):
        if self.gpio_initialized:
            return
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.SCK, GPIO.OUT)
        GPIO.setup(self.DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.output(self.SCK, GPIO.LOW)
        self.gpio_initialized = True

    def _read_raw_value(self) -> int:
        if not self.gpio_initialized:
            self.setup()
            
        timeout = 0.1
        start_time = time.time()
        while GPIO.input(self.DT):
            time.sleep(0.001)
            if time.time() - start_time > timeout:
                raise TimeoutError("传感器数据读取超时")
        
        value = 0
        for _ in range(24):
            GPIO.output(self.SCK, GPIO.HIGH)
            for _ in range(5):
                pass
            value = (value << 1) | GPIO.input(self.DT)
            GPIO.output(self.SCK, GPIO.LOW)
            for _ in range(5):
                pass

        GPIO.output(self.SCK, GPIO.HIGH)
        for _ in range(5):
            pass
        GPIO.output(self.SCK, GPIO.LOW)
        
        if value & 0x800000:
            value = value - 0x1000000
        return value
    
    def _read_weight_once(self) -> float:
        """单次测量，返回重量"""       
        raw_value = self._read_raw_value()
        weight = (raw_value - self.tare_offset) / self.reference_unit
        weight = max(0.0, weight)  
        # print(raw_value, weight, self.tare_offset, self.reference_unit)
        if self._on_measure:
            self._on_measure(weight, datetime.now()) 
        print(weight)     
        return weight
        
    def _auto_measure(self):
        """检测"""
        # 如果暂停，只读取重量但不检测异常
        if self._paused:
            new_weight = self._read_weight_once()
            self.current_weight = new_weight
            return
        if self.admit:
            self.last_normal = self.current_weight
            self.last_normal_time = datetime.now()
            self.admit = False  

        new_weight = self._read_weight_once()
        # 本次是否变化过大
        if abs(self.current_weight - new_weight) > self.garmmar:
            
            self.expect_happen_times += 1
            self.normal_happen_times = 0
            # 是否进入异常
            if not self._is_in_anomaly and self.expect_times <= self.expect_happen_times:
                self._is_in_anomaly = True
                print("excpet")
                if self._on_except:
                    self._on_except(self.last_normal, self.last_normal_time)
        else:
            
            self.last_normal = new_weight
            self.last_normal_time = datetime.now()
            self.normal_happen_times += 1
            self.expect_happen_times = 0
            if self._is_in_anomaly and self.normal_happen_times >= self.normal_times:
                self._is_in_anomaly = False
                print("normal")
                if self._on_normal:
                    self._on_normal(self.last_normal, self.last_normal_time)
        self.current_weight = new_weight