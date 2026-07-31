import os
import time
import subprocess
import json
import ctypes
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox

CONFIG_FILE = "config_posto.json"

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def get_tailscale_ip():
    try:
        # Tenta pegar o IP do Tailscale de forma robusta
        out = subprocess.check_output(["tailscale", "ip", "-4"], shell=True, stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except:
        return None

def forcar_limpeza_e_aplicar(ts_ip, ip_destino, porta):
    try:
        # 1. Garante que o serviço de rede está rodando
        subprocess.run("net start iphlpsvc", shell=True, capture_output=True)
        
        # 2. Limpa qualquer regra travada anteriormente para evitar conflito
        subprocess.run(f"netsh interface portproxy delete v4tov4 listenaddress={ts_ip} listenport={porta}", shell=True, capture_output=True)
        
        # 3. Aplica a nova regra de redirecionamento
        cmd = f"netsh interface portproxy add v4tov4 listenaddress={ts_ip} listenport={porta} connectaddress={ip_destino} connectport={porta}"
        subprocess.run(cmd, shell=True, capture_output=True)
        
        # 4. Força o MTU (estabilidade de dados)
        subprocess.run('netsh interface ipv4 set subinterface "Tailscale" mtu=1280 store=persistent', shell=True, capture_output=True)
        
        # 5. Garante regra no Firewall
        fw = f"netsh advfirewall firewall add rule name='Varela_Auto_{porta}' dir=in action=allow protocol=TCP localport={porta} profile=any"
        subprocess.run(fw, shell=True, capture_output=True)
    except Exception as e:
        pass

if __name__ == "__main__":
    # 1. VERIFICA ADMIN (CRÍTICO)
    if not is_admin():
        # Tenta reabrir o script como administrador automaticamente
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    # 2. CARREGA OU PEDE CONFIGURAÇÃO
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            ip_alvo = config['ip']
            porta_alvo = config['porta']
    else:
        root = tk.Tk()
        root.withdraw()
        ip_alvo = simpledialog.askstring("Configuração", "IP do Aparelho (ex: 192.168.0.88):")
        porta_alvo = simpledialog.askstring("Configuração", "Porta (ex: 2000):")
        
        if ip_alvo and porta_alvo:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"ip": ip_alvo, "porta": porta_alvo}, f)
        else:
            sys.exit()

    # 3. LOOP INFINITO DE AUTO-CORREÇÃO
    while True:
        ip_atual_ts = get_tailscale_ip()
        if ip_atual_ts:
            forcar_limpeza_e_aplicar(ip_atual_ts, ip_alvo, porta_alvo)
        
        # Espera 30 segundos para a próxima verificação
        time.sleep(30)