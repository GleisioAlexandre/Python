import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import pandas as pd

# Configuração do tema visual moderno (Estilo Claro conforme a imagem)
ctk.set_appearance_mode("Light")  
ctk.set_default_color_theme("blue")


class AppDesktop(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Configurações da Janela Principal
        self.title("Otimizador de Conferência de Extrato - PagBank")
        self.geometry("1100x650")
        self.minsize(900, 500)

        # Variáveis de Dados Internos
        self.caminho_arquivo = ""
        self.resultado_pivot = None
        self.df_exibicao = None

        # --- ESTILIZAÇÃO DO DATAGRID (CORES EXATAS DA IMAGEM EXEMPLO) ---
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            background="#ffffff",          # Fundo totalmente branco
            foreground="#000000",          # Texto preto nas linhas
            rowheight=28,                  # Altura confortável por linha
            fieldbackground="#ffffff",
            font=("Arial", 10),
        )
        self.style.configure(
            "Treeview.Heading",
            background="#f2f2f2",          # Cabeçalho cinza claro da imagem
            foreground="#333333",          # Texto do cabeçalho escuro
            font=("Arial", 10, "bold"),
            borderwidth=1,
        )
        self.style.map(
            "Treeview", 
            background=[("selected", "#d1e8ff")],  # Destaque azul suave ao clicar
            foreground=[("selected", "#000000")]
        )

        # --- 1. BARRA SUPERIOR DE BUSCA DE ARQUIVO ---
        self.frame_top_bar = ctk.CTkFrame(self, fg_color="#f8f9fa", corner_radius=0, border_width=1, border_color="#e9ecef")
        self.frame_top_bar.pack(side="top", fill="x", padx=0, pady=0)

        self.lbl_path_title = ctk.CTkLabel(self.frame_top_bar, text="Arquivo do Extrato:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#333333")
        self.lbl_path_title.pack(side="left", padx=15, pady=8)

        self.entry_caminho = ctk.CTkEntry(self.frame_top_bar, placeholder_text="Selecione a planilha .xlsx do PagBank...", width=500, height=28, fg_color="#ffffff", text_color="#333333")
        self.entry_caminho.pack(side="left", padx=5, pady=8, fill="x", expand=True)

        self.btn_buscar = ctk.CTkButton(self.frame_top_bar, text="Buscar...", command=self.selecionar_arquivo, width=90, height=28, fg_color="#1f538d", hover_color="#163e6a")
        self.btn_buscar.pack(side="right", padx=15, pady=8)

        # --- 2. BARRA DE FILTROS EM LINHA ---
        self.frame_filtros_container = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_filtros_container.pack(side="top", fill="x", padx=15, pady=10)

        self.frame_filtros = ctk.CTkFrame(self.frame_filtros_container, border_width=1, border_color="#cccccc", fg_color="#ffffff")
        self.frame_filtros.pack(fill="x", padx=0, pady=2)

        self.sub_filtros = ctk.CTkFrame(self.frame_filtros, fg_color="transparent")
        self.sub_filtros.pack(fill="x", padx=10, pady=6)

        # Filtro de Escolha da Data
        self.lbl_filtro_dia = ctk.CTkLabel(self.sub_filtros, text="Filtrar por Data:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#333333")
        self.lbl_filtro_dia.pack(side="left", padx=5)

        self.combo_datas = ctk.CTkComboBox(self.sub_filtros, values=["Todos os dias"], command=self.filtrar_por_data, width=160, height=26, state="disabled")
        self.combo_datas.set("Todos os dias")
        self.combo_datas.pack(side="left", padx=5)

        # Botão Limpar Filtro à Direita
        self.btn_limpar = ctk.CTkButton(self.sub_filtros, text="Mostrar Tudo", command=self.resetar_filtro, width=100, height=26, fg_color="#e74c3c", hover_color="#c0392b")
        self.btn_limpar.pack(side="right", padx=5)

        # --- 3. DATAGRID ÚNICO CONSOLIDADO ---
        self.frame_tabela_container = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tabela_container.pack(side="top", fill="both", expand=True, padx=15, pady=5)

        self.lbl_tabela_titulo = ctk.CTkLabel(self.frame_tabela_container, text="Resumo de Conferência Diária", font=ctk.CTkFont(size=12, weight="bold"), text_color="#333333")
        self.lbl_tabela_titulo.pack(anchor="nw", padx=5, pady=2)

        self.frame_tabela = ctk.CTkFrame(self.frame_tabela_container, border_width=1, border_color="#cccccc", fg_color="#ffffff")
        self.frame_tabela.pack(fill="both", expand=True, padx=0, pady=2)

        self.colunas = ["Data", "Disponivel PIX", "Disponivel CREDITO", "Disponivel DEBITO", "Total do Dia"]
        self.tree = ttk.Treeview(self.frame_tabela, columns=self.colunas, show="headings")

        # Ajuste e alinhamento das colunas
        for col in self.colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=160)

        # Barra de rolagem lateral da tabela
        self.scrollbar = ttk.Scrollbar(self.frame_tabela, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        self.scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        # --- 4. BARRA DE AÇÕES INFERIOR ---
        self.frame_acoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acoes.pack(padx=20, pady=15, fill="x", side="bottom")

        self.btn_salvar = ctk.CTkButton(
            self.frame_acoes,
            text="📥 Exportar Tabela para Excel (.xlsx)",
            command=self.salvar_resumo,
            state="disabled",
            fg_color="#27ae60",
            hover_color="#219653",
            width=230,
            height=32
        )
        self.btn_salvar.pack(side="right", padx=5)

    def selecionar_arquivo(self):
        arquivo = filedialog.askopenfilename(title="Selecione o extrato Excel", filetypes=[("Arquivos Excel", "*.xlsx")])
        if arquivo:
            self.caminho_arquivo = arquivo
            self.entry_caminho.delete(0, tk.END)
            self.entry_caminho.insert(0, arquivo)
            self.processar_extrato()

    def processar_extrato(self):
        try:
            df_cru = pd.read_excel(self.caminho_arquivo, header=None)

            linha_cabecalho = None
            colunas_alvo = ["Data", "Descrição", "Entradas"]

            for idx, row in df_cru.iterrows():
                valores_linha = [str(val).strip() for val in row.values]
                if all(col in valores_linha for col in colunas_alvo):
                    linha_cabecalho = idx
                    break

            if linha_cabecalho is None:
                messagebox.showerror("Erro de Estrutura", "Não foi possível encontrar as colunas 'Data', 'Descrição' e 'Entradas'.")
                return

            df = pd.read_excel(self.caminho_arquivo, skiprows=linha_cabecalho)
            df.columns = [str(col).strip() for col in df.columns]

            # Limpeza e formatação numérica brasileira
            if not pd.api.types.is_numeric_dtype(df["Entradas"]):
                df["Entradas"] = df["Entradas"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            df["Entradas"] = pd.to_numeric(df["Entradas"], errors="coerce").fillna(0)

            def categorizar_pagamento(descricao):
                desc = str(descricao).upper().strip()
                if "DISPONIVEL PIX" in desc: return "Disponivel PIX"
                elif "CREDITO" in desc: return "Disponivel CREDITO"
                elif "DEBITO" in desc: return "Disponivel DEBITO"
                return "Outros"

            df["Forma_Pagamento"] = df["Descrição"].apply(categorizar_pagamento)

            df_filtrado = df[df["Forma_Pagamento"].isin(["Disponivel PIX", "Disponivel CREDITO", "Disponivel DEBITO"])]
            resultado = df_filtrado.groupby(["Data", "Forma_Pagamento"])["Entradas"].sum().reset_index()

            self.resultado_pivot = resultado.pivot(index="Data", columns="Forma_Pagamento", values="Entradas").fillna(0)

            for col in ["Disponivel PIX", "Disponivel CREDITO", "Disponivel DEBITO"]:
                if col not in self.resultado_pivot.columns:
                    self.resultado_pivot[col] = 0.0

            self.resultado_pivot = self.resultado_pivot[["Disponivel PIX", "Disponivel CREDITO", "Disponivel DEBITO"]]
            self.resultado_pivot["Total do Dia"] = self.resultado_pivot.sum(axis=1)

            # Organiza a exibição final formatada
            self.df_exibicao = self.resultado_pivot.copy().reset_index()
            
            if pd.api.types.is_datetime64_any_dtype(self.df_exibicao["Data"]):
                self.df_exibicao["Data"] = self.df_exibicao["Data"].dt.strftime("%d/%m/%Y")
            else:
                self.df_exibicao["Data"] = self.df_exibicao["Data"].astype(str)

            # Atualiza o ComboBox de datas superiores
            lista_datas = ["Todos os dias"] + sorted(self.df_exibicao["Data"].unique().tolist())
            self.combo_datas.configure(values=lista_datas, state="normal")
            self.combo_datas.set("Todos os dias")

            # Atualiza o grid
            self.atualizar_datagrid(self.df_exibicao)
            self.btn_salvar.configure(state="normal")
            messagebox.showinfo("Sucesso", "Extrato processado com sucesso!")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler o arquivo:\n{e}")

    def atualizar_datagrid(self, dataframe_para_mostrar):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for _, row in dataframe_para_mostrar.iterrows():
            valores_formatados = [
                row["Data"],
                f"R$ {row['Disponivel PIX']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"R$ {row['Disponivel CREDITO']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"R$ {row['Disponivel DEBITO']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                f"R$ {row['Total do Dia']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ]
            self.tree.insert("", "end", values=valores_formatados)

    def filtrar_por_data(self, escolha):
        if self.df_exibicao is None: return
        if escolha == "Todos os dias":
            self.atualizar_datagrid(self.df_exibicao)
        else:
            df_filtrado = self.df_exibicao[self.df_exibicao["Data"] == escolha]
            self.atualizar_datagrid(df_filtrado)

    def resetar_filtro(self):
        self.combo_datas.set("Todos os dias")
        self.filtrar_por_data("Todos os dias")

    def salvar_resumo(self):
        if self.resultado_pivot is not None:
            local_salvar = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Arquivo Excel", "*.xlsx")],
                title="Salvar Resumo Consolidado",
                initialfile="resumo_conferencia.xlsx",
            )
            if local_salvar:
                try:
                    self.resultado_pivot.to_excel(local_salvar)
                    messagebox.showinfo("Sucesso", "Arquivo salvo com sucesso!")
                except Exception as e:
                    messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar:\n{e}")


if __name__ == "__main__":
    instancia_app = AppDesktop()
    instancia_app.mainloop()