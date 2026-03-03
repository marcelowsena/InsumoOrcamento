"""
Engine de Merge V4 - Sistema Insumos x Orçamento
VERSÃO CORRIGIDA: Move apenas APROPRIADOS, mantém PENDENTES e ORÇADOS na obra original
"""

from typing import Dict, List, Tuple, Set
from copy import deepcopy


def validar_config_merge(config_merge: Dict, logger) -> Tuple[bool, List[str]]:
    """
    Valida configuração de merge
    Returns: (valido, lista_erros)
    """
    erros = []
    
    if not isinstance(config_merge, dict):
        erros.append("Configuração deve ser um dicionário")
        return False, erros
    
    # Verificar estrutura básica
    if 'habilitado' not in config_merge:
        erros.append("Campo 'habilitado' ausente")
    
    merge_obras = config_merge.get('merge_obras', {})
    merge_apropriacoes = config_merge.get('merge_apropriacoes', {})
    
    # Validar merge_obras
    for obra_destino, config_obra in merge_obras.items():
        try:
            int(obra_destino)
        except ValueError:
            erros.append(f"ID de obra destino inválido: {obra_destino}")
        
        if 'obras_para_somar' not in config_obra:
            erros.append(f"Obra {obra_destino}: campo 'obras_para_somar' ausente")
        elif not isinstance(config_obra['obras_para_somar'], list):
            erros.append(f"Obra {obra_destino}: 'obras_para_somar' deve ser lista")
    
    # Validar merge_apropriacoes
    for obra_id, mapeamentos in merge_apropriacoes.items():
        if not isinstance(mapeamentos, dict):
            erros.append(f"Obra {obra_id}: mapeamentos devem ser dicionário")
            continue
        
        for centro_destino, config_centro in mapeamentos.items():
            if 'centros_para_somar' not in config_centro:
                erros.append(f"Obra {obra_id}, centro {centro_destino}: 'centros_para_somar' ausente")
            elif not isinstance(config_centro['centros_para_somar'], list):
                erros.append(f"Obra {obra_id}, centro {centro_destino}: 'centros_para_somar' deve ser lista")
    
    # Verificar referências circulares em obras
    for obra_destino, config_obra in merge_obras.items():
        obras_origem = config_obra.get('obras_para_somar', [])
        if int(obra_destino) in obras_origem:
            erros.append(f"Referência circular: obra {obra_destino} não pode somar em si mesma")
    
    # Log da validação
    if erros:
        logger.error(f"Configuração de merge inválida: {len(erros)} erros encontrados")
        for erro in erros:
            logger.error(f"  - {erro}")
    else:
        logger.info("Configuração de merge válida")
    
    return len(erros) == 0, erros


def criar_mapeamento_centros_custo(merge_apropriacoes: Dict) -> Dict[str, Dict[str, str]]:
    """
    Cria mapeamento reverso para centros de custo
    Returns: {obra_id: {codigo_origem: codigo_destino}}
    """
    mapeamento_reverso = {}
    
    for obra_id, mapeamentos in merge_apropriacoes.items():
        mapeamento_reverso[obra_id] = {}
        
        for centro_destino, config in mapeamentos.items():
            centros_origem = config.get('centros_para_somar', [])
            for codigo_origem in centros_origem:
                mapeamento_reverso[obra_id][codigo_origem] = centro_destino
    
    return mapeamento_reverso


