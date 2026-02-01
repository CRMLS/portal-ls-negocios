import streamlit as st
from supabase import create_client, Client
import pdfplumber
import re
import pandas as pd
import io
from datetime import datetime

# --- CONFIGURAÇÕES DO SUPABASE (Lendo da Railway) ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro nas credenciais do banco de dados. Verifique as variáveis na Railway.")
    st.stop()

st.set_page_config(page_title="Portal Ls Negócios VIP", layout="wide")

# --- FUNÇÕES DE AUTENTICAÇÃO ---
def login():
    st.title("🔑 Acesso ao Portal - Ls Negócios")
    email = st.text_input("Seu E-mail")
    password = st.text_input("Sua Senha", type="password")
    if st.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            st.rerun()
        except Exception as e:
            st.error("E-mail ou senha inválidos. Se você for novo, verifique seu e-mail para criar uma senha.")

def cadastrar_usuario(email_novo):
    try:
        # Cria o usuário e envia e-mail de confirmação automaticamente
        supabase.auth.admin.create_user({
            "email": email_novo,
            "email_confirm": False # O cliente precisará confirmar no e-mail dele
        })
        st.success(f"✅ Convite enviado com sucesso para: {email_novo}")
    except Exception as e:
        st.error(f"Erro ao cadastrar: {e}")

# --- LÓGICA DO EXTRATOR (Sua função atual) ---
def extrair_dados_contrato(file):
    try:
        with pdfplumber.open(file) as pdf:
            primeira_pagina = pdf.pages[0]
            texto = primeira_pagina.extract_text()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        padroes = {
            "Unidade": r"UNIDADE nº\s*(.*?)(?=\s+TIPO:|\n|$)",
            "Nome": r"Nome:\s*(.*?)(?=\n|Data de Nascimento|$)",
            "CPF": r"CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})",
            "Valor Total": r"Valor Total:\s*(R\$\s*[\d\.,]+)"
        }
        dados = {"Data Processamento": agora, "Arquivo": file.name}
        for campo, regex in padroes.items():
            match = re.search(regex, texto, re.IGNORECASE)
            dados[campo] = match.group(1).strip() if match else "Não encontrado"
        return dados
    except Exception as e:
        return {"Arquivo": file.name, "Erro": str(e)}

# --- INTERFACE PRINCIPAL ---
if "user" not in st.session_state:
    login()
else:
    user_email = st.session_state.user.email
    st.sidebar.write(f"👤 {user_email}")
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        del st.session_state.user
        st.rerun()

    # --- CONTROLE DE ACESSO ADM ---
    # MUDE O E-MAIL ABAIXO PARA O SEU E-MAIL REAL!
    ADMIN_EMAIL = "crmquicksale@gmail.com" 
    
    menu = ["Extrator de Contratos"]
    if user_email == ADMIN_EMAIL:
        menu.append("⚙️ Painel ADM")
    
    escolha = st.sidebar.selectbox("Navegação", menu)

    if escolha == "Extrator de Contratos":
        st.title("📄 Extrator de Contratos - Loteamentos")
        arquivos_subidos = st.file_uploader("Escolha os PDFs", type="pdf", accept_multiple_files=True)
        if arquivos_subidos:
            lista = [extrair_dados_contrato(arq) for arq in arquivos_subidos]
            df = pd.DataFrame(lista)
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Baixar Excel", output.getvalue(), "Relatorio_Ls.xlsx")

    elif escolha == "⚙️ Painel ADM":
        st.title("👥 Gestão de Usuários (Ls Negócios)")
        novo_email = st.text_input("E-mail do novo cliente/parceiro")
        if st.button("Enviar Convite e Criar Acesso"):
            cadastrar_usuario(novo_email)
            st.info("O cliente receberá um e-mail para confirmar a conta.")