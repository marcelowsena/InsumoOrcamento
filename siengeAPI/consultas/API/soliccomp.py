from .consultaapi import consultaAPI, user, pw
import datetime
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "https://api.sienge.com.br/trust/public/api/v1"


def consultaSC(idSC):

    apiEap = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-requests/",
        "": idSC,
    }

    dadosConsulta = consultaAPI(apiEap)

    return(dadosConsulta)

def consultaTodasSC():

    apiEap = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-requests/",
        #"&limit=": "200",
        #"&offset=": 0
    }

    dadosConsulta = consultaAPI(apiEap)

    return(dadosConsulta)


# ============================================================================
# NOVAS FUNCOES - Reprovacao e Autorizacao de SC
# ============================================================================

def reprovarSC(idSC):
    """
    Reprova todos os itens pendentes de uma Solicitacao de Compra

    Args:
        idSC: ID da Solicitacao de Compra

    Returns:
        True se reprovado com sucesso, False caso contrario
    """
    url = f"{BASE_URL}/purchase-requests/{idSC}/disapproval"

    response = requests.patch(url, auth=HTTPBasicAuth(user, pw))

    if response.status_code == 204:
        return True
    else:
        print(f"Erro ao reprovar SC {idSC}: {response.status_code} - {response.text}")
        return False


def reprovarItemSC(idSC, itemNumber):
    """
    Reprova um item especifico de uma Solicitacao de Compra

    Args:
        idSC: ID da Solicitacao de Compra
        itemNumber: Numero do item na SC

    Returns:
        True se reprovado com sucesso, False caso contrario
    """
    url = f"{BASE_URL}/purchase-requests/{idSC}/items/{itemNumber}/disapproval"

    response = requests.patch(url, auth=HTTPBasicAuth(user, pw))

    if response.status_code == 204:
        return True
    else:
        print(f"Erro ao reprovar item {itemNumber} da SC {idSC}: {response.status_code} - {response.text}")
        return False


def autorizarSC(idSC):
    """
    Autoriza todos os itens pendentes de uma Solicitacao de Compra

    Args:
        idSC: ID da Solicitacao de Compra

    Returns:
        Resposta da API com detalhes da autorizacao
    """
    url = f"{BASE_URL}/purchase-requests/{idSC}/authorize"

    response = requests.patch(url, auth=HTTPBasicAuth(user, pw))

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro ao autorizar SC {idSC}: {response.status_code} - {response.text}")
        return None


def autorizarItemSC(idSC, itemNumber):
    """
    Autoriza um item especifico de uma Solicitacao de Compra

    Args:
        idSC: ID da Solicitacao de Compra
        itemNumber: Numero do item na SC

    Returns:
        True se autorizado com sucesso, False caso contrario
    """
    url = f"{BASE_URL}/purchase-requests/{idSC}/items/{itemNumber}/authorize"

    response = requests.patch(url, auth=HTTPBasicAuth(user, pw))

    if response.status_code == 204:
        return True
    else:
        print(f"Erro ao autorizar item {itemNumber} da SC {idSC}: {response.status_code} - {response.text}")
        return False