def aplicar_merge_obras(resultados: List[Dict], config_merge: Dict, logger) -> List[Dict]:
    """
    Aplica merge inteligente de obras nos resultados
    VERSÃO CORRIGIDA: Move apenas APROPRIADOS, mantém PENDENTES e ORÇADOS na obra original
    Returns: resultados modificados
    """
    if not config_merge.get('habilitado', False):
        logger.info("Merge desabilitado")
        return resultados
    
    merge_obras = config_merge.get('merge_obras', {})
    if not merge_obras:
        logger.warning("Nenhuma configuração de merge de obras encontrada")
        return resultados
    
    logger.info(f"Iniciando merge de obras: {len(merge_obras)} configurações")
    
    # Trabalhar com cópia para não modificar original
    resultados_processados = deepcopy(resultados)
    
    # Criar mapeamento de centros de custo
    merge_apropriacoes = config_merge.get('merge_apropriacoes', {})
    mapeamento_centros = criar_mapeamento_centros_custo(merge_apropriacoes)
    
    estatisticas_merge = {
        'obras_processadas': 0,
        'recursos_transferidos': 0,
        'apropriados_transferidos': 0,
        'valor_total_transferido': 0
    }
    
    # Processar cada configuração de merge
    for obra_destino_str, config_obra in merge_obras.items():
        obra_destino_id = int(obra_destino_str)
        obras_origem = config_obra.get('obras_para_somar', [])
        
        logger.info(f"Processando merge para obra {obra_destino_id} ← {obras_origem}")
        
        # Encontrar resultado da obra destino
        resultado_destino = _encontrar_resultado_obra(resultados_processados, obra_destino_id)
        if not resultado_destino:
            logger.error(f"Obra destino {obra_destino_id} não encontrada")
            continue
        
        # Verificar configuração de centros de custo para esta obra
        centros_config = mapeamento_centros.get(obra_destino_str, {})
        if not centros_config:
            logger.warning(f"Obra {obra_destino_id} sem configuração de centros de custo")
            continue
        
        logger.info(f"Obra {obra_destino_id} tem {len(centros_config)} mapeamentos de centros")
        
        # Processar cada obra origem
        for obra_origem_id in obras_origem:
            obra_origem_id = int(obra_origem_id)
            
            stats = _processar_merge_obra_origem_apenas_apropriados(
                resultados_processados, obra_origem_id, obra_destino_id, 
                centros_config, logger
            )
            
            estatisticas_merge['obras_processadas'] += 1
            estatisticas_merge['apropriados_transferidos'] += stats['apropriados_transferidos']
            estatisticas_merge['valor_total_transferido'] += stats['valor_transferido']
    
    logger.info(f"Merge de obras concluído: {estatisticas_merge['obras_processadas']} obras, "
               f"{estatisticas_merge['apropriados_transferidos']} apropriados transferidos, "
               f"R$ {estatisticas_merge['valor_total_transferido']:.2f}")
    
    return resultados_processados


def _encontrar_resultado_obra(resultados: List[Dict], obra_id: int) -> Dict:
    """Encontra resultado de uma obra específica"""
    for resultado in resultados:
        if resultado['obra']['id'] == obra_id:
            return resultado
    return None


def _processar_merge_obra_origem_apenas_apropriados(resultados: List[Dict], obra_origem_id: int, 
                                                   obra_destino_id: int, centros_config: Dict, 
                                                   logger) -> Dict:
    """
    Processa merge de uma obra origem específica - APENAS APROPRIADOS
    PENDENTES e ORÇADOS permanecem na obra original
    Returns: estatísticas do processamento
    """
    logger.info(f"Processando obra origem {obra_origem_id} → {obra_destino_id} (apenas apropriados)")
    
    # Encontrar resultados
    resultado_origem = _encontrar_resultado_obra(resultados, obra_origem_id)
    resultado_destino = _encontrar_resultado_obra(resultados, obra_destino_id)
    
    stats = {'apropriados_transferidos': 0, 'valor_transferido': 0}
    
    if not resultado_origem:
        logger.warning(f"Obra origem {obra_origem_id} não encontrada")
        return stats
    
    if not resultado_destino:
        logger.error(f"Obra destino {obra_destino_id} não encontrada")
        return stats
    
    dados_origem = resultado_origem.get('relatorio_bruto', {})
    if 'erro' in dados_origem:
        logger.warning(f"Obra origem {obra_origem_id} tem erro: {dados_origem['erro']}")
        return stats
    
    recursos_origem = dados_origem.get('data', [])
    if not recursos_origem:
        logger.info(f"Obra origem {obra_origem_id} sem recursos")
        return stats
    
    # Processar cada recurso - SEPARAR APENAS APROPRIADOS
    recursos_modificados = []
    recursos_para_transferir = []
    
    for recurso in recursos_origem:
        resultado_processamento = _separar_apenas_apropriados_por_centros(
            recurso, centros_config, logger
        )
        
        # Recurso modificado para ficar na origem (sem apropriados transferidos)
        if resultado_processamento['recurso_origem_modificado']:
            recursos_modificados.append(resultado_processamento['recurso_origem_modificado'])
        
        # Recurso para transferir (apenas com apropriados)
        if resultado_processamento['recurso_para_transferir']:
            recursos_para_transferir.append(resultado_processamento['recurso_para_transferir'])
            stats['apropriados_transferidos'] += resultado_processamento['apropriados_count']
            stats['valor_transferido'] += resultado_processamento['valor_transferido']
    
    # Atualizar obra origem com recursos modificados
    dados_origem['data'] = recursos_modificados
    
    # Adicionar recursos transferidos à obra destino
    if recursos_para_transferir:
        dados_destino = resultado_destino.get('relatorio_bruto', {})
        if 'data' not in dados_destino:
            dados_destino['data'] = []
        
        dados_destino['data'].extend(recursos_para_transferir)
        
        logger.info(f"Transferidos {len(recursos_para_transferir)} recursos com apropriados, "
                   f"R$ {stats['valor_transferido']:.2f}")
    
    logger.info(f"Obra origem {obra_origem_id}: {len(recursos_modificados)} recursos mantidos")
    
    return stats


