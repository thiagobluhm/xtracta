import streamlit as st
import streamlit_authenticator as stauth
from yaml import safe_load
from stream_logs_alerta import logs_alerta

# Configuração de usuários e senhas (hash SHA512 gerado antes)
with open('./config.yaml') as file:
    config = safe_load(file)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

name, auth_status, username = authenticator.login('Login', 'main')

if auth_status is False:
    st.error("Usuário ou senha incorretos.")
elif auth_status is None:
    st.warning("Por favor, insira suas credenciais.")
elif auth_status:
    st.sidebar.success(f"Bem-vindo, {name} 👋")
    authenticator.logout("Logout", "sidebar")

    # Aqui vai seu app    
    logs_alerta()