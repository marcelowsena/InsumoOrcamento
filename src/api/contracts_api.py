"""
API de Contratos WORKITEM - VERSÃO CORRIGIDA
- Separa corretamente por número de medição
- Mantém fornecedor em todos os lançamentos
- Estrutura compatível com enriquecimento posterior
"""

import siengeAPI
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


def buscar_contratos_workitem(building_units_config: Dict, logger) -> List[Dict]:
    try:
        logger.info("Carregando contratos via siengeAPI...")
        base_contratos = siengeAPI.bases.carregabases.itensContratos()
        logger.info(f"Base de contratos carregada: {len(base_contratos)} contratos")
        
        workitem_contracts = []
        iterator = tqdm(base_contratos, desc="Filtrando WORKITEM", disable=not TQDM_AVAILABLE) if TQDM_AVAILABLE else base_contratos
        
        for contract in iterator:
            if contract.get("itemType") == "WORKITEM":
                workitem_contracts.append(contract)
        
        logger.info(f"Contratos WORKITEM encontrados: {len(workitem_contracts)}")
        return workitem_contracts
    except Exception as e:
        logger.error(f"Erro ao carregar contratos: {str(e)}")
        return []


def should_include_building_unit(building_unit_id: int, building_units_config: Dict) -> bool:
    if not building_units_config.get('filter_enabled', True):
        return True
    return building_unit_id in building_units_config.get('allowed_ids', [1])


def get_building_info_from_contract(contract: Dict) -> tuple:
    buildings = contract.get("buildings", [])
    if buildings:
        building = buildings[0]
        building_id = building.get("buildingId", 0)
        building_name = building.get("name", f"Building {building_id}")
        return building_id, building_name
    return 0, "Building Desconhecido"


def calculate_unit_price(item: Dict) -> float:
    labor_price = item.get("laborPrice", 0.0) or 0.0
    material_price = item.get("materialPrice", 0.0) or 0.0
    return labor_price + material_price


def agrupar_por_medicao(appropriations: List[Dict]) -> Dict[int, List[Dict]]:
    medicoes = defaultdict(list)
    
    for approp in appropriations:
        med_num = approp.get('measurementNumber')
        
        if med_num is None or med_num == 0:
            med_num = 0
        
        medicoes[med_num].append(approp)
    
    return dict(medicoes)


def criar_lancamento_base(contract: Dict, item: Dict, building_id: int, 
                          building_name: str, unit_price: float) -> Dict:
    contract_number = contract.get("contractNumber", "")
    supplier_name = contract.get("supplierName", "")
    contract_date = contract.get("contractDate", "")
    contract_id = contract.get("documentId", "")
    contract_status = contract.get("status", "")
    
    item_id = str(item.get("id", 0))
    item_description = item.get("description", "")
    unit_of_measure = item.get("unitOfMeasure", "")
    
    return {
        'building_id': building_id,
        'obra_nome': building_name,
        'insumo_id': item_id,
        'insumo_nome': item_description,
        'codigo_recurso': '',
        'categoria_recurso': 'LABOR',
        'grupo_recurso': 'CONTRATOS',
        'categoria': 'LABOR',
        'unidade': unit_of_measure,
        'valor_unitario': unit_price,
        'data_documento': contract_date,
        'status': contract_status,
        'fornecedor': supplier_name,
        'building_unit_name': '',
        'apropriacao_completa': '',
        'nivel_1': '',
        'nivel_2': '',
        'nivel_3': '',
        'nivel_4': '',
        'contract_id': contract_id,
        'supplier_name': supplier_name,
        'fonte': 'CONTRATO'
    }


def criar_lancamento_medicao(contract: Dict, item: Dict, appropriations: List[Dict],
                             measurement_number: int, building_units_config: Dict) -> List[Dict]:
    lancamentos = []
    
    building_id, building_name = get_building_info_from_contract(contract)
    unit_price = calculate_unit_price(item)
    contract_number = contract.get("contractNumber", "")
    
    for appropriation in appropriations:
        building_unit_id = appropriation.get("buildingUnitId", 0)
        
        if not should_include_building_unit(building_unit_id, building_units_config):
            continue
        
        wbs_code = appropriation.get("wbsCode", "")
        measured_quantity = appropriation.get("measuredQuantity", 0.0)
        
        if measured_quantity <= 0:
            continue
        
        lancamento = criar_lancamento_base(contract, item, building_id, building_name, unit_price)
        
        lancamento.update({
            'building_unit_id': building_unit_id,
            'tipo_documento': 'APROPRIADO',
            'classificacao': 'MEDIDO',
            'documento_origem': f"CT.{contract_number}",
            'numero_medicao': measurement_number,
            'codigo_apropriacao': wbs_code,
            'quantidade': measured_quantity,
            'valor_total': measured_quantity * unit_price
        })
        
        lancamentos.append(lancamento)
    
    return lancamentos


