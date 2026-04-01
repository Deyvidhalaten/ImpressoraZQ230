import os
import subprocess
from pathlib import Path
from cryptography.fernet import Fernet

class SecurityService:
    def __init__(self):
        # Movido do C:\ProgramData para LOCALAPPDATA para rodar 100% sem Admin (UAC Block)
        self.vault_dir = Path(os.environ.get('LOCALAPPDATA', 'C:/')) / "BistekPrinter" / "Vault"
        self.key_path = self.vault_dir / "secret.key"
        self.env_path = Path(os.environ.get('LOCALAPPDATA', 'C:/')) / "BistekPrinter" / ".env"
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.env_path.parent.mkdir(parents=True, exist_ok=True)

        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)

    def _get_or_create_key(self):
        if not self.key_path.exists():
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as f:
                f.write(key)
            return key
        
        with open(self.key_path, "rb") as f:
            return f.read()

    def lock_vault_folder(self):
        # A pasta LOCALAPPDATA já é bloqueada nativamente pelo Windows para outros usuários.
        # Desativamos o icacls pois ele dispara o alerta de necessidade de Administrador na instalação corporativa.
        return True

    def encrypt_data(self, plain_text: str) -> str:
        if not plain_text: return ""
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt_data(self, cipher_text: str) -> str:
        if not cipher_text: return ""
        try:
            return self.fernet.decrypt(cipher_text.encode()).decode()
        except Exception:
            return None

    def update_env_file(self, key: str, value: str):
        lines = []
        if self.env_path.exists():
            with open(self.env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"{key}={value}\n")

        with open(self.env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def instalar_certificado_no_windows(self, cert_path: Path):
        """Força o Windows a confiar no certificado gerado."""
        if not cert_path.exists():
            print(f"⚠️ Certificado não encontrado em: {cert_path}")
            return False
        try:
          # O comando 'certutil' adiciona o certificado às Raízes Confiáveis
          # Precisa de privilégios de Administrador!
          comando = ["certutil", "-addstore", "-f", "Root", str(cert_path)]
          subprocess.run(comando, check=True, capture_output=True)
          print("✅ Certificado instalado com sucesso nas Raízes Confiáveis!")
          return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Falha ao instalar certificado: {e}")
            return False