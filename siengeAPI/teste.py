from consultas.API.origem import bulktitulos, consultaContratos, consultaPedidos
from consultas.credores import importaCredores
import csv
from tqdm import tqdm
from bases import carregabases, atualizaBases
import json

#atualizaBases.bulkTitulos(bulktitulos())

def baseCredores():
    dicNovo = {}
    baseAntiga = importaCredores()
    for credor in baseAntiga:
        dicNovo[credor['id']] = credor['name']
    return(dicNovo)

def achaFornecedor(dadosTit={}):
    baseBulk = baseBulkOrg
    basePedidos = carregabases.pedidosCompra()
    baseContratos = carregabases.contratos()

    # Padrão = baseForn[codForn] = NomeForn, ex baseForn['40'] = 'EMBRADECON CONSTRUCOES LTDA'
    # Contratos tem SuppId e nome, pedidos tem supid, nf só tem nome :D

    def buscaDadosNosPedidos(dadosTit={}):
        if str(dadosTit['buildingId']) in basePedidos:
            for pedido in basePedidos[str(dadosTit['buildingId'])]:
                if pedido['id'] == dadosTit['docNumber']:
                    return((pedido['supplierId'], baseForn[str(pedido['supplierId'])]))
            return('Pedido não encontrado na obra - ', dadosTit['docNumber'])
        else:
            return('Obra sem pedido -', dadosTit['buildingId'])
    
    def buscaDadosNosContratos(dadosTit={}):
        for contrato in baseContratos:
            if str(dadosTit['docNumber']) == contrato["contractNumber"]:
                return((contrato['supplierId'], contrato['supplierName']))
        return('Contrato Não encontrado - ', dadosTit['docNumber'])

    def buscaDadosNasNF(dadosTit={}):
        if dadosTit['buildingId'] in baseBulk:
            dicObra = baseBulk[dadosTit['buildingId']]
            if dadosTit['tipoDoc'] in dicObra:
                dicTipoDoc = dicObra[dadosTit['tipoDoc']]
                if dadosTit['docNumber'] in dicTipoDoc:
                    titulos = dicTipoDoc[dadosTit['docNumber']]
                    if len(titulos) > 0:
                        dadosTitulos = []
                        for tit in titulos:
                            dadosTitulos.append(((tit['creditorId'], tit['creditorName'])))
                        return(dadosTitulos)
                else:
                    return(('', ''))
            else:
                return(('', ''))
        else:
            return(('', ''))

    if dadosTit['tipoDoc'] == 'OC':
        return(buscaDadosNosPedidos(dadosTit))
    elif dadosTit['tipoDoc'] == 'CT':
        return(buscaDadosNosContratos(dadosTit))
    elif 'NF' in dadosTit['tipoDoc']:
        return(buscaDadosNasNF(dadosTit))

def formataDadosTeste(dadosteste=[]):
    dicNovo = {
        'buildingId': dadosteste[0]
    }

    if 'NF' in dadosteste[2]:
        posP = dadosteste[2].find('.')
        dicNovo['tipoDoc'] = dadosteste[2][0:posP]
        dicNovo['docNumber'] = dadosteste[2][posP:dadosteste[2].find(' ')]
    if 'OC' in dadosteste[2]:
        dicNovo['tipoDoc'], dicNovo['docNumber'] = dadosteste[2].split('.')
    if 'CT' in dadosteste[2]:
        if 'Med' in dadosteste[2]:
            stexp = dadosteste[2].split(' ')
            dicNovo['tipoDoc'], dicNovo['docNumber'] = stexp[0], stexp[4]
        else:
            dicNovo['tipoDoc'], dicNovo['docNumber'] = dadosteste[2].split('.')
    else:
        dicNovo['tipoDoc'] = dadosteste[2][0:posP]
        dicNovo['docNumber'] = dadosteste[2][posP:dadosteste[2].find(' ')]
    
    return(dicNovo)

# Atualização de Bases
attBases = False

if attBases:
    consultaContratos = consultaContratos(True)
    atualizaBases.contratos(consultaContratos)

    pedidosSienge = consultaPedidos()
    atualizaBases.pedidosCompra(pedidosSienge)

# Carrega a base ajustada
print('Carregando Base Credores')
baseForn = baseCredores()
print('Base Credores Criada')
#Carrega dados de teste, depois validar no fluxo normal
dadosTeste = list(csv.reader(open('nfAprop.csv', encoding='latin-1', mode='r'), delimiter='\t'))


# um documento pode ter várias apropriações e insumos, portanto posso otimizar uma busca colocando obra e tipo de documento para referenciar aqui

def main():

    dadosGerais = []

    for dado in tqdm(dadosTeste):
        print(dado)
        if dado[1] != 'ORÇADO':
            dadoN = formataDadosTeste(dado)

            dadoN['DadosForn'] = achaFornecedor(dadoN)
            dadosGerais.append(dadoN)

    json.dump(dadosGerais, open('dadosTratados.json', mode='w', encoding='utf-8-sig'))


# Organiza base de títulos para uma organização mais eficaz para as apropriações existentes.
bbulk = carregabases.titulosBulk()['data']
baseBulkOrg = {}
repetidos = 0
filtros = [
    'DARF',
    'FP  ',
    'GPS ',
    'FGTS',
    'CAU ',
    'PCT ',
    ]

repetDoc = {}
normDoc = {}
maior = 0

for tit in tqdm(bbulk):
    aprops = tit['buildingsCosts']
    obras = []
    if tit['documentIdentificationId'] not in filtros :
        for ap in aprops:
            if ap['buildingId'] not in obras:
                obras.append(ap['buildingId'])
    if len(obras) == 1:
        titObra = obras[0]
        titTipoDoc = tit['documentIdentificationId']
        numDoc = tit['documentNumber']
        if titObra not in baseBulkOrg:
            baseBulkOrg[titObra] = {
                titTipoDoc: {
                    numDoc: [tit]
                }
            }
        elif titTipoDoc not in baseBulkOrg[titObra]:
            baseBulkOrg[titObra][titTipoDoc] = {
                numDoc: [tit]
            }
        else:
            if numDoc in baseBulkOrg[titObra][titTipoDoc]:
                listaTitExistentes = list(baseBulkOrg[titObra][titTipoDoc][numDoc])
                if len(listaTitExistentes) > maior:
                    maior = len(listaTitExistentes)
                    json.dump(listaTitExistentes, open('baseMaiorParacomparar.json', mode='w', encoding='utf-8-sig'))
                trMatch = False
                for titEx in listaTitExistentes:
                    if tit['billId'] == titEx['billId']:
                        trMatch = True
                    elif aprops == titEx['buildingsCosts']:
                        trMatch = True
                        if titTipoDoc in repetDoc:
                            repetDoc[titTipoDoc] += 1
                        else:
                            repetDoc[titTipoDoc] = 1
                if not trMatch:
                    baseBulkOrg[titObra][titTipoDoc][numDoc].append(tit)
                    if titTipoDoc in normDoc:
                        normDoc[titTipoDoc] += 1
                    else:
                        normDoc[titTipoDoc] = 1                       
            else:
                baseBulkOrg[titObra][titTipoDoc][numDoc] = [tit]
                if titTipoDoc in normDoc:
                    normDoc[titTipoDoc] += 1
                else:
                    normDoc[titTipoDoc] = 1

main()