"""
Cliente API Sienge V4 - Sistema Insumos x Orçamento
Abordagem funcional com cache integrado e error handling robusto
"""

import requests
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode


def create_api_session(api_config: Dict) -> requests.Session:
    """Cria sessão HTTP configurada"""
    session = requests.Session()
    session.auth = HTTPBasicAuth(api_config['user'], api_config['password'])
    session.headers.update({
        'User-Agent': 'InsumosOrcamento-V4/1.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })
    return session


def fazer_requisicao_com_retry(session: requests.Session, url: str, api_config: Dict) -> Tuple[bool, Dict]:
    """
    Faz requisição com retry automático
    Returns: (sucesso, dados_ou_erro)
    """
    max_retries = api_config['max_retries']
    base_timeout = api_config['timeout']
    delay = api_config['delay']
    
    for tentativa in range(max_retries):
        try:
            timeout = base_timeout + (tentativa * 30)
            
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            
            return True, response.json()
            
        except requests.exceptions.Timeout as e:
            erro = f"Timeout na tentativa {tentativa + 1}/{max_retries}"
            if tentativa < max_retries - 1:
                time.sleep(delay * (2 ** tentativa))
                continue
            return False, {"erro": f"{erro}. URL: {url}"}
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                return False, {"erro": f"Recurso não encontrado (404). URL: {url}"}
            elif response.status_code == 401:
                return False, {"erro": f"Credenciais inválidas (401). Verifique user/password"}
            elif response.status_code == 403:
                return False, {"erro": f"Acesso negado (403). Usuário sem permissão"}
            elif response.status_code >= 500:
                erro = f"Erro do servidor ({response.status_code})"
                if tentativa < max_retries - 1:
                    time.sleep(delay * (2 ** tentativa))
                    continue
                return False, {"erro": f"{erro}. URL: {url}"}
            else:
                return False, {"erro": f"HTTP {response.status_code}: {str(e)}"}
                
        except requests.exceptions.ConnectionError as e:
            erro = f"Erro de conexão na tentativa {tentativa + 1}/{max_retries}"
            if tentativa < max_retries - 1:
                time.sleep(delay * (2 ** tentativa))
                continue
            return False, {"erro": f"{erro}. Verifique conexão de rede"}
            
        except requests.exceptions.RequestException as e:
            return False, {"erro": f"Erro na requisição: {str(e)}"}
            
        except json.JSONDecodeError as e:
            return False, {"erro": f"Resposta inválida da API: {str(e)}"}
            
        except Exception as e:
            return False, {"erro": f"Erro inesperado: {str(e)}"}


def consulta_paginada(session: requests.Session, url_base: str, params: Dict, api_config: Dict) -> Tuple[bool, List[Dict]]:
    """
    Consulta com paginação automática
    Returns: (sucesso, lista_resultados)
    """
    params = params.copy()
    if 'limit' not in params:
        params['limit'] = 200
    if 'offset' not in params:
        params['offset'] = 0
    
    url = f"{url_base}?{urlencode(params)}"
    sucesso, dados = fazer_requisicao_com_retry(session, url, api_config)
    
    if not sucesso:
        return False, [dados]  # Retorna erro como item da lista
    
    # Se não tem 'results', assume que é lista direta
    if 'results' not in dados:
        return True, dados if isinstance(dados, list) else [dados]
    
    resultados = list(dados['results'])
    
    # Continuar paginação enquanto houver resultados
    while len(dados.get('results', [])) == params['limit']:
        params['offset'] += params['limit']
        url = f"{url_base}?{urlencode(params)}"
        
        sucesso, dados = fazer_requisicao_com_retry(session, url, api_config)
        
        if not sucesso:
            break  # Para em caso de erro, mas retorna o que já coletou
            
        if 'results' in dados and dados['results']:
            resultados.extend(dados['results'])
            time.sleep(api_config['delay'])
        else:
            break
    
    return True, resultados


def buscar_todas_empresas(session: requests.Session, api_config: Dict) -> Tuple[bool, List[Dict]]:
    """
    Busca todas as empresas/obras
    Returns: (sucesso, lista_empresas)
    """
    url_base = f"{api_config['base_url']}/v1/enterprises"
    params = {"onlyBuildingsEnabledForIntegration": "false"}
    
    return consulta_paginada(session, url_base, params, api_config)


def gerar_chave_cache(obra_id: int, opcoes: Dict) -> str:
    """Gera chave única para cache baseada nos parâmetros"""
    params_str = f"{obra_id}_{opcoes.get('startDate')}_{opcoes.get('endDate')}_{opcoes.get('bdi')}_{opcoes.get('laborBurden')}"
    return hashlib.md5(params_str.encode()).hexdigest()


def verificar_cache(cache_dir: Path, chave: str, validity_hours: int) -> Tuple[bool, Optional[Dict]]:
    """
    Verifica se cache é válido
    Returns: (cache_valido, dados_ou_none)
    """
    arquivo_cache = cache_dir / f"cache_{chave}.json"
    
    if not arquivo_cache.exists():
        return False, None
    
    try:
        with open(arquivo_cache, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Verificar timestamp
        timestamp = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - timestamp > timedelta(hours=validity_hours):
            return False, None
        
        # Se tem erro no cache, tentar novamente
        if 'erro' in cache_data.get('resultado', {}):
            return False, None
        
        return True, cache_data['resultado']
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return False, None


def salvar_cache(cache_dir: Path, chave: str, obra_nome: str, resultado: Dict) -> bool:
    """
    Salva resultado no cache
    Returns: sucesso
    """
    cache_data = {
        'obra_nome': obra_nome,
        'timestamp': datetime.now().isoformat(),
        'resultado': resultado
    }
    
    arquivo_cache = cache_dir / f"cache_{chave}.json"
    
    try:
        with open(arquivo_cache, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception:
        return False


def gerar_relatorio_obra(session: requests.Session, obra: Dict, opcoes: Dict,
                        api_config: Dict, cache_config: Dict) -> Dict:
    """
    Gera relatório de uma obra com cache automático
    Returns: dados_do_relatorio_ou_erro

    Se cache_config['skip_update'] for True, usa apenas cache existente (não faz requisições API)
    """
    obra_id = obra['id']
    obra_nome = obra['name']
    skip_cache_update = cache_config.get('skip_update', False)

    # Verificar cache se habilitado
    if cache_config['enabled']:
        chave_cache = gerar_chave_cache(obra_id, opcoes)

        if skip_cache_update:
            # Modo skip-cache: usar cache existente independente da validade
            cache_valido, dados_cache = verificar_cache_sem_validacao(
                cache_config['directory'],
                chave_cache
            )
            if cache_valido:
                return dados_cache
            else:
                return {"erro": f"Cache não encontrado para obra {obra_id} ({obra_nome}). Use sem --skip-cache primeiro."}
        else:
            # Modo normal: verificar validade do cache
            cache_valido, dados_cache = verificar_cache(
                cache_config['directory'],
                chave_cache,
                cache_config['validity_hours']
            )

            if cache_valido:
                return dados_cache

    # Se skip_cache_update está ativo mas cache não habilitado, retornar erro
    if skip_cache_update:
        return {"erro": f"Modo --skip-cache requer cache habilitado. Obra {obra_id} ({obra_nome})"}

    # Fazer requisição
    params = {
        "buildingId": obra_id,
        "startDate": opcoes.get('startDate', '2024-01-01'),
        "endDate": opcoes.get('endDate', datetime.now().strftime('%Y-%m-%d')),
        "includeDisbursement": opcoes.get('includeDisbursement', 'false'),
        "bdi": opcoes.get('bdi', '0.00'),
        "laborBurden": opcoes.get('laborBurden', '0.00')
    }

    url = f"{api_config['base_url']}/bulk-data/v1/building/resources?{urlencode(params)}"

    sucesso, resultado = fazer_requisicao_com_retry(session, url, api_config)

    # Salvar no cache se habilitado
    if cache_config['enabled']:
        chave_cache = gerar_chave_cache(obra_id, opcoes)
        salvar_cache(cache_config['directory'], chave_cache, obra_nome, resultado)

    return resultado


def verificar_cache_sem_validacao(cache_dir: Path, chave: str) -> Tuple[bool, Optional[Dict]]:
    """
    Verifica cache SEM validar tempo de expiração (para modo --skip-cache)
    Returns: (cache_existe, dados_ou_none)
    """
    arquivo_cache = cache_dir / f"cache_{chave}.json"

    if not arquivo_cache.exists():
        return False, None

    try:
        with open(arquivo_cache, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Se tem erro no cache, retornar mesmo assim (usuário escolheu usar cache antigo)
        return True, cache_data['resultado']

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return False, None


def limpar_cache(cache_dir: Path, max_age_days: int = 30) -> Tuple[int, int]:
    """
    Limpa arquivos de cache antigos
    Returns: (arquivos_removidos, arquivos_mantidos)
    """
    if not cache_dir.exists():
        return 0, 0
    
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    removidos = 0
    mantidos = 0
    
    for arquivo in cache_dir.glob("cache_*.json"):
        try:
            # Verificar data de modificação do arquivo
            mod_time = datetime.fromtimestamp(arquivo.stat().st_mtime)
            
            if mod_time < cutoff_date:
                arquivo.unlink()
                removidos += 1
            else:
                mantidos += 1
                
        except Exception:
            # Se der erro, tentar remover arquivo corrompido
            try:
                arquivo.unlink()
                removidos += 1
            except:
                mantidos += 1
    
    return removidos, mantidos


def estatisticas_cache(cache_dir: Path) -> Dict:
    """Retorna estatísticas do cache"""
    if not cache_dir.exists():
        return {
            'total_arquivos': 0,
            'tamanho_mb': 0,
            'arquivo_mais_antigo': None,
            'arquivo_mais_novo': None
        }
    
    arquivos = list(cache_dir.glob("cache_*.json"))
    
    if not arquivos:
        return {
            'total_arquivos': 0,
            'tamanho_mb': 0,
            'arquivo_mais_antigo': None,
            'arquivo_mais_novo': None
        }
    
    # Calcular tamanho total
    tamanho_total = sum(arquivo.stat().st_size for arquivo in arquivos)
    tamanho_mb = tamanho_total / (1024 * 1024)
    
    # Encontrar datas
    datas = []
    for arquivo in arquivos:
        try:
            mod_time = datetime.fromtimestamp(arquivo.stat().st_mtime)
            datas.append(mod_time)
        except:
            continue
    
    return {
        'total_arquivos': len(arquivos),
        'tamanho_mb': round(tamanho_mb, 2),
        'arquivo_mais_antigo': min(datas).isoformat() if datas else None,
        'arquivo_mais_novo': max(datas).isoformat() if datas else None
    }


def testar_conexao_api(api_config: Dict) -> Tuple[bool, str]:
    """
    Testa conexão com a API
    Returns: (conectado, mensagem)
    """
    try:
        session = create_api_session(api_config)
        url = f"{api_config['base_url']}/v1/enterprises?limit=1"
        
        sucesso, resultado = fazer_requisicao_com_retry(session, url, api_config)
        
        if sucesso:
            return True, "Conexão com API funcionando"
        else:
            return False, resultado.get('erro', 'Erro desconhecido')
            
    except Exception as e:
        return False, f"Erro ao testar conexão: {str(e)}"


def buscar_obras_filtradas(session: requests.Session, api_config: Dict, 
                          filtro_basico: str, filtros_config: Dict) -> Tuple[List[Dict], List[Dict]]:
    """
    Busca obras aplicando filtros
    Returns: (obras_incluidas, obras_excluidas)
    """
    from .settings import aplicar_filtros_obras
    
    # Buscar todas as empresas
    sucesso, empresas = buscar_todas_empresas(session, api_config)
    
    if not sucesso:
        return [], []
    
    # Aplicar filtros
    obras_incluidas, obras_excluidas = aplicar_filtros_obras(empresas, filtro_basico)
    
    return obras_incluidas, obras_excluidas


def processar_obras_em_lotes(session: requests.Session, obras: List[Dict], opcoes: Dict,
                           api_config: Dict, cache_config: Dict, 
                           callback_progress=None) -> List[Dict]:
    """
    Processa obras em lotes com callback de progresso
    Returns: lista_resultados
    """
    resultados = []
    total_obras = len(obras)
    
    for i, obra in enumerate(obras, 1):
        if callback_progress:
            callback_progress(i, total_obras, obra['name'])
        
        resultado = gerar_relatorio_obra(session, obra, opcoes, api_config, cache_config)
        
        resultados.append({
            'obra': obra,
            'relatorio_bruto': resultado,
            'timestamp': datetime.now().isoformat()
        })
        
        # Delay entre requisições para não sobrecarregar API
        if i < total_obras:
            time.sleep(api_config['delay'])
    
    return resultados


def debug_requisicao(url: str, params: Dict = None) -> str:
    """Formata URL e parâmetros para debug"""
    if params:
        url_completa = f"{url}?{urlencode(params)}"
    else:
        url_completa = url
    
    return f"URL: {url_completa}"


# Função de conveniência para uso direto
def criar_cliente_api(configs: Dict) -> requests.Session:
    """
    Cria cliente API configurado
    Usage: session = criar_cliente_api(load_all_configs())
    """
    return create_api_session(configs['api'])


if __name__ == '__main__':
    # Teste básico do cliente
    from settings import load_all_configs, validate_api_config
    
    # Carregar configurações
    configs = load_all_configs()
    
    # Validar API
    valido, erros = validate_api_config()
    if not valido:
        print("ERROS DE CONFIGURAÇÃO:")
        for erro in erros:
            print(f"  - {erro}")
        exit(1)
    
    # Testar conexão
    conectado, mensagem = testar_conexao_api(configs['api'])
    print(f"Teste de conexão: {mensagem}")
    
    if conectado:
        # Estatísticas do cache
        stats = estatisticas_cache(configs['cache']['directory'])
        print(f"Cache: {stats['total_arquivos']} arquivos, {stats['tamanho_mb']} MB")