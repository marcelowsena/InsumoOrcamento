from flask import Flask, request, jsonify, abort
import hmac
import json
from datetime import datetime
import os

from dotenv import load_dotenv

# Configuração via variáveis de ambiente (.env local, nunca versionado)
load_dotenv()

# Token que o Sienge deve enviar. Cadastre a URL do webhook no Sienge como:
#   https://<seu-host>/webhook?token=<WEBHOOK_TOKEN>
# (ou envie o header X-Webhook-Token). Use HTTPS para não trafegar o token em claro.
WEBHOOK_TOKEN = os.getenv('WEBHOOK_TOKEN', '')
# Token separado para consulta de logs. Se vazio, o endpoint /logs fica desabilitado.
WEBHOOK_LOGS_TOKEN = os.getenv('WEBHOOK_LOGS_TOKEN', '')
HOST = os.getenv('WEBHOOK_HOST', '127.0.0.1')
PORT = int(os.getenv('WEBHOOK_PORT', '5000'))

app = Flask(__name__)

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def _token_valido(recebido: str, esperado: str) -> bool:
    """Compara tokens em tempo constante (evita timing attack)."""
    if not esperado or not recebido:
        return False
    return hmac.compare_digest(recebido.encode(), esperado.encode())


@app.route('/webhook', methods=['POST'])
def receber_webhook():
    recebido = request.headers.get('X-Webhook-Token') or request.args.get('token', '')
    if not _token_valido(recebido, WEBHOOK_TOKEN):
        abort(401)

    dados = request.get_json(silent=True) or {}

    tenant = request.headers.get('X-Sienge-Tenant', '')
    evento = request.headers.get('X-Sienge-Event', 'desconhecido')
    hook_id = request.headers.get('X-Sienge-Hook-Id', '')
    sienge_id = request.headers.get('X-Sienge-Id', '')

    # ATENÇÃO (LGPD): o payload pode conter dados pessoais/financeiros.
    # Os arquivos em logs/ são confidenciais e não devem ser versionados nem expostos.
    registro = {"timestamp": datetime.now().isoformat(), "tenant": tenant, "evento": evento, "hook_id": hook_id, "sienge_id": sienge_id, "dados": dados}

    arquivo = os.path.join(LOG_DIR, f"webhook_{datetime.now().strftime('%Y%m%d')}.log")
    with open(arquivo, 'a', encoding='utf-8') as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    return jsonify({"status": "ok", "sienge_id": sienge_id}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online"}), 200


@app.route('/logs', methods=['GET'])
def ver_logs():
    # Somente via header (não aceita token na URL) e só se WEBHOOK_LOGS_TOKEN estiver definido
    if not _token_valido(request.headers.get('X-Logs-Token', ''), WEBHOOK_LOGS_TOKEN):
        abort(404)
    arquivo = os.path.join(LOG_DIR, f"webhook_{datetime.now().strftime('%Y%m%d')}.log")
    if not os.path.exists(arquivo):
        return jsonify({"mensagem": "Nenhum webhook recebido hoje"}), 200
    with open(arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()[-20:]
    return jsonify({"ultimos_20": [json.loads(l) for l in linhas if l.strip()]}), 200


if __name__ == '__main__':
    if not WEBHOOK_TOKEN:
        raise SystemExit("WEBHOOK_TOKEN não definido no .env - servidor não iniciado.")

    print(f"Servidor webhook iniciando em {HOST}:{PORT}...")
    try:
        # Servidor de produção (o servidor embutido do Flask é só para desenvolvimento)
        from waitress import serve
        serve(app, host=HOST, port=PORT)
    except ImportError:
        print("⚠️ waitress não instalado - usando servidor de desenvolvimento do Flask")
        app.run(host=HOST, port=PORT)
