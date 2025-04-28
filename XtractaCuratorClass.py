# ================================================================================================================================
# AUTHOR: THIAGO BLUHM | v1.17 | DATA MODIFIED: 17/04/2025
# *-************************************ CLASSE DE EXTRACAO DE FEATURES DE RECORTES DE JORNAIS *********************************-*
# BIBILIOTECAS UTILIZADAS ========================================================================================================

from azure.storage.blob import BlobServiceClient
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from azure.core.exceptions import ResourceExistsError
import asyncio
import cv2
import numpy as np
import io
import openpyxl
from pdf2image import convert_from_bytes
from tqdm import tqdm
import openai
from openai import OpenAI
from openai import AsyncOpenAI
import re
import pandas as pd
import base64
import requests
import tempfile
import os 
os.chdir(os.path.abspath(os.curdir))
from io import BytesIO
from time import time
import fitz
from PIL import Image
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ================================================================================================================================
# ================================================================================================================================
# ************************************** CLASSE DE EXTRACAO DE FEATURES DE RECORTES DE JORNAIS *********************************-*

# === AUXILIARES ===
def split_filename_page(name):
    if "_page_" in name:
        parts = name.split("_page_")
        return parts[0].split("/")[-1], f"pagina_{parts[1]}"
    return name.split("/")[-1], ""

def configurar_client_openai(chave):
    openai.api_key = chave
    return openai.api_key    

def get_client_api_openai(chave):
    return OpenAI(api_key=chave)

# === DECORATORS ===
def safe_run(func):
    # Evita que o programa morra por completo quando alguma parte falha.
    # Sempre executa, mas pode retornar None caso haja erro.
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Erro na função {func.__name__}: {e}")
            return None
    return wrapper

# === BLOB UTILITARIOS ===
class BlobUtils:
    @staticmethod
    def read_blob(container_client, blob_name):
        blob_client = container_client.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    @staticmethod
    def upload_blob(container_client, blob_name, data):
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=True)

    @staticmethod
    def delete_blobs_in_folder_except_marker(container_client, folder_path, marker_file=".keep"):
        blobs = container_client.list_blobs(name_starts_with=folder_path)
        for blob in blobs:
            blob_name = blob.name
            if blob_name.endswith(marker_file):
                print(f"📌 Mantendo marcador: {blob_name}")
                continue
            blob_client = container_client.get_blob_client(blob_name)
            try:
                blob_client.delete_blob()
                print(f"🗑️  Blob deletado: {blob_name}")
            except Exception as e:
                print(f"⚠️ Erro ao deletar {blob_name}: {str(e)}")
        try:
            container_client.upload_blob(name=f"{folder_path}/.keep", data="", overwrite=True)
            print(f"📂 Pasta recriada com marcador .keep")
        except Exception as e:
            print(f"⚠️ Erro ao criar marcador da pasta: {e}")

