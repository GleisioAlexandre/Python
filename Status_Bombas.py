import socket
import tkinter as tk
from tkinter import ttk, messagebox
import re
from datetime import datetime

class MonitorPistaCompanytec:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor Companytec - Fechamento Sincronizado V5.0")
        self.root.geometry("1100x800")
        
        self.widgets = {}        
        self.lista_fila = []     
        self.ponteiro = 0        
        self.running = False
        
        # Dicionário para armazenar bicos que estão em processo de abastecimento
        self.bicos_em_operacao = {} 

        self.tabela_dt360 = {
            1: ["04", "44", "84", "C4"],
            2: ["05", "45", "85", "C5"]
        }

        self.setup_ui()

    def setup_ui(self):
        frame_top = ttk.Frame(self.root, padding=10)
        frame_top.pack(fill="x")
        self.ent_ip = ttk.Entry(frame_top, width=15); self.ent_ip.insert(0, "127.0.0.1"); self.ent_ip.pack(side="left", padx=5)
        self.ent_porta = ttk.Entry(frame_top, width=8); self.ent_porta.insert(0, "1771"); self.ent_porta.pack(side="left", padx=5)
        self.btn_load = tk.Button(frame_top, text="SINCRONIZAR PISTA (&R)", command=self.situacao_carregar_pista, bg="#2980b9", fg="white", font=("Arial", 10, "bold"))
        self.btn_load.pack(side="left", padx=10)
        
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

    def calcular_bcc(self, comando):
        conteudo = comando.strip("()")
        bcc = 0
        for char in conteudo: bcc ^= ord(char)
        return f"{bcc:02X}"

    def comunicar(self, comando_simples, timeout=0.5):
        bcc = self.calcular_bcc(comando_simples)
        comando_final = f"({comando_simples.strip('()')}{bcc})"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((self.ent_ip.get(), int(self.ent_porta.get())))
                s.sendall(comando_final.encode('ascii'))
                data = s.recv(1024).decode('ascii')
                return data
        except: return None

    def registrar_vendas_lote(self):
        """Registra todas as vendas pendentes e limpa a tela"""
        if not self.bicos_em_operacao: return
        
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open("vendas_posto.txt", "a") as f:
            for b_id, vol in self.bicos_em_operacao.items():
                if float(vol.replace(' L','')) > 0:
                    log = f"[{data_hora}] BICO: {b_id} | VOLUME: {vol}\n"
                    f.write(log)
                    # Reset visual do widget
                    info = self.widgets[b_id]
                    info["status_widget"].config(text="LIVRE", bg="#2ecc71")
                    info["vol_widget"].config(text="0.00 L", fg="black")
                    info["ultimo_vol"] = "0.00 L"
        
        print("Lote de abastecimentos finalizado e registrado.")
        self.bicos_em_operacao = {}

    def situacao_carregar_pista(self):
        self.running = False
        res = self.comunicar("(&R)")
        if not res: return
        linhas_c = re.findall(r"\(C.*?\)", res)
        for w in self.container.winfo_children(): w.destroy()
        
        self.widgets = {}; self.lista_fila = []

        for idx, linha in enumerate(linhas_c):
            s = linha.replace("(","").replace(")","")
            id_end = int(s[6:8]); qtd = int(s[8:10])
            frame = tk.LabelFrame(self.container, text=f"LADO {id_end}", font=("Arial", 10, "bold"))
            frame.pack(fill="x", pady=5)
            
            bicos = self.tabela_dt360.get(id_end, [])
            for i in range(qtd):
                if i < len(bicos):
                    b_id = bicos[i]
                    self.lista_fila.append(b_id)
                    f_bico = tk.Frame(frame, bd=2, relief="ridge", width=180, height=110)
                    f_bico.pack_propagate(False); f_bico.pack(side="left", padx=10, pady=5)
                    
                    tk.Label(f_bico, text=f"BICO {b_id}", font=("Arial", 11, "bold")).pack()
                    lbl_st = tk.Label(f_bico, text="LIVRE", bg="#2ecc71", fg="white", width=16, font=("Arial", 9, "bold"))
                    lbl_st.pack(pady=5)
                    lbl_vol = tk.Label(f_bico, text="0.00 L", font=("Arial", 10, "bold"))
                    lbl_vol.pack()
                    
                    self.widgets[b_id] = {
                        "status_widget": lbl_st, "vol_widget": lbl_vol, 
                        "pos_s": idx, "ultimo_vol": "0.00 L"
                    }

        self.running = True
        self.loop_organizado()

    def loop_organizado(self):
        if not self.running or not self.lista_fila: return
        
        # 1. Verifica o status geral de todos os bicos primeiro
        res_s = self.comunicar("(&S)", timeout=0.3)
        
        algum_abastecendo = False
        status_atual_bicos = {}

        if res_s and "S" in res_s:
            pos_inicial = res_s.find("S") + 1
            for b_id, info in self.widgets.items():
                char = res_s[pos_inicial + info["pos_s"]]
                status_atual_bicos[b_id] = char
                if char in ["A", "C", "S"]: algum_abastecendo = True

        # 2. Se NINGUÉM mais está abastecendo/sacado, mas tínhamos bicos em operação, fecha o lote
        if not algum_abastecendo and self.bicos_em_operacao:
            self.registrar_vendas_lote()

        # 3. Processa o bico da vez na fila para atualizar litros
        bico_id = self.lista_fila[self.ponteiro]
        info = self.widgets[bico_id]
        char_bico = status_atual_bicos.get(bico_id, "L")

        if char_bico in ["A", "C"]:
            res_v = self.comunicar(f"(&V{bico_id})", timeout=0.4)
            if res_v and bico_id in res_v:
                dados = res_v.replace("(","").replace(")","")
                try:
                    p = dados.find(bico_id) + 2
                    volume = f"{int(dados[p:p+6])/100:.2f} L"
                    info["vol_widget"].config(text=volume, fg="#e74c3c")
                    info["status_widget"].config(text="ABASTECENDO", bg="#e74c3c", fg="white")
                    info["ultimo_vol"] = volume
                    # Adiciona ao dicionário de operação para fechamento posterior
                    self.bicos_em_operacao[bico_id] = volume
                except: pass
        elif char_bico == "S":
            info["status_widget"].config(text="SACADO", bg="#f1c40f", fg="black")

        self.ponteiro = (self.ponteiro + 1) % len(self.lista_fila)
        self.root.after(800, self.loop_organizado)

if __name__ == "__main__":
    root = tk.Tk(); app = MonitorPistaCompanytec(root); root.mainloop()