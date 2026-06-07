from utils import InitTool
from hardware import VideoStream, SimpleButton, ServoControl, Hx711, FeedMotor
from data import maoDB, BlockingBuffer
from data.time_queue import IncrementalBuffer
from service import AutoFeed, PetRecognizer
from web.app import App
from utils import InitTool
import threading
import time
from flask import request, Response
from datetime import datetime, timedelta
import json
class Manager:
    def __init__(self) -> None:
        self.init_tool = InitTool()
        
        # ========== 初始化硬件 ==========
        hardware = self.init_tool.init_all_hardware()
        self.hx711: Hx711 = hardware['hx711']
        self.camera: VideoStream = hardware['camera']
        self.button: SimpleButton = hardware['button']
        self.servo: ServoControl = hardware['servo']
        self.feed_motor: FeedMotor = hardware['feed_motor']
        
        # ========== 初始化数据层 ==========
        self.db: maoDB = self.init_tool.init_db()
        
        # ========== 初始化服务层 ==========
        services = self.init_tool.init_all_services()
        self.auto_feed: AutoFeed = services['auto_feed']
        self.pet_recognizer: PetRecognizer = services['pet_recognizer']
        
        # ========== 初始化Web ==========
        self.web: App = self.init_tool.init_web()
        
        # ========== 设置Web回调 ==========
        self._setup_web_callbacks()
        
        # ========== 设置硬件回调 ==========
        self._setup_hardware_callbacks()

        # ========== 设置自动投喂回调 ==========
        self.auto_feed.set_call_back(self._on_feed)

        # ========== 从数据库加载定时任务 ==========
        self._load_schedules_from_db()

        # ========== 内存存储必要数据 ======
        self.weight_history = IncrementalBuffer(10)
        self.log_history = IncrementalBuffer(50)

        self.new_log = {}
        self.daily_consumption = []
        self._init_eating_data()
                # SSE 客户端管理
        self.sse_clients = {}  # {client_id: {'weight_enabled': bool, 'last_log_id': int, 'last_event': time}}
        self.sse_lock = threading.Lock()
        

    def _init_eating_data(self):        
            records = self.db.get_all_eating_record()
            
            # 1. 从尾部开始选择50条（最近50条）
            recent_records = records[-50:] if len(records) > 50 else records
            for record in recent_records:
                self.log_history.append(record)
            
            # 2. 按天分类records，计算每天的进食总量
            daily_total = {}
            for record in records:
                begin_time = record.get('begin_time')
                if begin_time:
                    # 提取日期: "2024-01-15 08:00:00" -> "01-15" (月-日)
                    date_str = begin_time.split(' ')[0]  # "2024-01-15"
                    month_day = date_str[5:]  # "01-15" (去掉年份)
                    
                    # 计算消耗量
                    begin_weight = float(record.get('begin_weight', 0))
                    end_weight = float(record.get('end_weight', 0))
                    consume = begin_weight - end_weight if begin_weight >= end_weight else 0
                    
                    # 累加
                    daily_total[month_day] = daily_total.get(month_day, 0) + consume
            
            # 3. 转换为列表格式
            self.daily_consumption = [
                {'day': day, 'total': round(total, 1)}
                for day, total in sorted(daily_total.items())
            ]


    def _setup_web_callbacks(self):
        """设置Web路由回调"""
        self.web.set_callback('index', self._web_index)
        self.web.set_callback('video_stream', self._web_video_stream)
        self.web.set_callback('camera_open', self._web_camera_open)
        self.web.set_callback('camera_close', self._web_camera_close)
        self.web.set_callback('video_capture', self._web_video_capture)
        self.web.set_callback('servo_move', self._web_servo_move)
        self.web.set_callback('feed_motor', self._web_feed_motor)
        self.web.set_callback('enable_auto', self._web_enable_auto)
        self.web.set_callback('disable_auto', self._web_disable_auto)
        self.web.set_callback('add_schedule', self._web_add_schedule)
        self.web.set_callback('get_schedules', self._web_get_schedules)
        self.web.set_callback('remove_schedule', self._web_remove_schedule)
        self.web.set_callback('weight_start', self._web_weight_start)
        self.web.set_callback('weight_stop', self._web_weight_stop)
        self.web.set_callback('weight_get', self._web_weight_get)
        self.web.set_callback('eating_log_get', self._web_eating_log_get)
        self.web.set_callback('daily_consumption_get', self._web_daily_consumption_get)
        self.web.set_callback('sse_events', self._sse_events)
    def _setup_hardware_callbacks(self):
        """设置硬件回调"""
        # 按钮回调
        self.button.set_callback(self._on_feed)
        
        # 称重回调（如果有）
        if hasattr(self.hx711, 'set_callback'):
            self.hx711.set_callback(
                measured=self._on_weight_measured,
                excepted=self._on_weight_except,
                normalized=self._on_weight_normal
            )
    
    # ========== Web 回调实现 ==========
    def _web_index(self):
        from flask import render_template
        return render_template('index.html')
    
    def _web_video_stream(self):
        from flask import Response
        # 访问视频流时自动启动摄像头
        if not self.camera.running:
            self.camera.start(source='web')
        return Response(self.camera.generate(), 
                      mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def _web_camera_open(self):
        success = self.camera.start(source='web')
        return {"success": success}
    
    def _web_camera_close(self):
        self.camera.stop(source='web')
        # 检查是否还有其他客户端在看，如果没有再归位云台
        if self.camera.web_clients <= 0 and not self.camera.auto_active:
            self.servo.home()
        return {"success": True}
    
    def _web_video_capture(self):
        import time
        import os
        # 确保webphoto目录存在
        save_dir = "./webphoto"
        os.makedirs(save_dir, exist_ok=True)
        # 生成带时间戳的文件名
        filename = f"web_capture_{int(time.time())}.jpg"
        path = f"{save_dir}/{filename}"
        jpg = self.camera.capture_once(path)
        return {"success": jpg is not None, "path": path if jpg else None}
    
    def _web_servo_move(self, direction):
        if direction == "home":
            self.servo.home()
        else:
            self.servo.move(direction)
        return {"success": True, "direction": direction}
    
    def _web_feed_motor(self):
        self._on_feed()
        return {"success": True}
    
    def _web_enable_auto(self):
        self.auto_feed.on()
        return {"success": True}
    
    def _web_disable_auto(self):
        self.auto_feed.off()
        return {"success": True}
    
    def _web_add_schedule(self, data):
        hour = data.get('hour')
        minute = data.get('minute')
        if hour is not None and minute is not None:
            # 先添加到数据库
            if self.db.add_schedule(hour, minute):
                # 再添加到调度器
                self.auto_feed.add(hour, minute)
                print(f"已添加定时任务: {hour:02d}:{minute:02d}")
                return {"success": True}
            return {"success": False, "error": "schedule already exists"}
        return {"success": False, "error": "missing hour or minute"}
    
    def _web_get_schedules(self):
        schedules = self.db.get_all_schedules()
        return {"success": True, "schedules": schedules}
    
    def _web_remove_schedule(self, data):
        hour = data.get('hour')
        minute = data.get('minute')
        if hour is not None and minute is not None:
            # 先从数据库删除
            if self.db.remove_schedule(hour, minute):
                # 再从调度器删除
                self.auto_feed.remove(hour, minute)
                print(f"已删除定时任务: {hour:02d}:{minute:02d}")
                return {"success": True}
            return {"success": False, "error": "schedule not found"}
        return {"success": False}
    
    def _sse_events(self):
        """
        SSE 事件流
        
        前端参数：
        - client_id: 客户端唯一标识
        - last_log_id: 最后一条日志的ID
        - subscribe_weight: 是否订阅实时重量 (1/0)
        """
        client_id = request.args.get('client_id', default=None)
        last_log_id = request.args.get('last_log_id', type=int, default=-1)
        subscribe_weight = request.args.get('subscribe_weight', type=int, default=0)
        
        if not client_id:
            client_id = f"client_{int(time.time()*1000)}_{id(request)}"
        
        # 注册客户端
        with self.sse_lock:
            if client_id not in self.sse_clients:
                self.sse_clients[client_id] = {
                    'weight_enabled': subscribe_weight == 1,
                    'last_log_id': last_log_id,
                    'last_heartbeat': time.time(),
                    'created_at': datetime.now()
                }
            else:
                self.sse_clients[client_id]['weight_enabled'] = subscribe_weight == 1
                self.sse_clients[client_id]['last_log_id'] = last_log_id
                self.sse_clients[client_id]['last_heartbeat'] = time.time()
        
        print(f"SSE 客户端连接: {client_id}, 订阅重量: {subscribe_weight==1}, last_log_id: {last_log_id}")
        
        def generate():
            """生成器：持续推送事件"""
            try:
                last_check_time = time.time()
                
                while True:
                    current_time = time.time()
                    
                    # 更新心跳
                    with self.sse_lock:
                        if client_id in self.sse_clients:
                            self.sse_clients[client_id]['last_heartbeat'] = current_time
                    
                    # 1. 推送日志增量（所有客户端都推送）
                    with self.sse_lock:
                        current_last_id = self.sse_clients[client_id]['last_log_id']
                    
                    log_new = self.log_history.get_since(current_last_id)
                    if log_new:
                        for item_id, data in log_new:
                            # 格式化日志数据
                            log_data = {
                                'id': item_id,
                                'type': 'log',
                                'data': data
                            }
                            yield f"id: {item_id}\nevent: log\ndata: {json.dumps(log_data, ensure_ascii=False, default=str)}\n\n"
                            
                            # 更新 last_log_id
                            with self.sse_lock:
                                if client_id in self.sse_clients:
                                    self.sse_clients[client_id]['last_log_id'] = item_id
                    
                    # 2. 推送实时重量（只给订阅了重量的客户端）
                    with self.sse_lock:
                        weight_enabled = self.sse_clients.get(client_id, {}).get('weight_enabled', False)
                    
                    if weight_enabled:
                        current_weight = self.hx711.current_weight
                        weight_data = {
                            'type': 'weight',
                            'weight': current_weight,
                            'timestamp': datetime.now().isoformat()
                        }
                        yield f"event: weight\ndata: {json.dumps(weight_data, ensure_ascii=False)}\n\n"
                    
                    # 控制推送频率
                    time.sleep(0.3)
                    
            except GeneratorExit:
                # 客户端断开连接，清理
                with self.sse_lock:
                    if client_id in self.sse_clients:
                        # 记录断开但不立即删除，超时后自动清理
                        self.sse_clients[client_id]['last_heartbeat'] = 0
                        self.sse_clients[client_id]['weight_enabled'] = False
                print(f"SSE 客户端断开: {client_id}")
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*'
            }
        )
    
    def _web_weight_start(self):
        """客户端开启实时重量推送"""
        # 从请求中获取 client_id（通过 JSON body 或 query param）
        if request.is_json:
            data = request.get_json() or {}
            client_id = data.get('client_id')
        else:
            client_id = request.args.get('client_id')
        
        if not client_id:
            return {"success": False, "error": "client_id required"}
        
        with self.sse_lock:
            if client_id in self.sse_clients:
                self.sse_clients[client_id]['weight_enabled'] = True
                self.sse_clients[client_id]['last_heartbeat'] = time.time()
                print(f"客户端 {client_id} 开启实时重量推送")
                return {"success": True, "message": "weight subscription started"}
            else:
                # 客户端未连接，先创建占位
                self.sse_clients[client_id] = {
                    'weight_enabled': True,
                    'last_log_id': -1,
                    'last_heartbeat': time.time(),
                    'created_at': datetime.now()
                }
                print(f"客户端 {client_id} 预注册并开启重量推送")
                return {"success": True, "message": "client registered and weight subscription started"}
    
    def _web_weight_stop(self):
        """客户端关闭实时重量推送"""
        if request.is_json:
            data = request.get_json() or {}
            client_id = data.get('client_id')
        else:
            client_id = request.args.get('client_id')
        
        if not client_id:
            return {"success": False, "error": "client_id required"}
        
        with self.sse_lock:
            if client_id in self.sse_clients:
                self.sse_clients[client_id]['weight_enabled'] = False
                print(f"客户端 {client_id} 关闭实时重量推送")
                return {"success": True, "message": "weight subscription stopped"}
            else:
                return {"success": True, "message": "client not found"}
    
    def _web_weight_get(self):
        """获取当前重量（一次性）"""
        weight = self.hx711.current_weight
        return {"success": True, "weight": weight}
    
    def _web_eating_log_get(self):
        """获取日志（一次性，用于初始化）"""
        client_id = request.args.get('client_id')
        last_id = request.args.get('last_id', type=int, default=-1)
        
        if last_id >= 0:
            # 增量获取
            logs = self.log_history.get_since(last_id)
            records = [{'id': item_id, 'data': data} for item_id, data in logs]
        else:
            # 获取最近50条
            all_logs = self.log_history.get_since(-1)
            records = [{'id': item_id, 'data': data} for item_id, data in all_logs[-50:]]
        
        return {"success": True, "records": records}
    
    def _cleanup_inactive_clients(self):
        """清理不活跃的客户端（在后台线程中运行）"""
        while True:
            time.sleep(30)  # 每30秒检查一次
            current_time = time.time()
            with self.sse_lock:
                inactive = []
                for client_id, info in self.sse_clients.items():
                    # 超过60秒没有心跳的客户端视为断开
                    if current_time - info['last_heartbeat'] > 60:
                        inactive.append(client_id)
                
                for client_id in inactive:
                    del self.sse_clients[client_id]
                    print(f"清理不活跃客户端: {client_id}")
    
    def _web_daily_consumption_get(self):
        # 获取日消耗数据
        return {"success": True, "data": self.daily_consumption}
    
    # ========== 硬件回调实现 ==========        
    
    def _on_feed(self):
        """投喂回调（实体按钮/网页按钮/定时任务共用）"""
        print("开始投喂...")
        try:
            self.hx711.pause()
            self.feed_motor.feed()
            time.sleep(2)
            print("投喂完成")
        except Exception as e:
            print(f"投喂出错: {e}")
        finally:
            self.hx711.resume()

    '''"""投喂回调，先暂停异常检测，再放下食物，最后重启异常检测"""
        self.hx711.pause()
        self.feed_motor.feed()
        self.hx711.resume()'''
    
    def _load_schedules_from_db(self):
        """从数据库加载定时任务"""
        print("从数据库加载定时任务...")
        schedules = self.db.get_all_schedules()
        for s in schedules:
            self.auto_feed.add(s['hour'], s['minute'])
            print(f"  - 已加载: {s['hour']:02d}:{s['minute']:02d}")
        print(f"共加载 {len(schedules)} 个定时任务")
    
    def _on_weight_measured(self, weight , test_time):
        """重量测量回调，存入历史队列缓存"""
        print(f"当前重量: {weight}")
        self.weight_history.append((weight, test_time))
    
    def _on_weight_except(self, last_normal, last_normal_time):
        """重量异常回调：调整云台，启用摄像头拍摄，识别分析，回复云台"""
        print(f"重量异常，最后正常值: {last_normal}")
        
        # 1. 记录当前位置
        original_position = self.servo.get_position()
        print(f"📷 记录原位置: {original_position}")
        
        # 2. 归正云台
        self.servo.home()
        print("📷 云台已归正")
        
        # 3. 连拍3张照片
        images, img_paths = self.camera.capture_multiple(count=3, save_dir='./photos', prefix='exception')
        
        # 4. 识别分析
        if img_paths:
            result = self.pet_recognizer.recognize_multiple(img_paths)
            self.new_log['result'] = result['label'] if result else 'unknown'
        else:
            self.new_log['result'] = 'unknown'
        
        self.new_log['img_path'] = json.dumps(img_paths)
        self.new_log['begin_time'] = last_normal_time
        self.new_log['begin_weight'] = last_normal
        
        # 5. 回到原位置
        self.servo.set_position(original_position['horizontal'], original_position['vertical'])
        print(f"📷 云台已回到原位置: {original_position}")
    
    def _on_weight_normal(self, current_weight, current_time):
        """重量恢复正常回调"""
        if 'begin_time' in self.new_log and 'begin_weight' in self.new_log:
            self.new_log['end_time'] = current_time
            self.new_log['end_weight'] = current_weight
            self.log_history.append(self.new_log)
            print(self.new_log)
            self.db.insert_eating_records((self.new_log))
            self.new_log = {}
        else:
            print("跳过无效记录：缺少begin_time或begin_weight")
       
    
    # ========== 启动 ==========
    def run(self):
        """启动系统"""
        print("系统启动")
        # 启动自动投喂调度器
        # self.auto_feed.start()  # 如果有 start 方法
        # 启动 Web 服务
        self.web.run(host='0.0.0.0', port=5000)