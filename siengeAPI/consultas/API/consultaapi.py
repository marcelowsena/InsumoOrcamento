import requests
import json
import os
import time
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

MAX_TENTATIVAS = 6
STATUS_RETENTAVEIS = {429, 500, 502, 503, 504}


def _espera_retentativa(response, tentativa):
    """Segundos de espera antes de repetir: usa Retry-After se vier, senão backoff exponencial."""
    retry_after = response.headers.get('Retry-After')
    if retry_after and retry_after.isdigit():
        return min(int(retry_after), 120)
    return min(5 * (2 ** (tentativa - 1)), 120)  # 5, 10, 20, 40, 80s


def puxaDados(link):
    # Repete em limite de requisições (429) e erros temporários do servidor (5xx).
    # Sem isso, a resposta de erro era devolvida como se fossem dados.
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        response = requests.get(link, auth=HTTPBasicAuth(user, pw))
        if response.status_code not in STATUS_RETENTAVEIS or tentativa == MAX_TENTATIVAS:
            break
        espera = _espera_retentativa(response, tentativa)
        print(f"  Sienge HTTP {response.status_code}: aguardando {espera}s (tentativa {tentativa}/{MAX_TENTATIVAS})")
        time.sleep(espera)

    if response.status_code in STATUS_RETENTAVEIS:
        raise RuntimeError(f"Sienge respondeu HTTP {response.status_code} após {MAX_TENTATIVAS} tentativas.")
    # Falha explícita: sem isso, uma resposta de erro (ex.: 401) era tratada como dados
    if response.status_code == 401:
        raise RuntimeError("Sienge recusou as credenciais (HTTP 401). Verifique SIENGE_USER/SIENGE_PASSWORD.")
    if response.status_code == 403:
        raise RuntimeError("Sienge negou acesso (HTTP 403). Verifique as permissões do usuário de API.")
    retornos = json.loads(response.text)
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