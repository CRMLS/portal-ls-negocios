import streamlit as st
import pdfplumber
import re
import pandas as pd
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Ls Negócios", layout="wide") 

# --- FUNÇÃO DE LOGIN ---
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    def password_entered():
        # Verificação da senha
        if st.session_state["password"] == "ls2026":  # <--- VOCÊ PODE ALTERAR SUA SENHA AQUI
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Acesso Restrito - LS Negócios")
        st.text_input("Digite a senha para acessar o portal:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acesso Restrito - LS Negócios")
        st.text_input("Digite a senha para acessar o portal:", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta. Tente novamente.")
        return False
    else:
        return True

# --- FUNÇÃO DE EXTRAÇÃO (Sua lógica de loteamentos) ---
def extrair_dados_contrato(file):
    try:
        with pdfplumber.open(file) as pdf:
            primeira_pagina = pdf.pages[0]
            texto = primeira_pagina.extract_text()
        
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        padroes = {
            "Unidade": r"UNIDADE nº\s*(.*?)(?=\s+TIPO:|\n|$)",
            "Nome": r"Nome:\s*(.*?)(?=\n|Data de Nascimento|$)",
            "Data de Nascimento": r"Data de Nascimento:\s*(\d{2}/\d{2}/\d{4})",
            "Estado Civil": r"Estado Civil:\s*(.*?)(?=\s+Nacionalidade|CPF|Nome do Conjugue|\n|$)",
            "Nacionalidade": r"Nacionalidade:\s*(\w+)",
            "CPF": r"CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})",
            "Endereço Residencial": r"Endereço Residencial:\s*(.*?)(?=\n|Bairro|$)",
            "Bairro": r"Bairro:\s*(.*?)(?=\n|Telefone|Cidade|$)",
            "Cidade": r"Cidade:\s*(.*?)(?=\s+UF:|$)",
            "UF": r"UF:\s*([A-Z]{2})",
            "CEP": r"CEP:\s*(\d{5}-\d{3})",
            "E-mail": r"Email:\s*(\S+)",
            "Valor Total": r"Valor Total:\s*(R\$\s*[\d\.,]+)"
        }

        dados = {"Data Processamento": agora, "Arquivo": file.name}
        
        for campo, regex in padroes.items():
            match = re.search(regex, texto, re.IGNORECASE)
            if match:
                valor = match.group(1).strip()
                valor = re.split(r'Nacionalidade|CPF|TIPO:|UF:|Bairro|Telefone', valor, flags=re.IGNORECASE)[0].strip()
                dados[campo] = valor
            else:
                dados[campo] = "Não encontrado"

        if "feminino" in texto.lower(): dados["Sexo"] = "feminino"
        elif "masculino" in texto.lower(): dados["Sexo"] = "masculino"
        else: dados["Sexo"] = "Não encontrado"
        
        return dados
    except Exception as e:
        return {"Arquivo": file.name, "Erro": str(e)}

# --- EXECUÇÃO DO PORTAL (Conteúdo Protegido) ---
if check_password():
    # Barra lateral com opção de Sair
    if st.sidebar.button("Sair / Bloquear"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.title("🚀 Portal de Extração - Ls Negócios")
    st.subheader("Extração de dados de contratos de Loteamentos")
    st.markdown("Faça o upload dos contratos em PDF para gerar a planilha consolidada.")

    # Área de Upload
    arquivos_subidos = st.file_uploader("Escolha os contratos (PDF)", type="pdf", accept_multiple_files=True)

    if arquivos_subidos:
        lista_resultados = []
        with st.spinner('Processando contratos...'):
            for arq in arquivos_subidos:
                resultado = extrair_dados_contrato(arq)
                lista_resultados.append(resultado)
        
        df = pd.DataFrame(lista_resultados)
        
        # Exibe na tela
        st.success(f"{len(arquivos_subidos)} arquivos processados com sucesso!")
        st.dataframe(df)

        # Botão de Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Baixar Planilha Excel",
            data=output.getvalue(),
            file_name="Relatorio_Ls_Negocios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )