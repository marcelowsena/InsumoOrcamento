#!/usr/bin/env python3
"""
Gerenciador de Building Units V4 - Sistema Insumos x Orçamento
Interface moderna para configuração de Building Units usando módulos V4
"""

import sys
import os
from pathlib import Path

# Adicionar src ao path se necessário
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config.settings import (
    get_building_units_config, set_building_units_config,
    should_include_building_unit, load_all_configs
)
from src.utils.logger import get_main_logger
from src.api.api_client import criar_cliente_api, buscar_todas_empresas
from src.core.data_processor import processar_todos_resultados


def mostrar_configuracao_atual(logger):
    """Mostra configuração atual de Building Units"""
    config = get_building_units_config()
    
    print("\n📋 CONFIGURAÇÃO ATUAL DE BUILDING UNITS")
    print("="*60)
    
    if config['filter_enabled']:
        print("✅ Filtro HABILITADO")
        print(f"Building Units permitidos: {config['allowed_ids']}")
        print(f"IDs configurados: {len(config['allowed_ids'])}")
    else:
        print("❌ Filtro DESABILITADO")
        print("   ℹ️  Todos os Building Units serão incluídos nos relatórios")
    
    print(f"\nIDs padrão do sistema: {config['default_ids']}")
    
    logger.info(f"Configuração exibida: filtro={'habilitado' if config['filter_enabled'] else 'desabilitado'}")


def explicar_building_units():
    """Explica o conceito de Building Units"""
    print("""
🏗️  O QUE SÃO BUILDING UNITS?

Building Units representam diferentes centros de custo ou divisões 
dentro de uma obra no sistema Sienge:

📊 TIPOS COMUNS:
• Building Unit 1: Custos DIRETOS da obra
  - Materiais e mão de obra diretamente relacionados à construção
  - Equipamentos e ferramentas usados na produção

• Building Unit 2: Custos INDIRETOS
  - Administração da obra
  - Infraestrutura e apoio
  - Custos administrativos

• Building Unit 3+: Divisões específicas
  - Diferentes fases da obra
  - Tipos específicos de atividade
  - Centros de custo personalizados

🔍 EXEMPLO DE DADOS:
{
  "buildingUnitId": 2,
  "buildingUnitName": "SPE Benjamin Constant - Custo Indireto",
  "quantity": 1.0,
  "value": 350.0
}

⚙️ FILTRO DE BUILDING UNITS:
- Quando HABILITADO: apenas os IDs configurados são incluídos
- Quando DESABILITADO: todos os Building Units são processados
- Útil para análises específicas (ex: apenas custos diretos)
""")


def configuracao_rapida(logger):
    """Permite configuração rápida via menu"""
    print("\n⚡ CONFIGURAÇÃO RÁPIDA")
    print("="*30)
    print("1. Apenas Building Unit 1 (custos diretos)")
    print("2. Building Units 1 e 2 (diretos + indiretos)")
    print("3. Todos os Building Units (desabilitar filtro)")
    print("4. Configuração customizada")
    print("0. Cancelar")
    
    opcao = input("\nEscolha uma opção: ").strip()
    
    if opcao == "1":
        set_building_units_config(True, [1])
        print("✅ Configurado: Apenas Building Unit 1 (custos diretos)")
        logger.info("Configuração rápida: apenas Building Unit 1")
        
    elif opcao == "2":
        set_building_units_config(True, [1, 2])
        print("✅ Configurado: Building Units 1 e 2 (diretos + indiretos)")
        logger.info("Configuração rápida: Building Units 1 e 2")
        
    elif opcao == "3":
        set_building_units_config(False, [])
        print("✅ Configurado: Todos os Building Units (filtro desabilitado)")
        logger.info("Configuração rápida: filtro desabilitado")
        
    elif opcao == "4":
        configuracao_customizada(logger)
        
    elif opcao == "0":
        print("❌ Configuração cancelada")
        
    else:
        print("❌ Opção inválida")