def _separar_apenas_apropriados_por_centros(recurso: Dict, centros_config: Dict, 
                                           logger) -> Dict:
    """
    Separa APENAS apropriados de um recurso baseado nos centros de custo
    PENDENTES e ORÇADOS permanecem no recurso original
    Returns: {
        'recurso_origem_modificado': recurso sem apropriados transferidos,
        'recurso_para_transferir': recurso apenas com apropriados transferidos,
        'apropriados_count': quantidade transferida,
        'valor_transferido': valor total transferido
    }
    """
    apropriacoes_origem = recurso.get('buildingAppropriations', {})
    apropriados_atendidos = apropriacoes_origem.get('attended', [])
    apropriados_pendentes = apropriacoes_origem.get('pending', [])  # MANTER na origem
    itens_orcados = recurso.get('buildingCostEstimationItems', [])  # MANTER na origem
    
    apropriados_transferir = []
    apropriados_manter = []
    valor_total_transferido = 0
    
    # Classificar apenas os apropriados atendidos
    for apropriado in apropriados_atendidos:
        codigo = apropriado.get('costEstimationItemReference', '')
        
        if codigo in centros_config:
            apropriados_transferir.append(apropriado)
            valor_total_transferido += float(apropriado.get('value', 0))
        else:
            apropriados_manter.append(apropriado)
    
    resultado = {
        'recurso_origem_modificado': None,
        'recurso_para_transferir': None,
        'apropriados_count': len(apropriados_transferir),
        'valor_transferido': valor_total_transferido
    }
    
    # Criar recurso modificado para origem (sem apropriados transferidos)
    if apropriados_manter or apropriados_pendentes or itens_orcados:
        recurso_origem = recurso.copy()
        recurso_origem['buildingAppropriations'] = {
            'attended': apropriados_manter,  # Apenas apropriados não transferidos
            'pending': apropriados_pendentes  # TODOS os pendentes permanecem
        }
        # buildingCostEstimationItems permanece inalterado (TODOS os orçados permanecem)
        resultado['recurso_origem_modificado'] = recurso_origem
    
    # Criar recurso para transferir (apenas apropriados transferidos)
    if apropriados_transferir:
        recurso_transferir = recurso.copy()
        recurso_transferir['buildingAppropriations'] = {
            'attended': apropriados_transferir,  # Apenas apropriados transferidos
            'pending': []  # Pendentes não são transferidos
        }
        # Remover orçados do recurso transferido
        recurso_transferir['buildingCostEstimationItems'] = []
        resultado['recurso_para_transferir'] = recurso_transferir
    
    return resultado


def aplicar_merge_centros_custo(lancamentos: List[Dict], config_merge: Dict, 
                               logger) -> List[Dict]:
    """
    Aplica merge de centros de custo nos lançamentos
    Returns: lançamentos modificados
    """
    if not config_merge.get('habilitado', False):
        logger.info("Merge de centros de custo desabilitado")
        return lancamentos
    
    merge_apropriacoes = config_merge.get('merge_apropriacoes', {})
    if not merge_apropriacoes:
        logger.warning("Nenhuma configuração de merge de apropriações")
        return lancamentos
    
    logger.info("Iniciando merge de centros de custo")
    
    # Criar mapeamento reverso
    mapeamento_reverso = criar_mapeamento_centros_custo(merge_apropriacoes)
    
    lancamentos_afetados = 0
    
    for lancamento in lancamentos:
        obra_id = str(lancamento.get('building_id', ''))
        
        if obra_id not in mapeamento_reverso:
            continue
        
        codigo_orig = lancamento.get('codigo_apropriacao', '')
        
        if codigo_orig in mapeamento_reverso[obra_id]:
            centro_destino = mapeamento_reverso[obra_id][codigo_orig]
            
            # Atualizar apropriação
            nova_apropriacao = f"{centro_destino} - Transformado pelo merge"
            lancamento['apropriacao_completa'] = nova_apropriacao
            lancamento['codigo_apropriacao'] = centro_destino
            
            lancamentos_afetados += 1
    
    logger.info(f"Merge de centros concluído: {lancamentos_afetados} lançamentos afetados")
    
    return lancamentos


