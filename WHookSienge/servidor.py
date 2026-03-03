from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

@app.route('/webhook', methods=['POST'])
def receber_webhook():
    dados = request.json or {}
    
    tenant = request.headers.get('X-Sienge-Tenant', '')
    evento = request.headers.get('X-Sienge-Event', 'desconhecido')
    hook_id = request.headers.get('X-Sienge-Hook-Id', '')
    sienge_id = request.headers.get('X-Sienge-Id', '')
    
    registro = {"timestamp": datetime.now().isoformat(), "tenant": tenant, "evento": evento, "hook_id": hook_id, "sienge_id": sienge_id, "dados": dados}
    
    arquivo = os.path.join(LOG_DIR, f"webhook_{datetime.now().strftime('%Y%m%d')}.log")
    with open(arquivo, 'a', encoding='utf-8') as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    
    return jsonify({"status": "ok", "sienge_id": sienge_id}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "server": "Halsten Webhook Receiver"}), 200

@app.route('/logs', methods=['GET'])
def ver_logs():
    arquivo = os.path.join(LOG_DIR, f"webhook_{datetime.now().strftime('%Y%m%d')}.log")
    if not os.path.exists(arquivo):
        return jsonify({"mensagem": "Nenhum webhook recebido hoje"}), 200
    with open(arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()[-20:]
    return jsonify({"ultimos_20": [json.loads(l) for l in linhas if l.strip()]}), 200

if __name__ == '__main__':
    print("Servidor webhook iniciando...")
    print("URL externa: http://halstenwan2.npro.com.br:5000/webhook")
    print("Health check: http://halstenwan2.npro.com.br:5000/health")
    app.run(host='0.0.0.0', port=5000)