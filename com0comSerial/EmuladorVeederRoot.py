import customtkinter as ctk
import serial
import threading
import time
import re

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class EmuladorVeederRoot(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Simulador Oficial Veeder-Root (TLS-350/450)")
        self.geometry("700x650")
        self.resizable(False, False)

        self.rodando = False
        self.ser = None
        
        # Estrutura de dados para armazenar os tanques ativos
        # Formato: { numero_tanque: { "combustivel": str, "capacidade": int, "volume": int, "agua": int } }
        self.tanques = {
            1: {"combustivel": "GASOLINA COMUM", "capacidade": 20000, "volume": 12500, "agua": 0},
            2: {"combustivel": "DIESEL S10", "capacidade": 15000, "volume": 8400, "agua": 0}
        }

        # --- CONTAINER SUPERIOR: CADASTRO E SERIAL ---
        self.frame_topo = ctk.CTkFrame(self)
        self.frame_topo.pack(padx=15, pady=10, fill="x")

        # Configuração da Porta Serial
        self.lbl_serial = ctk.CTkLabel(self.frame_topo, text="Porta Serial do Simulador:", font=("Arial", 11, "bold"))
        self.lbl_serial.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.txt_porta = ctk.CTkEntry(self.frame_topo, width=120, placeholder_text="COM2")
        self.txt_porta.insert(0, "COM2")
        self.txt_porta.grid(row=0, column=1, padx=10, pady=5)

        self.btn_conectar = ctk.CTkButton(self.frame_topo, text="Ligar Simulador", fg_color="green", hover_color="darkgreen", command=self.alternar_simulador, font=("Arial", 12, "bold"))
        self.btn_conectar.grid(row=0, column=2, padx=10, pady=5)

        # Divisor de Cadastro de Tanques
        self.lbl_cadastro = ctk.CTkLabel(self.frame_topo, text="[ CADASTRO DE NOVO TANQUE ]", font=("Arial", 11, "bold"), text_color="#1f538d")
        self.lbl_cadastro.grid(row=1, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        self.txt_num_tanque = ctk.CTkEntry(self.frame_topo, width=80, placeholder_text="Nº (Ex: 3)")
        self.txt_num_tanque.grid(row=2, column=0, padx=10, pady=5)

        self.txt_nome_comb = ctk.CTkEntry(self.frame_topo, width=200, placeholder_text="Combustível (Ex: ETANOL)")
        self.txt_nome_comb.grid(row=2, column=1, padx=10, pady=5)

        self.txt_cap_tanque = ctk.CTkEntry(self.frame_topo, width=120, placeholder_text="Capacidade (L)")
        self.txt_cap_tanque.grid(row=2, column=2, padx=10, pady=5)

        self.btn_adicionar = ctk.CTkButton(self.frame_topo, text="Cadastrar", command=self.cadastrar_tanque, width=100)
        self.btn_adicionar.grid(row=2, column=3, padx=10, pady=5)

        # --- CONTAINER CENTRAL: LISTA DE TANQUES DINÂMICOS (ROLÁVEL) ---
        self.lbl_lista_titulo = ctk.CTkLabel(self, text="Controle de Estoque dos Tanques Cadastrados (Arraste os Sliders)", font=("Arial", 12, "bold"))
        self.lbl_lista_titulo.pack(pady=(10, 0))

        self.frame_lista = ctk.CTkScrollableFrame(self, width=660, height=280)
        self.frame_lista.pack(padx=15, pady=5, fill="both", expand=True)

        # --- CONTAINER INFERIOR: LOG DE COMANDOS ---
        self.txt_log = ctk.CTkTextbox(self, width=670, height=120, activate_scrollbars=True)
        self.txt_log.pack(padx=15, pady=10)
        self.txt_log.configure(state="disabled")

        # Atualiza a tela para desenhar os tanques iniciais padrão
        self.atualizar_painel_tanques()

    def log(self, msg):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def cadastrar_tanque(self):
        try:
            num = int(self.txt_num_tanque.get().strip())
            nome = self.txt_nome_comb.get().strip().upper()
            capacidade = int(self.txt_cap_tanque.get().strip())

            if num in self.tanques:
                self.log(f"[ERRO] O tanque nº {num} já está cadastrado!")
                return

            if not nome or capacidade <= 0:
                raise ValueError

            # Adiciona o novo tanque à memória com metade do volume preenchido por padrão
            self.tanques[num] = {
                "combustivel": nome,
                "capacidade": capacidade,
                "volume": int(capacidade / 2),
                "agua": 0
            }

            self.txt_num_tanque.delete(0, "end")
            self.txt_nome_comb.delete(0, "end")
            self.txt_cap_tanque.delete(0, "end")

            self.log(f"[SISTEMA] Tanque {num} ({nome}) cadastrado com sucesso!")
            self.atualizar_painel_tanques()
        except:
            self.log("[ERRO] Verifique os dados de cadastro. Insira números válidos!")

    def atualizar_painel_tanques(self):
        # Limpa todos os widgets antigos da lista rolável antes de redesenhar
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        # Desenha a linha de controle de cada tanque cadastrado
        for num in sorted(self.tanques.keys()):
            dados = self.tanques[num]
            
            card = ctk.CTkFrame(self.frame_lista, fg_color="#1d1e22")
            card.pack(fill="x", pady=4, padx=5)

            # Texto informativo do Tanque
            lbl_info = ctk.CTkLabel(card, text=f"Tanque {num}: {dados['combustivel']} (Máx: {dados['capacidade']}L)", font=("Arial", 11, "bold"), text_color="#1f538d", width=220, anchor="w")
            lbl_info.grid(row=0, column=0, padx=10, pady=5, sticky="w")

            # Variáveis e Sliders de Controle de Volume de Combustível
            lbl_vol = ctk.CTkLabel(card, text=f"Combustível: {dados['volume']} L", font=("Arial", 10), width=120)
            lbl_vol.grid(row=0, column=1, padx=5)
            
            slide_vol = ctk.CTkSlider(card, from_=0, to=dados['capacidade'], width=150, number_of_steps=dados['capacidade'])
            slide_vol.set(dados['volume'])
            slide_vol.grid(row=0, column=2, padx=5)
            
            # Variáveis e Sliders de Controle de Água no fundo do tanque
            lbl_agua = ctk.CTkLabel(card, text=f"Água: {dados['agua']} L", font=("Arial", 10), width=80)
            lbl_agua.grid(row=0, column=3, padx=5)
            
            slide_agua = ctk.CTkSlider(card, from_=0, to=500, width=80, number_of_steps=500)
            slide_agua.set(dados['agua'])
            slide_agua.grid(row=0, column=4, padx=5)

            # Funções de gatilho em tempo real dos sliders
            def vincular_volume(val, n=num, l=lbl_vol):
                self.tanques[n]['volume'] = int(val)
                l.configure(text=f"Combustível: {int(val)} L")

            def vincular_agua(val, n=num, l=lbl_agua):
                self.tanques[n]['agua'] = int(val)
                l.configure(text=f"Água: {int(val)} L")

            slide_vol.configure(command=vincular_volume)
            slide_agua.configure(command=vincular_agua)

    def alternar_simulador(self):
        if not self.rodando:
            porta = self.txt_porta.get().strip()
            try:
                self.ser = serial.Serial(porta, baudrate=9600, timeout=1)
                self.rodando = True
                self.btn_conectar.configure(text="Desligar Simulador", fg_color="red", hover_color="darkred")
                self.txt_porta.configure(state="disabled")
                
                # Inicia a thread que fica escutando as requisições seriais do PDV
                threading.Thread(target=self.escutar_porta_serial, daemon=True).start()
                self.log(f"[SIMULADOR] Rodando e ouvindo requisições na porta {porta}...")
            except Exception as e:
                self.log(f"[ERRO] Não foi possível abrir a porta {porta}: {e}")
        else:
            self.rodando = False
            if self.ser:
                self.ser.close()
            self.btn_conectar.configure(text="Ligar Simulador", fg_color="green", hover_color="darkgreen")
            self.txt_porta.configure(state="normal")
            self.log("[SIMULADOR] Encerrado.")

    def gerar_resposta_veeder_root(self):
        """Monta o pacote de dados hexadecimal no padrão ASCII oficial do TLS-350"""
        soh = "\x01"  # Caractere de controle de Início
        etx = "\x03"  # Caractere de controle de Fim
        
        # Estrutura do cabeçalho
        resposta = "I20100\n"
        resposta += f"{time.strftime('%b %d, %Y %I:%M %p')}\n\n"
        resposta += "INVENTARIO DE TANQUES\n\n"
        
        # Loop pelos tanques ativos cadastrados na tela
        for num in sorted(self.tanques.keys()):
            t = self.tanques[num]
            # Formata a linha estritamente espaçada como o Veeder-Root faz fisicamente
            combustivel_formatado = t['combustivel'].ljust(18)
            resposta += f"T {num}:{combustivel_formatado} | VOLUME = {str(t['volume']).rjust(6)} L | AGUA = {str(t['agua']).rjust(5)} L | TEMP = 24.20 C\n"
            
        return f"{soh}{resposta}{etx}"

    def escutar_porta_serial(self):
        while self.rodando:
            try:
                if self.ser.in_waiting > 0:
                    time.sleep(0.05)  # Pequeno delay para receber o pacote completo
                    comando = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    
                    # Limpa caracteres de controle para exibir no log de testes
                    comando_limpo = re.sub(r'[\x00-\x1F]', '', comando).strip()
                    self.log(f"[PDV -> REQUISIÇÃO]: '{comando_limpo}'")

                    # Se o PDV mandar "201" ou "i20100", responde o estoque atual da tela
                    if "201" in comando_limpo.lower():
                        self.log("[SIMULADOR -> PDV]: Enviando dados dos tanques da tela...")
                        pacote_resposta = self.gerar_resposta_veeder_root()
                        self.ser.write(pacote_resposta.encode('utf-8'))
            except:
                break
            time.sleep(0.05)

if __name__ == "__main__":
    app = EmuladorVeederRoot()
    app.mainloop()