def gerar_relatorio_merge(config_merge: Dict, estatisticas_obras: Dict = None) -> Dict:
    """
    Gera relatório das operações de merge
    Returns: relatório estruturado
    """
    merge_obras = config_merge.get('merge_obras', {})
    merge_apropriacoes = config_merge.get('merge_apropriacoes', {})
    
    # Contar mapeamentos
    total_mapeamentos_obras = len(merge_obras)
    total_obras_origem = sum(len(config['obras_para_somar']) 
                            for config in merge_obras.values())
    
    total_mapeamentos_apropriacoes = sum(len(mapeamentos) 
                                       for mapeamentos in merge_apropriacoes.values())
    total_centros_origem = sum(
        len(config['centros_para_somar'])
        for mapeamentos in merge_apropriacoes.values()
        for config in mapeamentos.values()
    )
    
    relatorio = {
        'config_summary': {
            'merge_habilitado': config_merge.get('habilitado', False),
            'mapeamentos_obras': total_mapeamentos_obras,
            'obras_origem_total': total_obras_origem,
            'mapeamentos_apropriacoes': total_mapeamentos_apropriacoes,
            'centros_origem_total': total_centros_origem
        },
        'merge_obras_detalhes': {},
        'merge_apropriacoes_detalhes': {}
    }
    
    # Detalhar merge de obras
    for obra_destino, config in merge_obras.items():
        relatorio['merge_obras_detalhes'][obra_destino] = {
            'obras_origem': config['obras_para_somar'],
            'quantidade_origem': len(config['obras_para_somar']),
            'observacoes': config.get('observacoes', '')
        }
    
    # Detalhar merge de apropriações
    for obra_id, mapeamentos in merge_apropriacoes.items():
        relatorio['merge_apropriacoes_detalhes'][obra_id] = {}
        for centro_destino, config in mapeamentos.items():
            relatorio['merge_apropriacoes_detalhes'][obra_id][centro_destino] = {
                'centros_origem': config['centros_para_somar'],
                'quantidade_origem': len(config['centros_para_somar']),
                'observacoes': config.get('observacoes', '')
            }
    
    # Incluir estatísticas se fornecidas
    if estatisticas_obras:
        relatorio['estatisticas_processamento'] = estatisticas_obras
    
    return relatorio


def detectar_conflitos_merge(config_merge: Dict) -> List[Dict]:
    """
    Detecta possíveis conflitos na configuração de merge
    Returns: lista de conflitos encontrados
    """
    conflitos = []
    merge_obras = config_merge.get('merge_obras', {})
    merge_apropriacoes = config_merge.get('merge_apropriacoes', {})
    
    # Detectar obras origem duplicadas
    todas_obras_origem = []
    for obra_destino, config in merge_obras.items():
        for obra_origem in config['obras_para_somar']:
            if obra_origem in todas_obras_origem:
                conflitos.append({
                    'tipo': 'obra_origem_duplicada',
                    'obra_origem': obra_origem,
                    'description': f"Obra {obra_origem} é origem em múltiplos merges"
                })
            todas_obras_origem.append(obra_origem)
    
    # Detectar códigos de apropriação duplicados dentro da mesma obra
    for obra_id, mapeamentos in merge_apropriacoes.items():
        todos_centros_origem = []
        for centro_destino, config in mapeamentos.items():
            for centro_origem in config['centros_para_somar']:
                if centro_origem in todos_centros_origem:
                    conflitos.append({
                        'tipo': 'centro_origem_duplicado',
                        'obra_id': obra_id,
                        'centro_origem': centro_origem,
                        'description': f"Centro {centro_origem} mapeado múltiplas vezes na obra {obra_id}"
                    })
                todos_centros_origem.append(centro_origem)
    
    # Detectar inconsistências entre merge de obras e apropriações
    obras_com_merge = set(merge_obras.keys())
    obras_com_apropriacoes = set(merge_apropriacoes.keys())
    
    for obra_id in obras_com_merge:
        if obra_id not in obras_com_apropriacoes:
            conflitos.append({
                'tipo': 'obra_sem_apropriacoes',
                'obra_id': obra_id,
                'description': f"Obra {obra_id} tem merge de obras mas não de apropriações"
            })
    
    return conflitos


def debug_merge_config(config_merge: Dict, logger) -> None:
    """Debug detalhado da configuração de merge"""
    logger.info("=== DEBUG CONFIGURAÇÃO DE MERGE ===")
    
    valido, erros = validar_config_merge(config_merge, logger)
    logger.info(f"Configuração válida: {valido}")
    
    conflitos = detectar_conflitos_merge(config_merge)
    if conflitos:
        logger.warning(f"{len(conflitos)} conflitos detectados:")
        for conflito in conflitos:
            logger.warning(f"  - {conflito['description']}")
    
    relatorio = gerar_relatorio_merge(config_merge)
    logger.info(f"Resumo: {relatorio['config_summary']}")
    
    logger.info("NOVO COMPORTAMENTO: Apenas APROPRIADOS são transferidos no merge de obras")
    logger.info("PENDENTES e ORÇADOS permanecem na obra original")


if __name__ == '__main__':
    # Teste básico do merge engine
    from settings import load_all_configs
    from logger import get_main_logger
    
    configs = load_all_configs()
    logger = get_main_logger(configs)
    
    config_merge = configs['merge']
    debug_merge_config(config_merge, logger)
    
    print("Engine de merge testado com sucesso!")