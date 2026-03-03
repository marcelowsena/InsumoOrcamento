#!/usr/bin/env python3
"""
Sistema de Análise Insumos x Orçamento - V4
Orchestrator principal usando arquitetura funcional modular
VERSÃO INTEGRADA: Inclui títulos + contratos por padrão + processamento completo de APROPRIADOS, PENDENTES e ORÇADOS
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.settings import (
    load_all_configs, validate_api_config, create_directories,
    aplicar_filtros_obras, set_building_units_config,
    print_config_summary
)
from utils.logger import get_main_logger, log_startup, log_processing_summary
from api.api_client import (
    criar_cliente_api, buscar_todas_empresas, processar_obras_em_lotes,
    testar_conexao_api, estatisticas_cache
)
from api.budget_api import buscar_mapeamentos_todas_obras
from api.titulos_api import buscar_titulos_com_filtros
from api.contracts_api import buscar_contratos_workitem, processar_contratos_para_lancamentos
from core.data_processor import (
    processar_todos_resultados, validar_lote_lancamentos,
    agrupar_lancamentos_por_obra, calcular_totais_por_obra,
    gerar_relatorio_processamento, filtrar_lancamentos_por_data,
    enriquecer_lancamentos_com_hierarquia, debug_hierarquia_lancamentos,
    enriquecer_lancamento_completo,
    enriquecer_lancamentos_com_classificacao_abc, enriquecer_lancamentos_com_mes_ano
)
from core.titulos_processor import processar_todos_titulos
from core.aditivos_processor import buscar_aditivos, filtrar_aditivos_por_obras
from core.merge_engine import (
    validar_config_merge, aplicar_merge_obras, aplicar_merge_centros_custo,
    debug_merge_config
)
from core.excel_generator import (
    gerar_excel_completo, gerar_excel_simples, gerar_nome_arquivo
)
from utils.sharepoint import enviar_para_sharepoint


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Sistema Insumos x Orçamento V4 com Títulos e Contratos Integrados',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos de uso:
  python main.py --export-excel                         # Relatório completo (obras + títulos + contratos)
  python main.py --export-excel --simple                # Excel simples (todos os tipos)
  python main.py --export-excel --disable-titulos       # Obras + contratos (sem títulos)
  python main.py --export-excel --disable-contratos     # Obras + títulos (sem contratos)
  python main.py --export-excel --disable-titulos --disable-contratos  # Apenas obras
  python main.py --diagnostico                          # Executar diagnóstico completo
        '''
    )
    
    parser.add_argument('--export-excel', action='store_true',
                       help='Gerar relatório Excel completo')
    parser.add_argument('--simple', action='store_true',
                       help='Gerar Excel simples (apenas lançamentos)')
    parser.add_argument('--test-connection', action='store_true',
                       help='Testar conexão com API')
    parser.add_argument('--cache-stats', action='store_true',
                       help='Mostrar estatísticas do cache')
    parser.add_argument('--config-summary', action='store_true',
                       help='Mostrar resumo das configurações')
    parser.add_argument('--debug-merge', action='store_true',
                       help='Debug da configuração de merge')
    parser.add_argument('--diagnostico', action='store_true',
                       help='Executar diagnóstico completo de fornecedores e contratos')
    
    parser.add_argument('--disable-titulos', action='store_true',
                       help='Desabilitar busca de títulos')
    parser.add_argument('--disable-contratos', action='store_true',
                       help='Desabilitar busca de contratos WORKITEM')
    parser.add_argument('--disable-aditivos', action='store_true',
                       help='Desabilitar busca de aditivos de contratos')
    parser.add_argument('--skip-cache', action='store_true',
                       help='Usar apenas cache existente (não faz novas requisições API)')
    
    parser.add_argument('--filter', default='- Obra',
                       help='Filtro básico de obras (padrão: "- Obra")')
    parser.add_argument('--start-date', help='Data início (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='Data fim (YYYY-MM-DD)')
    parser.add_argument('--bdi', default='0.00', help='BDI percentual (padrão: 0.00)')
    parser.add_argument('--labor-burden', default='0.00', help='Encargos sociais percentual (padrão: 0.00)')
    parser.add_argument('--building-units', help='Building Unit IDs permitidos (ex: 1,2,3)')
    parser.add_argument('--disable-building-unit-filter', action='store_true',
                       help='Desabilitar filtro de Building Units')
    parser.add_argument('--disable-merge', action='store_true',
                       help='Desabilitar merge de obras/centros')
    parser.add_argument('--output-file', help='Nome do arquivo de saída (opcional)')
    
    parser.add_argument('--verbose', '-v', action='store_true', help='Logs detalhados')
    parser.add_argument('--quiet', '-q', action='store_true', help='Apenas erros e resultados')
    
    return parser.parse_args()


def configurar_building_units(args, configs, logger):
    if args.disable_building_unit_filter:
        set_building_units_config(False, [])
        if args.verbose:
            logger.info("Filtro de Building Units desabilitado")
    elif args.building_units:
        try:
            unit_ids = [int(x.strip()) for x in args.building_units.split(',')]
            set_building_units_config(True, unit_ids)
            if args.verbose:
                logger.info(f"Building Units configurados: {unit_ids}")
        except ValueError:
            logger.error("Formato inválido para Building Units. Use números separados por vírgula")
            return False
    else:
        config = configs['building_units']
        if args.verbose:
            logger.info(f"Building Units padrão: filtro={'habilitado' if config['filter_enabled'] else 'desabilitado'}, "
                       f"IDs={config['allowed_ids']}")
    
    return True


def criar_opcoes_relatorio(args, configs):
    default_options = configs['report_options']
    return {
        'startDate': args.start_date or default_options['start_date'],
        'endDate': args.end_date or default_options['end_date'],
        'includeDisbursement': default_options['include_disbursement'],
        'bdi': args.bdi,
        'laborBurden': args.labor_burden
    }


def callback_progresso_simples(current, total, item_name):
    pass


def callback_progresso_verbose(current, total, item_name):
    if current == 1 or current % 10 == 0 or current == total:
        percentual = (current / total * 100) if total > 0 else 0
        print(f"  [{current}/{total}] ({percentual:.1f}%) {item_name}")


def executar_teste_conexao(configs, logger):
    print("Testando conexão com API...")
    
    conectado, mensagem = testar_conexao_api(configs['api'])
    
    if conectado:
        print(f"✅ {mensagem}")
        session = criar_cliente_api(configs)
        sucesso, empresas = buscar_todas_empresas(session, configs['api'])
        
        if sucesso:
            print(f"✅ Empresas acessíveis: {len(empresas)}")
            obras_incluidas, obras_excluidas = aplicar_filtros_obras(empresas, "- Obra")
            print(f"📊 Obras após filtros: {len(obras_incluidas)} incluídas, {len(obras_excluidas)} excluídas")
        else:
            print(f"❌ Erro ao buscar empresas: {empresas}")
    else:
        print(f"❌ {mensagem}")
    
    return conectado


def executar_cache_stats(configs, logger):
    print("📊 Estatísticas do Cache:")
    stats = estatisticas_cache(configs['cache']['directory'])
    print(f"  Total: {stats['total_arquivos']} arquivos, {stats['tamanho_mb']} MB")
    print(f"  Diretório: {configs['cache']['directory']}")


def executar_debug_merge(configs, logger):
    print("🔍 Debug da Configuração de Merge:")
    debug_merge_config(configs['merge'], logger)


def executar_diagnostico(args, configs, logger, bases_tuple):
    print("="*80)
    print("DIAGNÓSTICO COMPLETO - FORNECEDORES E CONTRATOS")
    print("="*80)
    
    if not bases_tuple:
        print("❌ Bases não disponíveis")
        return False
    
    base_bulk_org, base_pedidos, base_contratos, base_fornecedor = bases_tuple
    
    print("✅ Bases inicializadas com sucesso")
    
    print("\n2. Validando estrutura das bases...")
    print(f"  base_fornecedor: {type(base_fornecedor)}, {len(base_fornecedor)} itens")
    print(f"  base_pedidos: {type(base_pedidos)}, {len(base_pedidos)} itens")
    print(f"  base_contratos: {type(base_contratos)}, {len(base_contratos)} itens")
    print(f"  base_bulk_org: {type(base_bulk_org)}, {len(base_bulk_org)} itens")
    
    if base_fornecedor:
        print("\n3. Sample base_fornecedor:")
        items = list(base_fornecedor.items()) if isinstance(base_fornecedor, dict) else []
        for k, v in items[:3]:
            print(f"  {k} (tipo: {type(k)}): {v}")
    
    if base_pedidos:
        print("\n4. Sample base_pedidos:")
        if isinstance(base_pedidos, dict):
            for building_id in list(base_pedidos.keys())[:2]:
                pedidos = base_pedidos[building_id]
                print(f"  Building {building_id} (tipo: {type(building_id)}): {len(pedidos) if isinstance(pedidos, list) else 'N/A'} pedidos")
                if isinstance(pedidos, list) and len(pedidos) > 0:
                    pedido = pedidos[0]
                    print(f"    Pedido: id={pedido.get('id')} (tipo: {type(pedido.get('id'))}), supplierId={pedido.get('supplierId')} (tipo: {type(pedido.get('supplierId'))})")
    
    if base_contratos:
        print("\n5. Sample base_contratos:")
        contratos_list = base_contratos if isinstance(base_contratos, list) else []
        for contrato in contratos_list[:3]:
            print(f"  Contrato: number={contrato.get('contractNumber')} (tipo: {type(contrato.get('contractNumber'))}), supplier={contrato.get('supplierName')}")
    
    if base_bulk_org:
        print("\n6. Sample base_bulk_org:")
        if isinstance(base_bulk_org, dict):
            for building_id in list(base_bulk_org.keys())[:2]:
                dic_obra = base_bulk_org[building_id]
                print(f"  Building {building_id} (tipo: {type(building_id)}): {len(dic_obra) if isinstance(dic_obra, dict) else 'N/A'} tipos")
                if isinstance(dic_obra, dict):
                    for tipo in list(dic_obra.keys())[:2]:
                        dic_tipo = dic_obra[tipo]
                        print(f"    Tipo '{tipo}' (len={len(tipo)}, repr={repr(tipo)}): {len(dic_tipo) if isinstance(dic_tipo, dict) else 'N/A'} documentos")
                        if isinstance(dic_tipo, dict):
                            for num in list(dic_tipo.keys())[:2]:
                                print(f"      {num} (tipo: {type(num)}, repr={repr(num)})")
    
    print("\n7. Buscando contratos da API...")
    try:
        contratos = buscar_contratos_workitem(configs['building_units'], logger)
        print(f"✅ {len(contratos)} contratos encontrados")
        
        if contratos:
            print("\n8. Analisando estrutura de 1 contrato:")
            contrato = contratos[0]
            print(f"  contractNumber: {contrato.get('contractNumber')}")
            print(f"  status: {contrato.get('status')}")
            print(f"  supplierName: {contrato.get('supplierName')}")
            
            if 'itens' in contrato and 'WORKITEM' in contrato['itens']:
                items = contrato['itens']['WORKITEM']
                print(f"  WORKITEM: {len(items)} itens")
                
                if items:
                    item = items[0]
                    print(f"    Item: {item.get('description')}")
                    
                    if 'buildingAppropriations' in item:
                        aprops = item['buildingAppropriations']
                        print(f"    buildingAppropriations: {len(aprops)} appropriations")
                        
                        print("\n9. Validando measurementNumber:")
                        medicoes = set()
                        for i, approp in enumerate(aprops[:5]):
                            med = approp.get('measurementNumber')
                            medicoes.add(med)
                            print(f"      Approp {i}: measurementNumber={med} (tipo: {type(med)})")
                        
                        print(f"    Medições únicas: {sorted([m for m in medicoes if m is not None])}")
            
            print("\n10. Processando contratos para lançamentos...")
            lancamentos = processar_contratos_para_lancamentos(contratos, configs['building_units'], logger)
            print(f"✅ {len(lancamentos)} lançamentos gerados")
            
            if lancamentos:
                print("\n11. Análise de lançamentos gerados:")
                contratos_map = {}
                for lanc in lancamentos:
                    doc = lanc.get('documento_origem', '')
                    if doc.startswith('CT'):
                        if doc not in contratos_map:
                            contratos_map[doc] = []
                        contratos_map[doc].append(lanc.get('numero_medicao'))
                
                print(f"  Contratos únicos: {len(contratos_map)}")
                for doc, meds in list(contratos_map.items())[:5]:
                    meds_validas = [m for m in meds if m]
                    print(f"    {doc}: {len(meds)} lançamentos, medições: {set(meds_validas)}")
                
                print("\n12. Sample de 3 lançamentos:")
                for i, lanc in enumerate(lancamentos[:3]):
                    print(f"  Lançamento {i}:")
                    print(f"    documento_origem: {lanc.get('documento_origem')}")
                    print(f"    numero_medicao: {lanc.get('numero_medicao')} (tipo: {type(lanc.get('numero_medicao'))})")
                    print(f"    fornecedor: {lanc.get('fornecedor')}")
                    print(f"    tipo_documento: {lanc.get('tipo_documento')}")
                    print(f"    classificacao: {lanc.get('classificacao')}")
    
    except Exception as e:
        print(f"❌ Erro ao processar contratos: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("FIM DO DIAGNÓSTICO")
    print("="*80)
    
    return True


def print_progress(message, verbose=False):
    if verbose:
        print(message)


def executar_export_excel(args, configs, logger):
    inicio_processamento = time.time()
    verbose = args.verbose

    print("🚀 Iniciando geração de relatório Excel...")

    # Configurar modo skip-cache
    if args.skip_cache:
        configs['cache']['skip_update'] = True
        print("⚡ Modo --skip-cache: usando apenas cache existente (sem requisições API)")
    else:
        configs['cache']['skip_update'] = False

    titulos_habilitados = not args.disable_titulos
    contratos_habilitados = not args.disable_contratos
    aditivos_habilitados = not args.disable_aditivos
    fontes = []
    if titulos_habilitados: fontes.append("títulos")
    if contratos_habilitados: fontes.append("contratos")
    if aditivos_habilitados: fontes.append("aditivos")
    fontes_str = " + " + " + ".join(fontes) if fontes else ""
    print(f"📋 Fontes: obras{fontes_str}")

    opcoes = criar_opcoes_relatorio(args, configs)
    session = criar_cliente_api(configs)

    from src.core.data_processor import inicializar_bases_fornecedor

    # Carregar bases de fornecedor
    bases_tuple = None
    try:
        print_progress("📦 Inicializando bases de fornecedor...", verbose)
        bases_tuple = inicializar_bases_fornecedor(logger)
        
        if bases_tuple:
            print("✓ Bases de fornecedor carregadas")
            base_bulk_org, base_pedidos, base_contratos, base_fornecedor = bases_tuple
            
            if verbose:
                print(f"  Fornecedores: {len(base_fornecedor)}")
                print(f"  Pedidos: {len(base_pedidos)} obras")
                print(f"  Contratos: {len(base_contratos)}")
                print(f"  Títulos: {len(base_bulk_org)} obras")
        else:
            print("⚠️ Fornecedor não disponível - continuando sem")
    except Exception as e:
        logger.warning(f"Fornecedor não disponível: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        bases_tuple = None

    print_progress("🔍 Buscando empresas...", verbose)
    sucesso, empresas = buscar_todas_empresas(session, configs['api'])
    if not sucesso:
        logger.error(f"Erro ao buscar empresas: {empresas}")
        return False
    
    print_progress("🔧 Aplicando filtros...", verbose)
    obras_incluidas, obras_excluidas = aplicar_filtros_obras(empresas, args.filter)
    print(f"📊 Obras: {len(obras_incluidas)} selecionadas")
    
    if not obras_incluidas:
        print("❌ Nenhuma obra encontrada após aplicar filtros")
        return False
    
    print("⚙️ Processando obras...")
    callback = callback_progresso_verbose if verbose else callback_progresso_simples
    resultados = processar_obras_em_lotes(session, obras_incluidas, opcoes, configs['api'], configs['cache'], callback)
    
    lancamentos_contratos = []
    if contratos_habilitados:
        print_progress("📋 Buscando contratos WORKITEM...", verbose)
        try:
            contratos = buscar_contratos_workitem(configs['building_units'], logger)
            if contratos:
                print_progress(f"  {len(contratos)} contratos encontrados", verbose)
                lancamentos_contratos = processar_contratos_para_lancamentos(contratos, configs['building_units'], logger)
                print(f"📋 Contratos: {len(lancamentos_contratos)} lançamentos")
                
                if verbose and lancamentos_contratos:
                    contratos_map = {}
                    for lanc in lancamentos_contratos:
                        doc = lanc.get('documento_origem', '')
                        if doc not in contratos_map:
                            contratos_map[doc] = []
                        contratos_map[doc].append(lanc.get('numero_medicao'))
                    
                    print(f"  Contratos únicos processados: {len(contratos_map)}")
                    for doc, meds in list(contratos_map.items())[:3]:
                        meds_validas = [m for m in meds if m]
                        print(f"    {doc}: {len(meds)} lançamentos, medições: {set(meds_validas)}")
        except Exception as e:
            logger.error(f"Erro ao processar contratos: {str(e)}")
            print(f"⚠️ Erro nos contratos: {str(e)}")
            if verbose:
                import traceback
                traceback.print_exc()

    if not args.disable_merge and configs['merge'].get('habilitado', False):
        print_progress("🔄 Aplicando merge inteligente...", verbose)
        
        valido, erros = validar_config_merge(configs['merge'], logger)
        if not valido:
            print(f"❌ Configuração de merge inválida: {len(erros)} erros")
            return False
        
        resultados = aplicar_merge_obras(resultados, configs['merge'], logger)
        todos_lancamentos = processar_todos_resultados(resultados, configs['building_units'], logger)
        todos_lancamentos = aplicar_merge_centros_custo(todos_lancamentos, configs['merge'], logger)
    else:
        print_progress("📊 Extraindo lançamentos...", verbose)
        todos_lancamentos = processar_todos_resultados(resultados, configs['building_units'], logger)

    from src.core.validacao_building_ids import validar_obras_disponiveis, diagnosticar_fornecedores
    
    inicializar_bases_fornecedor(logger)

    from src.core.validacao_building_ids import validar_obras_disponiveis, diagnosticar_fornecedores
    
    # Enriquecimento com fornecedores
    if bases_tuple:
        print_progress("🔍 Validando building_ids das obras...", verbose)
        
        base_bulk_org, base_pedidos, base_contratos, base_fornecedor = bases_tuple
        
        if base_pedidos and base_bulk_org:
            todos_lancamentos, stats = validar_obras_disponiveis(
                todos_lancamentos, 
                base_pedidos, 
                base_bulk_org, 
                logger
            )
            
            if stats['obras_invalidas'] > 0:
                print(f"⚠️ {stats['lancamentos_invalidos']} lançamentos de obras sem base de fornecedor (mantidos)")
                if verbose:
                    print(f"  Obras sem base: {stats['obras_invalidas']}")
                    print(f"  Obras com base: {stats['obras_validas']}")
        
        print_progress("💼 Enriquecendo com fornecedores...", verbose)

        todos_lancamentos = [enriquecer_lancamento_completo(l, bases_tuple, logger) for l in todos_lancamentos]
        
        com_fornecedor = sum(1 for l in todos_lancamentos if l.get('fornecedor'))
        percentual = (com_fornecedor / len(todos_lancamentos) * 100) if todos_lancamentos else 0
        print(f"✓ Fornecedores: {com_fornecedor}/{len(todos_lancamentos)} ({percentual:.1f}%)")
        
        if verbose:
            diagnosticar_fornecedores(todos_lancamentos, logger)
    else:
        print("⚠️ Pula enriquecimento dos dados...")    

    if titulos_habilitados:
        print_progress("💰 Processando títulos...", verbose)
        try:
            titulos = buscar_titulos_com_filtros(configs['paths']['config'], logger)
            if titulos:
                lancamentos_titulos = processar_todos_titulos(titulos, configs['building_units'], logger)
                if lancamentos_titulos:
                    obras_ids_permitidos = {obra['id'] for obra in obras_incluidas}
                    lancamentos_titulos = [l for l in lancamentos_titulos if l.get('building_id') in obras_ids_permitidos]
                    
                    if not args.disable_merge and configs['merge'].get('habilitado', False):
                        lancamentos_titulos = aplicar_merge_centros_custo(lancamentos_titulos, configs['merge'], logger)
                    
                    todos_lancamentos.extend(lancamentos_titulos)
                    print(f"💰 Títulos: {len(lancamentos_titulos)} lançamentos")
        except Exception as e:
            logger.error(f"Erro ao processar títulos: {str(e)}")
            print(f"⚠️ Erro nos títulos: {str(e)}")
    
    if contratos_habilitados and lancamentos_contratos:
        print_progress("📋 Integrando contratos...", verbose)

        obras_ids_permitidos = {obra['id'] for obra in obras_incluidas}
        lancamentos_contratos = [l for l in lancamentos_contratos if l.get('building_id') in obras_ids_permitidos]

        if lancamentos_contratos:
            if not args.disable_merge and configs['merge'].get('habilitado', False):
                lancamentos_contratos = aplicar_merge_centros_custo(lancamentos_contratos, configs['merge'], logger)

            todos_lancamentos.extend(lancamentos_contratos)
            print_progress(f"✓ {len(lancamentos_contratos)} lançamentos de contratos integrados", verbose)

    # Processar aditivos
    if aditivos_habilitados:
        print_progress("📑 Buscando aditivos de contratos...", verbose)
        try:
            lancamentos_aditivos = buscar_aditivos(configs['paths']['config'], logger)

            if lancamentos_aditivos:
                obras_ids_permitidos = {obra['id'] for obra in obras_incluidas}
                lancamentos_aditivos = filtrar_aditivos_por_obras(lancamentos_aditivos, obras_ids_permitidos)

                if lancamentos_aditivos:
                    if not args.disable_merge and configs['merge'].get('habilitado', False):
                        lancamentos_aditivos = aplicar_merge_centros_custo(lancamentos_aditivos, configs['merge'], logger)

                    todos_lancamentos.extend(lancamentos_aditivos)
                    print(f"📑 Aditivos: {len(lancamentos_aditivos)} lançamentos")
        except Exception as e:
            logger.error(f"Erro ao processar aditivos: {str(e)}")
            print(f"⚠️ Erro nos aditivos: {str(e)}")

    if not todos_lancamentos:
        print("❌ Nenhum lançamento encontrado")
        return False
    
    tipos_count = {}
    fontes_count = {'OBRA': 0, 'TITULO': 0, 'CONTRATO': 0, 'ADITIVO': 0}
    for lancamento in todos_lancamentos:
        tipo = lancamento.get('tipo_documento', 'DESCONHECIDO')
        tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
        fonte = lancamento.get('fonte', 'OBRA')
        fontes_count[fonte] = fontes_count.get(fonte, 0) + 1

    print(f"📊 Lançamentos: {len(todos_lancamentos)} total ({tipos_count.get('APROPRIADO', 0)} apropriados, {tipos_count.get('PENDENTE', 0)} pendentes, {tipos_count.get('ORCADO', 0)} orçados)")
    if verbose:
        print(f"📊 Por fonte: {fontes_count['OBRA']} obras, {fontes_count['TITULO']} títulos, {fontes_count['CONTRATO']} contratos, {fontes_count['ADITIVO']} aditivos")
    
    print_progress("✅ Validando lançamentos...", verbose)
    lancamentos_validos, lancamentos_erro = validar_lote_lancamentos(todos_lancamentos, logger)
    if lancamentos_erro:
        print_progress(f"⚠️ {len(lancamentos_erro)} lançamentos com erro ignorados", verbose)
    
    print_progress("🗂️ Buscando mapeamentos WBS...", verbose)
    obras_finais = list(set(l['building_id'] for l in lancamentos_validos))
    obras_para_wbs = [o for o in obras_incluidas if o['id'] in obras_finais]
    
    callback_wbs = callback_progresso_verbose if verbose else callback_progresso_simples
    mapeamentos_wbs = buscar_mapeamentos_todas_obras(session, obras_para_wbs, configs['api'], configs['cache'], logger, callback_wbs)
    
    obras_com_wbs = len([m for m in mapeamentos_wbs.values() if m])
    print_progress(f"📊 WBS: {obras_com_wbs}/{len(obras_para_wbs)} obras com orçamento", verbose)
    
    print_progress("🗂️ Enriquecendo com hierarquia WBS...", verbose)
    lancamentos_validos = enriquecer_lancamentos_com_hierarquia(lancamentos_validos, mapeamentos_wbs, logger)

    if verbose:
        debug_hierarquia_lancamentos(lancamentos_validos, logger)

    # Enriquecer com classificação ABC
    print_progress("🏷️ Aplicando classificação ABC...", verbose)
    lancamentos_validos = enriquecer_lancamentos_com_classificacao_abc(
        lancamentos_validos, configs['classificacao_abc'], logger
    )

    # Enriquecer com mês e ano da apropriação
    print_progress("📅 Extraindo mês/ano de apropriação...", verbose)
    lancamentos_validos = enriquecer_lancamentos_com_mes_ano(lancamentos_validos, logger)

    if args.start_date or args.end_date:
        print_progress("📅 Aplicando filtro de data...", verbose)
        lancamentos_validos = filtrar_lancamentos_por_data(lancamentos_validos, args.start_date, args.end_date)
        print_progress(f"📊 Após filtro de data: {len(lancamentos_validos)} lançamentos", verbose)
    
    print_progress("📈 Gerando análises...", verbose)
    grupos_obras = agrupar_lancamentos_por_obra(lancamentos_validos)
    totais_obras = calcular_totais_por_obra(grupos_obras)
    relatorio_processamento = gerar_relatorio_processamento(lancamentos_validos, totais_obras, logger)
    
    print("📊 Gerando arquivo Excel...")
    
    if args.output_file:
        nome_arquivo = args.output_file
        if not nome_arquivo.endswith('.xlsx'):
            nome_arquivo += '.xlsx'
    else:
        nome_arquivo = gerar_nome_arquivo()
    
    output_path = configs['paths']['reports'] / nome_arquivo
    
    try:
        if args.simple:
            arquivo_gerado = gerar_excel_simples(lancamentos_validos, output_path, logger)
        else:
            arquivo_gerado = gerar_excel_completo(lancamentos_validos, totais_obras, relatorio_processamento, configs, output_path, logger)
        
        tempo_total = time.time() - inicio_processamento
        tamanho_mb = arquivo_gerado.stat().st_size / (1024 * 1024)
        
        print("\n" + "="*60)
        print("✅ RELATÓRIO GERADO COM SUCESSO!")
        print("="*60)
        print(f"📁 Arquivo: {arquivo_gerado.name}")
        print(f"📊 Registros: {len(lancamentos_validos):,}")
        print(f"🗂️ Obras: {len(grupos_obras)} ({obras_com_wbs} com WBS)")
        print(f"💰 Valor Total: R$ {relatorio_processamento['resumo_geral']['valor_total']:,.2f}")
        print(f"📦 Tamanho: {tamanho_mb:.2f} MB")
        print(f"⏱️ Tempo: {tempo_total:.1f}s")
        
        if verbose:
            print(f"📊 Fontes: {fontes_count['OBRA']} obras, {fontes_count['TITULO']} títulos, {fontes_count['CONTRATO']} contratos")
            if 'tipos_documento' in relatorio_processamento:
                tipos = relatorio_processamento['tipos_documento']
                print(f"📋 Detalhes: {tipos.get('APROPRIADO', {}).get('count', 0)} apropriados, "
                     f"{tipos.get('PENDENTE', {}).get('count', 0)} pendentes, "
                     f"{tipos.get('ORCADO', {}).get('count', 0)} orçados")
        
        print("="*60)

        # Enviar para SharePoint
        enviar_para_sharepoint(arquivo_gerado)

        log_processing_summary(logger, len(obras_incluidas), len(resultados),
                             len([r for r in resultados if 'erro' not in r.get('relatorio_bruto', {})]), tempo_total)

        return True
        
    except Exception as e:
        logger.error(f"Erro ao gerar Excel: {str(e)}")
        print(f"❌ Erro ao gerar Excel: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    args = parse_arguments()
    
    try:
        configs = load_all_configs()
        create_directories()
        
        if args.quiet:
            level = 'ERROR'
        elif args.verbose:
            level = 'DEBUG'
        else:
            level = 'INFO'
        
        configs['cache']['directory'].parent.mkdir(exist_ok=True)
        logger = get_main_logger(configs)

        log_startup(logger, configs)
        
        if not args.config_summary and not args.diagnostico:
            valido, erros = validate_api_config()
            if not valido:
                print("❌ ERROS DE CONFIGURAÇÃO:")
                for erro in erros:
                    print(f"  - {erro}")
                logger.error(f"Configuração inválida: {erros}")
                return 1
        
        if not configurar_building_units(args, configs, logger):
            return 1
        
        if args.config_summary:
            print_config_summary()
        elif args.test_connection:
            return 0 if executar_teste_conexao(configs, logger) else 1
        elif args.cache_stats:
            executar_cache_stats(configs, logger)
        elif args.debug_merge:
            executar_debug_merge(configs, logger)
        elif args.diagnostico:
            return 0 if executar_diagnostico(args, configs, logger, bases_tuple) else 1
        elif args.export_excel:
            return 0 if executar_export_excel(args, configs, logger) else 1
        else:
            print("Sistema Insumos x Orçamento V4 com Títulos e Contratos Integrados")
            print("Use --help para ver todas as opções disponíveis")
            print("\nAções principais:")
            print("  --export-excel                     Gerar relatório Excel (obras + títulos + contratos)")
            print("  --export-excel --disable-titulos   Gerar obras + contratos (sem títulos)")
            print("  --export-excel --disable-contratos Gerar obras + títulos (sem contratos)")
            print("  --diagnostico                      Executar diagnóstico completo")
            print("  --test-connection                  Testar conexão API")
            print("  --config-summary                   Mostrar configurações")
            return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Processo interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ Erro inesperado: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())