#!/usr/bin/env python3
"""
宠物投喂器 - 支持实体按钮和网页按钮
"""
from core.manager import Manager

if __name__ == "__main__":
    print("🚀 启动宠物投喂器...")
    
    # 创建管理器
    manager = Manager()
    
    
    # 启动 Web 服务
    manager.web.run(host='0.0.0.0', port=5000)
