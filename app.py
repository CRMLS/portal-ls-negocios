import streamlit as st
from supabase import create_client, Client
import pdfplumber
import re
import pandas as pd
import io
import os
from datetime import datetime

# --- CONFIGURAÇÕES DE CONEXÃO (Priorizando Railway) ---
# O uso de os.environ evita o erro de 'StreamlitSecretNotFoundError'
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# Se não encontrar na Railway, tenta o Streamlit (plano B para local)
if not url or not key:
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except:
        pass

# Verifica se as chaves foram carregadas antes de iniciar o Supabase
if not url or not key:
    st.error("❌ Variáveis de conexão não encontradas.")
    st.write(f"Diagnóstico: URL: {'✅ OK' if url else '❌ FALTA'} | KEY: {'✅ OK' if key else '❌ FALTA'}")
    st.info("Verifique se você criou as variáveis SUPABASE_URL e SUPABASE_KEY na aba 'Variables' da Railway.")
    st.stop()

# Inicializa o cliente do Supabase
supabase: Client = create_client(url, key)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Ls Negócios VIP", layout="wide")

# --- FUNÇÕES DE AUTENTICAÇÃO ---
def login():
    st.title("🔑 Acesso ao Portal - Ls Negócios")
    email = st.text_input("E-mail corporativo")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar no Sistema"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            st.rerun()
        except Exception:
            st.error("E-mail ou senha incorretos.")

def cadastrar_usuario(email_novo):
    try:
        # Cria o usuário via API Administrativa do Supabase
        supabase.auth.admin.create_user({
            "email": email_novo,
            "email_confirm": False  # Envia e-mail para o cliente definir a senha
        })
        st.success(f"✅ Convite enviado para: {email_novo}")
    except Exception as e:
        st.error(f"Erro ao cadastrar: {e}")

# --- LÓGICA DO EXTRATOR ---
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
    st.sidebar.write(f"👤 Usuário: **{user_email}**")
    
    if st.sidebar.button("Sair"):
        supabase.auth.sign_out()
        del st.session_state.user
        st.rerun()

    # --- CONTROLE DE ACESSO ADM ---
    # COLOQUE SEU E-MAIL ABAIXO
    ADMIN_EMAIL = "crmquicksale@gmail.com" 
    
    menu = ["📄 Extrator de Contratos"]
    if user_email == ADMIN_EMAIL:
        menu.append("⚙️ Painel ADM")
    
    escolha = st.sidebar.selectbox("Navegação", menu)

    if escolha == "📄 Extrator de Contratos":
        st.title("🚀 Portal de Extração - Ls Negócios")
        arquivos_subidos = st.file_uploader("Upload de PDFs", type="pdf", accept_multiple_files=True)
        if arquivos_subidos:
            lista = [extrair_dados_contrato(arq) for arq in arquivos_subidos]
            df = pd.DataFrame(lista)
            st.dataframe(df)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Baixar Excel", output.getvalue(), "Relatorio_Ls.xlsx")

    elif escolha == "⚙️ Painel ADM":
        st.title("👥 Gestão de Usuários")
        novo_email = st.text_input("E-mail do novo cliente")
        if st.button("Enviar Convite"):
            cadastrar_usuario(novo_email)