import streamlit as st
import os
import json
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from streamlit_autorefresh import st_autorefresh


# Logo na sidebar
st.sidebar.image(
    "https://www.institutoqueirozjereissati.org.br/wp-content/uploads/2024/07/IQJ.png",
    use_column_width=True
)

def logs_alerta():
    st.title("📄 Logger Xtracta")
    st.write("Página com refresh a cada 10 segundos.")

    # Atualiza automaticamente a cada 10 segundos
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

            # Processa conteúdo
            linhas = blob_content.strip().split("\n")
            texto_formatado = ""

            for linha in linhas:
                try:
                    obj = json.loads(linha)
                    timestamp = obj.get("time", "")
                    descricao = obj.get("resultDescription", "")
                    if timestamp and descricao:
                        texto_formatado += f"🕒 {timestamp}\nINFO:  {descricao}\n\n"
                except json.JSONDecodeError:
                    continue

            if texto_formatado.strip() == "":
                texto_formatado = "⚠️ Nenhum conteúdo formatado encontrado."

            st.subheader("📋 Conteúdo Formatado")
            st.code(texto_formatado.strip(), language="text")

            st.success(f"📄 Último log: `{blob_mais_recente.name.split('SITES/')[-1]}`")

            st.download_button(
                label="📥 Baixar como .TXT",
                data=texto_formatado,
                file_name="log_stream_formatado.txt",
                mime="text/plain"
            )

    except Exception as e:
        st.error(f"❌ Erro ao acessar ou processar blob: {e}")


# Roda se estiver sendo executado diretamente
# if __name__ == "__main__":
#     logs_alerta()