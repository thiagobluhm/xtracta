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
# Configurações de autenticação (sem 'preauthorized')
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
        'key': 'supersecretkey123',
        'expiry_days': 1
    }
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)


name, auth_status, username = authenticator.login()


if auth_status is False:
    st.error("Usuário ou senha incorretos.")
elif auth_status is None:
    st.warning("Por favor, insira suas credenciais.")
    st.write(auth_status)
elif auth_status:
    st.sidebar.success(f"Bem-vindo, {name} 👋")
    authenticator.logout("Logout", "sidebar")

    # Aqui vai seu app    
    logs_alerta()

# import streamlit_authenticator as stauth
# hashes = stauth.Hasher(['Ogaith@248#$']).generate()
# print(hashes[0])