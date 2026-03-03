from .API.consultaapi import consultaAPI
from .API.origem import formataData
import datetime

def consultaNFES(dataIn = datetime.date(2020, 1, 1)):
        
    dataFin = datetime.date.today()

    dataInFormatted = formataData(dataIn)
    dataFinFormatted = formataData(dataFin)

    nfeAPI = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/v1/nfes',
        '?startDate=': dataInFormatted,
        '&endDate=': dataFinFormatted,
        '&limit=': 200,
        '&offset=':0
    }
    
    return(consultaAPI(nfeAPI))

def consultaNFNumerico(num):
    NFNumAPI = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/v1/purchase-invoices/',
        '': str(num)
    }

    return(consultaAPI(NFNumAPI))

def consultaTitulos():
        
    dataIn = datetime.date(2020, 1, 1)
    dataFin = datetime.date.today()

    dataInFormatted = formataData(dataIn)
    dataFinFormatted = formataData(dataFin)

    titulosAPI = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/v1/bills',
        '?startDate=': dataInFormatted,
        '&endDate=': dataFinFormatted,
        '&limit=': 200,
        '&offset=':0
    }
    
    return(consultaAPI(titulosAPI))

def consultaEmitDestNF(akey):

    nfeAPI = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/v1/nfes/',
        '': str(akey),
        '/issuers-recipients' : ''
    }
    
    return(consultaAPI(nfeAPI))

def consultaPgtsNFE(akey):
        
    titulosAPI = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/v1/nfes/',
        '': str(akey),
        '/payments?' : '',
        'limit=': 200,
        '&offset=':0
    }
    
    return(consultaAPI(titulosAPI))

def consultaAdicionalNFE(akey):

    emit = consultaEmitDestNF(akey)
    pgts = consultaPgtsNFE(akey)

    dicdados = {
        'emitDest': emit,
        'pagamentos': pgts
    }

    return(dicdados)