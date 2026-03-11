import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time

class BistekPrinterService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BistekPrinter"
    _svc_display_name_ = "BistekPrinter - Serviço de Impressão ZQ230"
    _svc_description_ = "Gerencia as impressões de etiquetas na rede para a loja. (Flask/Waitress)"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False

    def SvcDoRun(self):
        # Atraso para garantir que a rede subiu caso inicializacao automatica
        time.sleep(2)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # Configurar ambiente de execucao (paths)
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        sys.path.insert(0, base_dir)

        # Importar a aplicacao Flask via Waitress
        try:
            from app.__main__ import app
            from waitress import serve
            
            # Rodar o servidor waitress em background non-blocking 
            # não vai dar certo direto porque o waitress block.
            # Vamos rodar em uma thread separada e usar a thread principal
            # do servico para monitorar o sinal de Stop.
            
            import threading
            def run_server():
                serve(app, host="0.0.0.0", port=8000)
                
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Manter o servico vivo enquanto nao receber sinal de Stop
            while self.is_alive:
                win32event.WaitForSingleObject(self.hWaitStop, 5000)
                
        except Exception as e:
            import traceback
            servicemanager.LogErrorMsg(f"Erro ao iniciar BistekPrinter Service: {str(e)}\n{traceback.format_exc()}")
            self.SvcStop()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(BistekPrinterService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(BistekPrinterService)
