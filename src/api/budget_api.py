"""
API de Orçamentos V4 - Sistema Insumos x Orçamento
Busca e cacheia mapeamentos WBS (estrutura hierárquica de apropriações)
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from requests import Session


def gerar_chave_cache_wbs(obra_id: int, sheet_id: int = 1) -> str:
    """Gera chave única para cache de WBS"""
    return hashlib.md5(f"wbs_{obra_id}_{sheet_id}".encode()).hexdigest()


def verificar_cache_wbs(cache_dir: Path, obra_id: int, validity_hours: int = 168) -> Tuple[bool, Optional[Dict]]:
    """
    Verifica se existe cache válido de WBS para a obra
    Returns: (cache_valido, mapeamento_ou_none)
    """
    chave = gerar_chave_cache_wbs(obra_id)
    arquivo_cache = cache_dir / f"wbs_{chave}.json"
    
    if not arquivo_cache.exists():
        return False, None
    
    try:
        with open(arquivo_cache, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Verificar timestamp
        timestamp = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - timestamp > timedelta(hours=validity_hours):
            return False, None
        
        # Verificar se tem erro
        if 'erro' in cache_data:
            return False, None
        
        return True, cache_data.get('mapeamento', {})
        
    except (json.JSONDecodeError, KeyError, ValueError):
        return False, None


def salvar_cache_wbs(cache_dir: Path, obra_id: int, mapeamento: Dict, total_itens: int = 0) -> bool:
    """Salva mapeamento WBS no cache"""
    chave = gerar_chave_cache_wbs(obra_id)
    arquivo_cache = cache_dir / f"wbs_{chave}.json"
    
    cache_data = {
        'obra_id': obra_id,
        'sheet_id': 1,
        'total_itens': total_itens,
        'total_mapeamentos': len(mapeamento),
        'timestamp': datetime.now().isoformat(),
        'mapeamento': mapeamento
    }
    
    try:
        with open(arquivo_cache, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def buscar_sheets_orcamento(session: Session, obra_id: int, api_config: Dict, logger) -> Optional[List[Dict]]:
    """Busca sheets de orçamento disponíveis para uma obra"""
    url = f"{api_config['base_url']}/v1/building-cost-estimations/{obra_id}/sheets"
    params = {'offset': 0, 'limit': 100}
    
    logger.debug(f"Buscando sheets de orçamento para obra {obra_id}")
    
    try:
        response = session.get(url, params=params, timeout=api_config['timeout'])
        response.raise_for_status()
        
        data = response.json()
        sheets = data.get('results', [])
        
        logger.debug(f"Obra {obra_id}: {len(sheets)} sheets encontrados")
        return sheets
        
    except Exception as e:
        logger.warning(f"Erro ao buscar sheets da obra {obra_id}: {str(e)}")
        return None


def buscar_itens_sheet_paginado(session: Session, obra_id: int, sheet_id: int, 
                               api_config: Dict, logger) -> List[Dict]:
    """Busca todos os itens de um sheet com paginação automática"""
    url = f"{api_config['base_url']}/v1/building-cost-estimations/{obra_id}/sheets/{sheet_id}/items"
    
    logger.info(f"Buscando itens WBS: Obra {obra_id}, Sheet {sheet_id}")
    
    todos_itens = []
    offset = 0
    limit = 200
    
    while True:
        params = {'offset': offset, 'limit': limit}
        
        try:
            logger.debug(f"Obra {obra_id}: página {offset//limit + 1} (offset: {offset})")
            
            response = session.get(url, params=params, timeout=api_config['timeout'])
            response.raise_for_status()
            
            data = response.json()
            itens = data.get('results', [])
            
            if not itens:
                break
            
            todos_itens.extend(itens)
            logger.debug(f"Obra {obra_id}: +{len(itens)} itens (total: {len(todos_itens)})")
            
            # Se retornou menos que o limite, chegamos ao fim
            if len(itens) < limit:
                break
            
            offset += limit
            time.sleep(api_config.get('delay', 1.0))
            
        except Exception as e:
            logger.error(f"Erro ao buscar página {offset//limit + 1} da obra {obra_id}: {str(e)}")
            break
    
    logger.info(f"Obra {obra_id}: {len(todos_itens)} itens WBS coletados")
    return todos_itens


def criar_mapeamento_wbs(itens_sheet: List[Dict], logger) -> Dict[str, str]:
    """
    Cria mapeamento completo de códigos WBS para descrições
    Inclui todos os níveis hierárquicos
    """
    mapeamento = {}
    
    for item in itens_sheet:
        wbs_code = item.get('wbsCode', '').strip()
        description = item.get('description', '').strip()
        
        if not wbs_code or not description:
            continue
        
        # Adicionar o código completo
        mapeamento[wbs_code] = description
        
        # Extrair e adicionar níveis hierárquicos
        niveis = extrair_niveis_codigo(wbs_code)
        
        # Para níveis intermediários, tentar inferir descrição
        # ou buscar se já existe um item específico para aquele nível
        for nivel in niveis[:-1]:  # Todos exceto o último (que já foi adicionado)
            if nivel not in mapeamento:
                # Procurar se existe um item específico para este nível
                item_nivel = next((it for it in itens_sheet 
                                 if it.get('wbsCode', '').strip() == nivel), None)
                if item_nivel:
                    mapeamento[nivel] = item_nivel.get('description', '').strip()
                else:
                    # Se não encontrou, deixar vazio para ser preenchido depois
                    mapeamento[nivel] = ''
    
    # Tentar inferir descrições de níveis intermediários vazios
    mapeamento = inferir_descricoes_niveis_intermediarios(mapeamento, logger)
    
    logger.debug(f"Mapeamento WBS criado: {len(mapeamento)} códigos")
    return mapeamento


def extrair_niveis_codigo(codigo_completo: str) -> List[str]:
    """
    Extrai todos os níveis hierárquicos de um código
    '05.002.001.001' → ['05', '05.002', '05.002.001', '05.002.001.001']
    """
    if not codigo_completo:
        return []
    
    partes = codigo_completo.split('.')
    niveis = []
    
    for i in range(1, len(partes) + 1):
        nivel = '.'.join(partes[:i])
        niveis.append(nivel)
    
    return niveis


def inferir_descricoes_niveis_intermediarios(mapeamento: Dict[str, str], logger) -> Dict[str, str]:
    """
    Tenta inferir descrições para níveis intermediários vazios
    baseado em códigos filhos que tenham descrição
    """
    mapeamento_atualizado = mapeamento.copy()
    
    # Agrupar códigos por nível hierárquico
    por_nivel = {}
    for codigo in mapeamento.keys():
        nivel = len(codigo.split('.'))
        if nivel not in por_nivel:
            por_nivel[nivel] = []
        por_nivel[nivel].append(codigo)
    
    # Para cada nível, tentar inferir descrições vazias
    for nivel in sorted(por_nivel.keys()):
        for codigo in por_nivel[nivel]:
            if not mapeamento_atualizado.get(codigo, '').strip():
                # Buscar códigos filhos que tenham descrição
                codigo_pattern = codigo + '.'
                filhos_com_desc = [
                    (c, desc) for c, desc in mapeamento.items()
                    if c.startswith(codigo_pattern) and desc.strip()
                ]
                
                if filhos_com_desc:
                    # Usar a descrição do primeiro filho como base
                    desc_filho = filhos_com_desc[0][1]
                    # Tentar extrair parte mais geral da descrição
                    desc_inferida = extrair_descricao_geral(desc_filho)
                    mapeamento_atualizado[codigo] = desc_inferida
                    logger.debug(f"Descrição inferida para {codigo}: {desc_inferida}")
    
    return mapeamento_atualizado


def extrair_descricao_geral(descricao_especifica: str) -> str:
    """
    Tenta extrair uma descrição mais geral de uma específica
    Ex: "RESERVATÓRIO INFERIOR CONCRETO" → "RESERVATÓRIOS"
    """
    # Por enquanto, retorna a descrição como está
    # Futuramente pode implementar lógica mais sofisticada
    return descricao_especifica


def buscar_mapeamento_wbs_obra(session: Session, obra_id: int, api_config: Dict, 
                              cache_config: Dict, logger) -> Dict[str, str]:
    """
    Busca mapeamento WBS de uma obra (com cache)
    Returns: dicionário {codigo_wbs: descricao}
    """
    # Verificar cache primeiro
    if cache_config.get('enabled', True):
        cache_valido, mapeamento_cache = verificar_cache_wbs(
            cache_config['directory'], obra_id, cache_config.get('validity_hours', 168)
        )
        
        if cache_valido and mapeamento_cache:
            logger.debug(f"Obra {obra_id}: usando mapeamento WBS do cache")
            return mapeamento_cache
    
    # Buscar via API
    logger.info(f"Buscando mapeamento WBS via API: Obra {obra_id}")
    
    # 1. Verificar se obra tem orçamento
    sheets = buscar_sheets_orcamento(session, obra_id, api_config, logger)
    if not sheets:
        logger.warning(f"Obra {obra_id}: sem sheets de orçamento")
        # Salvar cache vazio para evitar tentar novamente
        if cache_config.get('enabled', True):
            salvar_cache_wbs(cache_config['directory'], obra_id, {}, 0)
        return {}
    
    # 2. Buscar itens do sheet 1 (padrão)
    sheet_id = 1
    itens = buscar_itens_sheet_paginado(session, obra_id, sheet_id, api_config, logger)
    
    if not itens:
        logger.warning(f"Obra {obra_id}: sem itens no sheet {sheet_id}")
        # Salvar cache vazio
        if cache_config.get('enabled', True):
            salvar_cache_wbs(cache_config['directory'], obra_id, {}, 0)
        return {}
    
    # 3. Criar mapeamento
    mapeamento = criar_mapeamento_wbs(itens, logger)
    
    # 4. Salvar no cache
    if cache_config.get('enabled', True):
        sucesso = salvar_cache_wbs(cache_config['directory'], obra_id, mapeamento, len(itens))
        if sucesso:
            logger.debug(f"Obra {obra_id}: mapeamento WBS salvo no cache")
    
    logger.info(f"Obra {obra_id}: mapeamento WBS criado com {len(mapeamento)} códigos")
    return mapeamento


def buscar_mapeamentos_todas_obras(session: Session, obras: List[Dict], api_config: Dict,
                                  cache_config: Dict, logger, callback_progress=None) -> Dict[int, Dict[str, str]]:
    """
    Busca mapeamentos WBS de todas as obras selecionadas
    Returns: {obra_id: {codigo_wbs: descricao}}
    """
    logger.info(f"Iniciando busca de mapeamentos WBS para {len(obras)} obras")
    
    mapeamentos = {}
    obras_processadas = 0
    obras_com_orcamento = 0
    obras_sem_orcamento = 0
    
    for i, obra in enumerate(obras, 1):
        obra_id = obra['id']
        obra_nome = obra['name']
        
        if callback_progress:
            callback_progress(i, len(obras), f"WBS {obra_nome}")
        
        mapeamento = buscar_mapeamento_wbs_obra(session, obra_id, api_config, cache_config, logger)
        
        if mapeamento:
            mapeamentos[obra_id] = mapeamento
            obras_com_orcamento += 1
            logger.debug(f"Obra {obra_id}: {len(mapeamento)} códigos WBS")
        else:
            mapeamentos[obra_id] = {}
            obras_sem_orcamento += 1
            logger.warning(f"Obra {obra_id}: sem mapeamento WBS")
        
        obras_processadas += 1
        
        # Delay entre requisições
        if i < len(obras):
            time.sleep(api_config.get('delay', 1.0))
    
    logger.info(f"Mapeamentos WBS concluídos: {obras_processadas} obras, "
               f"{obras_com_orcamento} com orçamento, {obras_sem_orcamento} sem orçamento")
    
    return mapeamentos


def debug_mapeamento_wbs(mapeamento: Dict[str, str], logger, max_exemplos: int = 10) -> None:
    """Debug do mapeamento WBS de uma obra"""
    if not mapeamento:
        logger.info("Mapeamento WBS vazio")
        return
    
    # Agrupar por nível
    por_nivel = {}
    for codigo in mapeamento.keys():
        nivel = len(codigo.split('.'))
        if nivel not in por_nivel:
            por_nivel[nivel] = []
        por_nivel[nivel].append(codigo)
    
    logger.info(f"Mapeamento WBS - Total: {len(mapeamento)} códigos")
    
    for nivel in sorted(por_nivel.keys()):
        codigos_nivel = por_nivel[nivel]
        logger.info(f"  Nível {nivel}: {len(codigos_nivel)} códigos")
        
        # Mostrar alguns exemplos
        for codigo in sorted(codigos_nivel)[:max_exemplos]:
            descricao = mapeamento.get(codigo, '')
            logger.info(f"    {codigo} → {descricao}")
        
        if len(codigos_nivel) > max_exemplos:
            logger.info(f"    ... e mais {len(codigos_nivel) - max_exemplos} códigos")


if __name__ == '__main__':
    # Teste básico do módulo
    from ..config.settings import load_all_configs
    from ..utils.logger import get_main_logger
    from ..api.api_client import criar_cliente_api
    
    configs = load_all_configs()
    logger = get_main_logger(configs)
    session = criar_cliente_api(configs)
    
    # Testar com obra específica
    obra_teste = {'id': 905, 'name': 'SPE Cora'}
    
    mapeamento = buscar_mapeamento_wbs_obra(
        session, obra_teste['id'], configs['api'], configs['cache'], logger
    )
    
    debug_mapeamento_wbs(mapeamento, logger)
    print(f"Teste concluído: {len(mapeamento)} códigos WBS encontrados")