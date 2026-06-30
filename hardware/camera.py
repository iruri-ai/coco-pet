# video_stream.py
from flask import Response
import cv2
import threading
import time
import os

class VideoStream:
    """视频流服务 - 支持多客户端"""
    
    def __init__(self, camera_id=0, width=640, height=480, fps=10):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        
        self.cap = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        
        # 多客户端支持
        self.web_clients = 0  # Web 端连接计数
        self.auto_active = False  # 自动检测是否正在使用
        self.client_lock = threading.Lock()
    
    def start(self, source='web'):
        """启动摄像头和采集线程
        
        Args:
            source: 'web' 表示 Web 端调用，'auto' 表示自动检测调用
        """
        with self.client_lock:
            if not self.running:
                # 摄像头还没启动，启动它
                self.cap = cv2.VideoCapture(self.camera_id)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                
                if not self.cap.isOpened():
                    return False
                
                self.running = True
                threading.Thread(target=self._capture_loop, daemon=True).start()
                print("📹 摄像头已启动")
            
            # 根据来源增加相应计数
            if source == 'web':
                self.web_clients += 1
                print(f"📹 Web 端连接，当前 Web 端连接数: {self.web_clients}")
            elif source == 'auto':
                self.auto_active = True
                print(f"📹 自动检测激活")
            
            return True
    
    def _capture_loop(self):
        """采集线程"""
        while self.running:
            ret, img = self.cap.read()
            if ret:
                with self.lock:                   
                    self.frame = img
            time.sleep(0.05)  # 降频，减少CPU
    
    def stop(self, source='web'):
        """停止（只有当没有客户端和自动检测时才真正停止摄像头）
        
        Args:
            source: 'web' 表示 Web 端调用，'auto' 表示自动检测调用
        """
        with self.client_lock:
            if source == 'web' and self.web_clients > 0:
                self.web_clients -= 1
                print(f"📹 Web 端断开，当前 Web 端连接数: {self.web_clients}")
            elif source == 'auto':
                self.auto_active = False
                print(f"📹 自动检测结束")
            
            # 只有当没有 Web 客户端且没有自动检测时才真正停止摄像头
            if self.web_clients <= 0 and not self.auto_active and self.running:
                self.running = False
                if self.cap:
                    self.cap.release()
                print("📹 摄像头已关闭")
    
    def get_frame_jpeg(self):
        """获取当前帧的JPEG数据"""
        with self.lock:
            if self.frame is None:
                return None
            ret, buffer = cv2.imencode('.jpg', self.frame)
            return buffer.tobytes() if ret else None
    
    def capture_once(self, save_path=None):
        """拍一张照（可选功能）"""
        jpg = self.get_frame_jpeg()
        if jpg and save_path:
            with open(save_path, 'wb') as f:
                f.write(jpg)
        return jpg
    
    def capture_multiple(self, count=3, save_dir=None, prefix='photo', delay=0.5):
        """
        连拍多张照片
        :param count: 拍摄张数
        :param save_dir: 保存目录
        :param prefix: 文件名前缀
        :param delay: 每张照片间隔（秒）
        :return: 图片数据列表和保存路径列表
        """
        images = []
        paths = []
        
        try:
            # 如果摄像头没启动，先启动它（使用 auto 来源）
            started_by_this_call = False
            if not self.running:
                print("📹 自动检测启动摄像头...")
                self.start(source='auto')
                started_by_this_call = True
                # 等待一会儿让摄像头预热
                time.sleep(2)
            
            # 确保保存目录存在
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir, exist_ok=True)
            
            for i in range(count):
                jpg = self.get_frame_jpeg()
                if jpg:
                    images.append(jpg)
                    
                    if save_dir:
                        timestamp = int(time.time() * 1000)
                        filename = f"{prefix}_{timestamp}_{i+1}.jpg"
                        save_path = f"{save_dir}/{filename}"
                        with open(save_path, 'wb') as f:
                            f.write(jpg)
                        paths.append(save_path)
                else:
                    print((self.frame is not None))
                    print(f"⚠️ 第 {i+1} 张照片获取失败")
                
                if i < count - 1 and delay > 0:
                    time.sleep(delay)
        
        finally:
            # 如果是由这个调用启动的，拍摄完后停止摄像头
            if started_by_this_call:
                print("📹 自动检测拍摄完成")
                self.stop(source='auto')
        
        return images, paths
    
    def generate(self):
        """生成视频流用于 Flask Response"""
        try:
            while True:
                frame = self.get_frame_jpeg()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.1)
        finally:
            # 客户端断开连接时，减少计数
            self.stop(source='web')


# 全局单例（方便Web模块直接导入使用）
_stream = None

def get_video_stream(**kwargs):
    """获取全局视频流实例"""
    global _stream
    if _stream is None:
        _stream = VideoStream(**kwargs)
    return _stream
