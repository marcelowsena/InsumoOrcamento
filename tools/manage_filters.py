#!/usr/bin/env python3
"""
Gerenciador de Filtros de Obras V4 - Sistema Insumos x Orçamento
Interface moderna para configuração de filtros usando módulos V4
"""

import sys
from pathlib import Path

# Adicionar src ao path se necessário
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config.settings import (
    load_filtros_obras, save_filtros_obras, create_default_filtros,
    aplicar_filtros_obras, load_all_configs
)
from src.utils.logger import get_main_logger
from src.api.api_client import criar_cliente_api, buscar_todas_empresas


def mostrar_configuracao_atual(logger):
    """Mostra configuração atual de filtros"""
    filtros = load_filtros_obras()
    
    print("\n📋 CONFIGURAÇÃO ATUAL DE FILTROS")
    print("="*60)
    print(f"Modo: {filtros.get('modo', 'excluir').upper()}")
    
    if filtros.get('modo') == 'excluir':
        print("  ℹ️  As obras listadas serão IGNORADAS")
    else:
        print("  ℹ️  Apenas as obras listadas serão PROCESSADAS")
    
    # Filtros por ID
    ids_filtro = filtros['filtros']['por_id'].get('valores', [])
    print(f"\n🔢 FILTROS POR ID ({len(ids_filtro)}):")
    if ids_filtro:
        for i, obra_id in enumerate(sorted(ids_filtro), 1):
            if i <= 10:  # Mostrar apenas primeiros 10
                print(f"   {i:2d}. {obra_id}")
            elif i == 11:
                print(f"   ... e mais {len(ids_filtro) - 10} obras")
                break
    else:
        print("   Nenhum filtro por ID configurado")
    
    # Filtros por nome
    strings_filtro = filtros['filtros']['por_nome_contem'].get('valores', [])
    print(f"\n📝 FILTROS POR STRING NO NOME ({len(strings_filtro)}):")
    if strings_filtro:
        for i, string in enumerate(strings_filtro, 1):
            print(f"   {i}. '{string}'")
    else:
        print("   Nenhum filtro por nome configurado")
    
    # Filtros por empresa
    empresas_filtro = filtros['filtros']['por_empresa'].get('valores', [])
    print(f"\n🏢 FILTROS POR EMPRESA ({len(empresas_filtro)}):")
    if empresas_filtro:
        for i, empresa_id in enumerate(empresas_filtro, 1):
            print(f"   {i}. {empresa_id}")
    else:
        print("   Nenhum filtro por empresa configurado")
    
    logger.info("Configuração de filtros exibida")


def testar_filtros_na_api(logger):
    """Testa filtros usando dados reais da API"""
    print("\n🧪 TESTANDO FILTROS COM DADOS DA API")
    print("="*50)
    
    try:
        # Carregar configurações
        configs = load_all_configs()
        
        # Criar cliente API
        session = criar_cliente_api(configs)
        
        print("🔍 Buscando empresas da API...")
        sucesso, empresas = buscar_todas_empresas(session, configs['api'])
        
        if not sucesso:
            print(f"❌ Erro ao buscar empresas: {empresas}")
            return
        
        print(f"📊 Total de empresas encontradas: {len(empresas)}")
        
        # Aplicar filtro básico "- Obra"
        obras_basicas = [e for e in empresas if '- Obra' in e.get('name', '')]
        print(f"📊 Obras após filtro básico '- Obra': {len(obras_basicas)}")
        
        # Aplicar filtros configurados
        obras_incluidas, obras_excluidas = aplicar_filtros_obras(empresas, "- Obra")
        
        print(f"\n📈 RESULTADO DOS FILTROS:")
        print(f"   ✅ Obras incluídas: {len(obras_incluidas)}")
        print(f"   ❌ Obras excluídas: {len(obras_excluidas)}")
        
        # Mostrar algumas obras incluídas
        if obras_incluidas:
            print(f"\n📋 ALGUMAS OBRAS INCLUÍDAS (máximo 5):")
            for i, obra in enumerate(obras_incluidas[:5], 1):
                print(f"   {i}. {obra['id']} - {obra['name'][:60]}...")
        
        # Mostrar algumas obras excluídas
        if obras_excluidas:
            print(f"\n🚫 ALGUMAS OBRAS EXCLUÍDAS (máximo 5):")
            for i, obra in enumerate(obras_excluidas[:5], 1):
                print(f"   {i}. {obra['id']} - {obra['name'][:60]}...")
        
        logger.info(f"Teste de filtros: {len(obras_incluidas)} incluídas, {len(obras_excluidas)} excluídas")
        
    except Exception as e:
        print(f"❌ Erro ao testar filtros: {str(e)}")
        logger.error(f"Erro no teste de filtros: {str(e)}")


