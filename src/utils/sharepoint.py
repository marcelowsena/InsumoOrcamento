"""
Módulo para upload de arquivos ao SharePoint via Microsoft Graph API.
Configurações são carregadas do arquivo .env
"""
import os
import shutil
import time
from pathlib import Path

import requests
from msal import ConfidentialClientApplication

# Configurações de retry
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10


def get_sharepoint_config() -> dict:
    """Carrega configurações do SharePoint das variáveis de ambiente."""
    return {
        'tenant_id': os.getenv('SHAREPOINT_TENANT_ID', ''),
        'client_id': os.getenv('SHAREPOINT_CLIENT_ID', ''),
        'client_secret': os.getenv('SHAREPOINT_CLIENT_SECRET', ''),
        'drive_id': os.getenv('SHAREPOINT_DRIVE_ID', ''),
        'pasta_destino': os.getenv('SHAREPOINT_PASTA_DESTINO', ''),
        'enabled': os.getenv('SHAREPOINT_ENABLED', 'true').lower() == 'true'
    }


def gerar_token(config: dict) -> str | None:
    """
    Autentica via MSAL e retorna o token de acesso.

    Args:
        config: Dicionário com tenant_id, client_id e client_secret

    Returns:
        Token de acesso ou None se falhar
    """
    if not all([config.get('tenant_id'), config.get('client_id'), config.get('client_secret')]):
        print("⚠️ SharePoint: Credenciais não configuradas no .env")
        return None

    authority = f"https://login.microsoftonline.com/{config['tenant_id']}"
    scope = ["https://graph.microsoft.com/.default"]

    app = ConfidentialClientApplication(
        config['client_id'],
        authority=authority,
        client_credential=config['client_secret']
    )

    result = app.acquire_token_for_client(scopes=scope)

    if "access_token" in result:
        return result['access_token']
    else:
        print(f"❌ SharePoint: Erro ao obter token - {result.get('error_description')}")
        return None


def descartar_checkout(token: str, config: dict, nome_arquivo: str) -> bool:
    """
    Descarta o check-out de um arquivo no SharePoint (libera o bloqueio).

    Args:
        token: Token de acesso do Microsoft Graph
        config: Configurações do SharePoint (drive_id, pasta_destino)
        nome_arquivo: Nome do arquivo no SharePoint

    Returns:
        True se sucesso ou arquivo não estava bloqueado, False se falhar
    """
    drive_id = config.get('drive_id', '')
    pasta_destino = config.get('pasta_destino', '')

    # Primeiro, obter o item_id do arquivo
    item_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{pasta_destino}/{nome_arquivo}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(item_url, headers=headers)

        if response.status_code == 404:
            # Arquivo não existe ainda, não precisa descartar checkout
            return True

        if response.status_code != 200:
            return True  # Ignora erro e tenta upload mesmo assim

        item_id = response.json().get('id')
        if not item_id:
            return True

        # Tentar descartar o check-out
        checkout_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/discardCheckout"
        response = requests.post(checkout_url, headers=headers)

        if response.status_code in [200, 204]:
            print("🔓 SharePoint: Check-out descartado com sucesso")
            return True
        elif response.status_code == 423:
            # Ainda bloqueado, pode ser edição online
            print("⚠️ SharePoint: Arquivo em edição online, tentando forçar...")
            return True  # Continua tentando o upload
        else:
            # Pode não ter checkout ativo, continua normalmente
            return True

    except Exception as e:
        print(f"⚠️ SharePoint: Erro ao verificar checkout - {e}")
        return True  # Continua tentando o upload


def deletar_arquivo_remoto(token: str, config: dict, nome_arquivo: str) -> bool:
    """
    Deleta um arquivo no SharePoint.

    Args:
        token: Token de acesso do Microsoft Graph
        config: Configurações do SharePoint (drive_id, pasta_destino)
        nome_arquivo: Nome do arquivo a ser deletado

    Returns:
        True se deletou com sucesso ou arquivo não existia, False se falhar
    """
    drive_id = config.get('drive_id', '')
    pasta_destino = config.get('pasta_destino', '')

    # Obter o item_id do arquivo
    item_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{pasta_destino}/{nome_arquivo}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(item_url, headers=headers)

        if response.status_code == 404:
            # Arquivo não existe, nada a deletar
            return True

        if response.status_code != 200:
            print(f"⚠️ SharePoint: Erro ao localizar arquivo para deletar - {response.status_code}")
            return False

        item_id = response.json().get('id')
        if not item_id:
            return False

        # Deletar o arquivo
        delete_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
        response = requests.delete(delete_url, headers=headers)

        if response.status_code in [200, 204]:
            print("🗑️ SharePoint: Arquivo antigo deletado")
            return True
        else:
            print(f"⚠️ SharePoint: Erro ao deletar - {response.status_code} - {response.text[:100]}")
            return False

    except Exception as e:
        print(f"⚠️ SharePoint: Erro ao deletar arquivo - {e}")
        return False


