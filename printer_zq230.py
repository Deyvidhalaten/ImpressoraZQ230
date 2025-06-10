# printer_zq230.py
import socket

class ZQ230Printer:
    """
    Classe para conexão e impressão na Zebra ZQ230 via socket TCP.
    """
    def __init__(self, host: str, port: int = 9100, timeout: float = 5.0):
        self.host    = host
        self.port    = port
        self.timeout = timeout

    def print_label(self, zpl: str) -> None:
        """
        Envia o comando ZPL puro para a impressora via TCP.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            sock.sendall(zpl.encode('utf-8'))