# === BLOB SERVICE WRAPPER ===
class AzureBlobHandler:
    def __init__(self, modo, connection_string, container_name):
        if not connection_string:
            raise ValueError("⚠️ connection_string está vazia. Verifique as variáveis de ambiente.")
        self.client = AsyncBlobServiceClient.from_connection_string(connection_string).get_container_client(container_name)
        self.modo = modo

    @safe_run
    async def alterar_tier(self, blob_path, tier="Archive"):
        blob_client = self.client.get_blob_client(blob_path)
        try:
            blob_client.set_standard_blob_tier(tier)
            print(f"❄️ Tier de armazenamento alterado para {tier} para o blob: {blob_path}")
        except Exception as e:
            print(f"❌ Erro ao alterar tier para {blob_path}: {e}")

    @safe_run
    async def upload_blob(self, blob_path, data, overwrite=False):
        """Envia um blob para o container."""
        blob_client = self.client.get_blob_client(blob_path)
        try:
            await blob_client.upload_blob(data, overwrite=overwrite)
            print(f"✅ Blob enviado: {blob_path} (overwrite={overwrite})")
        except ResourceExistsError:
            print(f"⚠️ Blob já existe e overwrite=False: {blob_path}")

    @safe_run
    async def ensure_folder(self, path):
        """Garante que a 'pasta' exista criando um marcador .keep."""
        blob_path = f"{path}/.keep"
        blob = self.client.get_blob_client(blob_path)
        try:
            await blob.upload_blob(b"", overwrite=True)
        except Exception:
            pass
        return blob_path

    @safe_run
    async def delete_folder(self, folder, marker_file=".keep"):
        """Deleta todos os blobs dentro de uma 'pasta', exceto o .keep."""
        async for blob in self.client.list_blobs(name_starts_with=folder):
            if blob.name.endswith(marker_file):
                print(f"📌 Mantendo marcador: {blob.name}")
                continue
            await self.client.get_blob_client(blob.name).delete_blob()
            print(f"🗑️  Blob deletado: {blob.name}")
        await self.ensure_folder(folder)

    @safe_run
    async def list_real_blobs(self, prefix):
        """Lista blobs ignorando arquivos .keep"""
        blobs = []
        async for blob in self.client.list_blobs(name_starts_with=prefix):
            if not blob.name.endswith(".keep"):
                blobs.append(blob)
        return blobs

    @safe_run
    async def copy_blob(self, src, dst, delete_origin=False):
        """Copia blob de src para dst. Apaga o original se `delete_origin` for True."""
        src_blob = self.client.get_blob_client(src)
        dst_blob = self.client.get_blob_client(dst)
        await dst_blob.start_copy_from_url(src_blob.url)

        for _ in range(10):  # tenta por até 10 segundos
            props = await dst_blob.get_blob_properties()
            if props.copy.status == "success":
                print(f"✅ {src} copiado para {dst}")
                if delete_origin:
                    await self.client.get_blob_client(src).delete_blob()
                    print(f"🗑️ {src} deletado após cópia.")
                return True
            elif props.copy.status in ["pending", "running"]:
                await asyncio.sleep(1)
            else:
                print(f"❌ Falha ao copiar {src} para {dst}")
                return False

        print(f"⚠️ Tempo esgotado para copiar {src} para {dst}")
        return False

    @safe_run
    async def move_blob(self, src, dst, delete_origin=False):
        """Copia o blob e, se `delete_origin=True`, remove o original."""
        success = await self.copy_blob(src, dst)
        if success and delete_origin:
            await self.client.get_blob_client(src).delete_blob()
            print(f"🗑️ {src} deletado após cópia.")
        return success

# === PROCESSADORES DE ARQUIVOS ===
class ImageProcessor:
    @staticmethod
    def to_grayscale(image_data):
        img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, encoded = cv2.imencode('.png', gray)
        return encoded.tobytes()

    @staticmethod
    def encode_base64(image_data):
        return base64.b64encode(image_data).decode('utf-8')

# === VISION PROCESSOR ===
class OpenAIVisionExtractor:
    def __init__(self, api_key):
        self.client = AsyncOpenAI(api_key=api_key)

    async def extract_text_from_image(self, base64_image: str, filename: str):
        prompt_text = ("""Você é um excelente historiador e arquivista experiente. Sua tarefa é de CURADORIA e assim precisa\n
                          ler documentos antigos, manchetes de jornais e extrair toda informação possível dessas imagens,\n
                          IMPORTANTE INICIAR A EXTRAÇÃO DO TOPO AO RODAPÉ da imagem seguindo a ordem de cima para baixo,\n
                          capture a fonte da manchete que é o nome do jornal, pegar a DATA que aparece no texto seja da publicação ou de\n
                          algum fato, MUITO IMPORTANTE é o nome do autor do texto sendo àquele que escreveu ou falou de algo ou alguém,\n
                          título da manchete, o texto da manchete, até chegar no rodapé. Não invente nada. Responda em português do Brasil.\n"
                          "IMPORTANTE: Faça uma verificação ortográfica."""
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                temperature=0.2,
                max_tokens=4096
            )

            content = response.choices[0].message.content

            if not content or len(content.split()) < 5:
                print(f"⚠️ Falha no OCR para {filename}. Resultado: {content}")
                return None

            return content

        except Exception as e:
            print(f"❌ Erro ao chamar a OpenAI API para {filename}: {e}")
            return None

# === PDF Extract
class PDFProcessor:
    @staticmethod
    def to_images(pdf_data, dpi=150):
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        return [fitz_image.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72)).tobytes("jpeg") for fitz_image in doc]

