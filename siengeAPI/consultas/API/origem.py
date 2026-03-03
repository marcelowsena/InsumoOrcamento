from .consultaapi import consultaAPI
import datetime

# 1 - Administrativo - ex. 107 - Adm Opera
# 2 - Obra
# 3 - Marketing
# 4 - 

def formataData(datetimeObj):
    ano = str(datetimeObj.year)
    mes = str(datetimeObj.month)
    dia = str(datetimeObj.day)

    if len(mes) == 1:
        mes = '0'+mes
    if len(dia) == 1:
        dia = '0'+dia

    return('-'.join([ano, mes, dia]))

def consultaPedidos():

    apiPedidosPendentes = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-orders?",
        #"startDate=": 0,
        #"&endDate=": 0,
        "status=": "PENDING",
        "&limit=": "200",
        "&offset=": 0
    }

    apiPedidosParcial = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-orders?",
        #"startDate=": 0,
        #"&endDate=": 0,
        "status=": "PARTIALLY_DELIVERED",
        "&limit=": "200",
        "&offset=": 0
    }

    pedidospendentes = consultaAPI(apiPedidosPendentes)
    pedidosparciais = consultaAPI(apiPedidosParcial)

    pedidosDic = {}
    for pp in pedidospendentes:
        if pp['buildingId'] not in pedidosDic:
            pedidosDic[pp['buildingId']] = [pp]
        else:
            pedidosDic[pp['buildingId']].append(pp)
    
    for pp in pedidosparciais:
        if pp['buildingId'] not in pedidosDic:
            pedidosDic[pp['buildingId']] = [pp]
        else:
            pedidosDic[pp['buildingId']].append(pp)
    
    return(pedidosDic)

def consultaItemPedido(pedido):
    apiItens = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-orders/",
        "": pedido,
        "/items?": '',
        "&limit=": "200",
        "&offset=": 0
    }

    itens = consultaAPI(apiItens)

    return(itens)

def consultaTodosPedidos():

    apiPedidosPendentes = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-orders?",
        #"startDate=": 0,
        #"&endDate=": 0,
        "&limit=": "200",
        "&offset=": 0
    }

    pedidos = consultaAPI(apiPedidosPendentes)

    pedidosDic = {}
    for pp in pedidos:
        if pp['buildingId'] not in pedidosDic:
            pedidosDic[pp['buildingId']] = [pp]
        else:
            pedidosDic[pp['buildingId']].append(pp)
    
    return(pedidosDic)

def consultaItensPedidos(pedido):

    consApi = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-orders/",
        "": str(pedido)+'items?',
        "&limit=": "200",
        "&offset=": 0
    }

    itensContrato = consultaAPI(consApi)
    
    return(itensContrato)

def consultaContratos(basedepreco=False):

    apiContratos = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1//supply-contracts/all?",
        "contractStartDate=": 0,
        "&contractEndDate=": 0,
        "&statusApproval=": "A",
        "&authorization=": "A",        
        "&limit=": "200",
        "&offset=": 0
    }

    apiContratos["contractStartDate="] = "2007-01-01"
    apiContratos["&contractEndDate="] = "2040-12-31"

    contratos = consultaAPI(apiContratos)

    dadosfinais = []
    
    for c in contratos:
        if basedepreco == False:
            if c['status'] != "COMPLETED" and c['status'] != "RESCINDED":
                dadosfinais.append(c)
        else:
            dadosfinais.append(c)
    
    return(dadosfinais)

def consultaItensContratos(contrato, bUID):

    apiContratos = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/supply-contracts/items?",
        "documentId=": contrato['documentId'],
        "&contractNumber=": contrato['contractNumber'],
        "&buildingId=": contrato['buildings'][0]['buildingId'],
        "&buildingUnitId=": str(bUID),   
        "&limit=": "200",
        "&offset=": 0
    }

    itensContrato = consultaAPI(apiContratos)
    
    return(itensContrato)

def consultaCaucao(contrato):
    
    apiContratos = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/supply-contracts?",
        "documentId=": contrato['documentId'],
        "&contractNumber=": contrato['contractNumber'],
    }

    detalhesCaucao = consultaAPI(apiContratos)['securityDeposit']
    
    return(detalhesCaucao)

