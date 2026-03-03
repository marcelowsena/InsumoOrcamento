from .bases import carregabases as cb
from .bases import atualizaBases as ab
import datetime
from . import consultas
from progresso.logProgresso import monitoraProgresso

'''
baseContratosItens - ok
baseInContratos - ok
baseInCredor - ok
baseInNf - ok
basePedidos - ok
nfBase - ok
titBase
'''

def atualizaPedidosDeCompra(): # OK
    pedidosSienge = consultas.API.origem.consultaPedidos()
    ab.pedidosCompra(pedidosSienge)

def atualizaBaseNF(): # OK
    dataCorte = datetime.datetime.today()-datetime.timedelta(days = 30)
    ultimaConsulta = consultas.nf.consultaNFES(dataCorte)
    baseExistente = cb.NFEs()
    contagem = 0
    for nfe in ultimaConsulta:
        if nfe not in baseExistente:
            baseExistente.append(nfe)
            contagem += 1
    print('Qtd nfs trazidas sienge', len(ultimaConsulta))
    print('Contagem Loop', contagem)
    ab.NFEs(baseExistente)

def atualizaEmitPgtNFE(numconsultas=500):
    '''
    Base muito desatualizada, função provavelmente funciona mas preciso testar de noite
    '''

    baseNFE = cb.NFEs()
    baseEmitPgt = cb.NFEsComEmitPgt()

    chavesAConsultar = []
    chavesExistentes = 0
    for nf in baseNFE:
        chaveNF = nf['chaveAcessoNota']
        if chaveNF not in baseEmitPgt:
            chavesAConsultar.append(chaveNF)
        else:
            chavesExistentes += 1

    print(len(chavesAConsultar), 'chaves a consultar!')
    print(chavesExistentes, 'chaves existentes!')

    inicio = datetime.datetime.now()
    nconsult = 0
    if len(chavesAConsultar) < numconsultas:
        numconsultas = len(chavesAConsultar)

    while nconsult < numconsultas:
        chaveNF = chavesAConsultar[nconsult]
        dadosEmitPgt = consultas.nf.consultaAdicionalNFE(chaveNF)
        baseEmitPgt[chaveNF] = dadosEmitPgt
        nconsult += 1
        monitoraProgresso(inicio, numconsultas, nconsult, 20, 'Emit Pgt NFE')
    
    ab.NFEsComEmitPgt(baseEmitPgt)

def atualizaContratos(): #OK
    consultaContratos = consultas.API.origem.consultaContratos(True)
    ab.contratos(consultaContratos)

    buildingUnitsId = list(range(1, 9))

    inicio = datetime.datetime.now()
    contagem = 0
    for c in consultaContratos:

        obra = c['buildings'][0]['buildingId']
        caucao = consultas.API.origem.consultaCaucao(c)
        c['caucao'] = caucao
        if 'itens' not in c:
            c['itens'] = {}
            for buid in buildingUnitsId:    
                consultaItens = consultas.API.origem.consultaItensContratos(c, buid)
                if 'status' not in consultaItens:
                    c['itens'][buid] = consultaItens
                    if obra != 2014:
                        break
        contagem += 1
        monitoraProgresso(inicio, len(consultaContratos), contagem, 20, 'Contratos')

    ab.itensContratos(consultaContratos)

def atualizaTitulos(): #ok
    titulosSienge = consultas.nf.consultaTitulos()
    ab.titulosContasAPagar(titulosSienge)

def atualizaCredores():
    ab.credor(consultas.credores.importaCredores())

def atualizaBulkTitulos():
    baseBulk = consultas.API.origem.bulktitulos()
    ab.bulkTitulos(baseBulk)

def atualizaObras():
    baseObras = consultas.API.origem.consultaObras()
    ab.obras(baseObras)