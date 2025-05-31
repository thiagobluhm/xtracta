import streamlit as st
import streamlit_authenticator as stauth
from yaml import safe_load
from stream_logs_alerta import logs_alerta
from dotenv import load_dotenv
import os

# Configuração de usuários e senhas (hash SHA512 gerado antes)
# Carrega variáveis do .env
load_dotenv()

password_hash = os.environ.get("THIAGO_PASSWORD_HASH")
config = {
    'credentials': {
        'usernames': {
            'thiago': {
                'email': 'thiagobluhm@gmail.com',
                'name': 'Thiago Bluhm',
                'password': password_hash
            }
        }
    },
    'cookie': {
        'name': 'xtracta_login',
        'key': 'supersecretkey123',  # Troque por uma key mais segura em produção
        'expiry_days': 1
    },
    'preauthorized': {
        'emails': []
    }
}

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

