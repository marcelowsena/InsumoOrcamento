"""
Utilitarios para busca de fornecedores - Sistema Insumos x Orcamento V4
Integracao com matching de fornecedores via API Sienge
VERSÃO FINAL - Com tratamento N.ENC. e suporte a todos os tipos de documento
"""

from typing import Dict, List, Optional, Tuple, Union
import re


def extrair_info_documento(documento_origem: str) -> Tuple[str, str, Optional[int]]:
    """
    Extrai tipo, número e medição de um documento
    
    Exemplos:
        'CT / 970 Med.001' -> ('CT', '970', 1)
        'OC.9086' -> ('OC', '9086', None)
        'NFSE.839 / SU' -> ('NFSE', '839', None)
        'Sheet Item 1796' -> ('SHEET', '1796', None)
    """
    if not documento_origem or not isinstance(documento_origem, str):
        return ("", "", None)
    
    doc = documento_origem.strip()
    
    tipo_doc = ""
    numero_doc = ""
    numero_medicao = None
    
    # Extrair número de medição primeiro
    match_medicao = re.search(r'Med\.?\s*0*(\d+)', doc, re.IGNORECASE)
    if match_medicao:
        numero_medicao = int(match_medicao.group(1))
        doc = re.sub(r'Med\.?\s*\d+', '', doc, flags=re.IGNORECASE).strip()
    
    # Caso especial: Sheet Item XXXX
    if doc.upper().startswith('SHEET'):
        match_sheet = re.search(r'Sheet\s+Item\s+(\d+)', doc, re.IGNORECASE)
        if match_sheet:
            return ('SHEET', match_sheet.group(1), numero_medicao)
        return ('SHEET', '', numero_medicao)
    
    # Padrão geral: TIPO.NUMERO ou TIPO / NUMERO
    match_doc = re.match(r'([A-Z]+)[\s./-]+(\d+)', doc, re.IGNORECASE)
    if match_doc:
        tipo_doc = match_doc.group(1).upper()
        numero_doc = match_doc.group(2).strip()
    else:
        # Apenas tipo (sem número)
        match_tipo = re.match(r'([A-Z]+)', doc, re.IGNORECASE)
        if match_tipo:
            tipo_doc = match_tipo.group(1).upper()
    
    return (tipo_doc, numero_doc, numero_medicao)


def normalizar_chave(chave) -> int:
    """Normaliza chave para inteiro"""
    if chave is None:
        return 0
    if isinstance(chave, int):
        return chave
    if isinstance(chave, str):
        try:
            return int(chave.strip())
        except (ValueError, TypeError):
            return 0
    return 0


def normalizar_numero_documento(numero) -> str:
    """Normaliza número de documento removendo zeros à esquerda"""
    if numero is None:
        return ""
    numero_str = str(numero).strip()
    numero_str = numero_str.lstrip('0')
    if not numero_str:
        return "0"
    return numero_str


def normalizar_tipo_documento(tipo) -> str:
    """Normaliza tipo de documento para uppercase"""
    if tipo is None:
        return ""
    return str(tipo).strip().upper()