# === TEXTO E IA ===
class TextFormatter:
    def __init__(self, api_key):
        self.client =  OpenAI(api_key=api_key)
        print(">>> Tipo de self.client:", type(self.client))

    @safe_run
    def format_text_to_csv(self, text, nomearquivo):
        prompt = f"""
                                Você é um especialista em história e curador de um extenso acervo histórico do Estado do Ceará. Sua tarefa é receber um texto 
                                que contém informações de manchetes de jornais e documentos antigos, extrair e organizar essas informações de maneira estruturada. 
                                O texto que você receberá pode conter múltiplos recortes de jornais, e cada recorte deve ser identificado e estruturado separadamente. 
                                Cada recorte deve ser formatado seguindo o exemplo e as instruções abaixo. Se um recorte não possuir alguma informação, preencha com 
                                'INFORMAÇÃO NÃO ENCONTRADA'. 
                                
                                **IMPORTANTE**:
                                - Se a imagem contiver mais de um recorte, numere cada recorte na sequência, como "Recorte 1", "Recorte 2", e assim por diante.
                                - Cada recorte deve ser organizado usando o formato detalhado abaixo.
                                
                                Aqui está o formato que você deve seguir ao responder, extraindo as informações do texto e preenchendo as seções abaixo:
                                
                                **Recorte 1**

                                **Nome do Arquivo**: 
                                (Nome do arquivo é este {nomearquivo}, adicione _01, _02 se houver mais de uma foto, numerando de cima para baixo).

                                **Acervo**: 
                                (Sempre "Tasso Jereissati")

                                **Fonte**: 
                                (Nome da fonte ou jornal, adicione 'Jornal' se for "O Povo", "Diário do Nordeste" ou "Tribuna do Ceará").

                                **Título**: 
                                (Título da reportagem no formato "Título: subtítulo").

                                **Seção**: 
                                (Seção, coluna ou categoria da reportagem do Colunista. Caso o colunista tenha mais de uma Seçào no recorte 
                                PRECISAREMOS ESCREVER a seção de todos os recortes DEIXE ASSIM coluna1/ coluna2/ colunaN, se nao houver nenhum escreva 'INFORMAÇÃO NÃO ENCONTRADA').

                                **Página**: 
                                (Número da página onde a reportagem foi publicada, encontrasse normalmente ao lado da data e da palavra PÁG, ou 
                                escreva 'INFORMAÇÃO NÃO ENCONTRADA').

                                **Autor**: 
                                (Nome do autor da reportagem, coluna, matéria, manchete. Entenda AUTOR como a pessoa que escreveu o texto em primeira pessoa e que fala
                                de terceiro ou, no caso, fala de outras pessoas, podendo ser um jornalista, crítico, colunista, autoridade, etc. 
                                Caso não encontre escreva 'INFORMAÇÃO NÃO ENCONTRADA'). Exemplo: Coluna do Fulano de Tal, Matéria de Augusto do Anjos, 
                                Texto de José das Marias, Crítica de Maria Alencar da Silva
                                
                                **Localização**: 
                                (Local onde a reportagem foi publicada, exemplo: Cidade, Estado, País, ou escreva 'INFORMAÇÃO NÃO ENCONTRADA').

                                **Data**: 
                                (Data de publicação IMPORTANTE USAR O FORMATO dd/mm/yyyy. 
                                Use o nome do arquivo {nomearquivo} para conferir a data encontrada, caso a data encontrada e o nome 
                                do arquivo sejam divergentes então CORRIJA a data pelo nome do arquivo, preservando o DIA da data encontrada exemplo:
                                data encontrada 02/06/1993 e a do nome do arquivo é 01/06/1998 então a DATA FINAL ficará 02/06/1998.
                                Caso nao tenha ENCONTRADO A DATA USAR a data do nome do arquivo com o 01 como dia do mês. 
                                Porém DE FORMA ALGUMA ALTERE O NOME DO ARQUIVO! NÃO INVENTE DATAS. )

                                **Palavras-chave**: 
                                (Palavras-chave relacionadas ao conteúdo da reportagem, ou escreva 'INFORMAÇÃO NÃO ENCONTRADA').

                                **Pessoas**: 
                                (Nomes de PESSOAS MENCIONADAS na reportagem com seus respectivos cargos, ou escreva 'INFORMAÇÃO NÃO ENCONTRADA').
                                
                                **IMPORTANTE**: 
                                1. Você deve extrair as informações do texto que será fornecido abaixo e preencher os campos conforme descrito.
                                2. SEMPRE fazer a separação entre valores utilizando “virgula”.
                                3. O texto pode estar em qualquer formato, portanto, leia atentamente e organize as informações seguindo as instruções acima.
                                4. Não adicione informações que não estejam presentes no texto, e não invente nada.
                                5. O FORMATO da DATA deve ser SEMPRE dd/mm/yyyy
                                6. Após cada tipo de informação solicitada usar dois pontos para separar da resposta, dessa forma: 
                                Nome do Arquivo: nomearquivo.jpg
                                
                                Repita essa estrutura para quantos recortes forem encontrados no texto. Caso não exista uma informação específica em algum recorte, 
                                preencha o campo com 'INFORMAÇÃO NÃO ENCONTRADA'. Extraia e organize as informações conforme descrito acima para cada recorte.
                                
                                **Texto para ser analisado e onde devemos extrair as informações solicitadas**: {text}
    """  # o prompt original completo vai aqui
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """
                                                 Você é um assistente especializado em extrair e organizar informações históricas de textos 
                                                 para estruturar essas informações de forma clara e precisa. 
                                                 Use datas no FORMATO DD/MM/YYYY. 
                                              """},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.4
        )
        return response.choices[0].message.content

    @staticmethod
    def clean(text):
        if pd.isna(text): return text
        text = re.sub(r'\*\*(.*?)\*\*', '|', text)
        text = re.sub(r'^###\s*', '|', text)
        return text

