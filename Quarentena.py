import streamlit as st
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

def load_css(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def listar_arquivos():
    st.title("📂 Arquivos em Quarentena")
    st.write("Arquivos disponíveis na pasta.")

    # Carrega variáveis do .env
    load_dotenv()
    AZURE_CONNECTION_STRING = os.environ.get("AZURE_CONNECTION_STRING")
    AZURE_CONTAINER_NAME = os.environ.get("AZURE_CONTAINER_NAME")
    PASTA = os.environ.get("PASTA")

    try:
        # Lista os blobs da pasta
        blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)
        blobs = container_client.list_blobs(name_starts_with=PASTA)

        blobs_ordenados = sorted(
            [{'name': blob.name, 'size': blob.size, 'last_modified': blob.last_modified} for blob in blobs],
            key=lambda b: b['last_modified'],
            reverse=True
        )

        if not blobs_ordenados:
            st.warning("Nenhum arquivo listado.")
        else:
            texto_formatado = ""
            for blob in blobs_ordenados:
                nome = blob['name'].replace(PASTA, '')
                tamanho = blob['size']
                ultima_modificacao = blob['last_modified'].strftime('%d/%m/%Y %H:%M:%S') if blob['last_modified'] else "N/A"

                texto_formatado += (
                    f"📄 Nome: {nome}\n"
                    f"📏 Tamanho: {tamanho / 1024:.2f} KB\n"
                    f"🕒 Última Modificação: {ultima_modificacao}\n"
                    f"{'-'*40}\n"
                )
                
            if not blobs_ordenados:
                st.warning("Nenhum arquivo listado.")
            else:
                total_arquivos = len(blobs_ordenados)

            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"🔢 Total de arquivos: **{total_arquivos}**")
            with col2:
                st.download_button(
                    label="⬇️ Baixar lista .txt",
                    data=texto_formatado,
                    file_name="lista_arquivos.txt",
                    mime="text/plain"
                )

            st.code(texto_formatado.strip(), language="text")
            
            # st.code(texto_formatado.strip(), language="text")
    except Exception as e:
        st.error(f"Erro ao listar arquivos: {e}")

listar_arquivos()
load_css(".streamlit/dashboard.css")
