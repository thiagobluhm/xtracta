import streamlit as st
import os
import json
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from streamlit_autorefresh import st_autorefresh

# Configura layout largo
st.set_page_config(page_title="Log Stream Formatado", page_icon="📄", layout="wide")
st.title("📄 Logger Xtracta")
st.write("Página com refresh de 10/10 segundos.")
# 🔄 Atualiza automaticamente a cada 60 segundos
st_autorefresh(interval=10 * 1000, key="log_auto_refresh")
# Carrega variáveis do .env
load_dotenv()
AZURE_CONNECTION_STRING = os.environ.get("AZURE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.environ.get("AZURE_CONTAINER_NAME_LOGS")


try:
    # Conecta ao Blob Storage
    blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)

    # Lista apenas arquivos .json
    blobs = container_client.list_blobs()
    json_blobs = [b for b in blobs if b.name.endswith(".json")]

    if not json_blobs:
        st.warning("Nenhum arquivo .json encontrado.")
    else:
        # Seleciona o blob mais recente
        blob_mais_recente = sorted(json_blobs, key=lambda b: b.last_modified)[-1]
        blob_client = container_client.get_blob_client(blob_mais_recente.name)
        blob_content = blob_client.download_blob().readall().decode("utf-8", errors="ignore")
        
        linhas = blob_content.strip().split("\n")
        texto_formatado = ""

        for linha in linhas:
            try:
                obj = json.loads(linha)
                timestamp = obj.get("time", "")
                descricao = obj.get("resultDescription", "")
                if timestamp and descricao:
                    texto_formatado += f"🕒 {timestamp}\n{descricao}\n\n"
            except json.JSONDecodeError:
                continue

        if texto_formatado.strip() == "":
            texto_formatado = "⚠️ Nenhum conteúdo formatado encontrado."

        st.subheader("📋 Conteúdo Formatado")
        st.text_area("Log Processado", value=texto_formatado.strip(), height=400)
        st.success(f"📄 Último log: `{blob_mais_recente.name.split("SITES/")[1]}`")
        st.download_button(
            label="📥 Baixar como .TXT",
            data=texto_formatado,
            file_name="log_stream_formatado.txt",
            mime="text/plain"
        )

except Exception as e:
    st.error(f"❌ Erro ao acessar ou processar blob: {e}")

# # Variáveis da Azure
# webapp = os.environ.get("WEBAPP_NM")
# resource_group = os.environ.get("R_GROUP")


# # Comando para tail do log
# cmd = f"az webapp log tail --name {webapp} --resource-group {resource_group}" ##<<<<<<<

# print("📡 Monitorando logs em tempo real...")

# with open(log_file, "w", encoding="utf-8") as f:
#     process = subprocess.Popen(
#         cmd,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         shell=True,
#         text=True  # Faz o decode automático!
#     )

#     try:
#         for line in iter(process.stdout.readline, ''):
#             if line == '':
#                 break  # EOF
#             line = line.strip()
#             print(line)
#             #f.write(line + "\n")
#             #f.flush()  # ESSENCIAL: força a gravação no disco imediatamente

#             # Detecta erro 429
#             if "Error code: 429" in line or "insufficient_quota" in line:
#                 alerta = "🔴 ALERTA: Erro 429 detectado!"
#                 print(alerta)
#                 #f.write(alerta + "\n")
#                 #f.flush()

#     except KeyboardInterrupt:
#         print("🛑 Monitoramento interrompido pelo usuário.")
#         process.terminate()
