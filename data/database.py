import sqlite3
from typing import List, Dict, Optional

class maoDB:
    """猫粮数据库：吃饭事件记录 + 投喂时间表"""
    
    def __init__(self, db_path: str = "eating_records.db"):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """初始化表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 表1：吃饭事件记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eating_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result TEXT,
                img_path TEXT,
                begin_time TEXT NOT NULL,
                begin_weight REAL NOT NULL,
                end_time TEXT,
                end_weight REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 表2：投喂时间表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeding_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                UNIQUE(hour, minute)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== 表1：吃饭事件记录 ====================
    def get_all_eating_record(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM eating_records 
                WHERE begin_weight > end_weight
                ORDER BY begin_time
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def insert_eating_records(self, records):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT begin_time FROM eating_records")
            existing_times = {row[0] for row in cursor.fetchall()}
            inserted = 0
            skipped = 0
            
            # 兼容：如果是单个字典，转成列表
            if isinstance(records, dict):
                records = [records]
            
            for record in records:
                if record.get('begin_time') in existing_times:
                    skipped += 1
                    continue
                cursor.execute("""
                    INSERT INTO eating_records 
                    (result, img_path, begin_time, begin_weight, end_time, end_weight)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    record.get('result'),
                    record.get('img_path'),
                    record.get('begin_time'),
                    record.get('begin_weight'),
                    record.get('end_time'),      # 注意顺序
                    record.get('end_weight')
                ))
                inserted += 1
            conn.commit()
            
            return {'inserted': inserted, 'skipped': skipped}  
    
    # ==================== 表2：投喂时间表 ====================
    def get_all_schedules(self):
        """获取所有定时任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT hour, minute FROM feeding_schedule ORDER BY hour, minute")
            return [dict(row) for row in cursor.fetchall()]
    
    def add_schedule(self, hour: int, minute: int):
        """添加定时任务"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO feeding_schedule (hour, minute) VALUES (?, ?)", 
                             (hour, minute))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_schedule(self, hour: int, minute: int):
        """删除定时任务"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM feeding_schedule WHERE hour = ? AND minute = ?", 
                         (hour, minute))
            conn.commit()
            return cursor.rowcount > 0