def upload_arquivo_sharepoint(token: str, caminho_local: str | Path, config: dict, nome_destino: str = None) -> bool:
    """
    Faz upload de um arquivo local para o SharePoint.

    Args:
        token: Token de acesso do Microsoft Graph
        caminho_local: Caminho do arquivo local a ser enviado
        config: Configurações do SharePoint (drive_id, pasta_destino)
        nome_destino: Nome do arquivo no destino (opcional, usa o nome original se não informado)

    Returns:
        True se sucesso, False se falhar
    """
    caminho_local = Path(caminho_local)

    if not caminho_local.exists():
        print(f"❌ SharePoint: Arquivo não encontrado - {caminho_local}")
        return False

    nome_arquivo = nome_destino or caminho_local.name
    drive_id = config.get('drive_id', '')
    pasta_destino = config.get('pasta_destino', '')

    if not drive_id:
        print("⚠️ SharePoint: DRIVE_ID não configurado")
        return False

    upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{pasta_destino}/{nome_arquivo}:/content"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            with open(caminho_local, "rb") as arquivo:
                response = requests.put(upload_url, headers=headers, data=arquivo)

            if response.status_code in [200, 201]:
                print(f"✅ SharePoint: '{nome_arquivo}' enviado para '{pasta_destino}'")
                return True
            elif response.status_code == 423:
                # Arquivo bloqueado - tentar liberar
                if tentativa == 1:
                    print("🔒 SharePoint: Arquivo bloqueado, tentando liberar...")
                    descartar_checkout(token, config, nome_arquivo)
                elif tentativa == 2:
                    # Segunda tentativa: deletar o arquivo e tentar novamente
                    print("🔒 SharePoint: Ainda bloqueado, deletando arquivo remoto...")
                    if deletar_arquivo_remoto(token, config, nome_arquivo):
                        time.sleep(2)  # Aguarda a deleção propagar
                        continue  # Tenta upload imediatamente

                if tentativa < MAX_RETRIES:
                    print(f"⏳ SharePoint: Tentativa {tentativa}/{MAX_RETRIES}. Aguardando {RETRY_DELAY_SECONDS}s...")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    print(f"❌ SharePoint: Arquivo bloqueado após {MAX_RETRIES} tentativas.")
                    return False
            else:
                print(f"❌ SharePoint: Erro {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ SharePoint: Erro no upload - {e}")
            return False

    return False


def enviar_para_sharepoint(arquivo_origem: Path, nome_arquivo_sharepoint: str = "analise_insumos_orcamento.xlsx") -> bool:
    """
    Função principal para enviar arquivo ao SharePoint.
    Cria uma cópia temporária com o nome desejado e faz o upload.

    Args:
        arquivo_origem: Path do arquivo Excel gerado (com timestamp)
        nome_arquivo_sharepoint: Nome do arquivo no SharePoint (sem timestamp)

    Returns:
        True se sucesso, False se falhar ou desabilitado
    """
    config = get_sharepoint_config()

    if not config['enabled']:
        print("ℹ️ SharePoint: Upload desabilitado (SHAREPOINT_ENABLED=false)")
        return False

    # Gerar token
    token = gerar_token(config)
    if not token:
        return False

    # Criar cópia temporária com nome sem timestamp
    pasta_temp = arquivo_origem.parent
    arquivo_temp = pasta_temp / nome_arquivo_sharepoint

    try:
        shutil.copy2(arquivo_origem, arquivo_temp)

        # Fazer upload
        sucesso = upload_arquivo_sharepoint(token, arquivo_temp, config, nome_arquivo_sharepoint)

        # Remover cópia temporária
        if arquivo_temp.exists():
            arquivo_temp.unlink()

        return sucesso

    except Exception as e:
        print(f"❌ SharePoint: Erro ao preparar arquivo - {e}")
        # Limpar arquivo temporário se existir
        if arquivo_temp.exists():
            arquivo_temp.unlink()
        return False
