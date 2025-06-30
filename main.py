# # main.py (Autenticador e Loader do App)

# import streamlit as st
# import streamlit_authenticator as stauth
# from stream_logs_alerta import logs_alerta
# from dotenv import load_dotenv
# import os

# # Precisa ser o primeiro comando Streamlit
# st.set_page_config(page_title="Xtracta App", layout="wide")

# # Força modo escuro para evitar problemas com legibilidade
# st.markdown("""
#     <style>
#     html, body, [data-testid="stAppViewContainer"] {
#         background-color: #0b0f1a !important;
#         color: #e5e7eb !important;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # Carrega CSS
# def load_css(css_file):
#     with open(css_file) as f:
#         st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# # Carrega variáveis do ambiente (.env)
# load_dotenv()
# password_hash = os.environ.get("THIAGO_PASSWORD_HASH")
# password_hash2 = os.environ.get("VISITANTE_PASSWORD_HASH")

# # Configura login
# config = {
#     'credentials': {
#         'usernames': {
#             'thiago': {
#                 'email': 'thiagobluhm@gmail.com',
#                 'name': 'Thiago Bluhm',
#                 'password': password_hash
#             },
#             'visitante': {
#                 'email': 'visitante@portfoliotech.com',
#                 'name': 'Visitante Xtracta',
#                 'password': password_hash2
#             }
#         }
#     },
#     'cookie': {
#         'name': 'xtracta_login',
#         'key': 'supersecretkey123',
#         'expiry_days': 1
#     }
# }

# # Inicializa autenticação
# authenticator = stauth.Authenticate(
#     config['credentials'],
#     config['cookie']['name'],
#     config['cookie']['key'],
#     config['cookie']['expiry_days'],
# )

# # Login
# name, auth_status, username = authenticator.login()

# if auth_status is False:
#     st.error("Usuário ou senha incorretos.")
# elif auth_status is None:
#     load_css(".streamlit/login.css")
#     st.warning("Por favor, insira suas credenciais.")
# elif auth_status:
#     # Logo responsiva IQJ
#     st.sidebar.markdown(
#         """
#         <div style="padding: 0 10px;">
#             <img src="https://www.institutoqueirozjereissati.org.br/wp-content/uploads/2024/07/IQJ.png"
#                 style="width: 100%; height: auto; display: block; margin: 0 auto; max-width: 100%;" />
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     st.sidebar.success(f"Bem-vindo, {name} 👋")
#     authenticator.logout("Logout", "sidebar")
#     load_css(".streamlit/dashboard.css")
#     logs_alerta()

# Precisa ser o primeiro comando Streamlit


import streamlit as st
import streamlit_authenticator as stauth
from stream_logs_alerta import logs_alerta
from Quarentena import listar_arquivos
from dotenv import load_dotenv
import os

st.set_page_config(page_title="Xtracta App", initial_sidebar_state="expanded")

# Carrega CSS
def load_css(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(".streamlit/dashboard.css")

# Carrega variáveis do ambiente (.env)
load_dotenv()
password_hash = os.environ.get("THIAGO_PASSWORD_HASH")
password_hash2 = os.environ.get("VISITANTE_PASSWORD_HASH")

# Configura login
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

# Login
name, auth_status, username = authenticator.login()

if auth_status is False:
    st.error("Usuário ou senha incorretos.")
elif auth_status is None:
    st.warning("Por favor, insira suas credenciais.")
else:
    # Exibe elementos estáticos na sidebar primeiro
    with st.sidebar:
        # Adiciona uma imagem (local ou externa)
        st.image(
            "https://www.institutoqueirozjereissati.org.br/wp-content/uploads/2024/07/IQJ.png",
            use_container_width=True
        )
        st.markdown(f"### Bem-vindo, {name} 👋")
        authenticator.logout("Logout", "sidebar")

    # Navegação
    paginas = ["📄 Logs Formatados", "📂 Arquivos em Quarentena"]
    pagina = st.sidebar.radio("Navegação", paginas, index=0)

    # Carrega as páginas com base na seleção
    if pagina == "📄 Logs Formatados":
        logs_alerta()
    elif pagina == "📂 Arquivos em Quarentena":
        listar_arquivos()