# === RECORTES E ORGANIZAÇÃO ===
class RecorteAnalyzer:
    @staticmethod
    def count_recortes(text):
        try:
            recorte_pattern = r"\*\*Recorte\s\d+\*\*"
            recortes = re.findall(recorte_pattern, text)
            return len(recortes)
        except Exception as e:
            print(f"❌ Erro na função count_recortes: {e}")
            return 0
        
    @staticmethod
    def format_recortes(text):
        try:
            recortes = re.split(r"(?=\*\*Recorte\s\d+\*\*)", text)
            if not recortes or len(recortes) == 0:
                logger.warning("⚠️ Nenhum recorte detectado no texto.")
                return None
            return recortes
        except Exception as e:
            logger.error(f"❌ Erro na função format_recortes: {e}")
            return None

    @staticmethod
    def formata_folha(x, inicio=4):
        try:
            partes = x.split("**")
            partes.extend(["N/A"] * (26 - len(partes)))
            dados_folha = [partes[i].replace(":", "").replace("\n", "").strip() for i in range(inicio, 26, 2)]
            return dados_folha
        except Exception as e:
            logger.warning(f"⚠️ Erro ao formatar folha: {e}")
            return ["N/A"] * 11

    @staticmethod
    def splitar_nm_arquivo_pg(nome):
        try:
            if isinstance(nome, str) and "_page_" in nome:
                partes = nome.split("_page_")
                nome_final = partes[0].split("/")[1]
                return nome_final, "pagina_" + partes[1]  # Nome sem página, Página isolada

            nome_final = nome.split("/")[1]
            return nome, ""  # Retorna nome intacto e página vazia caso "_page_" não exista
        except Exception as e:
            logger.warning(f"⚠️ Erro ao dividir nome de arquivo e página: {e}")
            return nome, ""

