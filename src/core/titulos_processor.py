"""
Processador de Títulos V4 - Sistema Insumos x Orçamento
Converte títulos da API em lançamentos no formato do Excel
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple


def converter_titulo_para_lancamentos(titulo: Dict, building_units_config: Dict, logger) -> List[Dict]:
    """
    Converte um título em lançamentos com estrutura EXATA do Excel
    Returns: lista de lançamentos no formato das colunas existentes
    """
    bill_id = titulo.get('billId', 'N/A')
    installment_id = titulo.get('installmentId', 1)
    
    # Verificar se tem apropriação para obras
    buildings_costs = titulo.get('buildingsCosts', [])
    if not buildings_costs:
        logger.debug(f"Título {bill_id}: sem apropriações para obras")
        return []
    
    # Dados base do título
    credor_nome = titulo.get('creditorName', 'Fornecedor não informado')
    documento_numero = titulo.get('documentNumber', '')
    tipo_documento_origem = titulo.get('documentIdentificationId', '').strip()
    data_vencimento = titulo.get('dueDate', '')
    data_emissao = titulo.get('issueDate', '')
    valor_total_titulo = float(titulo.get('correctedBalanceAmount', 0))
    
    if valor_total_titulo <= 0:
        logger.debug(f"Título {bill_id}: valor zero ou negativo")
        return []
    
    # Categoria financeira padrão para títulos
    category_info = _extrair_categoria_financeira(titulo)
    
    lancamentos = []
    
    # Criar um lançamento para cada apropriação (buildingsCosts)
    for i, building_cost in enumerate(buildings_costs, 1):
        building_id = building_cost.get('buildingId')
        building_name = building_cost.get('buildingName', 'Obra não informada')
        building_unit_id = building_cost.get('buildingUnitId', 1)
        building_unit_name = building_cost.get('buildingUnitName', 'Unidade não informada')
        rate = float(building_cost.get('rate', 0))
        
        # Validações básicas
        if not building_id or rate <= 0:
            logger.debug(f"Título {bill_id}: apropriação inválida - Building {building_id}, Rate {rate}")
            continue
        
        # Aplicar filtro de Building Units
        if not _deve_incluir_building_unit(building_unit_id, building_units_config):
            logger.debug(f"Título {bill_id}: Building Unit {building_unit_id} filtrado")
            continue
        
        # Calcular valor proporcional
        valor_apropriado = valor_total_titulo * (rate / 100)
        
        # Código de apropriação (usar costEstimationSheetId se disponível)
        codigo_apropriacao = building_cost.get('costEstimationSheetId', category_info['codigo'])
        sheet_name = building_cost.get('costEstimationSheetName', category_info['nome'])
        
        # Montar apropriação completa
        apropriacao_completa = _montar_apropriacao_completa_titulo(codigo_apropriacao, sheet_name)
        
        # Criar lançamento com estrutura EXATA do Excel
        lancamento = {
            # === COLUNAS EXATAS DO EXCEL ATUAL ===
            'building_id': building_id,
            'obra_nome': building_name,
            'insumo_id': f"TIT_{bill_id}_{installment_id}_{i}",
            'insumo_nome': credor_nome,  # Nome do fornecedor como insumo
            'codigo_recurso': tipo_documento_origem,
            'categoria': 'Título a Pagar',
            'unidade': 'R$',
            'tipo_documento': 'PENDENTE',  # Todos títulos são pendentes
            'classificacao': 'TITULO_A_PAGAR',
            'documento_origem': f"Título {bill_id} - {documento_numero}",
            'building_unit_id': building_unit_id,
            'building_unit_name': building_unit_name,
            'apropriacao_completa': apropriacao_completa,
            'codigo_apropriacao': codigo_apropriacao,
            
            # Colunas hierárquicas WBS (vazias, serão preenchidas depois do merge)
            'nivel_1': '',
            'nivel_2': '',
            'nivel_3': '',
            'nivel_4': '',
            
            # Valores
            'quantidade': 1.0,  # Sempre 1 para títulos
            'valor_unitario': valor_apropriado,
            'valor_total': valor_apropriado,
            'data_documento': data_vencimento,
            'status': 'Pendente'  # Mesmo padrão dos lançamentos de obras
        }
        
        lancamentos.append(lancamento)
        logger.debug(f"Título {bill_id}: lançamento criado - Obra {building_id}, R$ {valor_apropriado:.2f}")
    
    logger.info(f"Título {bill_id}: {len(lancamentos)} lançamentos gerados, R$ {valor_total_titulo:.2f}")
    return lancamentos


def _extrair_categoria_financeira(titulo: Dict) -> Dict:
    """Extrai informações da categoria financeira ou usa padrão"""
    payment_categories = titulo.get('paymentsCategories', [])
    
    if payment_categories:
        primeira_categoria = payment_categories[0]
        return {
            'codigo': primeira_categoria.get('financialCategoryId', 'TIT.001'),
            'nome': primeira_categoria.get('financialCategoryName', 'Título a Pagar')
        }
    else:
        return {
            'codigo': 'TIT.001',
            'nome': 'Título a Pagar'
        }


def _montar_apropriacao_completa_titulo(codigo: str, descricao: str) -> str:
    """Monta string completa de apropriação para títulos"""
    if codigo and descricao:
        return f"{codigo} - {descricao}"
    elif codigo:
        return codigo
    elif descricao:
        return descricao
    else:
        return 'Título a Pagar'


def _deve_incluir_building_unit(building_unit_id: int, config: Dict) -> bool:
    """Verifica se Building Unit deve ser incluído (mesmo filtro das obras)"""
    if not config.get('filter_enabled', True):
        return True
    
    try:
        unit_id = int(building_unit_id) if building_unit_id else 0
        return unit_id in config.get('allowed_ids', [1])
    except (ValueError, TypeError):
        return False


def processar_todos_titulos(titulos: List[Dict], building_units_config: Dict, logger) -> List[Dict]:
    """
    Processa todos os títulos e retorna lista de lançamentos
    Returns: lista consolidada de lançamentos de títulos
    """
    logger.info(f"Iniciando processamento de {len(titulos)} títulos")
    
    todos_lancamentos = []
    estatisticas = {
        'titulos_processados': 0,
        'titulos_com_lancamentos': 0,
        'lancamentos_criados': 0,
        'valor_total': 0,
        'obras_afetadas': set(),
        'tipos_documento': {},
        'building_units_filtrados': 0,
        'erros': []
    }
    
    for titulo in titulos:
        try:
            estatisticas['titulos_processados'] += 1
            
            # Contabilizar tipo de documento
            tipo_doc = titulo.get('documentIdentificationId', '').strip()
            estatisticas['tipos_documento'][tipo_doc] = estatisticas['tipos_documento'].get(tipo_doc, 0) + 1
            
            # Converter título em lançamentos
            lancamentos = converter_titulo_para_lancamentos(titulo, building_units_config, logger)
            
            if lancamentos:
                estatisticas['titulos_com_lancamentos'] += 1
                estatisticas['lancamentos_criados'] += len(lancamentos)
                
                for lancamento in lancamentos:
                    estatisticas['valor_total'] += lancamento['valor_total']
                    estatisticas['obras_afetadas'].add(lancamento['building_id'])
                    todos_lancamentos.append(lancamento)
            
        except Exception as e:
            erro_msg = f"Título {titulo.get('billId', 'N/A')}: {str(e)}"
            estatisticas['erros'].append(erro_msg)
            logger.error(erro_msg)
    
    # Log consolidado das estatísticas
    logger.info(f"Processamento de títulos concluído:")
    logger.info(f"  - Títulos processados: {estatisticas['titulos_processados']}")
    logger.info(f"  - Títulos com lançamentos: {estatisticas['titulos_com_lancamentos']}")
    logger.info(f"  - Lançamentos criados: {estatisticas['lancamentos_criados']}")
    logger.info(f"  - Valor total: R$ {estatisticas['valor_total']:,.2f}")
    logger.info(f"  - Obras afetadas: {len(estatisticas['obras_afetadas'])}")
    
    if estatisticas['tipos_documento']:
        logger.info("  - Tipos de documento:")
        for tipo, count in sorted(estatisticas['tipos_documento'].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"    • '{tipo}': {count} títulos")
    
    if estatisticas['erros']:
        logger.warning(f"  - Erros: {len(estatisticas['erros'])} títulos com erro")
        for erro in estatisticas['erros'][:3]:
            logger.warning(f"    • {erro}")
    
    return todos_lancamentos


def validar_estrutura_titulo(titulo: Dict) -> Tuple[bool, List[str]]:
    """
    Valida estrutura básica de um título
    Returns: (valido, lista_erros)
    """
    erros = []
    
    # Campos obrigatórios
    campos_obrigatorios = ['billId', 'creditorName', 'correctedBalanceAmount']
    for campo in campos_obrigatorios:
        if campo not in titulo or titulo[campo] in [None, '']:
            erros.append(f"Campo obrigatório ausente: {campo}")
    
    # Validar valor
    try:
        valor = float(titulo.get('correctedBalanceAmount', 0))
        if valor <= 0:
            erros.append("Valor deve ser positivo")
    except (ValueError, TypeError):
        erros.append("Valor inválido")
    
    # Validar apropriações
    buildings_costs = titulo.get('buildingsCosts', [])
    if not buildings_costs:
        erros.append("Título sem apropriações para obras")
    else:
        for i, bc in enumerate(buildings_costs):
            if not bc.get('buildingId'):
                erros.append(f"Apropriação {i}: buildingId ausente")
            if not isinstance(bc.get('rate'), (int, float)) or bc.get('rate', 0) <= 0:
                erros.append(f"Apropriação {i}: rate inválido")
    
    return len(erros) == 0, erros


def debug_amostra_titulos(titulos: List[Dict], logger, max_exemplos: int = 3) -> None:
    """Debug de amostra de títulos"""
    logger.info("=== DEBUG AMOSTRA DE TÍTULOS ===")
    logger.info(f"Total de títulos: {len(titulos)}")
    
    for i, titulo in enumerate(titulos[:max_exemplos], 1):
        logger.info(f"\n--- TÍTULO {i} ---")
        logger.info(f"ID: {titulo.get('billId')}")
        logger.info(f"Credor: {titulo.get('creditorName', '')[:50]}...")
        logger.info(f"Documento: {titulo.get('documentIdentificationId')} - {titulo.get('documentNumber')}")
        logger.info(f"Valor: R$ {titulo.get('correctedBalanceAmount', 0):,.2f}")
        logger.info(f"Vencimento: {titulo.get('dueDate')}")
        
        buildings_costs = titulo.get('buildingsCosts', [])
        logger.info(f"Apropriações: {len(buildings_costs)}")
        
        for j, bc in enumerate(buildings_costs[:2], 1):
            logger.info(f"  {j}. Obra {bc.get('buildingId')} - Rate {bc.get('rate', 0)}%")
            logger.info(f"     Código: {bc.get('costEstimationSheetId', 'N/A')}")


def gerar_relatorio_titulos(lancamentos_titulos: List[Dict]) -> Dict:
    """
    Gera relatório resumido dos títulos processados
    Returns: dict com estatísticas
    """
    total_lancamentos = len(lancamentos_titulos)
    valor_total = sum(float(l.get('valor_total', 0)) for l in lancamentos_titulos)
    
    # Agrupar por obra
    por_obra = {}
    for lancamento in lancamentos_titulos:
        obra_id = lancamento.get('building_id')
        if obra_id not in por_obra:
            por_obra[obra_id] = {
                'nome': lancamento.get('obra_nome', ''),
                'count': 0,
                'valor': 0
            }
        por_obra[obra_id]['count'] += 1
        por_obra[obra_id]['valor'] += float(lancamento.get('valor_total', 0))
    
    # Agrupar por tipo de documento
    por_tipo = {}
    for lancamento in lancamentos_titulos:
        tipo = lancamento.get('codigo_recurso', 'N/A')
        if tipo not in por_tipo:
            por_tipo[tipo] = {'count': 0, 'valor': 0}
        por_tipo[tipo]['count'] += 1
        por_tipo[tipo]['valor'] += float(lancamento.get('valor_total', 0))
    
    # Top 5 obras por valor
    top_obras = sorted(
        [(obra_id, dados['valor'], dados['nome']) for obra_id, dados in por_obra.items()],
        key=lambda x: x[1], reverse=True
    )[:5]
    
    return {
        'timestamp': datetime.now().isoformat(),
        'resumo_geral': {
            'total_lancamentos': total_lancamentos,
            'valor_total': valor_total,
            'total_obras': len(por_obra),
            'valor_medio_por_titulo': valor_total / total_lancamentos if total_lancamentos > 0 else 0
        },
        'por_obra': por_obra,
        'por_tipo_documento': por_tipo,
        'top_obras_por_valor': top_obras
    }


if __name__ == '__main__':
    # Teste básico do processador
    import sys
    from pathlib import Path
    
    # Adicionar src ao path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config.settings import load_all_configs
    from utils.logger import get_main_logger
    
    configs = load_all_configs()
    logger = get_main_logger(configs)
    
    # Dados de teste (simulando estrutura da API)
    titulo_mock = {
        'billId': 12345,
        'installmentId': 1,
        'creditorName': 'FORNECEDOR TESTE LTDA',
        'documentIdentificationId': 'NFS',
        'documentNumber': '001234',
        'dueDate': '2024-07-15',
        'correctedBalanceAmount': 1500.00,
        'buildingsCosts': [
            {
                'buildingId': 905,
                'buildingName': 'SPE Cora - Obra',
                'buildingUnitId': 1,
                'buildingUnitName': 'Custos Diretos',
                'costEstimationSheetId': '03.001.001.001',
                'costEstimationSheetName': 'Escavação manual',
                'rate': 100.0
            }
        ]
    }
    
    # Testar conversão
    lancamentos = converter_titulo_para_lancamentos(titulo_mock, configs['building_units'], logger)
    
    print(f"Teste concluído: {len(lancamentos)} lançamentos gerados")
    for lancamento in lancamentos:
        print(f"  - {lancamento['insumo_nome']}: R$ {lancamento['valor_total']:.2f}")