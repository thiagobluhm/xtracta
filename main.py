import streamlit as st
import streamlit_authenticator as stauth
from yaml import safe_load
from stream_logs_alerta import logs_alerta
from dotenv import load_dotenv
import os

# Precisa vir antes de qualquer comando Streamlit
st.set_page_config(page_title="Xtracta App", layout="wide")

def load_css(css_file):
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Carrega variáveis de ambiente
load_dotenv()
password_hash = os.environ.get("THIAGO_PASSWORD_HASH")
password_hash2 = os.environ.get("VISITANTE_PASSWORD_HASH")

# Configurações de autenticação
config = {
    'credentials': {
        'usernames': {
            'thiago': {
                'email': 'thiagobluhm@gmail.com',
                'name': 'Thiago Bluhm',
                'password': password_hash
            },
            'visitante': {
                'email': 'visitante@portfoliotech.com',
                'name': 'Visitante Xtracta',
                'password': password_hash2
            }
        }
    },
    'cookie': {
        'name': 'xtracta_login',
        'key': 'supersecretkey123',
        'expiry_days': 1
    }
}

# Inicializa autenticação
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

# Tela de login
name, auth_status, username = authenticator.login()

# Tratamento do status de login
if auth_status is False:
    st.error("Usuário ou senha incorretos.")

elif auth_status is None:
    load_css(".streamlit/login.css")
    st.warning("Por favor, insira suas credenciais.")

elif auth_status:
    # Logo do IQJ na sidebar
    st.sidebar.markdown(
        """
        <div style="margin-bottom: 1rem; padding: 0 10px;">
            <img src="https://www.institutoqueirozjereissati.org.br/wp-content/uploads/2024/07/IQJ.png"
                style="width: 100%; height: auto; display: block; margin: 0 auto;" />
        </div>
        """,
        unsafe_allow_html=True
    )

    # Boas-vindas e logout
    st.sidebar.success(f"Bem-vindo, {name}")
    authenticator.logout("Logout", "sidebar")

    # Carrega visual do dashboard
    load_css(".streamlit/dashboard.css")

    # Chamada do app principal
    logs_alerta()