# === MONTAGEM DO Excel ===
class CSVBuilder:
    def __init__(self, planilha_destino, processado_destino, formatter: TextFormatter, analyzer: RecorteAnalyzer, blob_handler):
        self.formatter = formatter
        self.analyzer = analyzer
        self.blob_handler = blob_handler
        self.planilha_destino = planilha_destino
        self.processado_destino = processado_destino

    async def build(self, textos, nomes, input_folder, planilha_destino, processado_destino):
        dados_final = []
        pulados = 0
        processados = 0

        for i in range(len(textos)):
            nome = nomes[i]
            texto = textos[i]

            if not texto.strip():
                pulados += 1
                continue

            result = self.formatter.format_text_to_csv(texto, nome)
            if not result:
                pulados += 1
                continue

            n = self.analyzer.count_recortes(result)
            if n == 0:
                pulados += 1
                continue

            if n == 1:
                dados = self.analyzer.formata_folha(result)
                dados.extend([nome, texto])
                dados_final.append(dados)
            else:
                for bloco in self.analyzer.format_recortes(result)[1:]:
                    dados = self.analyzer.formata_folha(bloco)
                    dados.extend([nome, texto])
                    dados_final.append(dados)

            processados += 1
            if processados % 10 == 0:
                print(f"✅ Processados {processados}/{len(textos)} arquivos...")

        if not dados_final:
            print(f"❌ Nenhum dado válido processado. Arquivos ignorados: {pulados}")
            return None, None, None, False

        df = pd.DataFrame(dados_final, columns=[
            "nm_arq_original", "Acervo", "Fonte", "Título", "Seção", "Página",
            "Autor", "Localização", "Data", "Palavras-chave", "Pessoas",
            "pag_pdf", "texto_extraido"
        ])

        df[["nm_arq_original", "pag_pdf"]] = df["nm_arq_original"].astype(str).apply(
            lambda x: pd.Series(self.analyzer.splitar_nm_arquivo_pg(x))
        )

        df.drop(columns=["Localização", "Pessoas"], inplace=True)
        df = df.reindex(columns=[
            "nm_arq_original", "Acervo", "Fonte", "Título", "Seção", "Página", "Autor",
            "Data", "Palavras-chave", "pag_pdf", "texto_extraido"
        ])

        df["texto_extraido"] = df["texto_extraido"].apply(self.formatter.clean)
        filename = "_".join(df.iloc[0, 0].strip().split("_")[:4])
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        blob_dir = f"{planilha_destino}/{filename}"
        await self.blob_handler.ensure_folder(blob_dir)
        excel_path = f"{blob_dir}/{filename}.xlsx"
        await self.blob_handler.upload_blob(excel_path, buffer.getvalue())

        blobs_iter = self.blob_handler.client.list_blobs(name_starts_with=input_folder)
        async for blob in blobs_iter:
            if blob.name.endswith(".keep"):
                continue
            origem = blob.name
            destino = origem.replace(input_folder, processado_destino, 1)
            await self.blob_handler.copy_blob(origem, destino)
        
        # <- AQUI ENTRA A GARANTIA DA PASTA
        await self.blob_handler.ensure_folder(input_folder)

        print(f"✅ Processamento concluído! {processados} arquivos processados, {pulados} ignorados.")
        return filename, buffer, df, True

# === PROCESSAMENTO FINAL ===
class ProcessamentoFinal:
    def __init__(self, blob_handler: AzureBlobHandler, pastas: CSVBuilder, modo: str):
        self.blob_handler = blob_handler
        self.destino_planilha = pastas.planilha_destino
        self.destino_final = pastas.processado_destino
        self.modo = modo

    async def salvar_planilha_e_mover(self, filename, buffer, input_folder, destino_planilha, destino_final):
        try:
            # 1. Cria pasta de destino, se necessário
            await self.blob_handler.ensure_folder(destino_planilha)

            nome_arquivo_excel = f"{filename}.xlsx"
            blob_path = f"{destino_planilha}/{nome_arquivo_excel}"

            # 2. Upload da planilha com controle de overwrite
            overwrite = self.modo != "h"
            await self.blob_handler.upload_blob(blob_path, buffer.getvalue(), overwrite=overwrite)
            print(f"📊✅ Planilha salva no Blob Storage: {blob_path}")

            # 3. Move arquivos processados (usando async for)
            async for blob in self.blob_handler.client.list_blobs(name_starts_with=input_folder):
                if blob.name.endswith(".keep"):
                    continue

                origem = blob.name
                destino = origem.replace(input_folder, destino_final, 1)

                if self.modo != "h":
                    await self.blob_handler.move_blob(origem, destino, delete_origin=True)
                else:
                    await self.blob_handler.copy_blob(origem, destino)

            print("✅ Arquivos processados foram movidos!")
            return True

        except Exception as e:
            print(f"❌ Erro ao salvar planilha ou mover arquivos: {e}")
            return False
