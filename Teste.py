import platform
import psutil
import subprocess 
import json
import locale
import datetime
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext 
import socket # NOVO: Biblioteca para obter nome do host e IP

# ----------------------------------------------------
# Funções de Coleta de Dados
# ----------------------------------------------------

def obter_dados_hardware():
    info = {}
    
    # --- NOVO: Coleta de Informações de Rede ---
    try:
        info['Nome_da_Maquina'] = socket.gethostname()
        info['Endereco_IP_Local'] = socket.gethostbyname(info['Nome_da_Maquina'])
    except Exception:
        info['Nome_da_Maquina'] = "Falha na Coleta"
        info['Endereco_IP_Local'] = "Falha na Coleta"
    
    # --- Coleta de Informações de Hardware (Método existente) ---
    
    encoding = locale.getpreferredencoding(False) 

    def rodar_powershell_final(comando, chave, fallback=None):
        """Função auxiliar para rodar comandos PowerShell e tratar codificação."""
        try:
            powershell_cmd = f"powershell \"{comando} | ConvertTo-Json\""
            resultado = subprocess.run(powershell_cmd, 
                                       capture_output=True, 
                                       text=True, 
                                       shell=True, 
                                       check=True, 
                                       encoding=encoding)
            
            output_json = resultado.stdout.strip().replace('\ufeff', '')
            dados_json = json.loads(output_json)
            
            valor = dados_json[chave]
            return valor[0] if isinstance(valor, list) else valor
            
        except Exception:
            return fallback if fallback is not None else "Falha na Coleta"

    # ==================== Coleta de Dados ====================

    # 1. Sistema Operacional
    os_comando = "Get-CimInstance -ClassName Win32_OperatingSystem"
    info['Sistema_Operacional_Nome'] = rodar_powershell_final(os_comando, 'Caption')
    info['Sistema_Operacional_Kernel'] = rodar_powershell_final(os_comando, 'Version') 
    
    # 2. Processador
    cpu_comando = "Get-CimInstance -ClassName Win32_Processor"
    info['Processador_Nome'] = rodar_powershell_final(cpu_comando, 'Name', fallback=platform.processor()).strip()

    # 3. Placa-Mãe
    baseboard_comando = "Get-CimInstance -ClassName Win32_BaseBoard"
    info['Placa_Mae_Fabricante'] = rodar_powershell_final(baseboard_comando, 'Manufacturer')
    info['Placa_Mae_Produto'] = rodar_powershell_final(baseboard_comando, 'Product')
    
    # 4. Memória RAM
    mem = psutil.virtual_memory()
    info['Memoria_RAM_Total_GB'] = round(mem.total / (1024**3), 2)
    
    # 5. HD/SSD
    try:
        mount_point = 'C:' if platform.system() == 'Windows' else '/'
        usage = psutil.disk_usage(mount_point)
        info['HD_SSD_Tamanho_Total_GB'] = round(usage.total / (1024**3), 2)
    except Exception:
        info['HD_SSD_Tamanho_Total_GB'] = "Falha na Coleta do Disco"
    
    return info