def configuracao_customizada(logger):
    """Permite configuração detalhada"""
    print("\n🔧 CONFIGURAÇÃO CUSTOMIZADA")
    print("="*30)
    
    # Habilitar/desabilitar filtro
    config_atual = get_building_units_config()
    status_atual = "habilitado" if config_atual['filter_enabled'] else "desabilitado"
    
    print(f"Status atual do filtro: {status_atual}")
    habilitar = input("Habilitar filtro de Building Units? (s/N): ").strip().lower()
    
    if habilitar == 's':
        print("\n📝 CONFIGURAR IDs PERMITIDOS")
        print("Digite os IDs dos Building Units permitidos.")
        print("Exemplos:")
        print("  1 (apenas custos diretos)")
        print("  1,2 (diretos e indiretos)")
        print("  1,2,3,4 (múltiplas divisões)")
        
        try:
            ids_input = input("\nBuilding Unit IDs (separados por vírgula): ").strip()
            
            if not ids_input:
                print("❌ Nenhum ID fornecido")
                return
            
            unit_ids = [int(x.strip()) for x in ids_input.split(',') if x.strip()]
            
            if not unit_ids:
                print("❌ Nenhum ID válido fornecido")
                return
            
            # Validar IDs
            if any(id_unit < 1 for id_unit in unit_ids):
                print("⚠️  Atenção: IDs menores que 1 podem não ser válidos")
            
            # Confirmar configuração
            print(f"\n📋 RESUMO DA CONFIGURAÇÃO:")
            print(f"   Filtro: HABILITADO")
            print(f"   IDs permitidos: {sorted(unit_ids)}")
            print(f"   Total de IDs: {len(unit_ids)}")
            
            confirmar = input("\n✓ Confirma configuração? (s/N): ").strip().lower()
            
            if confirmar == 's':
                set_building_units_config(True, unit_ids)
                print(f"✅ Configurado: Building Units {sorted(unit_ids)}")
                logger.info(f"Configuração customizada: IDs {unit_ids}")
            else:
                print("❌ Configuração cancelada")
                
        except ValueError:
            print("❌ Formato inválido. Use números separados por vírgula")
            
    else:
        # Desabilitar filtro
        confirmar = input("Confirma desabilitar o filtro? (s/N): ").strip().lower()
        
        if confirmar == 's':
            set_building_units_config(False, [])
            print("✅ Filtro desabilitado - todos os Building Units serão incluídos")
            logger.info("Filtro de Building Units desabilitado")
        else:
            print("❌ Configuração cancelada")


def testar_configuracao(logger):
    """Testa a configuração atual com vários IDs"""
    print("\n🧪 TESTE DA CONFIGURAÇÃO ATUAL")
    print("="*40)
    
    config = get_building_units_config()
    
    # IDs de teste
    test_ids = [1, 2, 3, 4, 5, 0, -1, 999]
    
    print("Testando Building Unit IDs:")
    print("ID  | Resultado | Motivo")
    print("----|-----------|--------")
    
    for test_id in test_ids:
        incluido = should_include_building_unit(test_id)
        
        if not config['filter_enabled']:
            motivo = "filtro desabilitado"
            resultado = "✅ INCLUÍDO"
        elif test_id in config['allowed_ids']:
            motivo = "ID permitido"
            resultado = "✅ INCLUÍDO"
        else:
            motivo = "ID não permitido"
            resultado = "❌ EXCLUÍDO"
        
        print(f"{test_id:3d} | {resultado} | {motivo}")
    
    # Teste com dados inválidos
    print(f"\nTeste com valores inválidos:")
    valores_invalidos = [None, '', 'abc', 1.5]
    
    for valor in valores_invalidos:
        try:
            incluido = should_include_building_unit(valor)
            resultado = "✅ INCLUÍDO" if incluido else "❌ EXCLUÍDO"
        except:
            resultado = "❌ ERRO"
        
        print(f"'{valor}' → {resultado}")
    
    logger.info("Teste de configuração executado")


def testar_com_api_real(logger):
    """Testa configuração com dados reais da API"""
    print("\n🌐 TESTE COM DADOS REAIS DA API")
    print("="*40)
    
    try:
        # Carregar configurações
        configs = load_all_configs()
        
        # Criar cliente API
        session = criar_cliente_api(configs)
        
        print("🔍 Buscando dados da API...")
        sucesso, empresas = buscar_todas_empresas(session, configs['api'])
        
        if not sucesso:
            print(f"❌ Erro ao acessar API: {empresas}")
            return
        
        # Filtrar obras
        obras = [e for e in empresas if '- Obra' in e.get('name', '')][:3]  # Apenas 3 obras para teste
        
        if not obras:
            print("❌ Nenhuma obra encontrada")
            return
        
        print(f"📊 Testando com {len(obras)} obras...")
        
        # Simular processamento (apenas para teste de Building Units)
        for i, obra in enumerate(obras, 1):
            print(f"\n{i}. Obra {obra['id']} - {obra['name'][:50]}...")
            
            # Aqui você poderia fazer uma requisição real para testar
            # Por enquanto, apenas simular
            print("   (Teste simulado - use --test-connection no main.py para teste real)")
        
        config = get_building_units_config()
        print(f"\n📋 Configuração que seria aplicada:")
        print(f"   Filtro: {'habilitado' if config['filter_enabled'] else 'desabilitado'}")
        if config['filter_enabled']:
            print(f"   IDs permitidos: {config['allowed_ids']}")
        
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        logger.error(f"Erro no teste com API: {str(e)}")


