# 智能宠物喂食与行为监测系统

一个基于树莓派的智能宠物喂食系统，支持自动定时喂食、手动控制、实时视频监控、重量检测和行为分析。

## 功能特性

- 🤖 **自动喂食**：定时定量自动投喂宠物食物
- 🎮 **手动控制**：支持实体按钮和Web界面操作
- 📷 **实时监控**：集成摄像头，支持远程查看宠物状态
- ⚖️ **重量检测**：使用HX711传感器精确测量食物重量
- 🔍 **AI识别**：使用MobileNet进行宠物行为分析
- 🌐 **Web界面**：友好的网页管理界面，支持远程操作
- 📊 **数据记录**：记录进食数据，生成消费统计
- 🔧 **模块化设计**：核心、硬件、服务、Web等模块分离
- 🚨 **安全机制**：超时保护、异常检测、应急停止

## 项目结构

```
coco-pet/
├── core/                    # 核心控制模块
│   ├── __init__.py
│   ├── manager.py          # 主管理器
│   └── manager.pyc
├── data/                    # 数据存储模块
│   ├── __init__.py
│   ├── database.py         # 数据库操作
│   └── time_queue.py       # 定时任务队列
├── hardware/                # 硬件驱动模块
│   ├── __init__.py
│   ├── button.py           # 按钮控制
│   ├── camera.py           # 摄像头控制
│   ├── feed_motor.py       # 喂食电机控制
│   ├── hx711.py            # HX711重量传感器
│   └── servo.py            # 舵机控制
├── service/                 # 服务模块
│   ├── __init__.py
│   ├── auto_feeder.py      # 自动喂食服务
│   └── recognizer.py       # 识别服务
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── config.json         # 配置文件
│   └── config.py           # 配置管理
├── web/                     # Web服务模块
│   ├── __init__.py
│   ├── app.py              # Flask应用
│   ├── routes.py           # 路由定义
│   └── templates/          # 网页模板
├── webphoto/                # 摄像头抓拍图片存储
├── photos/                  # 照片存储目录
├── main.py                  # 主程序入口
├── eating_records.db        # 进食记录数据库
├── mobilenet_v1_1.0_224_quant.tflite  # AI模型
├── labels_mobilenet_quant_v1_224.txt  # AI标签
└── README.md                # 项目说明文档
```

## 硬件要求

- 树莓派（推荐4B或更高版本）
- HX711重量传感器
- 舵机（用于控制喂食装置）
- 喂食电机
- 实体按钮
- 摄像头（USB或CSI接口）
- 电源模块
- 电子秤或称重装置

## 安装与配置

1. 克隆项目到本地：
   ```bash
   cd coco-pet
   ```

2. 安装依赖：
   ```bash
   pip install flask opencv-python numpy RPi.GPIO apscheduler
   ```

3. 配置系统：
   
   编辑 `utils/config.json` 文件，根据硬件连接修改配置参数。主要配置项包括：
   
   - **HX711**：重量传感器配置（引脚、校准参数、自动去皮等）
   - **camera**：摄像头配置（分辨率、帧率、自动归位等）
   - **button**：按钮配置（引脚、防抖时间等）
   - **servo**：舵机配置（引脚、脉冲范围、移动速度等）
   - **feed_motor**：喂食电机配置
   - **auto_feeder**：自动喂食器配置（时区、检查间隔等）
   - **web**：Web服务配置（地址、端口、密钥等）
   - **database**：数据库配置（路径、备份等）

4. 运行主程序：
   ```bash
   python main.py
   ```

## 使用说明

### 启动系统

```bash
python main.py
```

系统启动后，Web服务将在 `http://0.0.0.0:5000` 上运行。

### Web界面

打开浏览器访问树莓派IP地址的5000端口，可以：

- 查看实时摄像头画面
- 手动触发喂食
- 查看进食记录
- 设置定时喂食任务
- 配置系统参数
- 查看日消费统计

### 实体按钮

按下硬件按钮可以直接触发喂食操作。支持长按和短按功能（根据配置）。

## 配置说明

主要配置项位于 `utils/config.json`：

### HX711 重量传感器
```json
{
  "sck_pin": 40,
  "dt_pin": 38,
  "reference_unit": 408,
  "tare_offset": -13938,
  "gamma": 2,
  "expect_times": 2,
  "normal_times": 3,
  "measure_interval": 2.0,
  "auto_tare": true,
  "sample_count": 10,
  "stabilization_time": 2
}
```

### Camera 摄像头
```json
{
  "camera_id": 0,
  "width": 640,
  "height": 480,
  "fps": 10,
  "auto_orient": true,
  "save_dir": "./webphoto",
  "capture_count": 3,
  "capture_interval": 0.5,
  "source": "web"
}
```

### Web服务
```json
{
  "host": "0.0.0.0",
  "port": 5000,
  "debug": false,
  "secret_key": "coco-pet-secret-key-change-in-production",
  "upload_folder": "./webphoto",
  "max_upload_size": 16777216,
  "session_timeout": 3600,
  "cors_enabled": true
}
```





## 技术栈

- **后端**：Python + Flask
- **硬件控制**：RPi.GPIO
- **图像处理**：OpenCV
- **数据库**：SQLite
- **AI识别**：MobileNet + TensorFlow Lite
- **任务调度**：APScheduler
- **实时通信**：SSE (Server-Sent Events)

## API接口

系统提供以下主要API接口：

- `GET /` - 主页
- `GET /api/video-stream` - 视频流
- `POST /hardware/camera/open` - 开启摄像头
- `POST /hardware/camera/close` - 关闭摄像头
- `POST /api/video/capture` - 拍照
- `POST /hardware/servo/move/<direction>` - 舵机移动
- `POST /hardware/feed-motor/feed` - 喂食电机控制
- `POST /api/auto-feeder/enable-auto` - 启用自动喂食
- `POST /api/auto-feeder/disable-auto` - 禁用自动喂食
- `POST /api/auto-feeder/add` - 添加定时任务
- `GET /api/auto-feeder/get` - 获取定时任务
- `POST /api/auto-feeder/remove` - 删除定时任务
- `POST /api/weight-table/start` - 开启重量推送
- `POST /api/weight-table/stop` - 停止重量推送
- `GET /api/weight-table/get` - 获取当前重量
- `GET /api/eating-log/get` - 获取进食记录
- `GET /api/daily-consumption/get` - 获取日消费数据
- `GET /api/events` - SSE事件流

## 注意事项

- 确保硬件连接正确，避免短路
- 定期校准重量传感器
- 注意喂食器的清洁和维护
- 建议使用UPS电源防止意外断电
- 定期检查数据库备份
- 在生产环境中修改默认密钥
- 确保摄像头和舵机运行时不被阻挡

## 故障排除

### 重量传感器读数异常
- 检查HX711连接是否正确
- 重新校准传感器
- 检查是否有物体干扰

### 摄像头无法启动
- 检查摄像头是否被其他程序占用
- 确认摄像头ID正确
- 查看日志获取详细错误信息

### Web界面无法访问
- 确认树莓派IP地址正确
- 检查防火墙设置
- 确认Flask服务正常运行

### 喂食器不工作
- 检查电机连接
- 确认舵机归位正常
- 查看是否有食物堵塞


## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的自动喂食功能
- 集成摄像头监控
- 实现Web控制界面
- 添加重量检测
- 支持AI宠物识别