def alternar_modo(logger):
    """Alterna entre modo incluir/excluir"""
    filtros = load_filtros_obras()
    modo_atual = filtros.get('modo', 'excluir')
    novo_modo = 'incluir' if modo_atual == 'excluir' else 'excluir'
    
    print(f"\n🔄 ALTERNANDO MODO: {modo_atual} → {novo_modo}")
    
    if novo_modo == 'incluir':
        print("  ⚠️  ATENÇÃO: Apenas as obras listadas nos filtros serão processadas!")
    else:
        print("  ℹ️  As obras listadas nos filtros serão ignoradas (modo padrão)")
    
    confirmar = input("\n✓ Confirma a alteração? (s/N): ").strip().lower()
    
    if confirmar == 's':
        filtros['modo'] = novo_modo
        if save_filtros_obras(filtros):
            print(f"✅ Modo alterado para: {novo_modo}")
            logger.info(f"Modo de filtro alterado: {modo_atual} → {novo_modo}")
        else:
            print("❌ Erro ao salvar configuração")
    else:
        print("❌ Alteração cancelada")


def gerenciar_filtros_por_id(logger):
    """Submenu para gerenciar filtros por ID"""
    while True:
        filtros = load_filtros_obras()
        ids_atuais = filtros['filtros']['por_id'].get('valores', [])
        
        print("\n" + "="*50)
        print("🔢 GERENCIAR FILTROS POR ID")
        print("="*50)
        print(f"Filtros atuais: {len(ids_atuais)} IDs")
        print("1. Listar IDs atuais")
        print("2. Adicionar ID")
        print("3. Remover ID")
        print("4. Adicionar múltiplos IDs")
        print("5. Limpar todos os IDs")
        print("0. Voltar")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == "1":
            if ids_atuais:
                print(f"\n📋 IDs CONFIGURADOS ({len(ids_atuais)}):")
                ids_ordenados = sorted(ids_atuais)
                for i, obra_id in enumerate(ids_ordenados, 1):
                    print(f"   {i:3d}. {obra_id}")
            else:
                print("\n📋 Nenhum ID configurado")
        
        elif opcao == "2":
            try:
                novo_id = int(input("Digite o ID da obra: "))
                if novo_id not in ids_atuais:
                    ids_atuais.append(novo_id)
                    filtros['filtros']['por_id']['valores'] = ids_atuais
                    if save_filtros_obras(filtros):
                        print(f"✅ ID {novo_id} adicionado")
                        logger.info(f"ID {novo_id} adicionado aos filtros")
                    else:
                        print("❌ Erro ao salvar")
                else:
                    print(f"⚠️  ID {novo_id} já está configurado")
            except ValueError:
                print("❌ ID deve ser um número")
        
        elif opcao == "3":
            if not ids_atuais:
                print("❌ Nenhum ID para remover")
                continue
            
            try:
                id_remover = int(input("Digite o ID para remover: "))
                if id_remover in ids_atuais:
                    ids_atuais.remove(id_remover)
                    filtros['filtros']['por_id']['valores'] = ids_atuais
                    if save_filtros_obras(filtros):
                        print(f"✅ ID {id_remover} removido")
                        logger.info(f"ID {id_remover} removido dos filtros")
                    else:
                        print("❌ Erro ao salvar")
                else:
                    print(f"⚠️  ID {id_remover} não está configurado")
            except ValueError:
                print("❌ ID deve ser um número")
        
        elif opcao == "4":
            entrada = input("Digite IDs separados por vírgula (ex: 123,456,789): ").strip()
            try:
                novos_ids = [int(x.strip()) for x in entrada.split(',') if x.strip()]
                if novos_ids:
                    ids_adicionados = []
                    for novo_id in novos_ids:
                        if novo_id not in ids_atuais:
                            ids_atuais.append(novo_id)
                            ids_adicionados.append(novo_id)
                    
                    if ids_adicionados:
                        filtros['filtros']['por_id']['valores'] = ids_atuais
                        if save_filtros_obras(filtros):
                            print(f"✅ {len(ids_adicionados)} IDs adicionados: {ids_adicionados}")
                            logger.info(f"IDs adicionados: {ids_adicionados}")
                        else:
                            print("❌ Erro ao salvar")
                    else:
                        print("⚠️  Todos os IDs já estavam configurados")
                else:
                    print("❌ Nenhum ID válido fornecido")
            except ValueError:
                print("❌ Formato inválido. Use números separados por vírgula")
        
        elif opcao == "5":
            if ids_atuais:
                confirmar = input(f"⚠️  Confirma remoção de {len(ids_atuais)} IDs? (s/N): ").strip().lower()
                if confirmar == 's':
                    filtros['filtros']['por_id']['valores'] = []
                    if save_filtros_obras(filtros):
                        print("✅ Todos os IDs foram removidos")
                        logger.info("Todos os filtros por ID foram limpos")
                    else:
                        print("❌ Erro ao salvar")
                else:
                    print("❌ Operação cancelada")
            else:
                print("⚠️  Não há IDs para remover")
        
        elif opcao == "0":
            break
        
        else:
            print("❌ Opção inválida")


