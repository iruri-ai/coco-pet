from flask import Flask, jsonify, request

class App:
    def __init__(self) -> None:
        self.app = Flask(
            __name__,
            template_folder="templates"
        )
        self.routes = {}
        self.set_route()
    
    def set_route(self):
        """注册所有路由"""
        
        @self.app.route('/')
        def index():
            return self._call_handler('index')
        
        @self.app.route('/api/video/video-stream')
        def video_stream():
            return self._call_handler('video_stream')
        
        @self.app.route('/hardware/camera/open', methods=['POST'])
        def camera_open():
            return self._call_handler('camera_open')
        
        @self.app.route('/hardware/camera/close', methods=['POST'])
        def camera_close():
            return self._call_handler('camera_close')
        
        @self.app.route('/api/video/capture', methods=['POST'])
        def video_capture():
            return self._call_handler('video_capture')
        
        @self.app.route('/hardware/servo/move/<direction>', methods=['POST'])
        def servo_move(direction):
            return self._call_handler('servo_move', direction=direction)
        
        @self.app.route('/hardware/feed-motor/feed', methods=['POST'])
        def feed_motor():
            return self._call_handler('feed_motor')
        
        @self.app.route('/api/auto-feeder/enable-auto', methods=['POST'])
        def enable_auto():
            return self._call_handler('enable_auto')
        
        @self.app.route('/api/auto-feeder/disable-auto', methods=['POST'])
        def disable_auto():
            return self._call_handler('disable_auto')
        
        @self.app.route('/api/auto-feeder/add', methods=['POST'])
        def add_schedule():
            data = request.get_json() or {}
            return self._call_handler('add_schedule', data=data)
        
        @self.app.route('/api/auto-feeder/get', methods=['GET', 'POST'])
        def get_schedules():
            return self._call_handler('get_schedules')
        
        @self.app.route('/api/auto-feeder/remove', methods=['POST'])
        def remove_schedule():
            data = request.get_json() or {}
            return self._call_handler('remove_schedule', data=data)
        
        @self.app.route('/api/weight-table/start', methods=['POST'])
        def weight_start():
            return self._call_handler('weight_start')
        
        @self.app.route('/api/weight-table/stop', methods=['POST'])
        def weight_stop():
            return self._call_handler('weight_stop')
        
        @self.app.route('/api/weight-table/get', methods=['GET', 'POST'])
        def weight_get():
            return self._call_handler('weight_get')
        
        @self.app.route('/api/eating-log/get', methods=['GET', 'POST'])
        def eating_log_get():
            return self._call_handler('eating_log_get')
        
        @self.app.route('/api/daily-consumption/get', methods=['GET', 'POST'])
        def daily_consumption_get():
            return self._call_handler('daily_consumption_get')
        @self.app.route('/api/events')
        def events():
            """SSE 事件流"""
            return self._call_handler('sse_events')
    def _call_handler(self, handler_name, **kwargs):
        """调用已注册的回调函数"""
        handler = self.routes.get(handler_name)
        if handler:
            result = handler(**kwargs)
            if isinstance(result, dict):
                return jsonify(result)
            return result
        return jsonify({"error": "handler not found"}), 404
    
    def set_callback(self, route_name, callback):
        """
        设置路由回调
        
        Args:
            route_name: 路由名称（见下方列表）
            callback: 回调函数
        """
        self.routes[route_name] = callback
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """启动Flask应用"""
        self.app.run(host=host, port=port, debug=debug)
