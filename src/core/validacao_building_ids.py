"""
Validação de Building IDs
Valida se os lançamentos têm building_ids disponíveis nas bases de fornecedor

MODO WARNING: Apenas alerta sobre obras sem base, mas NÃO remove lançamentos.
Para reverter ao comportamento anterior (remover lançamentos), altere MODO_WARNING para False.
"""

# CONFIGURAÇÃO: True = apenas warning, False = remove lançamentos inválidos
MODO_WARNING = True


def validar_obras_disponiveis(lancamentos, base_pedidos, base_bulk_org, logger):
    if not base_pedidos and not base_bulk_org:
        return lancamentos, {
            'obras_validas': 0,
            'obras_invalidas': 0,
            'lancamentos_invalidos': 0
        }

    obras_validas = set()
    if base_pedidos:
        obras_validas.update(base_pedidos.keys())
    if base_bulk_org:
        obras_validas.update(base_bulk_org.keys())

    lancamentos_validos = []
    lancamentos_sem_base = 0
    obras_sem_base = set()

    for lanc in lancamentos:
        building_id = lanc.get('building_id')

        if building_id not in obras_validas:
            lancamentos_sem_base += 1
            obras_sem_base.add(building_id)

        # MODO WARNING: mantém todos os lançamentos
        # MODO ORIGINAL: só adiciona se building_id válido
        if MODO_WARNING or building_id in obras_validas:
            lancamentos_validos.append(lanc)

    if obras_sem_base:
        logger.warning(f"Obras sem bases de fornecedor (mantidas): {sorted(obras_sem_base)[:10]}")
        if lancamentos_sem_base > 0:
            logger.warning(f"Total de {lancamentos_sem_base} lançamentos de obras sem base de fornecedor")

    return lancamentos_validos, {
        'obras_validas': len(obras_validas),
        'obras_invalidas': len(obras_sem_base),
        'lancamentos_invalidos': lancamentos_sem_base
    }


def diagnosticar_fornecedores(lancamentos, logger):
    por_tipo_doc = {}
    
    for lanc in lancamentos:
        doc = lanc.get('documento_origem', '')
        tipo = doc.split('.')[0] if '.' in doc else 'DESCONHECIDO'
        
        if tipo not in por_tipo_doc:
            por_tipo_doc[tipo] = {'total': 0, 'com_fornecedor': 0}
        
        por_tipo_doc[tipo]['total'] += 1
        if lanc.get('fornecedor'):
            por_tipo_doc[tipo]['com_fornecedor'] += 1
    
    logger.info("Diagnóstico de fornecedores por tipo de documento:")
    for tipo, stats in sorted(por_tipo_doc.items()):
        percentual = (stats['com_fornecedor'] / stats['total'] * 100) if stats['total'] > 0 else 0
        logger.info(f"  {tipo}: {stats['com_fornecedor']}/{stats['total']} ({percentual:.1f}%)")