import socket
from pathlib import Path
from app.constants import DEFAULT_PORTA as PORTA_IMPRESSORA
from app.bootstrap import get_appdata_root


def _is_test_mode() -> bool:
    """Lê settings.txt e retorna True se impressora_teste=1."""
    settings_file = get_appdata_root() / "config" / "settings.txt"
    if settings_file.exists():
        content = settings_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.strip().lower().startswith("impressora_teste"):
                _, _, value = line.partition("=")
                return value.strip() == "1"
    return False


def enviar_para_impressora_ip(zpl: str, ip: str, porta: int = PORTA_IMPRESSORA, timeout: float = 1.0, client_ip: str = None) -> bool:
    # Detecta modo teste: settings.txt OU client_ip é localhost
    is_test_config = _is_test_mode()
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost") if client_ip else False
    is_test = is_test_config or is_localhost
    
    # Modo teste: simula envio sem conexão real
    if is_test:
        print(f"[MODO TESTE] Simulando envio de {len(zpl)} bytes para {ip}:{porta}")
        return True

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

