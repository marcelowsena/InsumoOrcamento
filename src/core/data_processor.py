"""
Processador de Dados - VERSÃO FINAL
Enriquecimento completo com fornecedores e medições
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Import relativo
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.fornecedor_utils import (
    extrair_info_documento,
    buscar_fornecedor_por_documento
)

_base_pedidos = None
_base_bulk_org = None
_base_contratos = None
_base_fornecedor = None


def inicializar_bases_fornecedor(logger):
    try:
        from siengeAPI.bases.carregabases import pedidosCompra, titulosBulk, contratos
        from siengeAPI.consultas.credores import baseCredores
        from utils.fornecedor_utils import _organizar_base_bulk
        
        logger.info("Carregando bases de fornecedor...")
        
        base_fornecedor = baseCredores()
        base_pedidos = pedidosCompra()
        base_contratos = contratos()
        
        titulos_bulk = titulosBulk()['data']
        base_bulk_org = _organizar_base_bulk(titulos_bulk)
        
        # Normalizar pedidos
        base_pedidos_norm = {}
        for building_id, pedidos in base_pedidos.items():
            try:
                building_id_int = int(building_id)
                base_pedidos_norm[building_id_int] = pedidos
            except (ValueError, TypeError):
                pass
        
        logger.info(f"Bases carregadas: {len(base_fornecedor)} fornecedores, "
                   f"{len(base_contratos)} contratos, "
                   f"{len(base_pedidos_norm)} pedidos, "
                   f"{len(base_bulk_org)} obras bulk")
        
        # RETORNAR TUPLA COM AS BASES
        return (base_bulk_org, base_pedidos_norm, base_contratos, base_fornecedor)
        
    except Exception as e:
        logger.warning(f"Fornecedor não disponível: {e}")
        return None

def enriquecer_lancamento_completo(lancamento: Dict, bases_tuple: tuple, logger) -> Dict:
    """
    VERSÃO FINAL - Enriquece lançamento com fornecedor e medição
    Retorna N.ENC. para documentos não encontrados
    """
    if not bases_tuple:
        return lancamento
    
    base_bulk_org, base_pedidos, base_contratos, base_fornecedor = bases_tuple
    
    tipo_documento = lancamento.get('tipo_documento', '')
    
    # ORÇADOS não têm fornecedor nem medição
    if tipo_documento == 'ORCADO':
        lancamento['numero_medicao'] = ''
        lancamento['fornecedor'] = ''
        return lancamento
    
    documento_origem = lancamento.get('documento_origem', '')
    building_id = lancamento.get('building_id', 0)
    numero_medicao_existente = lancamento.get('numero_medicao')
    
    # EXTRAIR INFORMAÇÕES DO DOCUMENTO
    tipo_doc, numero_doc, numero_medicao = extrair_info_documento(documento_origem)
    
    # ATUALIZAR NÚMERO DE MEDIÇÃO
    if numero_medicao is not None:
        lancamento['numero_medicao'] = numero_medicao
    elif not numero_medicao_existente:
        lancamento['numero_medicao'] = ''
    
    # LIMPAR DOCUMENTO_ORIGEM (remover medição do texto)
    if tipo_doc and numero_doc:
        doc_limpo = f"{tipo_doc}.{numero_doc}"
        lancamento['documento_origem'] = doc_limpo
    
    # SE JÁ TEM FORNECEDOR, RETORNAR
    if lancamento.get('fornecedor'):
        return lancamento
    
    # BUSCAR FORNECEDOR
    lancamento['fornecedor'] = ''
    
    # Documentos SHEET não têm fornecedor (orçamento)
    if tipo_doc == 'SHEET':
        return lancamento
    
    
    if base_fornecedor and base_pedidos and base_bulk_org and tipo_doc and numero_doc:
        try:
            fornecedor = buscar_fornecedor_por_documento(
                tipo_doc=tipo_doc,
                numero_doc=numero_doc,
                building_id=building_id,
                base_bulk_org=base_bulk_org,  # SEM underline
                base_pedidos=base_pedidos,     # SEM underline
                base_contratos=base_contratos, # SEM underline
                base_forn=base_fornecedor,     # SEM underline
                logger=logger
            )
            
            if fornecedor:
                lancamento['fornecedor'] = fornecedor
        
        except Exception as e:
            if logger:
                logger.error(f"Erro ao buscar fornecedor {tipo_doc}.{numero_doc}: {str(e)}")
            lancamento['fornecedor'] = "N.ENC."
    
    return lancamento


def extrair_lancamentos_de_resultado(resultado: Dict, obra: Dict, 
                                   building_units_config: Dict, logger) -> List[Dict]:
    if 'erro' in resultado:
        logger.warning(f"Obra {obra['id']} tem erro: {resultado['erro']}")
        return []
    
    dados = resultado.get('data', [])
    if not dados:
        logger.info(f"Obra {obra['id']} sem dados")
        return []
    
    lancamentos = []
    estatisticas = {
        'recursos_processados': 0,
        'apropriados': 0,
        'pendentes': 0,
        'orcados': 0,
        'building_units_filtrados': 0
    }
    
    for recurso in dados:
        estatisticas['recursos_processados'] += 1
        
        apropriacoes_atendidas = recurso.get('buildingAppropriations', {}).get('attended', [])
        for apropriado in apropriacoes_atendidas:
            building_unit_id = apropriado.get('buildingUnitId', '')
            
            if not _deve_incluir_building_unit(building_unit_id, building_units_config):
                estatisticas['building_units_filtrados'] += 1
                continue
            
            lancamento = _criar_lancamento_apropriado(recurso, apropriado, obra)
            lancamentos.append(lancamento)
            estatisticas['apropriados'] += 1
        
        apropriacoes_pendentes = recurso.get('buildingAppropriations', {}).get('pending', [])
        for pendente in apropriacoes_pendentes:
            building_unit_id = pendente.get('buildingUnitId', '')
            
            if not _deve_incluir_building_unit(building_unit_id, building_units_config):
                estatisticas['building_units_filtrados'] += 1
                continue
            
            lancamento = _criar_lancamento_pendente(recurso, pendente, obra)
            lancamentos.append(lancamento)
            estatisticas['pendentes'] += 1
        
        itens_orcados = recurso.get('buildingCostEstimationItems', [])
        for item_orcado in itens_orcados:
            building_unit_id = item_orcado.get('buildingUnitId', '')
            
            if not _deve_incluir_building_unit(building_unit_id, building_units_config):
                estatisticas['building_units_filtrados'] += 1
                continue
            
            lancamento = _criar_lancamento_orcado(recurso, item_orcado, obra)
            lancamentos.append(lancamento)
            estatisticas['orcados'] += 1
    
    logger.info(f"Obra {obra['id']}: {estatisticas['recursos_processados']} recursos -> "
               f"{estatisticas['apropriados']} apropriados, {estatisticas['pendentes']} pendentes, "
               f"{estatisticas['orcados']} orcados. {estatisticas['building_units_filtrados']} filtrados")
    
    return lancamentos


def _deve_incluir_building_unit(building_unit_id: Any, config: Dict) -> bool:
    if not config.get('filter_enabled', True):
        return True
    
    try:
        unit_id = int(building_unit_id) if building_unit_id else 0
        return unit_id in config.get('allowed_ids', [1])
    except (ValueError, TypeError):
        return False


def _criar_lancamento_apropriado(recurso: Dict, apropriado: Dict, obra: Dict) -> Dict:
    codigo_ref = apropriado.get('costEstimationItemReference', '')
    descricao = apropriado.get('costEstimationItemDescription', '')
    apropriacao_completa = _montar_apropriacao_completa(codigo_ref, descricao)
    
    quantidade = float(apropriado.get('quantity', 0))
    valor_total = float(apropriado.get('value', 0))
    valor_unitario = _calcular_valor_unitario(valor_total, quantidade)
    
    categoria_recurso = recurso.get('category', '')
    grupo_recurso = recurso.get('resourceGroup', '')
    
    return {
        'building_id': obra['id'],
        'obra_nome': obra['name'],
        'insumo_id': recurso.get('id', ''),
        'insumo_nome': recurso.get('description', ''),
        'codigo_recurso': recurso.get('resourceCode', ''),
        'categoria_recurso': categoria_recurso,
        'grupo_recurso': grupo_recurso,
        'categoria': recurso.get('category', ''),
        'unidade': recurso.get('unitOfMeasure', ''),
        'tipo_documento': 'APROPRIADO',
        'classificacao': 'APROPRIADO',
        'documento_origem': apropriado.get('documentLabel', ''),
        'building_unit_id': apropriado.get('buildingUnitId', ''),
        'building_unit_name': apropriado.get('buildingUnitName', ''),
        'apropriacao_completa': apropriacao_completa,
        'codigo_apropriacao': codigo_ref,
        'quantidade': quantidade,
        'valor_unitario': valor_unitario,
        'valor_total': valor_total,
        'data_documento': apropriado.get('date', ''),
        'status': 'Apropriado',
        'numero_medicao': '',
        'fornecedor': '',
        'fonte': 'OBRA'
    }


def _criar_lancamento_pendente(recurso: Dict, pendente: Dict, obra: Dict) -> Dict:
    codigo_ref = pendente.get('costEstimationItemReference', '')
    descricao = pendente.get('costEstimationItemDescription', '')
    apropriacao_completa = _montar_apropriacao_completa(codigo_ref, descricao)
    
    quantidade = float(pendente.get('quantity', 0))
    valor_total = float(pendente.get('value', 0))
    valor_unitario = _calcular_valor_unitario(valor_total, quantidade)
    
    categoria_recurso = recurso.get('category', '')
    grupo_recurso = recurso.get('resourceGroup', '')
    
    return {
        'building_id': obra['id'],
        'obra_nome': obra['name'],
        'insumo_id': recurso.get('id', ''),
        'insumo_nome': recurso.get('description', ''),
        'codigo_recurso': recurso.get('resourceCode', ''),
        'categoria_recurso': categoria_recurso,
        'grupo_recurso': grupo_recurso,
        'categoria': recurso.get('category', ''),
        'unidade': recurso.get('unitOfMeasure', ''),
        'tipo_documento': 'PENDENTE',
        'classificacao': 'PENDENTE',
        'documento_origem': pendente.get('documentLabel', ''),
        'building_unit_id': pendente.get('buildingUnitId', ''),
        'building_unit_name': pendente.get('buildingUnitName', ''),
        'apropriacao_completa': apropriacao_completa,
        'codigo_apropriacao': codigo_ref,
        'quantidade': quantidade,
        'valor_unitario': valor_unitario,
        'valor_total': valor_total,
        'data_documento': pendente.get('date', ''),
        'status': 'Pendente',
        'numero_medicao': '',
        'fornecedor': '',
        'fonte': 'OBRA'
    }


def _criar_lancamento_orcado(recurso: Dict, item_orcado: Dict, obra: Dict) -> Dict:
    wbs_code = item_orcado.get('wbsCode', '')
    descricao = item_orcado.get('description', '')
    apropriacao_completa = _montar_apropriacao_completa(wbs_code, descricao)
    
    quantidade = float(item_orcado.get('quantity', 0))
    valor_total = float(item_orcado.get('totalPrice', 0))
    valor_unitario = _calcular_valor_unitario(valor_total, quantidade)
    
    categoria_recurso = recurso.get('category', '')
    grupo_recurso = recurso.get('resourceGroup', '')
    
    return {
        'building_id': obra['id'],
        'obra_nome': obra['name'],
        'insumo_id': recurso.get('id', ''),
        'insumo_nome': recurso.get('description', ''),
        'codigo_recurso': recurso.get('resourceCode', ''),
        'categoria_recurso': categoria_recurso,
        'grupo_recurso': grupo_recurso,
        'categoria': recurso.get('category', ''),
        'unidade': recurso.get('unitOfMeasure', ''),
        'tipo_documento': 'ORCADO',
        'classificacao': 'ORCADO',
        'documento_origem': f"Sheet Item {item_orcado.get('sheetItemId', '')}",
        'building_unit_id': item_orcado.get('buildingUnitId', ''),
        'building_unit_name': item_orcado.get('buildingUnitName', ''),
        'apropriacao_completa': apropriacao_completa,
        'codigo_apropriacao': wbs_code,
        'quantidade': quantidade,
        'valor_unitario': valor_unitario,
        'valor_total': valor_total,
        'data_documento': '',
        'status': 'Orcado',
        'numero_medicao': '',
        'fornecedor': '',
        'fonte': 'OBRA'
    }


def _montar_apropriacao_completa(codigo: str, descricao: str) -> str:
    if codigo and descricao:
        return f"{codigo} - {descricao}"
    elif codigo:
        return codigo
    elif descricao:
        return descricao
    else:
        return 'N/A'


def _calcular_valor_unitario(valor_total: float, quantidade: float) -> float:
    if quantidade > 0:
        return valor_total / quantidade
    return 0.0


def processar_todos_resultados(resultados: List[Dict], building_units_config: Dict, 
                              logger) -> List[Dict]:
    logger.info(f"Iniciando processamento de {len(resultados)} resultados")
    
    todos_lancamentos = []
    estatisticas = {
        'resultados_processados': 0,
        'resultados_com_erro': 0,
        'resultados_sem_dados': 0,
        'total_apropriados': 0,
        'total_pendentes': 0,
        'total_orcados': 0,
        'obras_processadas': set()
    }
    
    for resultado_info in resultados:
        obra = resultado_info['obra']
        resultado = resultado_info['relatorio_bruto']
        
        estatisticas['resultados_processados'] += 1
        
        if 'erro' in resultado:
            estatisticas['resultados_com_erro'] += 1
            logger.warning(f"Obra {obra['id']} com erro: {resultado['erro']}")
            continue
        
        lancamentos = extrair_lancamentos_de_resultado(resultado, obra, building_units_config, logger)
        
        if not lancamentos:
            estatisticas['resultados_sem_dados'] += 1
        else:
            for lancamento in lancamentos:
                tipo = lancamento.get('tipo_documento', 'DESCONHECIDO')
                if tipo == 'APROPRIADO':
                    estatisticas['total_apropriados'] += 1
                elif tipo == 'PENDENTE':
                    estatisticas['total_pendentes'] += 1
                elif tipo == 'ORCADO':
                    estatisticas['total_orcados'] += 1
            
            todos_lancamentos.extend(lancamentos)
            estatisticas['obras_processadas'].add(obra['id'])
    
    total_lancamentos = len(todos_lancamentos)
    logger.info(f"Extracao concluida: {total_lancamentos} lancamentos "
               f"({estatisticas['total_apropriados']} apropriados, "
               f"{estatisticas['total_pendentes']} pendentes, "
               f"{estatisticas['total_orcados']} orcados) "
               f"de {len(estatisticas['obras_processadas'])} obras")
    
    return todos_lancamentos


def validar_estrutura_lancamento(lancamento: Dict) -> Tuple[bool, List[str]]:
    """
    Valida estrutura de um lançamento.
    Para aditivos (fonte=ADITIVO), insumo_id não é obrigatório.
    """
    fonte = lancamento.get('fonte', 'OBRA')
    is_aditivo = fonte == 'ADITIVO'

    # Para aditivos, insumo_id não é obrigatório
    if is_aditivo:
        campos_obrigatorios = [
            'building_id', 'obra_nome', 'insumo_nome',
            'quantidade', 'valor_total', 'tipo_documento'
        ]
    else:
        campos_obrigatorios = [
            'building_id', 'obra_nome', 'insumo_id', 'insumo_nome',
            'quantidade', 'valor_unitario', 'valor_total', 'tipo_documento'
        ]

    erros = []

    for campo in campos_obrigatorios:
        if campo not in lancamento:
            erros.append(f"Campo obrigatorio ausente: {campo}")
        elif lancamento[campo] in [None, '']:
            erros.append(f"Campo obrigatorio vazio: {campo}")

    campos_numericos = ['building_id', 'quantidade', 'valor_total']
    for campo in campos_numericos:
        if campo in lancamento and lancamento[campo] not in [None, '']:
            try:
                float(lancamento[campo])
            except (ValueError, TypeError):
                erros.append(f"Campo {campo} deve ser numerico: {lancamento[campo]}")

    # Tipos válidos: inclui COMPROMETIDO para aditivos e títulos
    tipos_validos = ['APROPRIADO', 'PENDENTE', 'ORCADO', 'COMPROMETIDO']
    tipo_doc = lancamento.get('tipo_documento', '')
    if tipo_doc not in tipos_validos:
        erros.append(f"Tipo de documento invalido: {tipo_doc}")

    # Quantidade negativa só é erro se não for aditivo (aditivos podem ter estorno)
    if not is_aditivo and 'quantidade' in lancamento:
        try:
            if float(lancamento.get('quantidade', 0)) < 0:
                erros.append("Quantidade nao pode ser negativa")
        except (ValueError, TypeError):
            pass

    return len(erros) == 0, erros


def validar_lote_lancamentos(lancamentos: List[Dict], logger) -> Tuple[List[Dict], List[Dict]]:
    logger.info(f"Validando {len(lancamentos)} lancamentos")
    
    validos = []
    com_erro = []
    
    for i, lancamento in enumerate(lancamentos):
        valido, erros = validar_estrutura_lancamento(lancamento)
        
        if valido:
            validos.append(lancamento)
        else:
            lancamento_erro = lancamento.copy()
            lancamento_erro['validation_errors'] = erros
            com_erro.append(lancamento_erro)
            
            logger.warning(f"Lancamento {i} invalido (Obra {lancamento.get('building_id', 'N/A')}): "
                         f"{'; '.join(erros)}")
    
    logger.info(f"Validacao concluida: {len(validos)} validos, {len(com_erro)} com erro")
    
    return validos, com_erro


def agrupar_lancamentos_por_obra(lancamentos: List[Dict]) -> Dict[int, List[Dict]]:
    grupos = {}
    for lancamento in lancamentos:
        obra_id = lancamento['building_id']
        if obra_id not in grupos:
            grupos[obra_id] = []
        grupos[obra_id].append(lancamento)
    return grupos


def calcular_totais_por_obra(lancamentos_por_obra: Dict[int, List[Dict]]) -> Dict[int, Dict]:
    totais = {}
    
    for obra_id, lancamentos in lancamentos_por_obra.items():
        total_valor = sum(float(l.get('valor_total', 0)) for l in lancamentos)
        total_quantidade = sum(float(l.get('quantidade', 0)) for l in lancamentos)
        
        tipos = {}
        for lancamento in lancamentos:
            tipo = lancamento.get('tipo_documento', 'N/A')
            if tipo not in tipos:
                tipos[tipo] = {'count': 0, 'valor': 0}
            tipos[tipo]['count'] += 1
            tipos[tipo]['valor'] += float(lancamento.get('valor_total', 0))
        
        categorias = {}
        for lancamento in lancamentos:
            categoria = lancamento.get('categoria', 'N/A')
            if categoria not in categorias:
                categorias[categoria] = {'count': 0, 'valor': 0}
            categorias[categoria]['count'] += 1
            categorias[categoria]['valor'] += float(lancamento.get('valor_total', 0))
        
        building_units = {}
        for lancamento in lancamentos:
            unit_id = lancamento.get('building_unit_id', 'N/A')
            unit_name = lancamento.get('building_unit_name', 'N/A')
            if unit_id not in building_units:
                building_units[unit_id] = {'name': unit_name, 'count': 0, 'valor': 0}
            building_units[unit_id]['count'] += 1
            building_units[unit_id]['valor'] += float(lancamento.get('valor_total', 0))
        
        totais[obra_id] = {
            'total_lancamentos': len(lancamentos),
            'total_valor': total_valor,
            'total_quantidade': total_quantidade,
            'valor_medio_lancamento': total_valor / len(lancamentos) if lancamentos else 0,
            'tipos': tipos,
            'categorias': categorias,
            'building_units': building_units,
            'obra_nome': lancamentos[0].get('obra_nome', 'N/A') if lancamentos else 'N/A'
        }
    
    return totais


def filtrar_lancamentos_por_data(lancamentos: List[Dict], data_inicio: str = None, 
                                data_fim: str = None) -> List[Dict]:
    if not data_inicio and not data_fim:
        return lancamentos
    
    lancamentos_filtrados = []
    
    for lancamento in lancamentos:
        data_doc = lancamento.get('data_documento', '')
        
        if not data_doc:
            if lancamento.get('tipo_documento') == 'ORCADO':
                lancamentos_filtrados.append(lancamento)
            continue
        
        try:
            if 'T' in data_doc:
                data_lancamento = datetime.fromisoformat(data_doc.replace('Z', '+00:00'))
            else:
                data_lancamento = datetime.strptime(data_doc, '%Y-%m-%d')
            
            incluir = True
            
            if data_inicio:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                if data_lancamento < data_inicio_dt:
                    incluir = False
            
            if data_fim and incluir:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
                if data_lancamento > data_fim_dt:
                    incluir = False
            
            if incluir:
                lancamentos_filtrados.append(lancamento)
                
        except (ValueError, TypeError):
            lancamentos_filtrados.append(lancamento)
    
    return lancamentos_filtrados


def gerar_relatorio_processamento(todos_lancamentos: List[Dict], 
                                 totais_por_obra: Dict, logger) -> Dict:
    total_obras = len(totais_por_obra)
    total_lancamentos = len(todos_lancamentos)
    valor_total_geral = sum(t['total_valor'] for t in totais_por_obra.values())
    
    tipos_consolidados = {}
    for lancamento in todos_lancamentos:
        tipo = lancamento.get('tipo_documento', 'N/A')
        if tipo not in tipos_consolidados:
            tipos_consolidados[tipo] = {'count': 0, 'valor': 0}
        tipos_consolidados[tipo]['count'] += 1
        tipos_consolidados[tipo]['valor'] += float(lancamento.get('valor_total', 0))
    
    top_obras_valor = sorted(
        [(obra_id, dados['total_valor'], dados['obra_nome']) 
         for obra_id, dados in totais_por_obra.items()],
        key=lambda x: x[1], reverse=True
    )[:5]
    
    relatorio = {
        'timestamp': datetime.now().isoformat(),
        'resumo_geral': {
            'total_obras': total_obras,
            'total_lancamentos': total_lancamentos,
            'valor_total': valor_total_geral,
            'valor_medio_por_obra': valor_total_geral / total_obras if total_obras > 0 else 0,
            'lancamentos_medio_por_obra': total_lancamentos / total_obras if total_obras > 0 else 0
        },
        'tipos_documento': tipos_consolidados,
        'top_obras_por_valor': top_obras_valor
    }
    
    logger.info(f"Relatorio gerado: {total_obras} obras, {total_lancamentos} lancamentos, "
               f"R$ {valor_total_geral:,.2f} total")
    
    return relatorio


def enriquecer_lancamentos_com_hierarquia(lancamentos: List[Dict], mapeamentos_wbs: Dict[int, Dict[str, str]], 
                                        logger) -> List[Dict]:
    logger.info(f"Enriquecendo {len(lancamentos)} lancamentos com hierarquia WBS")
    
    lancamentos_enriquecidos = 0
    
    for lancamento in lancamentos:
        obra_id = lancamento.get('building_id')
        codigo_apropriacao = lancamento.get('codigo_apropriacao', '').strip()
        
        mapeamento_obra = mapeamentos_wbs.get(obra_id, {})
        
        if not mapeamento_obra:
            _adicionar_niveis_vazios(lancamento)
            continue
        
        niveis = _extrair_niveis_codigo_local(codigo_apropriacao)
        
        if niveis:
            _adicionar_niveis_apropriacao(lancamento, niveis, mapeamento_obra)
            lancamentos_enriquecidos += 1
        else:
            _adicionar_niveis_vazios(lancamento)
    
    logger.info(f"Enriquecimento WBS: {lancamentos_enriquecidos} lancamentos")
    
    return lancamentos


def _extrair_niveis_codigo_local(codigo_completo: str) -> List[str]:
    if not codigo_completo:
        return []
    
    partes = codigo_completo.split('.')
    niveis = []
    
    for i in range(1, len(partes) + 1):
        nivel = '.'.join(partes[:i])
        niveis.append(nivel)
    
    return niveis


def _adicionar_niveis_apropriacao(lancamento: Dict, niveis: List[str], mapeamento_obra: Dict[str, str]) -> None:
    max_niveis = 4
    
    for i, nivel_codigo in enumerate(niveis[:max_niveis], 1):
        desc_nivel = mapeamento_obra.get(nivel_codigo, '')
        
        if desc_nivel:
            campo_combinado = f"{nivel_codigo} - {desc_nivel}"
        else:
            campo_combinado = nivel_codigo if nivel_codigo else ''
        
        lancamento[f'nivel_{i}'] = campo_combinado
    
    for i in range(len(niveis) + 1, max_niveis + 1):
        lancamento[f'nivel_{i}'] = ''


def _adicionar_niveis_vazios(lancamento: Dict) -> None:
    max_niveis = 4
    
    for i in range(1, max_niveis + 1):
        lancamento[f'nivel_{i}'] = ''


def debug_estrutura_api_single(resultado: Dict, logger, max_recursos: int = 3) -> None:
    logger.info("DEBUG ESTRUTURA API")
    
    if 'erro' in resultado:
        logger.error(f"Resultado contem erro: {resultado['erro']}")
        return
    
    dados = resultado.get('data', [])
    if not dados:
        logger.warning("Resultado sem dados")
        return
    
    logger.info(f"Total de recursos: {len(dados)}")
    
    for i, recurso in enumerate(dados[:max_recursos]):
        logger.info(f"RECURSO {i+1}")
        logger.info(f"ID: {recurso.get('id', 'N/A')}")
        logger.info(f"Descricao: {recurso.get('description', 'N/A')}")
        logger.info(f"Categoria: {recurso.get('category', 'N/A')}")


def debug_amostra_lancamentos(lancamentos: List[Dict], quantidade: int = 3) -> List[Dict]:
    if len(lancamentos) <= quantidade:
        return lancamentos
    
    indices = [0, len(lancamentos) // 2, len(lancamentos) - 1]
    return [lancamentos[i] for i in indices[:quantidade]]


def debug_hierarquia_lancamentos(lancamentos: List[Dict], logger, max_exemplos: int = 5) -> None:
    logger.info("DEBUG HIERARQUIA WBS")

    com_hierarquia = 0
    sem_hierarquia = 0

    for lancamento in lancamentos:
        if lancamento.get('nivel_1', ''):
            com_hierarquia += 1
        else:
            sem_hierarquia += 1

    logger.info(f"Lancamentos com hierarquia: {com_hierarquia}")
    logger.info(f"Lancamentos sem hierarquia: {sem_hierarquia}")

    logger.info("Exemplos de hierarquia:")

    exemplos_mostrados = 0
    for lancamento in lancamentos:
        if exemplos_mostrados >= max_exemplos:
            break

        if lancamento.get('nivel_1', ''):
            codigo_orig = lancamento.get('codigo_apropriacao', '')
            tipo_doc = lancamento.get('tipo_documento', '')
            logger.info(f"Tipo: {tipo_doc}, Codigo original: {codigo_orig}")

            for i in range(1, 5):
                nivel = lancamento.get(f'nivel_{i}', '')
                if nivel:
                    logger.info(f"Nivel {i}: {nivel}")

            exemplos_mostrados += 1


def extrair_mes_ano_data(data_str: str) -> Tuple[str, str]:
    """
    Extrai mês e ano de uma string de data.
    Suporta formatos: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, etc.
    Retorna (mes, ano) ou ('', '') se não conseguir extrair.
    """
    if not data_str:
        return '', ''

    try:
        # Tentar extrair apenas a parte da data (antes do T se houver)
        data_parte = data_str.split('T')[0] if 'T' in data_str else data_str

        # Formato esperado: YYYY-MM-DD
        partes = data_parte.split('-')
        if len(partes) >= 2:
            ano = partes[0]
            mes = partes[1]
            # Validar que são números
            if ano.isdigit() and mes.isdigit():
                return mes, ano

        return '', ''

    except Exception:
        return '', ''


def enriquecer_lancamentos_com_classificacao_abc(lancamentos: List[Dict], config_abc: Dict, logger) -> List[Dict]:
    """
    Enriquece lançamentos com classificação ABC baseada no config.
    """
    from config.settings import obter_classificacao_abc

    logger.info(f"Enriquecendo {len(lancamentos)} lançamentos com classificação ABC")

    classificados = 0
    for lancamento in lancamentos:
        classificacao = obter_classificacao_abc(lancamento, config_abc)
        lancamento['classificacao_abc'] = classificacao
        if classificacao:
            classificados += 1

    logger.info(f"Classificação ABC: {classificados} lançamentos classificados")

    return lancamentos


def enriquecer_lancamentos_com_mes_ano(lancamentos: List[Dict], logger) -> List[Dict]:
    """
    Enriquece lançamentos com mês e ano extraídos da data_documento.
    """
    logger.info(f"Enriquecendo {len(lancamentos)} lançamentos com mês/ano de apropriação")

    com_data = 0
    for lancamento in lancamentos:
        data_doc = lancamento.get('data_documento', '')
        mes, ano = extrair_mes_ano_data(data_doc)
        lancamento['mes_apropriacao'] = mes
        lancamento['ano_apropriacao'] = ano
        if mes and ano:
            com_data += 1

    logger.info(f"Mês/Ano: {com_data} lançamentos com data extraída")

    return lancamentos