def gerenciar_filtros_por_nome(logger):
    """Submenu para gerenciar filtros por nome"""
    while True:
        filtros = load_filtros_obras()
        strings_atuais = filtros['filtros']['por_nome_contem'].get('valores', [])
        
        print("\n" + "="*50)
        print("📝 GERENCIAR FILTROS POR NOME")
        print("="*50)
        print(f"Filtros atuais: {len(strings_atuais)} strings")
        print("1. Listar strings atuais")
        print("2. Adicionar string")
        print("3. Remover string")
        print("4. Limpar todas as strings")
        print("0. Voltar")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == "1":
            if strings_atuais:
                print(f"\n📋 STRINGS CONFIGURADAS ({len(strings_atuais)}):")
                for i, string in enumerate(strings_atuais, 1):
                    print(f"   {i}. '{string}'")
            else:
                print("\n📋 Nenhuma string configurada")
        
        elif opcao == "2":
            nova_string = input("Digite a string para filtrar: ").strip()
            if nova_string:
                if nova_string not in strings_atuais:
                    strings_atuais.append(nova_string)
                    filtros['filtros']['por_nome_contem']['valores'] = strings_atuais
                    if save_filtros_obras(filtros):
                        print(f"✅ String '{nova_string}' adicionada")
                        logger.info(f"String '{nova_string}' adicionada aos filtros")
                    else:
                        print("❌ Erro ao salvar")
                else:
                    print(f"⚠️  String '{nova_string}' já está configurada")
            else:
                print("❌ String não pode estar vazia")
        
        elif opcao == "3":
            if not strings_atuais:
                print("❌ Nenhuma string para remover")
                continue
            
            print("\nStrings disponíveis:")
            for i, string in enumerate(strings_atuais, 1):
                print(f"   {i}. '{string}'")
            
            try:
                indice = int(input("Número da string para remover: ")) - 1
                if 0 <= indice < len(strings_atuais):
                    string_removida = strings_atuais.pop(indice)
                    filtros['filtros']['por_nome_contem']['valores'] = strings_atuais
                    if save_filtros_obras(filtros):
                        print(f"✅ String '{string_removida}' removida")
                        logger.info(f"String '{string_removida}' removida dos filtros")
                    else:
                        print("❌ Erro ao salvar")
                else:
                    print("❌ Número inválido")
            except ValueError:
                print("❌ Digite um número válido")
        
        elif opcao == "4":
            if strings_atuais:
                confirmar = input(f"⚠️  Confirma remoção de {len(strings_atuais)} strings? (s/N): ").strip().lower()
                if confirmar == 's':
                    filtros['filtros']['por_nome_contem']['valores'] = []
                    if save_filtros_obras(filtros):
                        print("✅ Todas as strings foram removidas")
                        logger.info("Todos os filtros por nome foram limpos")
                    else:
                        print("❌ Erro ao salvar")
                else:
                    print("❌ Operação cancelada")
            else:
                print("⚠️  Não há strings para remover")
        
        elif opcao == "0":
            break
        
        else:
            print("❌ Opção inválida")


def resetar_configuracao(logger):
    """Reseta toda a configuração de filtros"""
    print("\n⚠️  RESETAR CONFIGURAÇÃO DE FILTROS")
    print("="*50)
    print("Esta ação irá:")
    print("- Remover todos os filtros por ID")
    print("- Remover todos os filtros por nome")
    print("- Remover todos os filtros por empresa")
    print("- Voltar o modo para 'excluir'")
    
    confirmar = input("\n❗ Confirma o reset completo? (digite 'RESET' para confirmar): ").strip()
    
    if confirmar == 'RESET':
        filtros_padrao = create_default_filtros()
        if save_filtros_obras(filtros_padrao):
            print("✅ Configuração resetada com sucesso")
            logger.info("Configuração de filtros resetada")
        else:
            print("❌ Erro ao resetar configuração")
    else:
        print("❌ Reset cancelado")


