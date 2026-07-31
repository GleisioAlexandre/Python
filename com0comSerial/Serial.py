import customtkinter as ctk
import socket
import serial
import serial.tools.list_ports
import threading
import time
import subprocess
import os
import sys
import configparser
import re
from PIL import Image, ImageDraw
import pystray

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppVeederRootPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- GARANTIR INSTÂNCIA ÚNICA ---
        self.lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.lock_socket.bind(("127.0.0.1", 50007))
        except socket.error:
            print("O aplicativo já está em execução.")
            sys.exit(0)

        self.title("Ponte Serial TCP/IP - Inteligência WebPosto")
        self.geometry("620x540")
        self.resizable(False, False)

        self.rodando = False
        self.sock_global = None
        self.pasta_com0com = r"C:\Program Files (x86)\com0com"
        self.com0com_exe = os.path.join(self.pasta_com0com, "setupc.exe")
        
        self.pasta_appdata = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "QualityBridge")
        if not os.path.exists(self.pasta_appdata):
            try: os.makedirs(self.pasta_appdata)
            except: pass
            
        self.arquivo_config = os.path.join(self.pasta_appdata, "config.ini")

        # --- CONFIGURAÇÃO DA BANDEJA DO SISTEMA (TRAY) ---
        self.protocol('WM_DELETE_WINDOW', self.minimizar_para_bandeja)
        self.criar_icone_bandeja()

        # ==========================================
        # --- ESTRUTURA DE ABAS (TABVIEW) ---
        # ==========================================
        self.tabview = ctk.CTkTabview(self, width=580, height=380)
        self.tabview.pack(padx=20, pady=(10, 5), fill="both", expand=True)
        
        self.tab_config = self.tabview.add("Configurações da Ponte")
        self.tab_log = self.tabview.add("Monitor de Fluxo (Log)")
        self.tab_teste = self.tabview.add("Testar Envio (Injetor TCP)")

        # --- CONTEÚDO DA ABA 1: CONFIGURAÇÕES ---
        self.frame_campos = ctk.CTkFrame(self.tab_config, fg_color="transparent")
        self.frame_campos.pack(padx=5, pady=5, fill="both", expand=True)

        # Coluna da Esquerda: Rede e Conexão
        self.lbl_rede = ctk.CTkLabel(self.frame_campos, text="[ REDE E CONEXÃO ]", font=("Arial", 11, "bold"), text_color="#1f538d")
        self.lbl_rede.grid(row=0, column=0, padx=12, pady=(5,2), sticky="w")

        self.lbl_com_local = ctk.CTkLabel(self.frame_campos, text="Porta do PDV Quality (Ex: COM2):", font=("Arial", 11))
        self.lbl_com_local.grid(row=1, column=0, padx=12, pady=1, sticky="w")
        self.txt_com_local = ctk.CTkEntry(self.frame_campos, width=250, height=26)
        self.txt_com_local.grid(row=2, column=0, padx=12, pady=3)

        self.lbl_protocolo = ctk.CTkLabel(self.frame_campos, text="Protocolo:", font=("Arial", 11))
        self.lbl_protocolo.grid(row=3, column=0, padx=12, pady=1, sticky="w")
        self.cb_protocolo = ctk.CTkComboBox(self.frame_campos, values=["RAW", "RFC2217"], width=250, height=26)
        self.cb_protocolo.grid(row=4, column=0, padx=12, pady=3)

        self.lbl_ip = ctk.CTkLabel(self.frame_campos, text="Endereço IP Remoto:", font=("Arial", 11))
        self.lbl_ip.grid(row=5, column=0, padx=12, pady=1, sticky="w")
        self.txt_ip = ctk.CTkEntry(self.frame_campos, width=250, height=26)
        self.txt_ip.grid(row=6, column=0, padx=12, pady=3)

        self.lbl_porta_tcp = ctk.CTkLabel(self.frame_campos, text="Porta TCP Remota:", font=("Arial", 11))
        self.lbl_porta_tcp.grid(row=7, column=0, padx=12, pady=1, sticky="w")
        self.txt_porta_tcp = ctk.CTkEntry(self.frame_campos, width=250, height=26)
        self.txt_porta_tcp.grid(row=8, column=0, padx=12, pady=3)

        self.lbl_reconexao = ctk.CTkLabel(self.frame_campos, text="Tempo limite de reconexão (s):", font=("Arial", 11))
        self.lbl_reconexao.grid(row=9, column=0, padx=12, pady=1, sticky="w")
        self.txt_reconexao = ctk.CTkEntry(self.frame_campos, width=250, height=26)
        self.txt_reconexao.grid(row=10, column=0, padx=12, pady=(3,5))

        # Coluna da Direita: Parâmetros da Porta COM
        self.lbl_param = ctk.CTkLabel(self.frame_campos, text="[ PARÂMETROS DA PORTA COM ]", font=("Arial", 11, "bold"), text_color="#1f538d")
        self.lbl_param.grid(row=0, column=1, padx=12, pady=(5,2), sticky="w")

        self.lbl_baud = ctk.CTkLabel(self.frame_campos, text="Velocidade de transmissão (Baud):", font=("Arial", 11))
        self.lbl_baud.grid(row=1, column=1, padx=12, pady=1, sticky="w")
        self.cb_baud = ctk.CTkComboBox(self.frame_campos, values=["2400", "4800", "9600", "19200", "115200"], width=250, height=26)
        self.cb_baud.grid(row=2, column=1, padx=12, pady=3)

        self.lbl_databits = ctk.CTkLabel(self.frame_campos, text="Bits de dados:", font=("Arial", 11))
        self.lbl_databits.grid(row=3, column=1, padx=12, pady=1, sticky="w")
        self.cb_databits = ctk.CTkComboBox(self.frame_campos, values=["5", "6", "7", "8"], width=250, height=26)
        self.cb_databits.grid(row=4, column=1, padx=12, pady=3)

        self.lbl_paridade = ctk.CTkLabel(self.frame_campos, text="Paridade:", font=("Arial", 11))
        self.lbl_paridade.grid(row=5, column=1, padx=12, pady=1, sticky="w")
        self.cb_paridade = ctk.CTkComboBox(self.frame_campos, values=["Nenhum", "Ímpar", "Par"], width=250, height=26)
        self.cb_paridade.grid(row=6, column=1, padx=12, pady=3)

        self.lbl_stopbits = ctk.CTkLabel(self.frame_campos, text="Bits de paragem (Stop Bits):", font=("Arial", 11))
        self.lbl_stopbits.grid(row=7, column=1, padx=12, pady=1, sticky="w")
        self.cb_stopbits = ctk.CTkComboBox(self.frame_campos, values=["1", "1.5", "2"], width=250, height=26)
        self.cb_stopbits.grid(row=8, column=1, padx=12, pady=3)

        # --- CONTEÚDO DA ABA 2: MONITOR DE LOG ---
        self.txt_log = ctk.CTkTextbox(self.tab_log, width=550, height=310, activate_scrollbars=True)
        self.txt_log.pack(padx=5, pady=5, fill="both", expand=True)
        self.txt_log.configure(state="disabled")

        # --- CONTEÚDO DA ABA 3: INJETOR MANUAL DE COMANDOS ---
        self.frame_teste = ctk.CTkFrame(self.tab_teste, fg_color="transparent")
        self.frame_teste.pack(padx=10, pady=10, fill="both", expand=True)

        self.lbl_instrucao_teste = ctk.CTkLabel(self.frame_teste, text="Injete comandos de teste direto para o Conversor de Rede (IP):", font=("Arial", 11, "bold"))
        self.lbl_instrucao_teste.pack(anchor="w", pady=(0, 5))

        self.frame_atalhos_teste = ctk.CTkFrame(self.frame_teste, fg_color="transparent")
        self.frame_atalhos_teste.pack(fill="x", pady=2)
        
        btn_soh = ctk.CTkButton(self.frame_atalhos_teste, text="+ <SOH>", width=90, height=24, fg_color="#333", command=lambda: self.inserir_controle_teste("\x01"))
        btn_soh.pack(side="left", padx=2)
        
        btn_stx = ctk.CTkButton(self.frame_atalhos_teste, text="+ <STX>", width=90, height=24, fg_color="#333", command=lambda: self.inserir_controle_teste("\x02"))
        btn_stx.pack(side="left", padx=2)

        btn_etx = ctk.CTkButton(self.frame_atalhos_teste, text="+ <ETX>", width=90, height=24, fg_color="#333", command=lambda: self.inserir_controle_teste("\x03"))
        btn_etx.pack(side="left", padx=2)

        self.txt_comando_teste = ctk.CTkTextbox(self.frame_teste, height=130, width=540)
        self.txt_comando_teste.pack(pady=5, fill="both", expand=True)
        self.txt_comando_teste.insert("1.0", "\x01i20100\x03")

        self.btn_enviar_teste = ctk.CTkButton(self.frame_teste, text="Injetar e Enviar para a Rede", fg_color="#1f538d", hover_color="#14375e", font=("Arial", 12, "bold"), height=35, command=self.injetar_comando_rede)
        self.btn_enviar_teste.pack(fill="x", pady=(5, 0))

        # ==========================================
        # --- RODAPÉ FIXO (BOTÕES DA JANELA) ---
        # ==========================================
        self.frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botoes.pack(padx=20, pady=(5, 15), fill="x")

        self.btn_salvar = ctk.CTkButton(self.frame_botoes, text="Salvar Configurações", command=self.salvar_configuracoes, fg_color="#1f538d", hover_color="#14375e", font=("Arial", 12, "bold"), height=32, width=580)
        self.btn_salvar.pack(pady=(0, 8))

        self.btn_action = ctk.CTkButton(self.frame_botoes, text="Iniciar Ponte de Comunicação", command=self.alternar_servico, fg_color="green", hover_color="darkgreen", font=("Arial", 13, "bold"), height=40, width=580)
        self.btn_action.pack()

        self.carregar_configuracoes()
        self.after(1000, self.auto_start)

    def log(self, msg):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def inserir_controle_teste(self, char):
        self.txt_comando_teste.insert("insert", char)

    def injetar_comando_rede(self):
        if not self.rodando or not self.sock_global:
            self.log("[AVISO] Ative a ponte de dados primeiro para abrir o canal com o IP!")
            return
        try:
            dados_entrada = self.txt_comando_teste.get("1.0", "end-1c")
            if dados_entrada:
                self.sock_global.sendall(dados_entrada.encode('utf-8'))
                dados_limpos = re.sub(r'[\x00-\x1F]', lambda m: f"<{m.group(0).encode('unicode_escape').decode()[2:].upper()}>", dados_entrada)
                self.log(f"[INJETOR TCP -> REDE]: Enviado comando manual '{dados_limpos}'")
                self.tabview.set("Monitor de Fluxo (Log)")
        except Exception as e:
            self.log(f"[ERRO] Falha ao injetar dado no barramento TCP: {e}")

    def obter_ip_da_rede_local(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()
            return ip_local
        except:
            return "192.168.0.1"

    def carregar_configuracoes(self):
        config = configparser.ConfigParser()
        
        self.txt_com_local.configure(state="normal")
        self.txt_ip.configure(state="normal")
        self.txt_porta_tcp.configure(state="normal")
        self.txt_reconexao.configure(state="normal")

        self.txt_com_local.delete(0, "end")
        self.txt_ip.delete(0, "end")
        self.txt_porta_tcp.delete(0, "end")
        self.txt_reconexao.delete(0, "end")

        if os.path.exists(self.arquivo_config):
            try:
                config.read(self.arquivo_config, encoding="utf-8")
                self.txt_com_local.insert(0, config.get("CONFIG", "porta_com", fallback="COM2"))
                self.cb_protocolo.set(config.get("CONFIG", "protocolo", fallback="RAW"))
                self.txt_ip.insert(0, config.get("CONFIG", "ip", fallback="192.168.0.66"))
                self.txt_porta_tcp.insert(0, config.get("CONFIG", "porta_tcp", fallback="23"))
                self.txt_reconexao.insert(0, config.get("CONFIG", "reconexao", fallback="5"))
                self.cb_baud.set(config.get("CONFIG", "baud", fallback="9600"))
                self.cb_databits.set(config.get("CONFIG", "databits", fallback="7"))
                self.cb_paridade.set(config.get("CONFIG", "paridade", fallback="Nenhum"))
                self.cb_stopbits.set(config.get("CONFIG", "stopbits", fallback="1"))
                self.log(f"[SISTEMA] Configurações carregadas!")
            except Exception as e:
                self.log(f"[AVISO] Erro ao ler config, aplicando padrões: {e}")
                self.carregar_valores_padrao()
        else:
            self.carregar_valores_padrao()

    def carregar_valores_padrao(self):
        ip_proprio = self.obter_ip_da_rede_local()
        partes_ip = ip_proprio.split(".")
        faixa_rede = f"{partes_ip[0]}.{partes_ip[1]}.{partes_ip[2]}" if len(partes_ip) == 4 else "192.168.0"
        ip_dinamico_padrao = f"{faixa_rede}.66"

        self.txt_com_local.insert(0, "COM2")
        self.cb_protocolo.set("RAW")
        self.txt_ip.insert(0, ip_dinamico_padrao)
        self.txt_porta_tcp.insert(0, "23")
        self.txt_reconexao.insert(0, "5")
        self.cb_baud.set("9600")
        self.cb_databits.set("7")
        self.cb_paridade.set("Nenhum")
        self.cb_stopbits.set("1")
        
        self.salvar_configuracoes_silencioso()

    def salvar_configuracoes(self):
        config = configparser.ConfigParser()
        config["CONFIG"] = {
            "porta_com": str(self.txt_com_local.get()).strip(),
            "protocolo": self.cb_protocolo.get(),
            "ip": str(self.txt_ip.get()).strip(),
            "porta_tcp": str(self.txt_porta_tcp.get()).strip(),
            "reconexao": str(self.txt_reconexao.get()).strip(),
            "baud": self.cb_baud.get(),
            "databits": self.cb_databits.get(),
            "paridade": self.cb_paridade.get(),
            "stopbits": self.cb_stopbits.get()
        }
        try:
            with open(self.arquivo_config, "w", encoding="utf-8") as f:
                config.write(f)
            self.log("[SISTEMA] Configurações salvas!")
            self.carregar_configuracoes()
        except Exception as e:
            self.log(f"[ERRO CRÍTICO] Falha ao gravar arquivo: {e}")

    def salvar_configuracoes_silencioso(self):
        config = configparser.ConfigParser()
        config["CONFIG"] = {
            "porta_com": str(self.txt_com_local.get()).strip(),
            "protocolo": self.cb_protocolo.get(),
            "ip": str(self.txt_ip.get()).strip(),
            "porta_tcp": str(self.txt_porta_tcp.get().strip()),
            "reconexao": str(self.txt_reconexao.get().strip()),
            "baud": self.cb_baud.get(),
            "databits": self.cb_databits.get(),
            "paridade": self.cb_paridade.get(),
            "stopbits": self.cb_stopbits.get()
        }
        try:
            with open(self.arquivo_config, "w", encoding="utf-8") as f:
                config.write(f)
        except: pass

    def auto_start(self):
        self.log("[SISTEMA] Inicialização automática acionada...")
        self.alternar_servico()

    def executar_com0com(self, comando):
        if not os.path.exists(self.com0com_exe):
            return None
        try:
            resultado = subprocess.run(f'"{self.com0com_exe}" --silent {comando}', shell=True, cwd=self.pasta_com0com, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3.0)
            return resultado
        except:
            return None

    def alternar_servico(self):
        try:
            self.porta_pdv = self.txt_com_local.get().strip().upper()
            self.porta_python = f"COM{int(self.porta_pdv.replace('COM', '')) * 11}" 
        except Exception:
            self.porta_pdv = "COM2"
            self.porta_python = "COM22"

        if not self.rodando:
            self.log(f"[SISTEMA] Validando se as portas já existem no Windows...")
            
            porta_existe = False
            try:
                filtro = subprocess.run(
                    'wmic path Win32_SerialPort get DeviceID', 
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                if filtro.stdout:
                    retorno_limpo = filtro.stdout.upper()
                    if self.porta_python in retorno_limpo or self.porta_pdv in retorno_limpo:
                        porta_existe = True
            except Exception as e:
                self.log(f"[AVISO] Erro ao consultar hardware WMI: {e}")

            if not porta_existe:
                try:
                    portas_sistema = [p.device.strip().upper() for p in serial.tools.list_ports.comports()]
                    if self.porta_python in portas_sistema or self.porta_pdv in portas_sistema:
                        porta_existe = True
                except: pass

            if not porta_existe:
                self.log(f"[AVISO] Par de portas não localizado. Criando hardware {self.porta_pdv} <-> {self.porta_python}...")
                cmd_criar = f"install PortName={self.porta_pdv} PortName={self.porta_python}"
                resultado_criacao = self.executar_com0com(cmd_criar)
                
                if resultado_criacao and resultado_criacao.returncode == 0:
                    self.executar_com0com(f"set enc{self.porta_pdv} pnc=yes")
                    self.executar_com0com(f"set enc{self.porta_python} pnc=yes")
                    self.executar_com0com("update")
                    
                    subprocess.run("powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {$_.Name -match 'com0com'} | ForEach-Object { $_.InvokeMethod('Update', $null) }\"", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.log("[SISTEMA] Portas instaladas com sucesso! A aguardar registo...")
                    time.sleep(4.0)
                else:
                    self.log("[AVISO] Ambiente restrito (com0com ausente). Modo simulação ativo.")
                    self.txt_com_local.configure(state="normal")
                    self.txt_ip.configure(state="normal")
                    self.txt_porta_tcp.configure(state="normal")
                    self.btn_salvar.configure(state="normal")
                    return
            else:
                self.log(f"[SISTEMA] {self.porta_python} confirmada via Win32_SerialPort. Ignorando instalador.")

            self.rodando = True
            self.btn_action.configure(text="Parar Serviço da Ponte", fg_color="red", hover_color="darkred")
            
            self.txt_com_local.configure(state="disabled")
            self.txt_ip.configure(state="disabled")
            self.txt_porta_tcp.configure(state="disabled")
            self.btn_salvar.configure(state="disabled")
            
            threading.Thread(target=self.motor_conexao, daemon=True).start()
        else:
            self.rodando = False
            self.sock_global = None
            self.btn_action.configure(text="Iniciar Ponte de Comunicação", fg_color="green", hover_color="darkgreen")
            
            self.txt_com_local.configure(state="normal")
            self.txt_ip.configure(state="normal")
            self.txt_porta_tcp.configure(state="normal")
            self.btn_salvar.configure(state="normal")
            self.log("[SISTEMA] Ponte desligada. Forçando liberação de hardware.")

    def motor_conexao(self):
        paridades = {"Nenhum": serial.PARITY_NONE, "Ímpar": serial.PARITY_ODD, "Par": serial.PARITY_EVEN}
        try:
            ip = self.txt_ip.get().strip()
            porta_tcp = int(self.txt_porta_tcp.get().strip())
            baud = int(self.cb_baud.get())
            bytesize = int(self.cb_databits.get())
            parity = paridades[self.cb_paridade.get()]
            stopbits = float(self.cb_stopbits.get())
            tempo_reconectar = int(self.txt_reconexao.get().strip())
        except:
            return

        while self.rodando:
            sock = None
            ser = None
            try:
                ser = serial.Serial(port=self.porta_python, baudrate=baud, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=1.0)
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((ip, porta_tcp))
                sock.settimeout(None)
                
                self.sock_global = sock
                self.log(f"[CONEXÃO] Conectado ao conversor IP: {ip}:{porta_tcp}")

                conexao_ativa = True

                def serial_para_rede():
                    nonlocal conexao_ativa
                    while self.rodando and conexao_ativa:
                        try:
                            if ser and ser.is_open and ser.in_waiting > 0:
                                time.sleep(0.04)
                                dados = ser.read(ser.in_waiting)
                                comando = dados.decode('utf-8', errors='ignore').strip()
                                
                                # Limpa caracteres especiais para ver no log técnico
                                comando_limpo = re.sub(r'[\x00-\x1F]', '', comando).strip()
                                
                                # =========================================================================
                                # --- EMULADOR EMBUTIDO INTERNO: RESPOSTA LOCAL E DIRETA AO WEBPOSTO ---
                                # =========================================================================
                                if "i20101" in comando_limpo.lower():
                                    self.log(f"[PDV -> LOCAL] i20101 recebido. Respondendo Tanque 1 (8190L) imediatamente!")
                                    resp = "\x01i20101251216035701100000745FFF5EC45FD985244FDA85244EE1F460000000041D9DBAF00000000&&EE46\x03"
                                    ser.write(resp.encode('utf-8'))
                                    
                                elif "i20102" in comando_limpo.lower():
                                    self.log(f"[PDV -> LOCAL] i20102 recebido. Respondendo Tanque 2 (3308L) imediatamente!")
                                    resp = "\x01i201022512160357022000007454EC171454CDCF64684FBD2440BEAFD0000000041D6325700000000&&EE8B\x03"
                                    ser.write(resp.encode('utf-8'))
                                    
                                elif "i20103" in comando_limpo.lower():
                                    self.log(f"[PDV -> LOCAL] i20103 recebido. Respondendo Tanque 3 (1074L) imediatamente!")
                                    resp = "\x01i20103251216035703300000744865E1544856BD7460EE43E43CE61A60000000041D247B400000000&&EEC0\x03"
                                    ser.write(resp.encode('utf-8'))
                                    
                                elif "i20104" in comando_limpo.lower():
                                    self.log(f"[PDV -> LOCAL] i20104 recebido. Respondendo Tanque 4 (8145L) imediatamente!")
                                    resp = "\x01i20104251216035704400000745FE8A90460E1D6C4501AAE144ECC3C000000000C2918E3900000000&&EE8E\x03"
                                    ser.write(resp.encode('utf-8'))

                                elif "i20105" in comando_limpo.lower():
                                    self.log(f"[PDV -> LOCAL] i20105 recebido. Respondendo Tanque 5 (8103L) imediatamente!")
                                    resp = "\x01i20105251216035705500000745FD3D7B45FADFE24504450A44EBB0460000000041E0B12E00000000&&EE87\x03"
                                    ser.write(resp.encode('utf-8'))
                                    
                                elif "i20204" in comando_limpo.lower():
                                    self.log(f"[PDV -> LOCAL] i20204 histórico recebido. Respondendo localmente!")
                                    resp = "\x01i20204251216035704410251215235725121600550A45AE3A7145C2929A00000000C2918E3945D8561F45F1A\x03"
                                    ser.write(resp.encode('utf-8'))
                                    
                                else:
                                    # Se for qualquer outro comando de pista comum, encaminha normal para a rede
                                    if sock:
                                        sock.sendall(dados)
                                        self.log(f"[PDV -> REDE] Comando encaminhado: {comando_limpo}")
                                        
                        except Exception as ex: 
                            conexao_ativa = False
                            break
                        time.sleep(0.02)

                t_serial = threading.Thread(target=serial_para_rede, daemon=True)
                t_serial.start()

                while self.rodando and conexao_ativa:
                    try:
                        sock.settimeout(2.0)
                        dados_rede = sock.recv(4096)
                        if not dados_rede: break
                        time.sleep(0.02)
                        if ser and ser.is_open:
                            ser.write(dados_rede)
                            self.log(f"[REDE -> PDV] Resposta do Conversor foward ({len(dados_rede)} bytes)")
                    except socket.timeout:
                        continue
                    except:
                        break

                conexao_ativa = False

            except Exception as e:
                self.log(f"[AVISO] Aguardando conexão: {e}")
                self.sock_global = None
                if ser and ser.is_open: ser.close()
                if sock: sock.close()
                if self.rodando:
                    time.sleep(tempo_reconectar)
            finally:
                self.sock_global = None
                try: 
                    if sock: sock.close()
                except: pass
                try:
                    if ser and ser.is_open: 
                        ser.reset_input_buffer()
                        ser.reset_output_buffer()
                        ser.close()
                except: pass

    def criar_icone_bandeja(self):
        image = Image.new('RGB', (64, 64), color='#1f538d')
        d = ImageDraw.Draw(image)
        d.text((12, 24), "COM", fill="white")

        menu = pystray.Menu(
            pystray.MenuItem('Abrir Painel', self.restaurar_janela),
            pystray.MenuItem('Fechar Definitivamente', self.fechar_aplicativo_total)
        )
        self.icon = pystray.Icon("VeederRootBridge", image, "Ponte Veeder-Root", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def minimizar_para_bandeja(self):
        self.withdraw()

    def restaurar_janela(self):
        self.deiconify()

    def fechar_aplicativo_total(self):
        self.rodando = False
        self.icon.stop()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = AppVeederRootPro()
    app.mainloop()