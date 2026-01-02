from datetime import datetime
from uuid import uuid4

class Job:
    def __init__(self, printer_ip, zpl, loja):
        self.job_id = str(uuid4())
        self.printer_ip = printer_ip
        self.zpl = zpl
        self.loja = loja
        self.status = "queued"
        self.created_at = datetime.utcnow()
        self.finished_at = None

    def mark_success(self):
        self.status = "success"
        self.finished_at = datetime.utcnow()

    def mark_failed(self):
        self.status = "failed"
        self.finished_at = datetime.utcnow()