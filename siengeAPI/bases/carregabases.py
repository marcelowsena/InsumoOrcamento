import json
from pathlib import Path

def _get_bases_path():
    """
    Encontra o caminho absoluto da pasta bases
    """
    # Caminho do arquivo atual
    current_file = Path(__file__)
    
    # A pasta bases deve estar no mesmo diretório que este arquivo
    bases_path = current_file.parent / 'bases'
    
    if bases_path.exists():
        return bases_path
    
    # Se não encontrou, procurar na pasta pai
    bases_path = current_file.parent.parent / 'bases'
    if bases_path.exists():
        return bases_path
    
    # Último recurso: usar caminho relativo mesmo
    return Path('bases')

def itensContratos():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'baseContratosItens.json'
    with open(arquivo_path, mode='r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

def contratos():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'baseInContratosPreco.json'
    with open(arquivo_path, mode='r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

def credor():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'baseInCredor.json'
    with open(arquivo_path, mode='r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

def NFEs():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'nfBase.json'
    with open(arquivo_path, mode='r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

def NFEsComEmitPgt():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'baseInNf.json'
    with open(arquivo_path, mode='r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

def pedidosCompra():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'basePedidos.json'
    with open(arquivo_path, mode='r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

def titulosContasAPagar():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'titBase.json'
    with open(arquivo_path, mode='r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

def titulosBulk():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'bulkTitulos.json'
    with open(arquivo_path, mode='r', encoding='utf-8-sig') as arquivo:
        return json.load(arquivo)

def obras():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'enterprises.json'
    with open(arquivo_path, mode='r', encoding='utf-8-sig') as arquivo:
        return json.load(arquivo)

def itensSC():
    bases_path = _get_bases_path()
    arquivo_path = bases_path / 'itensSC.json'
    with open(arquivo_path, mode='r', encoding='utf-8-sig') as arquivo:
        return json.load(arquivo)