def buscar_fornecedor_por_documento(
    tipo_doc: str,
    numero_doc: str,
    building_id: int,
    base_bulk_org: Dict = None,
    base_pedidos: Dict = None,
    base_contratos: List = None,
    base_forn: Dict = None,
    bases: Tuple = None,
    logger = None
) -> Optional[str]:
    """
    VERSÃO FINAL - Busca fornecedor com fallback para N.ENC.
    
    Retorna:
        - Nome do fornecedor (str) se encontrado
        - "N.ENC." se o tipo é válido mas não foi encontrado
        - None se o tipo não deve ter fornecedor (ex: SHEET)
    """
    
    if bases is not None:
        base_bulk_org, base_pedidos, base_contratos, base_forn = bases
    
    if not tipo_doc or not numero_doc:
        return None
    
    tipo_doc = tipo_doc.strip().upper()
    numero_doc = str(numero_doc).strip()
    
    # SHEET items não têm fornecedor (são orçamento)
    if tipo_doc == 'SHEET':
        return None
    
    # ESTRATÉGIA 1: Contratos (CT, OCT, PCT)
    if tipo_doc in ['CT', 'OCT', 'PCT']:
        if base_contratos:
            numero_norm = normalizar_numero_documento(numero_doc)
            
            for contrato in base_contratos:
                contract_num = normalizar_numero_documento(contrato.get('contractNumber'))
                if contract_num == numero_norm:
                    fornecedor = contrato.get('supplierName')
                    if fornecedor:
                        if logger:
                            logger.debug(f"Contrato {numero_doc}: {fornecedor}")
                        return fornecedor
            
            # Não encontrou
            if logger:
                logger.debug(f"Contrato {numero_doc} não encontrado")
            return "N.ENC."
        else:
            return "N.ENC."
    
    # ESTRATÉGIA 2: Pedidos (OC, PC)
    if tipo_doc in ['OC', 'PC']:
        if base_pedidos and base_forn:
            building_id_norm = normalizar_chave(building_id)
            
            if building_id_norm in base_pedidos:
                numero_norm = normalizar_numero_documento(numero_doc)
                pedidos_obra = base_pedidos[building_id_norm]
                
                for pedido in pedidos_obra:
                    pedido_id = normalizar_numero_documento(pedido.get('id'))
                    if pedido_id == numero_norm:
                        supplier_id = normalizar_chave(pedido.get('supplierId'))
                        if supplier_id in base_forn:
                            fornecedor = base_forn[supplier_id]
                            if logger:
                                logger.debug(f"Pedido {numero_doc}: {fornecedor}")
                            return fornecedor
                
                # Não encontrou
                if logger:
                    logger.debug(f"Pedido {numero_doc} não encontrado na obra {building_id_norm}")
                return "N.ENC."
            else:
                if logger:
                    logger.debug(f"Obra {building_id_norm} não tem pedidos")
                return "N.ENC."
        else:
            return "N.ENC."
    
    # ESTRATÉGIA 3: Títulos (NF, NFSE, NFE, FAT, FL, CF, REC, etc)
    tipos_fiscais = ['NF', 'NFSE', 'NFE', 'FAT', 'FL', 'CF', 'REC', 'FATURA']
    
    # Verifica se é um tipo fiscal
    is_fiscal = any(tf in tipo_doc for tf in tipos_fiscais) or tipo_doc in tipos_fiscais
    
    if is_fiscal:
        if base_bulk_org:
            building_id_norm = normalizar_chave(building_id)
            
            if building_id_norm in base_bulk_org:
                tipo_norm = normalizar_tipo_documento(tipo_doc)
                numero_norm = normalizar_numero_documento(numero_doc)
                
                dic_obra = base_bulk_org[building_id_norm]
                
                if tipo_norm in dic_obra:
                    dic_tipo_doc = dic_obra[tipo_norm]
                    
                    if numero_norm in dic_tipo_doc:
                        titulo = dic_tipo_doc[numero_norm]
                        fornecedor = titulo.get('creditorName')
                        if fornecedor:
                            if logger:
                                logger.debug(f"Título {tipo_norm}.{numero_norm}: {fornecedor}")
                            return fornecedor
                    
                    # Não encontrou o número
                    if logger:
                        logger.debug(f"Título {tipo_norm}.{numero_norm} não encontrado")
                    return "N.ENC."
                else:
                    # Tipo não existe na obra
                    if logger:
                        logger.debug(f"Tipo {tipo_norm} não existe na obra {building_id_norm}")
                    return "N.ENC."
            else:
                if logger:
                    logger.debug(f"Obra {building_id_norm} não tem títulos")
                return "N.ENC."
        else:
            return "N.ENC."
    
    # Tipo desconhecido
    if logger:
        logger.debug(f"Tipo de documento desconhecido: {tipo_doc}")
    return "N.ENC."


