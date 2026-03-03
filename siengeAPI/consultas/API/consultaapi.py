import requests
import json
import os
from dotenv import load_dotenv, find_dotenv
from requests.auth import HTTPBasicAuth
from pathlib import Path

# Carrega .env automaticamente (procura na árvore de diretórios)
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path, override=True)
else:
    # Se não encontrou, procura manualmente na raiz do siengeAPI
    sienge_root = Path(__file__).parent.parent.parent
    env_file = sienge_root / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=True)
    else:
        raise ValueError(f"Credenciais não encontradas. .env não existe em: {env_file}")

# Credenciais da API
user = os.getenv('SIENGE_USER')
pw = os.getenv('SIENGE_PASSWORD')
base_url = os.getenv('SIENGE_BASE_URL', 'https://api.sienge.com.br/trust/public/api/v1')

if not user or not pw:
    raise ValueError("Credenciais não encontradas. Verifique o arquivo .env")


def formalink(linkdic):
    raizlink = linkdic["raiz"]
    for var in list(linkdic.keys()):
        if var != "raiz":
            raizlink+= var+str(linkdic[var])
    return(raizlink)

def puxaDados(link):
    response = requests.get(link, auth=HTTPBasicAuth(user, pw)).text
    retornos = json.loads(response)
    return(retornos)

def consultaAPI(diclink):

    linkfinal = formalink(diclink)
    dados = puxaDados(linkfinal)
    if 'results' in dados:
        dadosfinais = list(dados['results'])
        lenconsulta = len(dadosfinais)
        consultas = 1
        while lenconsulta == 200:
            diclink["&offset="] += 200
            linkfinal = formalink(diclink)
            dados = puxaDados(linkfinal)['results']
            lenconsulta = len(dados)
            for d in dados:
                dadosfinais.append(d)
            consultas += 1
        
        return(dadosfinais)
    else:
        return(dados)