def gerar_arquivo_json(dados):
    """Função que converte o dicionário para JSON e salva em arquivo."""
    
    dados['Data_Exportacao'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"dados_hardware_{timestamp}_simplificado.json"
    
    try:
        json_string = json.dumps(dados, indent=4, ensure_ascii=False)
    except Exception as e:
        return f"Erro ao converter para JSON: {e}", None

    try:
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write(json_string)
            
        caminho_completo = os.path.abspath(nome_arquivo)
        return f"Arquivo salvo com sucesso:\n{caminho_completo}", nome_arquivo
        
    except IOError as e:
        return f"Erro ao salvar o arquivo:\nVerifique as permissões de escrita. Erro: {e}", None

# ----------------------------------------------------
# Classe da Interface Gráfica (Tkinter)
# ----------------------------------------------------

class AplicacaoHardware(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Coletor de Informações de Hardware e Rede")
        self.geometry("650x500") # Aumentando um pouco a janela
        
        self.dados_coletados = {}
        
        self.criar_widgets()
        self.coletar_e_exibir_dados()

    def criar_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Informações do Sistema e Rede", font=("Helvetica", 16, "bold")).pack(pady=10)

        self.texto_dados = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=18, font=("Courier", 10))
        self.texto_dados.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.texto_dados.insert(tk.END, "Coletando informações... aguarde.")
        self.texto_dados.config(state=tk.DISABLED)

        self.btn_exportar = tk.Button(main_frame, text="Exportar para JSON", command=self.exportar_para_json, bg="darkblue", fg="white", font=("Helvetica", 12, "bold"))
        self.btn_exportar.pack(pady=10)
        self.btn_exportar.config(state=tk.DISABLED)

    def formatar_dados_para_exibicao(self, dados):
        """Formata o dicionário de dados em uma string legível."""
        
        texto = "=== Detalhes da Rede ===\n"
        texto += f"Nome da Máquina: **{dados.get('Nome_da_Maquina', 'N/A')}**\n"
        texto += f"Endereço IP Local: **{dados.get('Endereco_IP_Local', 'N/A')}**\n\n"
        
        texto += "=== Detalhes do Hardware e SO ===\n"
        
        # Mapeamento para exibição amigável
        mapeamento = {
            'Sistema_Operacional_Nome': 'Sistema Operacional',
            'Processador_Nome': 'Processador',
            'Memoria_RAM_Total_GB': 'Memória RAM Total',
            'Placa_Mae_Fabricante': 'Placa Mãe (Fabricante)',
            'Placa_Mae_Produto': 'Placa Mãe (Produto)',
            'HD_SSD_Tamanho_Total_GB': 'HD/SSD Tamanho Total'
        }

        for chave_original, rotulo in mapeamento.items():
            valor = dados.get(chave_original, "N/A")
            
            # Adiciona unidade de medida
            if 'GB' in rotulo:
                valor_str = f"{valor} GB"
            else:
                valor_str = valor

            texto += f"{rotulo:<25}: {valor_str}\n"
            
        texto += f"\n[Detalhes Técnicos]\nKernel: {dados.get('Sistema_Operacional_Kernel', 'N/A')}"
        
        return texto

    def coletar_e_exibir_dados(self):
        """Chama a função de coleta e atualiza a interface."""
        try:
            self.texto_dados.config(state=tk.NORMAL)
            self.texto_dados.delete(1.0, tk.END)
            self.texto_dados.insert(tk.END, "Coletando dados... Isso pode levar alguns segundos.")
            self.update()

            dados = obter_dados_hardware()
            self.dados_coletados = dados

            texto_formatado = self.formatar_dados_para_exibicao(dados)
            
            self.texto_dados.delete(1.0, tk.END)
            self.texto_dados.insert(tk.END, texto_formatado)
            self.texto_dados.config(state=tk.DISABLED)
            
            self.btn_exportar.config(state=tk.NORMAL)

        except Exception as e:
            msg = f"Erro fatal ao coletar dados:\n{e}"
            self.texto_dados.delete(1.0, tk.END)
            self.texto_dados.insert(tk.END, msg)
            self.btn_exportar.config(state=tk.DISABLED)
            messagebox.showerror("Erro de Coleta", msg)

    def exportar_para_json(self):
        """Chama a função de exportação e exibe o resultado."""
        if not self.dados_coletados:
            messagebox.showwarning("Aviso", "Nenhum dado foi coletado para exportar.")
            return

        mensagem, nome_arquivo = gerar_arquivo_json(self.dados_coletados)
        
        if nome_arquivo:
            messagebox.showinfo("Exportação Concluída", mensagem)
        else:
            messagebox.showerror("Erro de Exportação", mensagem)


# ----------------------------------------------------
# Inicialização da Aplicação
# ----------------------------------------------------

if __name__ == "__main__":
    app = AplicacaoHardware()
    app.mainloop()