def carregar_bases_fornecedor():
    """Carrega todas as bases de fornecedores da API Sienge"""
    try:
        from siengeAPI.bases import carregabases
        from siengeAPI.consultas import credores
        
        base_forn_raw = credores.importaCredores()
        if not base_forn_raw:
            print("AVISO: Base de credores vazia")
            return None
        
        base_forn = {str(c['id']): c['name'] for c in base_forn_raw if c.get('id') and c.get('name')}
        
        base_pedidos = carregabases.pedidosCompra()
        if not base_pedidos:
            print("AVISO: Base de pedidos vazia")
        
        base_contratos = carregabases.contratos()
        if not base_contratos:
            print("AVISO: Base de contratos vazia")
        
        titulos_bulk_raw = carregabases.titulosBulk()
        if not titulos_bulk_raw or 'data' not in titulos_bulk_raw:
            print("AVISO: Base de titulos bulk vazia")
            titulos_bulk = []
        else:
            titulos_bulk = titulos_bulk_raw['data']
        
        base_bulk_org = _organizar_base_bulk(titulos_bulk)
        
        print(f"Bases carregadas: {len(base_forn)} fornecedores, {len(base_contratos)} contratos, "
              f"{len(base_pedidos)} obras pedidos, {len(base_bulk_org)} obras bulk")
        
        return base_bulk_org, base_pedidos, base_contratos, base_forn
        
    except ImportError as e:
        print(f"ERRO: siengeAPI não encontrado - {str(e)}")
        return None
    except Exception as e:
        print(f"ERRO ao carregar bases de fornecedor: {str(e)}")
        return None


def _organizar_base_bulk(
    titulos_bulk: List[Dict],
    filtros: List[str] = None
) -> Dict:
    """
    Organiza títulos bulk em estrutura hierárquica: obra_id -> tipo_doc -> numero_doc -> titulo
    """
    if filtros is None:
        filtros = ['DARF', 'FP  ', 'GPS ', 'FGTS', 'CAU ', 'PCT ']
    
    base_organizada = {}
    
    for tit in titulos_bulk:
        try:
            tipo_doc = tit.get('documentIdentificationId', '').strip()
            num_doc = str(tit.get('documentNumber', '')).strip()
            
            if not tipo_doc or not num_doc:
                continue
            
            if tipo_doc in filtros:
                continue
            
            aprops = tit.get('buildingsCosts', [])
            if not aprops:
                continue
            
            obras = []
            for ap in aprops:
                building_id = ap.get('buildingId')
                if building_id and building_id not in obras:
                    obras.append(building_id)
            
            # Apenas títulos de uma única obra
            if len(obras) != 1:
                continue
            
            obra_id = obras[0]
            
            tipo_norm = normalizar_tipo_documento(tipo_doc)
            num_norm = normalizar_numero_documento(num_doc)
            
            if obra_id not in base_organizada:
                base_organizada[obra_id] = {}
            
            if tipo_norm not in base_organizada[obra_id]:
                base_organizada[obra_id][tipo_norm] = {}
            
            if num_norm not in base_organizada[obra_id][tipo_norm]:
                base_organizada[obra_id][tipo_norm][num_norm] = tit
                
        except Exception:
            continue
    
    return base_organizada


NOMENCLATURA_MAP = {
    'APROPRIADO': 'INCORRIDO',
    'PENDENTE': 'COMPROMETIDO',
    'ORCADO': 'ORCADO',
    'ADITIVO': 'ADITIVO'
}


def converter_nomenclatura(tipo_documento: str) -> str:
    """Converte nomenclatura de tipos de documento"""
    return NOMENCLATURA_MAP.get(tipo_documento.upper(), tipo_documento)


if __name__ == '__main__':
    print("="*80)
    print("TESTES DE EXTRAÇÃO DE DOCUMENTO")
    print("="*80)
    
    test_cases = [
        "CT /970 Med.001",
        "CT. / 970 Med.001",
        "CT.652 Med.003",
        "CT.652",
        "NF.839",
        "NFSE.839 / SU",
        "OC.12345",
        "CT.652 Med.001",
        "OCT.456",
        "NFSE.839",
        "Sheet Item 1796",
        "NFE.37476 / 3",
        "FAT.202 / SU",
        ""
    ]
    
    print("\nTestes de extração de documento:")
    for caso in test_cases:
        tipo, numero, medicao = extrair_info_documento(caso)
        print(f"'{caso:30}' -> Tipo: '{tipo:10}', Numero: '{numero:10}', Medicao: {medicao}")
    
    print("\n" + "="*80)
    print("TESTES DE CONVERSÃO DE NOMENCLATURA")
    print("="*80)
    
    for termo in ['APROPRIADO', 'PENDENTE', 'ORCADO']:
        print(f"{termo:15} -> {converter_nomenclatura(termo)}")