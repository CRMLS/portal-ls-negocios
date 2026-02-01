import streamlit as st
from supabase import create_client, Client
import pdfplumber
import re
import pandas as pd
import io
import os
from datetime import datetime

# --- CONFIGURAÇÕES DE CONEXÃO (Railway + Supabase) ---
# O código abaixo busca as variáveis de ambiente de forma robusta
url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")

# Verifica se as chaves existem antes de tentar conectar
if not url or not key:
    st.error("❌ Erro de Conexão com o Banco de Dados")
    st.write(f"Verificação técnica: URL: {'✅ OK' if url else '❌ FALTA'} | KEY: {'✅ OK' if key else '❌ FALTA'}")
    st.info("Acesse a aba 'Variables' na Railway e garanta que os nomes SUPABASE_URL e SUPABASE_KEY estão corretos.")
    st.stop()

# Inicializa o cliente do Supabase
try:
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Erro ao inicializar Supabase: {e}")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Ls Negócios VIP", layout="wide")

# --- FUNÇÕES DE AUTENTICAÇÃO ---
def login():
    st.title("🔑 Acesso ao Portal - Ls Negócios")
    st.markdown("Entre com suas credenciais para acessar o extrator.")
    
    email = st.text_input("E-mail corporativo")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar no Sistema"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            st.rerun()
        except Exception:
            st.error("E-mail ou senha incorretos. Verifique seus dados.")

def cadastrar_usuario(email_novo):
    try:
        # Cria o usuário via API Administrativa do Supabase
        supabase.auth.admin.create_user({
            "email": email_novo,
            "email_confirm": False  # Envia e-mail para o cliente confirmar
        })
        st.success(f"✅ Convite enviado para: {email_novo}")
    except Exception as e:
        st.error(f"Erro ao cadastrar: {e}")

# --- LÓGICA DO EXTRATOR (Sua lógica original) ---
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

# --- CONTROLE DE FLUXO PRINCIPAL ---
if "user" not in st.session_state:
    login()
else:
    user_email = st.session_state.user.email
    st.sidebar.write(f"👤 Conectado: **{user_email}**")
    
    if st.sidebar.button("Sair do Sistema"):
        supabase.auth.sign_out()
        del st.session_state.user
        st.rerun()

    # --- CONTROLE DE ACESSO ADM ---
    # COLOQUE SEU E-MAIL ABAIXO PARA TER ACESSO AO PAINEL DE CADASTRO
    ADMIN_EMAIL = "crmquicksale@gmail.com" 
    
    menu = ["📄 Extrator de Contratos"]
    if user_email == ADMIN_EMAIL:
        menu.append("⚙️ Painel ADM")
    
    escolha = st.sidebar.selectbox("Navegação", menu)

    if escolha == "📄 Extrator de Contratos":
        st.title("🚀 Portal de Extração - Ls Negócios")
        st.markdown("Extração de dados de contratos de Loteamentos.")

        arquivos_subidos = st.file_uploader("Escolha os contratos (PDF)", type="pdf", accept_multiple_files=True)

        if arquivos_subidos:
            lista_resultados = []
            with st.spinner('Processando contratos...'):
                for arq in arquivos_subidos:
                    resultado = extrair_dados_contrato(arq)
                    lista_resultados.append(resultado)
            
            df = pd.DataFrame(lista_resultados)
            st.success(f"{len(arquivos_subidos)} arquivos processados!")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Baixar Planilha Excel",
                data=output.getvalue(),
                file_name="Relatorio_Ls_Negocios.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    elif escolha == "⚙️ Painel ADM":
        st.title("👥 Gestão de Usuários")
        st.write("Cadastre novos clientes para que eles recebam um convite por e-mail.")
        
        novo_email = st.text_input("E-mail do novo usuário")
        if st.button("Enviar Convite"):
            if novo_email:
                cadastrar_usuario(novo_email)
            else:
                st.warning("Por favor, digite um e-mail válido.")