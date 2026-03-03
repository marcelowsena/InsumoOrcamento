from consultas.API.origem import consultaContratos, consultaPedidos
from consultas.credores import importaCredores
from bases import carregabases, atualizaBases
import csv
import json
from typing import Dict, List, Optional, Tuple, Union

def baseCredores() -> Dict[str, str]:
    baseAntiga = importaCredores()
    return {str(credor['id']): credor['name'] for credor in baseAntiga}

def busca_fornecedor_pedido(
    dados_tit: Dict, 
    base_pedidos: Dict, 
    base_forn: Dict
) -> Optional[Tuple[str, str]]:
    obra_id = str(dados_tit['buildingId'])
    doc_number = str(dados_tit['docNumber']).strip()
    
    if obra_id not in base_pedidos:
        return None
    
    try:
        doc_number_int = int(doc_number)
    except ValueError:
        return None
    
    for pedido in base_pedidos[obra_id]:
        if pedido['id'] == doc_number_int:
            supp_id = str(pedido['supplierId'])
            return (supp_id, base_forn.get(supp_id, 'NAO ENCONTRADO'))
    
    return None

def busca_fornecedor_contrato(
    dados_tit: Dict, 
    base_contratos: List
) -> Optional[Tuple[str, str]]:
    doc_number = str(dados_tit['docNumber']).strip()
    
    for contrato in base_contratos:
        contrato_number = str(contrato["contractNumber"]).strip()
        if doc_number == contrato_number:
            return (str(contrato['supplierId']), contrato['supplierName'])
    
    try:
        doc_number_int = int(doc_number)
        for contrato in base_contratos:
            contrato_number = str(contrato["contractNumber"]).strip()
            try:
                if doc_number_int == int(contrato_number):
                    return (str(contrato['supplierId']), contrato['supplierName'])
            except ValueError:
                if str(doc_number_int) == contrato_number:
                    return (str(contrato['supplierId']), contrato['supplierName'])
    except ValueError:
        pass
    
    return None

def busca_fornecedor_nf(
    dados_tit: Dict, 
    base_bulk_org: Dict
) -> List[Tuple[str, str]]:
    obra_id = dados_tit['buildingId']
    tipo_doc = dados_tit['tipoDoc'].strip()
    num_doc = dados_tit['docNumber'].strip()
    
    if obra_id not in base_bulk_org:
        return []
    
    dic_obra = base_bulk_org[obra_id]
    
    if tipo_doc not in dic_obra:
        tipo_encontrado = None
        for tipo_key in dic_obra.keys():
            if tipo_key.strip() == tipo_doc:
                tipo_encontrado = tipo_key
                break
        if not tipo_encontrado:
            return []
        dic_tipo_doc = dic_obra[tipo_encontrado]
    else:
        dic_tipo_doc = dic_obra[tipo_doc]
    
    if num_doc in dic_tipo_doc:
        titulos = dic_tipo_doc[num_doc]
        if titulos:
            credores = [(tit['creditorId'], tit['creditorName']) for tit in titulos]
            return list(set(credores))
    
    try:
        num_doc_normalizado = str(int(num_doc))
        if num_doc_normalizado in dic_tipo_doc:
            titulos = dic_tipo_doc[num_doc_normalizado]
            if titulos:
                credores = [(tit['creditorId'], tit['creditorName']) for tit in titulos]
                return list(set(credores))
    except ValueError:
        pass
    
    if num_doc.isdigit() and len(num_doc) <= 6:
        for zeros in range(1, 4):
            num_doc_com_zeros = num_doc.zfill(len(num_doc) + zeros)
            if num_doc_com_zeros in dic_tipo_doc:
                titulos = dic_tipo_doc[num_doc_com_zeros]
                if titulos:
                    credores = [(tit['creditorId'], tit['creditorName']) for tit in titulos]
                    return list(set(credores))
    
    return []

