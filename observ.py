from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

import openai
print(openai.__version__)


#def extract_text_from_image(self, base64_image: str, filename: str):
def extract_text_from_image(base64_image: str, filename: str):
    segredo = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=segredo)

    prompt_text = (
        "Você é um excelente historiador e arquivista experiente. Sua tarefa é de CURADORIA e assim precisa\n"
        "ler documentos antigos, manchetes de jornais e extrair toda informação possível dessas imagens,\n"
        "IMPORTANTE INICIAR A EXTRAÇÃO DO TOPO AO RODAPÉ da imagem seguindo a ordem de cima para baixo,\n"
        "capture a fonte da manchete que é o nome do jornal, pegar a DATA que aparece no texto seja da publicação ou de\n"
        "algum fato, MUITO IMPORTANTE é o nome do autor do texto sendo àquele que escreveu ou falou de algo ou alguém,\n"
        "título da manchete, o texto da manchete, até chegar no rodapé. Não invente nada. Responda em português do Brasil.\n"
        "IMPORTANTE: Faça uma verificação ortográfica."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": filename}}
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

if __name__ == "__main__":
    imagem = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
    resultado = extract_text_from_image("", imagem)
    print("📝 Resultado:", resultado)