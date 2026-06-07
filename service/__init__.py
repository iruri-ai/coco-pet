# service/__init__.py
"""
硬件模块包
统一导出各个硬件控制类
"""

from .auto_feeder import AutoFeed
from .recognizer import PetRecognizer

__all__ = [
    'AutoFeed',
    'PetRecognizer'
]