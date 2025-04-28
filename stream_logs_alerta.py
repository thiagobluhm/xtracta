import subprocess
import datetime
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Nome do arquivo de log com timestamp
log_file = f"log_stream_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Variáveis da Azure
webapp = os.environ.get("WEBAPP_NM")
resource_group = os.environ.get("R_GROUP")

# Comando para tail do log
cmd = f"az webapp log tail --name {webapp} --resource-group {resource_group}"

print("📡 Monitorando logs em tempo real...")

with open(log_file, "w", encoding="utf-8") as f:
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        text=True  # Faz o decode automático!
    )

    try:
        for line in iter(process.stdout.readline, ''):
            if line == '':
                break  # EOF
            line = line.strip()
            print(line)
            f.write(line + "\n")
            f.flush()  # ESSENCIAL: força a gravação no disco imediatamente

            # Detecta erro 429
            if "Error code: 429" in line or "insufficient_quota" in line:
                alerta = "🔴 ALERTA: Erro 429 detectado!"
                print(alerta)
                f.write(alerta + "\n")
                f.flush()

    except KeyboardInterrupt:
        print("🛑 Monitoramento interrompido pelo usuário.")
        process.terminate()
