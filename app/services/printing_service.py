import socket
from ..constants import DEFAULT_PORTA as PORTA_IMPRESSORA

def enviar_para_impressora_ip(zpl: str, ip: str, porta: int = PORTA_IMPRESSORA, timeout: float = 1.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, porta))
            s.sendall(zpl.encode('latin1'))
        return True
    except socket.timeout:
        print(f"Timeout após {timeout}s ao conectar em {ip}:{porta}")
        return False
    except Exception as e:
        print("Erro ao enviar ZPL por IP:", e)
        return False
