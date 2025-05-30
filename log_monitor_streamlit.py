import streamlit as st
import time
import os
import glob
import subprocess
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Logger Xtracta", page_icon="📄")
st.title("📄 Logger Xtracta")

# Inicializa controle
if "captura_iniciada" not in st.session_state:
    st.session_state["captura_iniciada"] = False

# Função para pegar o arquivo de log mais recente
def pegar_ultimo_log():
    arquivos = glob.glob("log_stream_*.txt")
    if not arquivos:
        return None
    return max(arquivos, key=os.path.getctime)

# Função para iniciar o script de captura de log
def iniciar_captura_logs():
    subprocess.Popen(["python", "stream_logs_alerta.py"], shell=True)
    st.session_state["captura_iniciada"] = True

# Botão para iniciar captura
if st.button("🚀 Iniciar Captura de Logs") and not st.session_state["captura_iniciada"]:
    iniciar_captura_logs()
    st.success("🛰️ Captura de logs iniciada!")

# Pega o último arquivo gerado
log_file = pegar_ultimo_log()

if not log_file:
    st.warning("Nenhum arquivo de log encontrado ainda. Clique no botão acima para iniciar.")
else:
    st.success(f"📄 Monitorando: {log_file}")

    with st.expander("📄 Últimos Logs"):
        refresh_rate = st.slider("Atualizar a cada (segundos)", 1, 10, 3)
        st_autorefresh(interval=refresh_rate * 1000, key="log_refresh")

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                texto = "".join(lines[-200:])
                st.text_area("📋 Logs em tempo quase real", value=texto, height=400, key="log_output")

                # Pega as últimas 5 linhas para checar status recente
                ultimas_linhas = lines[-5:] if len(lines) >= 5 else lines

                status_mostrado = False
                for linha in reversed(ultimas_linhas):
                    if "Error code: 429" in linha or "insufficient_quota" in linha:
                        st.error("❗ Detecção de erro 429 (quota excedida)!")
                        status_mostrado = True
                        break
                    elif "Monitoramento interrompido" in linha or "finalizado" in linha:
                        st.success("✅ Monitoramento finalizado com sucesso.")
                        status_mostrado = True
                        break

                if not status_mostrado and len(texto.strip()) == 0:
                    st.info("💤 Aguardando logs...")

        except Exception as e:
            st.error(f"Erro ao ler o log: {e}")
