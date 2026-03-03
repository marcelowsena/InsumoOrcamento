"""
API de Títulos V4 - Sistema Insumos x Orçamento
Busca títulos usando a biblioteca siengeAPI existente e aplica filtros configurados
SEM CACHE - Sempre busca direto da API (base muito pesada)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


def load_filtros_titulos(config_dir: Path) -> Dict:
    """Carrega filtros de títulos do JSON"""
    try:
        filtros_path = config_dir / 'filtros_titulos.json'
        if filtros_path.exists():
            with open(filtros_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return create_default_filtros_titulos()
    except Exception as e:
        print(f"Erro ao carregar filtros de títulos: {e}")
        return create_default_filtros_titulos()


def create_default_filtros_titulos() -> Dict:
    """Cria filtros padrão para títulos"""
    return {
        "description": "Filtros para busca de títulos na API Sienge",
        "habilitado": True,
        "periodo": {
            "description": "Parâmetros de data para busca (data de vencimento)",
            "dias_futuro": 90,
            "dias_passado": 30
        },
        "filtros": {
            "tipos_documento": {
                "description": "Tipos de documento para incluir na busca",
                "modo": "incluir",
                "valores": ["NFS", "PCT", "DUP", "BOL"]
            }
        }
    }


def save_filtros_titulos(filtros: Dict, config_dir: Path) -> bool:
    """Salva filtros de títulos no JSON"""
    try:
        filtros_path = config_dir / 'filtros_titulos.json'
        with open(filtros_path, 'w', encoding='utf-8') as f:
            json.dump(filtros, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar filtros de títulos: {e}")
        return False


def calcular_periodo_busca(filtros: Dict) -> Tuple[str, str]:
    """
    Calcula período de busca baseado na configuração
    NOVO: Usa datas fixas para buscar TODOS os títulos
    Returns: (data_inicio, data_fim) no formato YYYY-MM-DD
    """
    periodo = filtros.get('periodo', {})
    
    # Usar datas fixas se disponíveis, senão usar padrão amplo
    data_inicio = periodo.get('data_inicio', '2000-01-01')
    data_fim = periodo.get('data_fim', '2080-12-31')
    
    return data_inicio, data_fim


# Cache removido - títulos sempre buscados diretamente da API


def buscar_titulos_biblioteca_existente(data_inicio: str, data_fim: str, logger) -> Tuple[bool, List[Dict]]:
    """
    Busca títulos usando a biblioteca siengeAPI existente
    Returns: (sucesso, lista_titulos)
    """
    try:
        # Importar biblioteca existente
        from siengeAPI.consultas.API import bulktitulos
        
        logger.info(f"Buscando títulos via siengeAPI: {data_inicio} a {data_fim}")
        
        # Chamar função da biblioteca (baseado no teste_tit.py)
        dados = bulktitulos(
            selectiontype='D',  # Data de vencimento
            dataIn=data_inicio,
            dataFin=data_fim
        )
        
        if dados and 'data' in dados:
            titulos = dados['data']
            logger.info(f"Títulos encontrados: {len(titulos)}")
            return True, titulos
        else:
            logger.warning("API não retornou dados válidos")
            return False, []
            
    except ImportError:
        logger.error("Biblioteca siengeAPI não encontrada")
        return False, []
        
    except Exception as e:
        logger.error(f"Erro na busca de títulos: {str(e)}")
        return False, []


def aplicar_filtros_titulos(titulos: List[Dict], filtros: Dict, logger) -> List[Dict]:
    """
    Aplica filtros configurados nos títulos
    Returns: lista de títulos filtrados
    """
    if not filtros.get('habilitado', True):
        logger.info("Filtros de títulos desabilitados")
        return titulos
    
    logger.info(f"Aplicando filtros em {len(titulos)} títulos")
    
    titulos_filtrados = titulos.copy()
    
    # Filtro por tipos de documento
    tipos_config = filtros.get('filtros', {}).get('tipos_documento', {})
    tipos_valores = tipos_config.get('valores', [])
    modo = tipos_config.get('modo', 'incluir')
    
    if tipos_valores:
        if modo == 'incluir':
            titulos_filtrados = [
                t for t in titulos_filtrados 
                if t.get('documentIdentificationId', '').strip() in tipos_valores
            ]
        else:  # excluir
            titulos_filtrados = [
                t for t in titulos_filtrados 
                if t.get('documentIdentificationId', '').strip() not in tipos_valores
            ]
        
        logger.info(f"Filtro tipos documento ({modo}): {len(titulos_filtrados)} títulos")
    
    # Filtro básico: apenas títulos com apropriação para obras
    titulos_com_obra = []
    for titulo in titulos_filtrados:
        buildings_costs = titulo.get('buildingsCosts', [])
        if buildings_costs:
            # Verificar se tem pelo menos uma apropriação válida
            tem_apropriacao_valida = any(
                bc.get('buildingId') and bc.get('rate', 0) > 0 
                for bc in buildings_costs
            )
            if tem_apropriacao_valida:
                titulos_com_obra.append(titulo)
    
    logger.info(f"Filtro apropriação para obras: {len(titulos_com_obra)} títulos")
    
    return titulos_com_obra


def buscar_titulos_com_filtros(config_dir: Path, logger) -> List[Dict]:
    """
    Busca títulos aplicando filtros (SEM cache - sempre busca direto da API)
    Returns: lista de títulos filtrados
    """
    # Carregar filtros
    filtros = load_filtros_titulos(config_dir)
    
    if not filtros.get('habilitado', True):
        logger.warning("Busca de títulos desabilitada nos filtros")
        return []
    
    # Calcular período
    data_inicio, data_fim = calcular_periodo_busca(filtros)
    tipos_doc = filtros.get('filtros', {}).get('tipos_documento', {}).get('valores', [])
    
    logger.info(f"Período de busca: {data_inicio} a {data_fim}")
    logger.info(f"Tipos documento: {tipos_doc}")
    
    # Buscar na API usando biblioteca existente (SEMPRE direto da API)
    sucesso, titulos_brutos = buscar_titulos_biblioteca_existente(data_inicio, data_fim, logger)
    
    if not sucesso:
        logger.error("Falha na busca de títulos")
        return []
    
    # Aplicar filtros
    titulos_filtrados = aplicar_filtros_titulos(titulos_brutos, filtros, logger)
    
    logger.info(f"Busca de títulos concluída: {len(titulos_filtrados)} títulos")
    
    return titulos_filtrados


def debug_titulo_structure(titulo: Dict, logger) -> None:
    """Debug da estrutura de um título"""
    logger.info("=== DEBUG ESTRUTURA TÍTULO ===")
    logger.info(f"Bill ID: {titulo.get('billId')}")
    logger.info(f"Credor: {titulo.get('creditorName')}")
    logger.info(f"Documento: {titulo.get('documentIdentificationId')} - {titulo.get('documentNumber')}")
    logger.info(f"Valor: R$ {titulo.get('correctedBalanceAmount', 0):,.2f}")
    logger.info(f"Vencimento: {titulo.get('dueDate')}")
    
    buildings_costs = titulo.get('buildingsCosts', [])
    logger.info(f"Apropriações: {len(buildings_costs)}")
    
    for i, bc in enumerate(buildings_costs[:3], 1):
        logger.info(f"  {i}. Obra {bc.get('buildingId')} - {bc.get('buildingName', '')[:30]}...")
        logger.info(f"     Building Unit: {bc.get('buildingUnitId')} - {bc.get('buildingUnitName', '')}")
        logger.info(f"     Código: {bc.get('costEstimationSheetId')} - {bc.get('costEstimationSheetName', '')[:30]}...")
        logger.info(f"     Rate: {bc.get('rate', 0)}%")


if __name__ == '__main__':
    # Teste básico do módulo
    from pathlib import Path
    
    config_dir = Path('src/config')
    
    # Testar criação de filtros padrão
    filtros = create_default_filtros_titulos()
    print("Filtros padrão criados:")
    print(json.dumps(filtros, indent=2, ensure_ascii=False))
    
    # Testar cálculo de período
    data_inicio, data_fim = calcular_periodo_busca(filtros)
    print(f"\nPeríodo calculado: {data_inicio} a {data_fim}")