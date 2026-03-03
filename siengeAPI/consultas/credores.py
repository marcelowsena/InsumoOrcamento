from .API.consultaapi import consultaAPI
from .API.origem import formataData

def importaCredores():
    credoresAPI = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/v1/creditors?',
        '&limit=': 200,
        '&offset=':0
    }    

    return(consultaAPI(credoresAPI))

def consultaCredor(credor):
    credoresAPI = {
        'raiz': 'https://api.sienge.com.br/trust/public/api/v1/creditors?',
        '': str(credor)
    }    
    
    return(consultaAPI(credoresAPI))

def baseCredores():
    dicNovo = {}
    baseAntiga = importaCredores()
    for credor in baseAntiga:
        dicNovo[credor['id']] = credor['name']
    return(dicNovo)