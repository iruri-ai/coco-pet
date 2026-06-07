# video_stream.py
from flask import Response
import cv2
import threading
import time

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
        self.streaming_clients = 0
        self.client_lock = threading.Lock()
    
    def start(self):
        """启动摄像头和采集线程"""
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
            
            # 增加客户端计数
            self.streaming_clients += 1
            print(f"📹 客户端连接，当前连接数: {self.streaming_clients}")
            return True
    
    def _capture_loop(self):
        """采集线程"""
        while self.running:
            ret, img = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = img
            time.sleep(0.01)  # 降频，减少CPU
    
    def stop(self):
        """停止（只有当没有客户端时才真正停止摄像头）"""
        with self.client_lock:
            if self.streaming_clients > 0:
                self.streaming_clients -= 1
                print(f"📹 客户端断开，当前连接数: {self.streaming_clients}")
            
            # 只有当没有客户端时才真正停止摄像头
            if self.streaming_clients <= 0 and self.running:
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
            self.stop()


# 全局单例（方便Web模块直接导入使用）
_stream = None

def get_video_stream(**kwargs):
    """获取全局视频流实例"""
    global _stream
    if _stream is None:
        _stream = VideoStream(**kwargs)
    return _stream