def importar_lista_ids(logger):
    """Importa lista de IDs de um arquivo"""
    print("\n📁 IMPORTAR LISTA DE IDs")
    print("="*30)
    print("Formatos suportados:")
    print("- Um ID por linha")
    print("- IDs separados por vírgula")
    print("- Arquivo .txt ou .csv")
    
    arquivo = input("\nCaminho do arquivo: ").strip()
    
    try:
        arquivo_path = Path(arquivo)
        if not arquivo_path.exists():
            print("❌ Arquivo não encontrado")
            return
        
        ids_importados = []
        
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Tentar diferentes formatos
        for linha in conteudo.split('\n'):
            linha = linha.strip()
            if ',' in linha:
                # IDs separados por vírgula
                for item in linha.split(','):
                    try:
                        id_obra = int(item.strip())
                        if id_obra not in ids_importados:
                            ids_importados.append(id_obra)
                    except ValueError:
                        continue
            else:
                # Um ID por linha
                try:
                    id_obra = int(linha)
                    if id_obra not in ids_importados:
                        ids_importados.append(id_obra)
                except ValueError:
                    continue
        
        if ids_importados:
            print(f"📊 {len(ids_importados)} IDs encontrados no arquivo")
            print("Primeiros 10:", ids_importados[:10])
            
            confirmar = input("\n✓ Confirma importação? (s/N): ").strip().lower()
            
            if confirmar == 's':
                filtros = load_filtros_obras()
                ids_atuais = filtros['filtros']['por_id'].get('valores', [])
                
                novos_ids = [id_obra for id_obra in ids_importados if id_obra not in ids_atuais]
                
                if novos_ids:
                    ids_atuais.extend(novos_ids)
                    filtros['filtros']['por_id']['valores'] = ids_atuais
                    
                    if save_filtros_obras(filtros):
                        print(f"✅ {len(novos_ids)} novos IDs importados")
                        logger.info(f"Importados {len(novos_ids)} IDs do arquivo {arquivo}")
                    else:
                        print("❌ Erro ao salvar")
                else:
                    print("⚠️  Todos os IDs já estavam configurados")
            else:
                print("❌ Importação cancelada")
        else:
            print("❌ Nenhum ID válido encontrado no arquivo")
    
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {str(e)}")
        logger.error(f"Erro na importação: {str(e)}")


def main():
    """Menu principal"""
    # Configurar logger
    configs = load_all_configs()
    logger = get_main_logger(configs)
    
    logger.info("Gerenciador de filtros iniciado")
    
    while True:
        print("\n" + "="*60)
        print("🔧 GERENCIADOR DE FILTROS DE OBRAS V4")
        print("="*60)
        print("1. Ver configuração atual")
        print("2. Testar filtros com API")
        print("3. Alternar modo (incluir/excluir)")
        print("4. Gerenciar filtros por ID")
        print("5. Gerenciar filtros por nome")
        print("6. Importar lista de IDs")
        print("7. Resetar configuração")
        print("8. Ver arquivo JSON completo")
        print("0. Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        try:
            if opcao == "1":
                mostrar_configuracao_atual(logger)
            
            elif opcao == "2":
                testar_filtros_na_api(logger)
            
            elif opcao == "3":
                alternar_modo(logger)
            
            elif opcao == "4":
                gerenciar_filtros_por_id(logger)
            
            elif opcao == "5":
                gerenciar_filtros_por_nome(logger)
            
            elif opcao == "6":
                importar_lista_ids(logger)
            
            elif opcao == "7":
                resetar_configuracao(logger)
            
            elif opcao == "8":
                filtros = load_filtros_obras()
                print("\n📄 ARQUIVO JSON COMPLETO:")
                print("="*50)
                import json
                print(json.dumps(filtros, ensure_ascii=False, indent=2))
            
            elif opcao == "0":
                print("👋 Saindo do gerenciador de filtros...")
                logger.info("Gerenciador de filtros finalizado")
                break
            
            else:
                print("❌ Opção inválida")
        
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            logger.error(f"Erro no gerenciador: {str(e)}")


if __name__ == '__main__':
    main()