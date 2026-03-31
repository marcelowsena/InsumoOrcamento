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
]


def bases_existem():
    return all(f.exists() for f in ARQUIVOS_NECESSARIOS)


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