def busca_fornecedor(
    dados_tit: Dict, 
    base_bulk_org: Dict, 
    base_pedidos: Dict, 
    base_contratos: List, 
    base_forn: Dict
) -> Union[Tuple[str, str], List[Tuple[str, str]], None]:
    tipo_doc = dados_tit['tipoDoc']
    
    if tipo_doc in ['OC', 'OCT']:
        return busca_fornecedor_pedido(dados_tit, base_pedidos, base_forn)
    elif tipo_doc == 'CT' or tipo_doc.startswith('CT'):
        return busca_fornecedor_contrato(dados_tit, base_contratos)
    elif 'NF' in tipo_doc:
        return busca_fornecedor_nf(dados_tit, base_bulk_org)
    
    return None

def formata_dados_documento(dados_linha: List[str]) -> Dict:
    dicNovo = {'buildingId': int(dados_linha[0])}
    doc_info = dados_linha[2].strip()
    
    if 'NF' in doc_info:
        pos_p = doc_info.find('.')
        if pos_p != -1:
            dicNovo['tipoDoc'] = doc_info[0:pos_p].strip()
            fim = doc_info.find(' ', pos_p)
            dicNovo['docNumber'] = doc_info[pos_p+1:fim if fim != -1 else len(doc_info)].strip()
        else:
            dicNovo['tipoDoc'] = 'NF'
            dicNovo['docNumber'] = doc_info.replace('NF', '').strip()
        return dicNovo
    
    if any(prefix in doc_info for prefix in ['FL.', 'FAT.', 'CF.', 'REC.', 'AV.', 'PPC.', 'PRV.', 'DARM.', 'ADTO.']):
        dicNovo['tipoDoc'] = doc_info
        dicNovo['docNumber'] = ''
        return dicNovo
    
    if 'Med' in doc_info:
        doc_limpo = doc_info.replace('CT', '').replace('/', '').strip()
        partes = doc_limpo.split()
        if len(partes) >= 1 and partes[0].isdigit():
            dicNovo['tipoDoc'] = 'CT'
            dicNovo['docNumber'] = partes[0]
        else:
            dicNovo['tipoDoc'] = 'CT'
            dicNovo['docNumber'] = ''
        return dicNovo
    
    if 'OCT' in doc_info:
        partes = doc_info.split('.')
        dicNovo['tipoDoc'] = 'OCT'
        dicNovo['docNumber'] = partes[1].strip() if len(partes) > 1 else ''
        return dicNovo
    
    if 'OC' in doc_info:
        partes = doc_info.split('.')
        dicNovo['tipoDoc'] = 'OC'
        dicNovo['docNumber'] = partes[1].strip() if len(partes) > 1 else ''
        return dicNovo
    
    if 'CT' in doc_info:
        if '/' in doc_info:
            partes = doc_info.split('/')
            dicNovo['tipoDoc'] = 'CT'
            if len(partes) > 1:
                num = partes[1].strip().replace('SU', '').strip()
                if num and num not in ['/', ''] and not num.isspace() and num.replace(' ', '').isdigit():
                    dicNovo['docNumber'] = num.replace(' ', '')
                else:
                    dicNovo['docNumber'] = ''
            else:
                dicNovo['docNumber'] = ''
        else:
            partes = doc_info.split('.')
            dicNovo['tipoDoc'] = 'CT'
            if len(partes) > 1:
                num = partes[1].strip().replace('SU', '').strip()
                if num and num.isdigit():
                    dicNovo['docNumber'] = num
                else:
                    dicNovo['docNumber'] = ''
            else:
                dicNovo['docNumber'] = ''
        return dicNovo
    
    dicNovo['tipoDoc'] = doc_info
    dicNovo['docNumber'] = ''
    return dicNovo

