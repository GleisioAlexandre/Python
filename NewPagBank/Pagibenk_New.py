import pandas as pd
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime, time
import numpy as np


# --- FUNÇÃO DE AUXÍLIO PARA EXTRAIR DATAS ÚNICAS ---
def extrair_datas_disponiveis(file_name):
    try:
        try:
            df = pd.read_csv(file_name, delimiter=';', encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_name, delimiter=';', encoding='latin1')

        df['Data da Transação'] = pd.to_datetime(df['Data da Transação'],
                                                 format='%d/%m/%Y %H:%M',
                                                 errors='coerce')
        df.dropna(subset=['Data da Transação'], inplace=True)

        datas_unicas = sorted(df['Data da Transação'].dt.date.unique())
        datas_formatadas = ["TODAS"] + [
            dt.strftime('%d/%m/%Y') for dt in datas_unicas
        ]
        return datas_formatadas
    except Exception:
        return ["TODAS"]


# --- CLASSE DA APLICAÇÃO TKINTER ---
class AplicacaoAnalise(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Analisador de Vendas por Dia, Turno e Prazo")
        self.geometry("1600x950")

        self.df_original = None
        self.caminho_arquivo = tk.StringVar()
        self.turno_var = tk.StringVar(value="TODOS")

        # VARIÁVEL DO REGIONAL: "RJ" (Rio de Janeiro) ou "CV" (Costa Verde)
        self.regiao_var = tk.StringVar(value="RJ")
        self.bloqueio_disparo = False

        self.criar_widgets()

    def criar_widgets(self):
        frame_controles = ttk.Frame(self, padding="10")
        frame_controles.pack(fill='x')

        frame_arquivo = ttk.Frame(frame_controles)
        frame_arquivo.pack(fill='x', pady=(0, 5))
        ttk.Label(frame_arquivo, text="Caminho do Arquivo CSV:").pack(side='left', padx=(0, 5))
        self.entry_caminho = ttk.Entry(frame_arquivo, textvariable=self.caminho_arquivo, width=80)
        self.entry_caminho.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(frame_arquivo, text="Buscar...", command=self.abrir_explorador).pack(side='left', padx=5)

        frame_filtros = ttk.LabelFrame(frame_controles, text=" Filtros de Pesquisa Dinâmicos ", padding="10")
        frame_filtros.pack(fill='x', pady=5)

        ttk.Label(frame_filtros, text="Selecione o Dia (DD/MM/AAAA):").pack(side='left', padx=(0, 5))
        self.combo_data = ttk.Combobox(frame_filtros, width=15, state="readonly")
        self.combo_data.pack(side='left', padx=(0, 15))
        self.combo_data.set("TODAS")
        self.combo_data.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        ttk.Label(frame_filtros, text="Turno:").pack(side='left', padx=(0, 5))
        self.cb_turno = ttk.Combobox(frame_filtros, textvariable=self.turno_var, values=["TODOS", "T1", "T2", "T3"], width=10, state="readonly")
        self.cb_turno.pack(side='left', padx=(0, 25))
        self.cb_turno.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        # === ADIÇÃO DOS DOIS RADIO BUTTONS DE REGIÃO ===
        ttk.Label(frame_filtros, text="Região:").pack(side='left', padx=(0, 5))
        self.rb_rj = ttk.Radiobutton(frame_filtros, text="Rio de Janeiro", variable=self.regiao_var, value="RJ", command=self.aplicar_filtros)
        self.rb_rj.pack(side='left', padx=5)
        self.rb_cv = ttk.Radiobutton(frame_filtros, text="Costa Verde", variable=self.regiao_var, value="CV", command=self.aplicar_filtros)
        self.rb_cv.pack(side='left', padx=5)

        ttk.Button(frame_filtros, text="Limpar Filtros", command=self.limpar_filtros).pack(side='right', padx=5)

        self.content_frame = ttk.Frame(self, padding="10")
        self.content_frame.pack(fill='both', expand=True)

        self.frame_tabelas = ttk.Frame(self.content_frame)
        self.frame_tabelas.pack(side="left", fill="both", expand=True)

        self.frame_resumo = ttk.Frame(self.frame_tabelas)
        self.frame_resumo.pack(fill='x', pady=(0, 15))
        ttk.Label(self.frame_resumo, text="Resumo por Modalidade", font=("Arial", 10, "bold")).pack(anchor='w')

        colunas_resumo = ["Modalidade", "Bruto", "Líquido"]
        self.tree_resumo = ttk.Treeview(self.frame_resumo, columns=colunas_resumo, show='headings', height=6)
        for col in colunas_resumo:
            self.tree_resumo.heading(col, text=col, command=lambda c=col: self.ordenar_por_coluna(self.tree_resumo, c, False))
            self.tree_resumo.column(col, width=150, anchor='center')
        self.tree_resumo.pack(fill='x', expand=True)

        self.frame_credito_container = ttk.LabelFrame(self.frame_tabelas, text=" Transações de Crédito / Outros ", padding="5")
        self.frame_credito_container.pack(fill='both', expand=True, pady=(0, 10))

        self.frame_band_credito = ttk.Frame(self.frame_credito_container)
        self.frame_band_credito.pack(fill='x', pady=2)

        colunas_transacoes = ["Data", "Bandeira", "Bruto", "Líquido", "Status"]
        self.tree_credito = ttk.Treeview(self.frame_credito_container, columns=colunas_transacoes, show='headings', height=6)
        for col in colunas_transacoes:
            self.tree_credito.heading(col, text=col, command=lambda c=col: self.ordenar_por_coluna(self.tree_credito, c, False))
            self.tree_credito.column(col, width=130, anchor='center')
        self.tree_credito.pack(fill='both', expand=True)
        
        self.lbl_tot_credito = ttk.Label(self.frame_credito_container, text="Total Crédito -> Bruto: R$ 0.00 | Líquido: R$ 0.00", font=("Arial", 9, "bold"), foreground="darkred")
        self.lbl_tot_credito.pack(anchor='e', pady=2)

        self.frame_debito_container = ttk.LabelFrame(self.frame_tabelas, text=" Transações de Débito ", padding="5")
        self.frame_debito_container.pack(fill='both', expand=True)

        self.frame_band_debito = ttk.Frame(self.frame_debito_container)
        self.frame_band_debito.pack(fill='x', pady=2)

        self.tree_debito = ttk.Treeview(self.frame_debito_container, columns=colunas_transacoes, show='headings', height=6)
        for col in colunas_transacoes:
            self.tree_debito.heading(col, text=col, command=lambda c=col: self.ordenar_por_coluna(self.tree_debito, c, False))
            self.tree_debito.column(col, width=130, anchor='center')
        self.tree_debito.pack(fill='both', expand=True)
        
        self.lbl_tot_debito = ttk.Label(self.frame_debito_container, text="Total Débito -> Bruto: R$ 0.00 | Líquido: R$ 0.00", font=("Arial", 9, "bold"), foreground="blue")
        self.lbl_tot_debito.pack(anchor='e', pady=2)

    def abrir_explorador(self):
        caminho_selecionado = filedialog.askopenfilename(
            defaultextension=".csv",
            filetypes=[("Arquivos CSV", "*.csv")],
            title="Selecione o arquivo PagBank Detalhado")
        if caminho_selecionado:
            self.bloqueio_disparo = True
            self.caminho_arquivo.set(caminho_selecionado)

            try:
                try:
                    self.df_original = pd.read_csv(caminho_selecionado, delimiter=';', encoding='utf-8')
                except UnicodeDecodeError:
                    self.df_original = pd.read_csv(caminho_selecionado, delimiter=';', encoding='latin1')

                self.df_original['Data da Transação'] = pd.to_datetime(self.df_original['Data da Transação'],
                                                                         format='%d/%m/%Y %H:%M',
                                                                         errors='coerce')
                self.df_original.dropna(subset=['Data da Transação'], inplace=True)

                lista_datas = extrair_datas_disponiveis(caminho_selecionado)
                self.combo_data['values'] = lista_datas
                self.combo_data.set("TODAS")

                self.bloqueio_disparo = False
                self.aplicar_filtros()

            except Exception as e:
                self.bloqueio_disparo = False
                messagebox.showerror(
                    "Erro de Leitura",
                    f"Não foi possível processar a estrutura desse CSV.\nDetalhe: {e}"
                )

    def aplicar_filtros(self, event=None):
        if self.df_original is None or self.bloqueio_disparo: 
            return
        
        df = self.df_original.copy()
        data_sel = self.combo_data.get()
        if data_sel != "TODAS":
            df = df[df['Data da Transação'].dt.strftime('%d/%m/%Y') == data_sel]

        t = self.turno_var.get()
        regiao = self.regiao_var.get()

        # === LÓGICA DINÂMICA DE FILTRAGEM POR TURNO E REGIÃO ===
        if regiao == "RJ":
            if t == "T1":
                df = df[df['Data da Transação'].dt.time < time(6, 0)]
            elif t == "T2":
                df = df[(df['Data da Transação'].dt.time >= time(6, 0)) & (df['Data da Transação'].dt.time < time(18, 0))]
            elif t == "T3":
                df = df[df['Data da Transação'].dt.time >= time(18, 0)]
        else:
            if t == "T1":
                df = df[df['Data da Transação'].dt.time < time(7, 0)]
            elif t == "T2":
                df = df[(df['Data da Transação'].dt.time >= time(7, 0)) & (df['Data da Transação'].dt.time < time(19, 0))]
            elif t == "T3":
                df = df[df['Data da Transação'].dt.time >= time(19, 0)]

        self.atualizar_telas(df)

    def limpar_filtros(self):
        self.combo_data.set("TODAS")
        self.turno_var.set("TODOS")
        self.regiao_var.set("RJ")
        self.aplicar_filtros()

    def ordenar_por_coluna(self, tree, col, reverse):
        lista_dados = [(tree.set(k, col), k) for k in tree.get_children("")]
        if col in ["Bruto", "Líquido"]:
            try:
                lista_dados.sort(
                    key=lambda t: float(t[0].replace('R$', '').replace('.', '').replace(',', '.').strip()),
                    reverse=reverse)
            except ValueError:
                lista_dados.sort(reverse=reverse)
        elif col == "Data":
            try:
                lista_dados.sort(
                    key=lambda t: datetime.strptime(t[0], "%d/%m/%Y %H:%M"),
                    reverse=reverse)
            except ValueError:
                lista_dados.sort(reverse=reverse)
        else:
            lista_dados.sort(reverse=reverse)
            
        for index, (val, k) in enumerate(lista_dados):
            tree.move(k, "", index)
        tree.heading(col, command=lambda: self.ordenar_por_coluna(tree, col, not reverse))

    def atualizar_telas(self, df):
        for t in [self.tree_resumo, self.tree_debito, self.tree_credito]:
            for i in t.get_children():
                t.delete(i)
                
        for w in self.frame_band_debito.winfo_children():
            w.destroy()
        for w in self.frame_band_credito.winfo_children():
            w.destroy()
            
        if df.empty:
            self.lbl_tot_debito.config(text="Total Débito -> Bruto: R$ 0.00 | Líquido: R$ 0.00")
            self.lbl_tot_credito.config(text="Total Crédito -> Bruto: R$ 0.00 | Líquido: R$ 0.00")
            return

        df['Valor Líquido'] = (df['Valor Líquido'].astype(str)
                               .str.replace('.', '', regex=False)
                               .str.replace(',', '.', regex=False)
                               .astype(float))
        
        if 'Valor Bruto' in df.columns:
            df['Valor Bruto'] = (df['Valor Bruto'].astype(str)
                                 .str.replace('.', '', regex=False)
                                 .str.replace(',', '.', regex=False)
                                 .astype(float))
        else:
            df['Valor Bruto'] = df['Valor Líquido']

        for mod in df['Forma de Pagamento'].unique():
            df_m = df[df['Forma de Pagamento'] == mod]
            self.tree_resumo.insert("", "end", values=(
                str(mod).upper(),
                f"R$ {df_m['Valor Bruto'].sum():,.2f}",
                f"R$ {df_m['Valor Líquido'].sum():,.2f}"
            ))

        bandeiras_debito = {}
        bandeiras_credito = {}
        deb_bruto = 0.0
        deb_liquido = 0.0
        cre_bruto = 0.0
        cre_liquido = 0.0

        for _, bundle_linha in df.iterrows():
            forma = str(bundle_linha['Forma de Pagamento']).upper()
            if "PIX" in forma:
                band = "PIX"
            elif "BOLETO" in forma:
                band = "BOLETO"
            else:
                band = str(bundle_linha['Bandeira']).upper().strip() if pd.notna(bundle_linha['Bandeira']) else 'OUTRAS'
            
            if band == "MASTER":
                band = "MASTERCARD"

            status = bundle_linha['Status'] if 'Status' in df.columns else 'CONCLUÍDA'
            
            valores_tabela = (
                bundle_linha['Data da Transação'].strftime('%d/%m/%Y %H:%M'), 
                band,
                f"R$ {bundle_linha['Valor Bruto']:,.2f}",
                f"R$ {bundle_linha['Valor Líquido']:,.2f}",
                status
            )

            if "DÉBITO" in forma or "DEB" in forma:
                self.tree_debito.insert("", "end", values=valores_tabela)
                deb_bruto += bundle_linha['Valor Bruto']
                deb_liquido += bundle_linha['Valor Líquido']
                if band not in bandeiras_debito:
                    bandeiras_debito[band] = {"bruto": 0.0, "liquido": 0.0}
                bandeiras_debito[band]["bruto"] += bundle_linha['Valor Bruto']
                bandeiras_debito[band]["liquido"] += bundle_linha['Valor Líquido']
            else:
                self.tree_credito.insert("", "end", values=valores_tabela)
                cre_bruto += bundle_linha['Valor Bruto']
                cre_liquido += bundle_linha['Valor Líquido']
                if band not in bandeiras_credito:
                    bandeiras_credito[band] = {"bruto": 0.0, "liquido": 0.0}
                bandeiras_credito[band]["bruto"] += bundle_linha['Valor Bruto']
                bandeiras_credito[band]["liquido"] += bundle_linha['Valor Líquido']

        self.lbl_tot_debito.config(text=f"Total Débito -> Bruto: R$ {deb_bruto:,.2f} | Líquido: R$ {deb_liquido:,.2f}")
        self.lbl_tot_credito.config(text=f"Total Crédito -> Bruto: R$ {cre_bruto:,.2f} | Líquido: R$ {cre_liquido:,.2f}")

        ordem_credito = ["AMEX", "ELO", "MASTERCARD", "VISA", "PIX", "BOLETO"]
        ordem_debito = ["ELO", "MASTERCARD", "VISA"]

        idx_c = 0
        for b in ordem_credito:
            if b in bandeiras_credito:
                valores = bandeiras_credito[b]
                cor_texto = "#006400" if b == "PIX" else ("#FF8C00" if b == "BOLETO" else "darkred")
                txt = f"{b} -> B: R$ {valores['bruto']:,.2f} | L: R$ {valores['liquido']:,.2f}"
                tk.Label(self.frame_band_credito, text=txt, font=("Arial", 8, "bold"), fg=cor_texto, padx=10).grid(row=0, column=idx_c)
                idx_c += 1

        for b, valores in bandeiras_credito.items():
            if b not in ordem_credito:
                txt = f"{b} -> B: R$ {valores['bruto']:,.2f} | L: R$ {valores['liquido']:,.2f}"
                tk.Label(self.frame_band_credito, text=txt, font=("Arial", 8, "bold"), fg="darkred", padx=10).grid(row=0, column=idx_c)
                idx_c += 1

        idx_d = 0
        for b in ordem_debito:
            if b in bandeiras_debito:
                valores = bandeiras_debito[b]
                txt = f"{b} -> B: R$ {valores['bruto']:,.2f} | L: R$ {valores['liquido']:,.2f}"
                tk.Label(self.frame_band_debito, text=txt, font=("Arial", 8, "bold"), fg="blue", padx=10).grid(row=0, column=idx_d)
                idx_d += 1

        for b, valores in bandeiras_debito.items():
            if b not in ordem_debito:
                txt = f"{b} -> B: R$ {valores['bruto']:,.2f} | L: R$ {valores['liquido']:,.2f}"
                tk.Label(self.frame_band_debito, text=txt, font=("Arial", 8, "bold"), fg="blue", padx=10).grid(row=0, column=idx_d)
                idx_d += 1


# --- EXECUÇÃO DO PROGRAMA ---
if __name__ == "__main__":
    app = AplicacaoAnalise()
    app.mainloop()