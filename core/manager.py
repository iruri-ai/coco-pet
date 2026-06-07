from utils import InitTool
from hardware import VideoStream, SimpleButton, ServoControl, Hx711, FeedMotor
from data import maoDB, BlockingBuffer
from service import AutoFeed, PetRecognizer
from web.app import App
from utils import InitTool

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
        self.weight_history = BlockingBuffer(10)
        self.log_history = BlockingBuffer(50)
        self.new_log = {}
        self.daily_consumption = []

    def _init_sub_module_data(self):
        # 初始化定时任务
        schedules = self.db.get_all_schedules()
        for schedule in schedules:
            # 假设 schedule 是字典，包含 hour, minute
            hour = schedule.get('hour')
            minute = schedule.get('minute')
            if hour is not None and minute is not None:
                self.auto_feed.add(hour, minute)
        
        # 初始化进食记录缓冲区
        self.weight_history: BlockingBuffer = BlockingBuffer(maxlen=10)
        self.log_history: BlockingBuffer = BlockingBuffer(maxlen=50)
        
        # 初始化每日进食量
        self.daily_consumption: list = []
        
        # 从数据库加载历史记录
        records = self.db.get_all_eating_record()
        if records:
            # 计算每日进食量
            self.daily_consumption = self._calculate_daily_consumption(records)
            
            # 将最近10条记录压入缓冲区
            for record in records[-10:]:
                self.log_history.append(record)

    def _calculate_daily_consumption(self, records):
        """
        计算每日进食量
        
        Args:
            records: 进食记录列表，每条记录包含 begin_time 和 consume
        
        Returns:
            list: [{'date': '2024-01-01', 'total': 125.5}, ...]
        """
        daily_total = {}
        
        for record in records:
            # 从 begin_time 提取日期
            begin_time = record.get('begin_time')
            if begin_time:
                date = begin_time.split(' ')[0]  # 取日期部分 YYYY-MM-DD
                consume = record.get('consume', 0)
                daily_total[date] = daily_total.get(date, 0) + consume
        
        # 转换为列表并排序
        result = [
            {'date': date, 'total': round(total, 1)}
            for date, total in sorted(daily_total.items())
        ]
        
        return result

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
            self.camera.start()
        return Response(self.camera.generate(), 
                      mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def _web_camera_open(self):
        success = self.camera.start()
        return {"success": success}
    
    def _web_camera_close(self):
        self.camera.stop()
        # 检查是否还有其他客户端在看，如果没有再归位云台
        if self.camera.streaming_clients <= 0:
            self.servo.home()
        return {"success": True}
    
    def _web_video_capture(self):
        import time
        path = f"capture_{int(time.time())}.jpg"
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
    
    def _web_weight_start(self):
        # 开始记录重量
        return {"success": True}
    
    def _web_weight_stop(self):
        return {"success": True}
    
    def _web_weight_get(self):
        weight = self.hx711.current_weight
        return {"success": True, "weight": weight}
    
    def _web_eating_log_get(self):
        records = self.db.get_all_eating_record()
        return {"success": True, "records": records}
    
    def _web_daily_consumption_get(self):
        # 获取日消耗数据
        return {"success": True, "data": {}}
    
    # ========== 硬件回调实现 ==========        
    
    def _on_feed(self):
        """投喂回调（实体按钮/网页按钮/定时任务共用）"""
        print("开始投喂...")
        try:
            self.feed_motor.feed()
            print("投喂完成")
        except Exception as e:
            print(f"投喂出错: {e}")

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
        
        self.new_log['resutl']
        self.new_log['img_path']
        self.new_log['begin_time'] = last_normal_time
        self.new_log['begin_weight'] = last_normal
    
    def _on_weight_normal(self, current_weight, current_time):
        """重量恢复正常回调"""
        self.new_log['end_time'] = current_time
        self.new_log['end_weight'] = current_weight
        self.log_history.append(self.new_log)
        self.new_log = {}
       
    
    # ========== 启动 ==========
    def run(self):
        """启动系统"""
        print("系统启动")
        # 启动自动投喂调度器
        # self.auto_feed.start()  # 如果有 start 方法
        # 启动 Web 服务
        self.web.run(host='0.0.0.0', port=5000)