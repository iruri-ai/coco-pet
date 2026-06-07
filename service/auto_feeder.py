# auto_feed.py
from apscheduler.schedulers.background import BackgroundScheduler

class AutoFeed:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs = []
        self.enabled = False
        self.feed_callback = None
        self.scheduler.start()
    
    def _on_timer(self):
        if self.enabled and self.feed_callback:
            self.feed_callback()
    
    def set_call_back(self, back):
        self.feed_callback = back

    def add(self, hour, minute):
        job_id = f"{hour}_{minute}"
        if job_id not in self.jobs:
            self.scheduler.add_job(self._on_timer, 'cron', hour=hour, minute=minute, id=job_id)
            self.jobs.append(job_id)
    
    def remove(self, hour, minute):
        job_id = f"{hour}_{minute}"
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            self.jobs.remove(job_id)
    
    def get_all(self):
        """返回所有定时任务，格式为 [{'hour': h, 'minute': m}, ...]"""
        schedules = []
        for job_id in self.jobs:
            hour, minute = map(int, job_id.split('_'))
            schedules.append({'hour': hour, 'minute': minute})
        return schedules
    
    def on(self):
        self.enabled = True
    
    def off(self):
        self.enabled = False
    
    def status(self):
        return self.enabled
    
    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()