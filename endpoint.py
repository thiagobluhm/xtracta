from fastapi import FastAPI, Query
import os
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from azure.storage.blob import BlobServiceClient
import httpx
from dotenv import load_dotenv
from io import BytesIO
from tqdm import tqdm
import base64
import logging
import pandas as pd

from XtractaCuratorClass import (
    BlobUtils, 
    OpenAIVisionExtractor, 
    PDFProcessor, 
    ImageProcessor, 
    TextFormatter, 
    RecorteAnalyzer, 
    CSVBuilder, 
    ProcessamentoFinal, 
    AzureBlobHandler
)

load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# Suprimir logs detalhados da Azure SDK
logging.getLogger("azure").setLevel(logging.ERROR)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

from fastapi import FastAPI

app = FastAPI(
    title="Xtracta Curador App API 🚀",
    description="API para extração e processamento de documentos com IA e Azure Blob Storage.",
    version="2.0.0",
    contact={
        "name": "Time de IA - Grupo Portfolio",
        "url": "https://grupoporfolio.com.br",
        "email": "thiago.bluhm@portfoliotech.com.br"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    terms_of_service="https://grupoportfolio.com.br/fale-conosco/"
)

@app.post("/extrai-logo")
async def extrair_e_processar(
    modo: str = Query("h"),
    input_folder: str = Query("1988"),
    destino_planilha: str = Query("teste"),
    destino_final: str = Query("teste"),
    quarantine_folder: str = Query("Quarentena")
):
    textos_extraidos = []
    nomes_arquivos = []
    
    AZURE_CONNECTION_STRING = os.environ.get("AZURE_CONNECTION_STRING")
    CONTAINER_NAME = os.environ.get("AZURE_CONTAINER_NAME")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

    logger.info(f"🔍 AZURE_CONNECTION_STRING: {AZURE_CONNECTION_STRING}")
    logger.info(f"🧭 Modo de execução: {'Produção' if modo != 'h' else 'Homologação'}")

    # Async Blob Client
    async_blob_service = AsyncBlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    container_client = async_blob_service.get_container_client(CONTAINER_NAME)

    vision = OpenAIVisionExtractor(OPENAI_API_KEY)
    formatter = TextFormatter(OPENAI_API_KEY)
    analyzer = RecorteAnalyzer()
    blob_handler = AzureBlobHandler(modo, AZURE_CONNECTION_STRING, CONTAINER_NAME)  # ainda sync
    builder = CSVBuilder(destino_planilha, destino_final, formatter, analyzer, blob_handler)
    finalizador = ProcessamentoFinal(blob_handler, builder, modo)

    blobs = []
    async for blob in container_client.list_blobs(name_starts_with=input_folder):
        if not blob.name.endswith(".keep"):
            blobs.append(blob)

    logger.info(f"🔍 Total de arquivos encontrados: {len(blobs)}")
    if len(blobs) == 0:
        logger.info("📭 Nenhum arquivo para processar.")
        return {
            "mensagem": "Recebemos uma chamada com sucesso",
            "quantidade": f"Porém nenhuma imagem foi entregue: {len(blobs)}"
        }
    else:
        logger.info(f"📦 {len(blobs)} arquivos encontrados. Iniciando processamento...")

    for blob in tqdm(blobs, desc="Processando arquivos do Blob"):
        blob_name = blob.name
        logger.info(f"📥 Processando: {blob_name}")
        blob_client = container_client.get_blob_client(blob_name)
        stream = await blob_client.download_blob()
        data = await stream.readall()

        if blob_name.lower().endswith(".pdf"):
            imagens = PDFProcessor.to_images(data)
            logger.info(f"📄 Total de páginas convertidas do PDF {blob_name}: {len(imagens)}")
        else:
            imagens = [data]
            logger.info(f"🖼️ Imagem única detectada no arquivo: {blob_name}")

        paginas_falhas = []

        for i, imagem in enumerate(imagens):
            try:
                b64_image = base64.b64encode(imagem).decode("utf-8")
                texto = await vision.extract_text_from_image(b64_image, f"{blob_name}_page_{i+1}")

                if texto:
                    textos_extraidos.append(texto)
                    nomes_arquivos.append(f"{blob_name}_page_{i+1}")
                else:
                    paginas_falhas.append(i + 1)
                    logger.warning(f"⚠️ Texto da página {i+1} do arquivo {blob_name} não pôde ser extraído.")
            except Exception as e:
                logger.warning(f"❌ Erro ao processar página {i+1} de {blob_name}: {e}")
                paginas_falhas.append(i + 1)

        if paginas_falhas:
            novo_nome = blob_name.replace(input_folder, quarantine_folder)
            try:
                await container_client.get_blob_client(novo_nome).start_copy_from_url(blob_client.url)
                await blob_handler.alterar_tier(novo_nome, tier="Archive")  # ✅ Muda tier da cópia na quarentena
                logger.warning(f"🚨 {blob_name} também copiado para quarentena por falhas nas páginas {paginas_falhas}")
            except Exception as e:
                logger.error(f"❌ Erro ao mover {blob_name} para quarentena: {e}")

    if not textos_extraidos:
        logger.warning("⚠️ Nenhum texto foi extraído de nenhum arquivo.")
        return {"mensagem": "Nenhum texto extraído."}

    logger.info(f"📦 Total de textos extraídos: {len(textos_extraidos)}")

    filename, buffer, df, sucesso = await builder.build(
        textos_extraidos,
        nomes_arquivos,
        input_folder,
        destino_planilha,
        destino_final
    )

    if sucesso:
        sucesso_salvo = await finalizador.salvar_planilha_e_mover(
            filename,
            buffer,
            input_folder,
            destino_planilha,
            destino_final
        )

        if sucesso_salvo:
            return {
                "mensagem": "Processamento finalizado com sucesso",
                "arquivo": f"{builder.planilha_destino}/{filename}.xlsx"
            }
        else:
            logger.error("❌ Erro ao salvar a planilha.")
            return {"mensagem": "Erro ao salvar planilha."}

    logger.error("❌ Erro ao gerar planilha.")
    return {"mensagem": "Erro ao gerar planilha."}
