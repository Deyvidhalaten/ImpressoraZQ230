import uuid, time
from flask import g, has_request_context

class RequestTrace:
    def __init__(self, action: str):
        self.id = str(uuid.uuid4())
        self.action = action
        self.start = time.time()
        self.events = []

    def add(self, event: str, **meta):
        self.events.append({
            "t": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event": event,
            **meta
        })

    def finish(self, status="ok"):
        self.end = time.time()
        self.status = status
        self.duration = round(self.end - self.start, 3)
        return {
            "trace_id": self.id,
            "action": self.action,
            "duration": self.duration,
            "status": status,
            "events": self.events
        }

def start_trace(action: str) -> RequestTrace:
    """
    Cria um novo trace para a requisição corrente
    """
    if has_request_context():
        g.trace = RequestTrace(action)
        return g.trace
    # fallback se por algum motivo não houver contexto flask
    return RequestTrace(action)

def get_trace():
    """
    Retorna o trace atual da requisição.
    """
    if has_request_context() and hasattr(g, "trace"):
        return g.trace
    return None