def criar_lancamento_saldo(contract: Dict, item: Dict, appropriations: List[Dict],
                          building_units_config: Dict) -> List[Dict]:
    lancamentos = []
    
    building_id, building_name = get_building_info_from_contract(contract)
    unit_price = calculate_unit_price(item)
    contract_number = contract.get("contractNumber", "")
    
    for appropriation in appropriations:
        building_unit_id = appropriation.get("buildingUnitId", 0)
        
        if not should_include_building_unit(building_unit_id, building_units_config):
            continue
        
        wbs_code = appropriation.get("wbsCode", "")
        quantity_total = appropriation.get("quantity", 0.0)
        measured_quantity = appropriation.get("measuredQuantity", 0.0)
        pending_quantity = max(0.0, quantity_total - measured_quantity)
        
        if pending_quantity <= 0:
            continue
        
        lancamento = criar_lancamento_base(contract, item, building_id, building_name, unit_price)
        
        lancamento.update({
            'building_unit_id': building_unit_id,
            'tipo_documento': 'PENDENTE',
            'classificacao': 'SALDO',
            'documento_origem': f"CT.{contract_number}",
            'numero_medicao': '',
            'codigo_apropriacao': wbs_code,
            'quantidade': pending_quantity,
            'valor_total': pending_quantity * unit_price
        })
        
        lancamentos.append(lancamento)
    
    return lancamentos


def processar_item_contrato(contract: Dict, item: Dict, building_units_config: Dict, logger) -> List[Dict]:
    contract_status = contract.get("status", "")
    lancamentos = []
    
    appropriations = item.get("buildingAppropriations", [])
    if not appropriations:
        return lancamentos
    
    valid_appropriations = [
        app for app in appropriations
        if should_include_building_unit(app.get("buildingUnitId", 0), building_units_config)
    ]
    
    if not valid_appropriations:
        return lancamentos
    
    if contract_status in ["NOT_MEASURED", "PENDING"]:
        lancamentos.extend(
            criar_lancamento_saldo(contract, item, valid_appropriations, building_units_config)
        )
    
    elif contract_status in ["PARTIALLY_MEASURED", "FULLY_MEASURED", "COMPLETED", "RESCINDED"]:
        medicoes = agrupar_por_medicao(valid_appropriations)
        
        tem_medicoes = any(med_num > 0 for med_num in medicoes.keys())
        
        if tem_medicoes:
            for med_num in sorted(medicoes.keys()):
                if med_num > 0:
                    lancamentos.extend(
                        criar_lancamento_medicao(
                            contract, item, medicoes[med_num], med_num, building_units_config
                        )
                    )
        else:
            for appropriation in valid_appropriations:
                measured_quantity = appropriation.get("measuredQuantity", 0.0)
                if measured_quantity > 0:
                    building_unit_id = appropriation.get("buildingUnitId", 0)
                    wbs_code = appropriation.get("wbsCode", "")
                    
                    building_id, building_name = get_building_info_from_contract(contract)
                    unit_price = calculate_unit_price(item)
                    contract_number = contract.get("contractNumber", "")
                    
                    lancamento = criar_lancamento_base(contract, item, building_id, building_name, unit_price)
                    lancamento.update({
                        'building_unit_id': building_unit_id,
                        'tipo_documento': 'APROPRIADO',
                        'classificacao': 'MEDIDO',
                        'documento_origem': f"CT.{contract_number}",
                        'numero_medicao': '',
                        'codigo_apropriacao': wbs_code,
                        'quantidade': measured_quantity,
                        'valor_total': measured_quantity * unit_price
                    })
                    lancamentos.append(lancamento)
        
        if contract_status == "PARTIALLY_MEASURED":
            lancamentos.extend(
                criar_lancamento_saldo(contract, item, valid_appropriations, building_units_config)
            )
    
    else:
        logger.warning(f"Status desconhecido: {contract_status}")
    
    return lancamentos


def processar_contratos_para_lancamentos(contratos: List[Dict], building_units_config: Dict, logger) -> List[Dict]:
    if not contratos:
        return []
    
    logger.info(f"Processando {len(contratos)} contratos WORKITEM...")
    config = building_units_config
    logger.info(f"Building Units: {'Filtrado' if config.get('filter_enabled') else 'Todos'} {config.get('allowed_ids', []) if config.get('filter_enabled') else ''}")
    
    todos_lancamentos = []
    contratos_com_medicao = 0
    total_medicoes = 0
    
    iterator = tqdm(contratos, desc="Processando contratos", disable=not TQDM_AVAILABLE) if TQDM_AVAILABLE else contratos
    
    for contract in iterator:
        contract_id = contract.get("documentId", "")
        try:
            items_data = contract.get("itens", {})
            for group_key, items_list in items_data.items():
                for item in items_list:
                    lancamentos_item = processar_item_contrato(contract, item, building_units_config, logger)
                    
                    medicoes_item = [l for l in lancamentos_item if l.get('numero_medicao') and l.get('numero_medicao') != '']
                    if medicoes_item:
                        contratos_com_medicao += 1
                        total_medicoes += len(medicoes_item)
                    
                    todos_lancamentos.extend(lancamentos_item)
        except Exception as e:
            logger.error(f"Erro ao processar contrato {contract_id}: {str(e)}")
            continue
    
    logger.info(f"Contratos processados: {len(todos_lancamentos)} lançamentos gerados")
    logger.info(f"Contratos com medições: {contratos_com_medicao}")
    logger.info(f"Total de lançamentos de medições: {total_medicoes}")
    
    tipos_count = {}
    for lancamento in todos_lancamentos:
        tipo = lancamento.get('tipo_documento', 'DESCONHECIDO')
        tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
    
    logger.info(f"Lançamentos de contratos por tipo: {tipos_count}")
    
    return todos_lancamentos