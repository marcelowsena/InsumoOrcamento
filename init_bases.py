#!/usr/bin/env python3
"""
Inicializa as bases de dados necessárias para enriquecimento de fornecedores.
Deve ser executado antes do main.py quando as bases não existem (ex: GitHub Actions).
"""

import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BASES_PATH = Path(__file__).parent / 'siengeAPI' / 'bases'

ARQUIVOS_NECESSARIOS = [
    BASES_PATH / 'basePedidos.json',
    BASES_PATH / 'bulkTitulos.json',
    BASES_PATH / 'baseInContratosPreco.json',
    # Lida por src/api/contracts_api.py (contratos WORKITEM com itens/apropriações)
    BASES_PATH / 'baseContratosItens.json',
]

# Unidades construtivas consultadas por contrato (mesma regra de
# siengeAPI.atualizacaoBasesSienge.atualizaContratos)
BUILDING_UNITS_IDS = list(range(1, 9))
OBRA_MULTI_UNIDADES = 2014


def bases_existem():
    return all(f.exists() for f in ARQUIVOS_NECESSARIOS)


def gerar_itens_contratos(contratos):
    """
    Monta a base de itens de contratos no formato esperado por
    src/api/contracts_api.py: cada contrato recebe 'itens' = {buildingUnitId: [itens]}.

    Diferente de atualizaContratos(), consulta apenas contratos WORKITEM (os únicos
    usados no relatório) e não consulta caução (não usada), reduzindo as chamadas à API.
    """
    import copy
    from siengeAPI.consultas.API.origem import consultaItensContratos

    workitem = [copy.deepcopy(c) for c in contratos if c.get('itemType') == 'WORKITEM']
    print(f"Contratos WORKITEM: {len(workitem)} de {len(contratos)}")

    from collections import Counter

    falhas = 0
    # Formatos de resposta inesperados (só tipo/chaves, sem conteúdo: o log é público)
    respostas_inesperadas = Counter()
    for i, c in enumerate(workitem, start=1):
        c['itens'] = {}
        try:
            obra = c['buildings'][0]['buildingId']
            for buid in BUILDING_UNITS_IDS:
                itens = consultaItensContratos(c, buid)
                if isinstance(itens, list):
                    c['itens'][buid] = itens
                    if obra != OBRA_MULTI_UNIDADES:
                        break
                elif isinstance(itens, dict) and 'status' in itens:
                    # Unidade construtiva não existe no contrato: tenta a próxima
                    continue
                else:
                    # Qualquer outra coisa (ex.: mensagem de erro) não é lista de itens;
                    # antes era gravada na base e quebrava o processamento no main.py
                    chaves = sorted(itens.keys()) if isinstance(itens, dict) else []
                    raise ValueError(f"resposta inesperada {type(itens).__name__} {chaves}")
        except Exception as e:
            falhas += 1
            c['itens'] = {}
            respostas_inesperadas[str(e)[:120]] += 1
        if i % 200 == 0:
            print(f"  {i}/{len(workitem)} contratos processados")

    print(f"Itens de contratos: {len(workitem) - falhas} ok, {falhas} com falha")
    for motivo, qtd in respostas_inesperadas.most_common(10):
        print(f"  Falha ({qtd}x): {motivo}")
    # Muitas falhas indicam problema na API: melhor falhar o job do que gerar relatório incompleto
    if workitem and falhas > len(workitem) * 0.1:
        raise RuntimeError(f"{falhas} de {len(workitem)} contratos falharam ao consultar itens")
    return workitem


def gerar_bases():
    from siengeAPI.consultas.API.origem import (
        consultaPedidos, bulktitulos, consultaContratos
    )
    from siengeAPI.bases import atualizaBases as ab

    print("Gerando base de pedidos de compra...")
    pedidos = consultaPedidos()
    ab.pedidosCompra(pedidos)

    print("Gerando base de títulos bulk...")
    titulos = bulktitulos()
    ab.bulkTitulos(titulos)

    print("Gerando base de contratos...")
    contratos = consultaContratos(basedepreco=True)
    ab.contratos(contratos)

    print("Gerando base de itens de contratos (WORKITEM)...")
    ab.itensContratos(gerar_itens_contratos(contratos))

    print("Bases geradas com sucesso.")


if __name__ == '__main__':
    if bases_existem():
        print("Bases já existem, pulando geração.")
        sys.exit(0)

    print("Bases não encontradas. Gerando via API Sienge...")
    try:
        gerar_bases()
    except Exception as e:
        print(f"Erro ao gerar bases: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