def salvar_configuracao_arquivo(logger):
    """Salva configuração atual em arquivo .env"""
    print("\n💾 SALVAR CONFIGURAÇÃO EM ARQUIVO")
    print("="*40)
    
    config = get_building_units_config()
    
    # Preparar linhas para .env
    linhas_env = [
        f"# Building Units Configuration - {Path(__file__).name}",
        f"# Generated on: {__import__('datetime').datetime.now().isoformat()}",
        f"BUILDING_UNIT_FILTER_ENABLED={'true' if config['filter_enabled'] else 'false'}",
        f"BUILDING_UNIT_IDS_ALLOWED={','.join(map(str, config['allowed_ids']))}",
        ""
    ]
    
    print("Configuração a ser salva:")
    for linha in linhas_env:
        if linha.strip():
            print(f"  {linha}")
    
    nome_arquivo = input("\nNome do arquivo (padrão: building_units.env): ").strip()
    if not nome_arquivo:
        nome_arquivo = "building_units.env"
    
    if not nome_arquivo.endswith('.env'):
        nome_arquivo += '.env'
    
    try:
        arquivo_path = Path(nome_arquivo)
        
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(linhas_env))
        
        print(f"✅ Configuração salva: {arquivo_path}")
        print(f"   Para usar: copie as linhas para seu arquivo .env principal")
        logger.info(f"Configuração salva em {arquivo_path}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar: {str(e)}")
        logger.error(f"Erro ao salvar configuração: {str(e)}")


def exemplos_uso():
    """Mostra exemplos de uso na linha de comando"""
    print("""
💡 EXEMPLOS DE USO NA LINHA DE COMANDO

# Building Units padrão (configuração atual)
python main.py --export-excel

# Building Units específicos (sobrescreve configuração)
python main.py --export-excel --building-units 1,2

# Desabilitar filtro de Building Units
python main.py --export-excel --disable-building-unit-filter

# Apenas Building Unit 1 (custos diretos)
python main.py --export-excel --building-units 1

# Building Units 1, 2 e 3
python main.py --export-excel --building-units 1,2,3

# Combinar com outros filtros
python main.py --export-excel --building-units 1,2 --filter "- Obra" --start-date 2024-01-01

# Testar configuração
python main.py --test-connection

📝 NOTAS:
- As configurações da linha de comando são temporárias (apenas para aquela execução)
- Para configurações permanentes, use este gerenciador ou edite o arquivo .env
- O filtro só afeta lançamentos que têm buildingUnitId definido
- Building Units sem ID ou com ID inválido são tratados conforme configuração
""")


def main():
    """Menu principal"""
    # Configurar logger
    configs = load_all_configs()
    logger = get_main_logger(configs)
    
    logger.info("Gerenciador de Building Units iniciado")
    
    while True:
        print("\n" + "="*60)
        print("🏗️  GERENCIADOR DE BUILDING UNITS V4")
        print("="*60)
        print("1. Ver configuração atual")
        print("2. Explicação sobre Building Units")
        print("3. Configuração rápida")
        print("4. Configuração customizada")
        print("5. Testar configuração")
        print("6. Testar com API real")
        print("7. Salvar configuração em arquivo")
        print("8. Exemplos de uso")
        print("0. Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        try:
            if opcao == "1":
                mostrar_configuracao_atual(logger)
            
            elif opcao == "2":
                explicar_building_units()
            
            elif opcao == "3":
                configuracao_rapida(logger)
            
            elif opcao == "4":
                configuracao_customizada(logger)
            
            elif opcao == "5":
                testar_configuracao(logger)
            
            elif opcao == "6":
                testar_com_api_real(logger)
            
            elif opcao == "7":
                salvar_configuracao_arquivo(logger)
            
            elif opcao == "8":
                exemplos_uso()
            
            elif opcao == "0":
                print("👋 Saindo do gerenciador de Building Units...")
                logger.info("Gerenciador de Building Units finalizado")
                break
            
            else:
                print("❌ Opção inválida")
        
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            logger.error(f"Erro no gerenciador: {str(e)}")


if __name__ == '__main__':
    main()