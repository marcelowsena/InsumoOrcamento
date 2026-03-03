"""
Processador de Aditivos - Sistema Insumos x Orçamento V4
Carrega e processa dados de aditivos de contratos a partir de CSV
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


def carregar_aditivos_csv(caminho_csv: Path, logger) -> List[Dict]:
    """
    Carrega aditivos de um arquivo CSV e converte para o formato de lançamentos.

    Args:
        caminho_csv: Caminho para o arquivo CSV de aditivos
        logger: Logger para registrar mensagens

    Returns:
        Lista de lançamentos no formato padrão do sistema
    """
    if not caminho_csv.exists():
        logger.warning(f"Arquivo de aditivos não encontrado: {caminho_csv}")
        return []

    lancamentos = []
    erros = 0

    try:
        with open(caminho_csv, 'r', encoding='utf-8-sig') as f:
            # Detectar delimitador (pode ser ; ou ,)
            sample = f.read(2048)
            f.seek(0)

            if sample.count(';') > sample.count(','):
                delimiter = ';'
            else:
                delimiter = ','

            reader = csv.DictReader(f, delimiter=delimiter)

            for row_num, row in enumerate(reader, start=2):
                try:
                    lancamento = _converter_linha_para_lancamento(row)
                    if lancamento:
                        lancamentos.append(lancamento)
                except Exception as e:
                    erros += 1
                    if erros <= 5:
                        logger.warning(f"Erro na linha {row_num} do CSV de aditivos: {e}")

        logger.info(f"Aditivos carregados: {len(lancamentos)} lançamentos de {caminho_csv.name}")
        if erros > 0:
            logger.warning(f"Aditivos: {erros} linhas com erro ignoradas")

    except Exception as e:
        logger.error(f"Erro ao carregar CSV de aditivos: {e}")
        return []

    return lancamentos


def _converter_linha_para_lancamento(row: Dict) -> Optional[Dict]:
    """
    Converte uma linha do CSV para o formato de lançamento padrão.
    """
    # Campos obrigatórios
    building_id = row.get('Building_ID', '')
    if not building_id:
        return None

    try:
        building_id = int(building_id)
    except (ValueError, TypeError):
        return None

    # Converter valores numéricos
    quantidade = _parse_float(row.get('Quantidade', '0'))
    valor_unitario = _parse_float(row.get('Valor_Unitário', '0'))
    valor_total = _parse_float(row.get('Valor_Total', '0'))

    # Construir lançamento no formato padrão
    lancamento = {
        'building_id': building_id,
        'obra_nome': row.get('Obra', ''),
        'insumo_id': row.get('Insumo_ID', ''),
        'insumo_nome': row.get('Insumo', ''),
        'codigo_recurso': row.get('Código_Recurso', ''),
        'categoria_recurso': row.get('Categoria_Recurso', ''),
        'grupo_recurso': row.get('Grupo_Recurso', ''),
        'classificacao_abc': row.get('Classificação_ABC', ''),
        'categoria': row.get('Categoria', ''),
        'unidade': row.get('Unidade', ''),
        'tipo_documento': row.get('Tipo_Documento', 'COMPROMETIDO'),
        'classificacao': row.get('Classificação', 'ADITIVO'),
        'documento_origem': row.get('Documento_Origem', ''),
        'numero_medicao': row.get('Número_Medição', ''),
        'fornecedor': row.get('Fornecedor', ''),
        'building_unit_id': row.get('Building_Unit_ID', ''),
        'building_unit_name': row.get('Building_Unit_Name', ''),
        'apropriacao_completa': row.get('Apropriação_Completa', ''),
        'codigo_apropriacao': row.get('Código_Apropriação', ''),
        'nivel_1': row.get('Nível_1', ''),
        'nivel_2': row.get('Nível_2', ''),
        'nivel_3': row.get('Nível_3', ''),
        'nivel_4': row.get('Nível_4', ''),
        'quantidade': quantidade,
        'valor_unitario': valor_unitario,
        'valor_total': valor_total,
        'data_documento': row.get('Data', ''),
        'mes_apropriacao': row.get('Mês_Apropriação', ''),
        'ano_apropriacao': row.get('Ano_Apropriação', ''),
        'status': row.get('Status', ''),
        'fonte': 'ADITIVO'
    }

    return lancamento


def _parse_float(valor: str) -> float:
    """
    Converte string para float, tratando formatos BR e EN.
    """
    if not valor or valor == '':
        return 0.0

    try:
        # Remover R$ se existir
        valor = str(valor).replace('R$', '').strip()

        # Se tem vírgula e ponto, assumir formato BR (1.234,56)
        if ',' in valor and '.' in valor:
            valor = valor.replace('.', '').replace(',', '.')
        # Se só tem vírgula, assumir decimal BR
        elif ',' in valor:
            valor = valor.replace(',', '.')

        return float(valor)
    except (ValueError, TypeError):
        return 0.0


def buscar_aditivos(config_path: Path, logger) -> List[Dict]:
    """
    Busca aditivos no arquivo CSV padrão.

    Args:
        config_path: Diretório de configuração (base para encontrar o CSV)
        logger: Logger para mensagens

    Returns:
        Lista de lançamentos de aditivos
    """
    # Procurar CSV em locais padrão
    possiveis_caminhos = [
        config_path.parent.parent / 'Aditivos_Consolidados_v2.csv',
        config_path.parent.parent / 'Aditivos_Consolidados.csv',
        config_path.parent.parent.parent / 'Aditivos_Consolidados_v2.csv',
        config_path.parent.parent.parent / 'Aditivos_Consolidados.csv',
        Path('Aditivos_Consolidados_v2.csv'),
        Path('Aditivos_Consolidados.csv'),
    ]

    for caminho in possiveis_caminhos:
        if caminho.exists():
            logger.info(f"Arquivo de aditivos encontrado: {caminho}")
            return carregar_aditivos_csv(caminho, logger)

    logger.info("Nenhum arquivo de aditivos encontrado")
    return []


def filtrar_aditivos_por_obras(aditivos: List[Dict], obras_ids: set) -> List[Dict]:
    """
    Filtra aditivos para incluir apenas obras permitidas.
    """
    return [a for a in aditivos if a.get('building_id') in obras_ids]


if __name__ == '__main__':
    # Teste básico
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import get_main_logger
    from config.settings import load_all_configs

    configs = load_all_configs()
    logger = get_main_logger(configs)

    # Testar carregamento
    aditivos = buscar_aditivos(configs['paths']['config'], logger)

    print(f"\nTotal de aditivos: {len(aditivos)}")

    if aditivos:
        print("\nExemplo de aditivo:")
        for key, value in list(aditivos[0].items())[:10]:
            print(f"  {key}: {value}")
