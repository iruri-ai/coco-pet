from collections import deque
from threading import Lock, Condition

class IncrementalBuffer:
    def __init__(self, maxlen=100) -> None:
        self.buffer = deque(maxlen=maxlen)
        self.lock = Lock()
        self.next_id = 0
    
    def append(self, data):
        with self.lock:
            self.buffer.append((self.next_id, data))
            self.next_id += 1
    
    def get_since(self, last_id):
        """返回所有 id > last_id 的数据"""
        with self.lock:
            # 从 buffer 尾部向前找
            result = []
            for item_id, data in self.buffer:
                if item_id > last_id:
                    result.append((item_id, data))
            return result
        

# 可选：支持阻塞等待
class BlockingBuffer(IncrementalBuffer):
    def __init__(self, maxlen=1000):
        super().__init__(maxlen)
        self.cond = Condition(self.lock)
    
    def append(self, data):
        with self.cond:
            super().append(data)
            self.cond.notify_all()  # 唤醒所有等待的读者
    
    def wait_for_new(self, last_id, timeout=None):
        with self.cond:
            # 先检查有没有新数据
            new = self.get_since(last_id)
            if new:
                return new
            # 没有就等待
            self.cond.wait(timeout)
            return self.get_since(last_id)