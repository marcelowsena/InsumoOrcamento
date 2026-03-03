import json
import os

# Diretório onde está este script (siengeAPI/bases/)
BASE_DIR = os.path.dirname(__file__)

def _salvar_json(nome_arquivo, dados, mensagem):
    caminho = os.path.join(BASE_DIR, nome_arquivo)
    with open(caminho, mode='w', encoding='utf-8') as arquivo:
        json.dump(dados, arquivo)
    print(mensagem)

def itensContratos(dados):
    _salvar_json('baseContratosItens.json', dados, 'Base - Contratos e Itens - Atualizada')

def contratos(dados):
    _salvar_json('baseInContratosPreco.json', dados, 'Base - Contratos - Atualizada')

def credor(dados):
    _salvar_json('baseInCredor.json', dados, 'Base - Credores - Atualizada')

def NFEs(dados):
    _salvar_json('nfBase.json', dados, 'Base - NFEs - Atualizada')

def NFEsComEmitPgt(dados):
    _salvar_json('baseInNf.json', dados, 'Base - NFEs Emit e Pgt - Atualizada')

def pedidosCompra(dados):
    _salvar_json('basePedidos.json', dados, 'Base - Pedido de Compra - Atualizada')

def titulosContasAPagar(dados):
    _salvar_json('titBase.json', dados, 'Base - Titulos - Atualizada')

def bulkTitulos(dados):
    _salvar_json('bulkTitulos.json', dados, 'Base - Titulos Bulk - Atualizada')

def obras(dados):
    _salvar_json('enterprises.json', dados, 'Base - Obras - Atualizada')

def itensSC(dados):
    _salvar_json('itensSC.json', dados, 'Base - SC - Atualizada')