def organiza_base_bulk(titulos_bulk: List[Dict], filtros: List[str] = None) -> Dict:
    if filtros is None:
        filtros = ['DARF', 'FP  ', 'GPS ', 'FGTS', 'CAU ', 'PCT ']
    
    base_organizada = {}
    
    for tit in titulos_bulk:
        aprops = tit['buildingsCosts']
        obras = []
        
        if tit['documentIdentificationId'] not in filtros:
            for ap in aprops:
                if ap['buildingId'] not in obras:
                    obras.append(ap['buildingId'])
        
        if len(obras) == 1:
            titObra = obras[0]
            titTipoDoc = tit['documentIdentificationId']
            numDoc = tit['documentNumber']
            
            if titObra not in base_organizada:
                base_organizada[titObra] = {titTipoDoc: {numDoc: [tit]}}
            elif titTipoDoc not in base_organizada[titObra]:
                base_organizada[titObra][titTipoDoc] = {numDoc: [tit]}
            else:
                if numDoc in base_organizada[titObra][titTipoDoc]:
                    listaTitExistentes = base_organizada[titObra][titTipoDoc][numDoc]
                    trMatch = False
                    
                    for titEx in listaTitExistentes:
                        if tit['billId'] == titEx['billId'] or aprops == titEx['buildingsCosts']:
                            trMatch = True
                            break
                    
                    if not trMatch:
                        base_organizada[titObra][titTipoDoc][numDoc].append(tit)
                else:
                    base_organizada[titObra][titTipoDoc][numDoc] = [tit]
    
    return base_organizada

def processar_dados(
    dados_csv: List[List[str]], 
    base_bulk_org: Dict, 
    base_pedidos: Dict, 
    base_contratos: List, 
    base_forn: Dict,
    filtrar_orcado: bool = True
) -> List[Dict]:
    dados_processados = []
    
    for dado in dados_csv:
        if filtrar_orcado and dado[1] == 'ORCADO':
            continue
        
        dados_formatado = formata_dados_documento(dado)
        dados_formatado['DadosForn'] = busca_fornecedor(
            dados_formatado, 
            base_bulk_org, 
            base_pedidos, 
            base_contratos, 
            base_forn
        )
        dados_processados.append(dados_formatado)
    
    return dados_processados

def atualizar_bases(atualizar: bool = False) -> None:
    if not atualizar:
        return
    
    contratos = consultaContratos(True)
    atualizaBases.contratos(contratos)
    
    pedidos = consultaPedidos()
    atualizaBases.pedidosCompra(pedidos)

def exportar_json(dados: Union[List, Dict], arquivo: str) -> None:
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def exportar_dados_completos(
    dados_formatados: List[Dict],
    base_bulk_org: Dict,
    base_pedidos: Dict,
    base_contratos: List,
    base_forn: Dict,
    arquivo: str = 'dados_tratados_fornecedor.json'
) -> List[Dict]:
    dados_completos = []
    
    for dados in dados_formatados:
        registro = dados.copy()
        resultado = busca_fornecedor(dados, base_bulk_org, base_pedidos, base_contratos, base_forn)
        
        if isinstance(resultado, list):
            if len(resultado) == 1:
                registro['fornecedorId'] = resultado[0][0]
                registro['fornecedorNome'] = resultado[0][1]
            elif len(resultado) > 1:
                registro['fornecedores'] = resultado
        elif isinstance(resultado, tuple):
            registro['fornecedorId'] = resultado[0]
            registro['fornecedorNome'] = resultado[1]
        
        dados_completos.append(registro)
    
    exportar_json(dados_completos, arquivo)
    return dados_completos

def carregar_csv(arquivo: str, delimiter: str = ';', encoding: str = 'latin-1') -> List[List[str]]:
    with open(arquivo, encoding=encoding, mode='r') as f:
        return list(csv.reader(f, delimiter=delimiter))

def main(
    arquivo_csv: str = 'nfAprop.csv',
    atualizar: bool = False
) -> List[Dict]:
    atualizar_bases(atualizar)
    
    base_forn = baseCredores()
    base_pedidos = carregabases.pedidosCompra()
    base_contratos = carregabases.contratos()
    
    titulos_bulk = carregabases.titulosBulk()['data']
    base_bulk_org = organiza_base_bulk(titulos_bulk)
    
    dados_csv = carregar_csv(arquivo_csv)
    
    dados_processados = processar_dados(
        dados_csv,
        base_bulk_org,
        base_pedidos,
        base_contratos,
        base_forn
    )
    
    return dados_processados

if __name__ == '__main__':
    resultado = main()