def bulktitulos(selectiontype='I', dataIn="2000-01-01", dataFin="2060-12-31"):
    '''
    Opções de selectiontype, se não escolher ou vier string fora do padrão, escolhe I
    Para filtrar por data da emissão do título (I), 
    data de vencimento da parcela (D), 
    data de pagamento da parcela (P) ou data de competência (B)
    formato da data - "AAAA-MM-DD" PADRÕES - 2000-01-01 - 2060-12-31
    '''

    stypeOptions = [
        'I',
        'D',
        'P',
        'B',
    ]
    if selectiontype not in stypeOptions:
        selectiontype == 'I'

    apiLink = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/bulk-data/v1/outcome?',
        'startDate=': dataIn,
        '&endDate=': dataFin,
        '&selectionType=':selectiontype,
        '&correctionIndexerId=':0,
        '&correctionDate=':formataData(datetime.datetime.today()),
        '&withBankMovements=': 'false',
    }

    dadosConsulta = consultaAPI(apiLink)

    return(dadosConsulta)

def consultaObradoTitulo(link):
    apiLink = {
        'raiz': link
    }
    dadosConsulta = consultaAPI(apiLink)

    return(dadosConsulta['0'])

def consultaEAP(obra, aloc):

    apiEap = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/building-cost-estimations/",
        "": obra,
        "/sheets/": aloc,
        "/items?": "",
        "&limit=": "200",
        "&offset=": 0
    }

    dadosConsulta = consultaAPI(apiEap)

    return(dadosConsulta)

def consultaObras():

    apiEap = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/enterprises?",
        "limit=": "200",
        "&offset=": 0,
        "&onlyBuildingsEnabledForIntegration=false": ''
    }

    dadosConsulta = consultaAPI(apiEap)

    return(dadosConsulta)

def consultaItensSC():

    apiEap = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-requests/all/items?",
        "limit=": "200",
        "&offset=": 0,
    }

    dadosConsulta = consultaAPI(apiEap)

    return(dadosConsulta)

def consultaItensSolicitacoesSC():

    apiItensSC = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-requests/all/items?",
        "startDate=": "2025-01-01",
        "&endDate=": "2025-12-31",
        "&limit=": "200",
        "&offset=": 0
    }

    dados = consultaAPI(apiItensSC)

    return dados

def consultaDetalheSolicitacaoSC(id):
    
    apiDetalhe = {
        "raiz": "https://api.sienge.com.br/trust/public/api/v1/purchase-requests/",
        "": str(id)
    }

    return consultaAPI(apiDetalhe)

def consultaNFBulk(empresa, dataIn="2000-01-01", dataFin="2060-12-31", mostraCC='S'):

    apiDetalhe = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/bulk-data/v1/invoice-itens?',
        'companyId=': empresa,
        '&startDate=': dataIn,
        '&endDate=': dataFin,
        '&showCostCenterId=': mostraCC
    }

    return consultaAPI(apiDetalhe)


def consultaInsumosObra(buildingId, startDate=None, endDate=None, resourcesIds=None):
    '''
    Consulta insumos de uma obra com dados de orcamento e apropriacao

    Parametros:
        buildingId: ID da obra (obrigatorio)
        startDate: Data inicial para apropriacoes (padrao: 2020-01-01)
        endDate: Data final para apropriacoes (padrao: data atual)
        resourcesIds: Lista de IDs de insumos especificos (opcional, max 5 digitos cada)

    Retorna:
        Lista de insumos com:
        - buildingCostEstimationItems: quantidade orcada
        - buildingAppropriations.pending: apropriacoes pendentes
        - buildingAppropriations.attended: apropriacoes atendidas (consumidas)
        - unitOfMeasure: unidade de medida
    '''
    if startDate is None:
        startDate = "2020-01-01"
    if endDate is None:
        endDate = formataData(datetime.datetime.today())

    apiDetalhe = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/bulk-data/v1/building/resources?',
        'buildingId=': buildingId,
        '&startDate=': startDate,
        '&endDate=': endDate,
    }

    if resourcesIds:
        # Formata lista de IDs como parametro
        apiDetalhe['&resourcesIds='] = ','.join(str(r) for r in resourcesIds)

    dados = consultaAPI(apiDetalhe)

    # A API retorna um objeto com 'data' contendo a lista
    if isinstance(dados, dict) and 'data' in dados:
        return dados['data']

    return dados
