"""
Configurações Centralizadas V4 - Sistema Insumos x Orçamento
Abordagem funcional para gerenciar todas as configurações
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Diretórios base
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / 'config'
DATA_DIR = BASE_DIR / 'data'
CACHE_DIR = DATA_DIR / 'cache'
REPORTS_DIR = DATA_DIR / 'reports'


def create_directories():
    """Cria diretórios necessários"""
    for directory in [CONFIG_DIR, DATA_DIR, CACHE_DIR, REPORTS_DIR]:
        directory.mkdir(exist_ok=True)


def get_api_config() -> Dict:
    """Configurações da API Sienge"""
    return {
        'user': os.getenv('SIENGE_USER', 'trust-francisco'),
        'password': os.getenv('SIENGE_PASSWORD', 'vSMeJeliJNfpkrXv7lDvrR6v2aLaynnZ'),
        'subdomain': os.getenv('SIENGE_SUBDOMAIN', 'trust'),
        'timeout': int(os.getenv('API_TIMEOUT', '60')),
        'max_retries': int(os.getenv('API_MAX_RETRIES', '3')),
        'delay': float(os.getenv('API_DELAY', '1.5')),
        'base_url': f"https://api.sienge.com.br/{os.getenv('SIENGE_SUBDOMAIN', 'trust')}/public/api"
    }


def get_cache_config() -> Dict:
    """Configurações do cache"""
    return {
        'enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
        'validity_hours': int(os.getenv('CACHE_VALIDITY_HOURS', '24')),
        'max_size_mb': int(os.getenv('CACHE_MAX_SIZE_MB', '500')),
        'directory': CACHE_DIR
    }


def get_default_report_options() -> Dict:
    """Opções padrão para relatórios"""
    return {
        'start_date': os.getenv('DEFAULT_START_DATE', '2000-01-01'),
        'end_date': os.getenv('DEFAULT_END_DATE', datetime.now().strftime('%Y-%m-%d')),
        'include_disbursement': os.getenv('DEFAULT_INCLUDE_DISBURSEMENT', 'false'),
        'bdi': os.getenv('DEFAULT_BDI', '0.00'),
        'labor_burden': os.getenv('DEFAULT_LABOR_BURDEN', '0.00')
    }


def load_filtros_obras() -> Dict:
    """Carrega filtros de obras do JSON"""
    try:
        filtros_path = CONFIG_DIR / 'filtros_obras.json'
        if filtros_path.exists():
            with open(filtros_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return create_default_filtros()
    except Exception as e:
        print(f"Erro ao carregar filtros: {e}")
        return create_default_filtros()


def create_default_filtros() -> Dict:
    """Cria estrutura padrão de filtros"""
    return {
        "description": "Configuração de filtros para obras",
        "modo": "excluir",
        "opcoes_modo": {
            "incluir": "Apenas as obras listadas serão processadas",
            "excluir": "As obras listadas serão ignoradas (padrão)"
        },
        "filtros": {
            "por_id": {
                "description": "Lista de IDs de obras para incluir/excluir",
                "valores": []
            },
            "por_nome_contem": {
                "description": "Excluir obras que contenham estas strings no nome",
                "valores": []
            },
            "por_empresa": {
                "description": "Excluir obras de empresas específicas (companyId)",
                "valores": []
            }
        }
    }


def save_filtros_obras(filtros: Dict) -> bool:
    """Salva filtros de obras no JSON"""
    try:
        filtros_path = CONFIG_DIR / 'filtros_obras.json'
        with open(filtros_path, 'w', encoding='utf-8') as f:
            json.dump(filtros, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar filtros: {e}")
        return False


def aplicar_filtros_obras(obras: List[Dict], filtro_basico: str = "- Obra") -> Tuple[List[Dict], List[Dict]]:
    """
    Aplica filtros às obras
    Returns: (obras_incluidas, obras_excluidas)
    """
    filtros = load_filtros_obras()
    
    # Filtro básico por string
    obras_basico = [obra for obra in obras if filtro_basico in obra.get('name', '')]
    
    # Se não há filtros configurados, retorna tudo
    if not filtros.get('filtros'):
        return obras_basico, []
    
    modo = filtros.get('modo', 'excluir')
    obras_filtradas = obras_basico.copy()
    
    # Filtro por ID
    ids_filtro = filtros['filtros']['por_id'].get('valores', [])
    if ids_filtro:
        if modo == 'excluir':
            obras_filtradas = [o for o in obras_filtradas if o['id'] not in ids_filtro]
        else:
            obras_filtradas = [o for o in obras_filtradas if o['id'] in ids_filtro]
    
    # Filtro por string no nome
    strings_filtro = filtros['filtros']['por_nome_contem'].get('valores', [])
    for string_filtro in strings_filtro:
        if modo == 'excluir':
            obras_filtradas = [o for o in obras_filtradas 
                             if string_filtro.lower() not in o['name'].lower()]
        else:
            obras_filtradas = [o for o in obras_filtradas 
                             if string_filtro.lower() in o['name'].lower()]
    
    # Filtro por empresa
    empresas_filtro = filtros['filtros']['por_empresa'].get('valores', [])
    if empresas_filtro:
        if modo == 'excluir':
            obras_filtradas = [o for o in obras_filtradas 
                             if o.get('companyId') not in empresas_filtro]
        else:
            obras_filtradas = [o for o in obras_filtradas 
                             if o.get('companyId') in empresas_filtro]
    
    # Calcular excluídas
    ids_incluidas = {obra['id'] for obra in obras_filtradas}
    obras_excluidas = [obra for obra in obras_basico if obra['id'] not in ids_incluidas]
    
    return obras_filtradas, obras_excluidas


def load_merge_config() -> Dict:
    """Carrega configuração de merge"""
    try:
        merge_path = CONFIG_DIR / 'merge_centros_custo.json'
        if merge_path.exists():
            with open(merge_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return create_default_merge_config()
    except Exception as e:
        print(f"Erro ao carregar merge config: {e}")
        return create_default_merge_config()


def create_default_merge_config() -> Dict:
    """Cria configuração padrão de merge"""
    return {
        "habilitado": False,
        "merge_obras": {},
        "merge_apropriacoes": {}
    }


def save_merge_config(config: Dict) -> bool:
    """Salva configuração de merge"""
    try:
        merge_path = CONFIG_DIR / 'merge_centros_custo.json'
        with open(merge_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar merge config: {e}")
        return False


def get_building_units_config() -> Dict:
    """Configurações de Building Units"""
    return {
        'filter_enabled': os.getenv('BUILDING_UNIT_FILTER_ENABLED', 'true').lower() == 'true',
        'allowed_ids': [int(x.strip()) for x in os.getenv('BUILDING_UNIT_IDS_ALLOWED', '1').split(',')],
        'default_ids': [1, 2, 3, 4, 5, 6, 7, 8]
    }


def set_building_units_config(filter_enabled: bool, allowed_ids: List[int]) -> None:
    """Define configuração de Building Units (temporária para sessão)"""
    os.environ['BUILDING_UNIT_FILTER_ENABLED'] = str(filter_enabled).lower()
    os.environ['BUILDING_UNIT_IDS_ALLOWED'] = ','.join(map(str, allowed_ids))


def should_include_building_unit(building_unit_id: int) -> bool:
    """Verifica se Building Unit deve ser incluído"""
    config = get_building_units_config()
    
    if not config['filter_enabled']:
        return True
    
    return building_unit_id in config['allowed_ids']


def validate_api_config() -> Tuple[bool, List[str]]:
    """Valida configurações da API"""
    config = get_api_config()
    errors = []
    
    if not config['user']:
        errors.append("SIENGE_USER não está definido")
    
    if not config['password']:
        errors.append("SIENGE_PASSWORD não está definido")
    
    if not config['subdomain']:
        errors.append("SIENGE_SUBDOMAIN não está definido")
    
    if config['timeout'] < 10:
        errors.append("API_TIMEOUT deve ser pelo menos 10 segundos")
    
    if config['max_retries'] < 1:
        errors.append("API_MAX_RETRIES deve ser pelo menos 1")
    
    return len(errors) == 0, errors


def get_paths() -> Dict[str, Path]:
    """Retorna todos os caminhos importantes"""
    return {
        'base': BASE_DIR,
        'config': CONFIG_DIR,
        'data': DATA_DIR,
        'cache': CACHE_DIR,
        'reports': REPORTS_DIR,
        'filtros_obras': CONFIG_DIR / 'filtros_obras.json',
        'merge_config': CONFIG_DIR / 'merge_centros_custo.json'
    }


def load_classificacao_abc() -> Dict:
    """Carrega configuração de classificação ABC de insumos"""
    try:
        abc_path = CONFIG_DIR / 'classificacao_abc.json'
        if abc_path.exists():
            with open(abc_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return create_default_classificacao_abc()
    except Exception as e:
        print(f"Erro ao carregar classificação ABC: {e}")
        return create_default_classificacao_abc()


def create_default_classificacao_abc() -> Dict:
    """Cria configuração padrão de classificação ABC"""
    return {
        "por_insumo_id": {},
        "por_grupo_recurso": {},
        "por_categoria_recurso": {}
    }


def obter_classificacao_abc(lancamento: Dict, config_abc: Dict) -> str:
    """
    Obtém classificação ABC para um lançamento.
    Prioridade: insumo_id > grupo_recurso > categoria_recurso
    Retorna string vazia se não encontrar classificação.
    """
    insumo_id = str(lancamento.get('insumo_id', ''))
    grupo_recurso = lancamento.get('grupo_recurso', '')
    categoria_recurso = lancamento.get('categoria_recurso', '')

    # Prioridade 1: Por insumo_id específico
    if insumo_id and insumo_id in config_abc.get('por_insumo_id', {}):
        return config_abc['por_insumo_id'][insumo_id]

    # Prioridade 2: Por grupo de recurso
    if grupo_recurso and grupo_recurso in config_abc.get('por_grupo_recurso', {}):
        return config_abc['por_grupo_recurso'][grupo_recurso]

    # Prioridade 3: Por categoria de recurso
    if categoria_recurso and categoria_recurso in config_abc.get('por_categoria_recurso', {}):
        return config_abc['por_categoria_recurso'][categoria_recurso]

    # Não encontrou classificação
    return ''


def load_all_configs() -> Dict:
    """Carrega todas as configurações de uma vez"""
    return {
        'api': get_api_config(),
        'cache': get_cache_config(),
        'filtros_obras': load_filtros_obras(),
        'merge': load_merge_config(),
        'building_units': get_building_units_config(),
        'report_options': get_default_report_options(),
        'paths': get_paths(),
        'classificacao_abc': load_classificacao_abc()
    }


def print_config_summary():
    """Imprime resumo das configurações"""
    configs = load_all_configs()
    
    print("CONFIGURAÇÕES DO SISTEMA")
    print("=" * 50)
    
    # API
    print(f"API User: {configs['api']['user']}")
    print(f"API Subdomain: {configs['api']['subdomain']}")
    print(f"API Timeout: {configs['api']['timeout']}s")
    
    # Cache
    print(f"Cache: {'Habilitado' if configs['cache']['enabled'] else 'Desabilitado'}")
    print(f"Cache Validade: {configs['cache']['validity_hours']}h")
    
    # Building Units
    units_config = configs['building_units']
    if units_config['filter_enabled']:
        print(f"Building Units: Filtro ativo - IDs {units_config['allowed_ids']}")
    else:
        print("Building Units: Todos incluídos (sem filtro)")
    
    # Filtros
    filtros = configs['filtros_obras']
    modo = filtros.get('modo', 'excluir')
    ids_count = len(filtros['filtros']['por_id'].get('valores', []))
    strings_count = len(filtros['filtros']['por_nome_contem'].get('valores', []))
    print(f"Filtros Obras: Modo '{modo}' - {ids_count} IDs, {strings_count} strings")
    
    # Merge
    merge = configs['merge']
    merge_status = "Habilitado" if merge.get('habilitado') else "Desabilitado"
    obras_merge = len(merge.get('merge_obras', {}))
    print(f"Merge: {merge_status} - {obras_merge} mapeamentos de obras")


if __name__ == '__main__':
    # Teste das configurações
    create_directories()
    
    valid, errors = validate_api_config()
    if not valid:
        print("ERROS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"  - {error}")
    else:
        print_config_summary()
