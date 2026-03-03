#!/usr/bin/env python3
"""
Gerenciador de Merge Completo V4 - Sistema Insumos x Orçamento
Interface moderna para configuração de merge usando módulos V4
"""

import sys
from pathlib import Path

# Adicionar src ao path se necessário
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config.settings import (
    load_merge_config, save_merge_config, create_default_merge_config,
    load_all_configs
)
from src.utils.logger import get_main_logger
from src.core.merge_engine import (
    validar_config_merge, gerar_relatorio_merge, detectar_conflitos_merge,
    debug_merge_config
)


def mostrar_status_sistema(logger):
    """Mostra status completo do sistema de merge"""
    config = load_merge_config()
    
    print("\n📋 STATUS DO SISTEMA DE MERGE")
    print("="*60)
    
    # Status geral
    habilitado = config.get('habilitado', False)
    status_emoji = "✅" if habilitado else "❌"
    print(f"Status Geral: {status_emoji} {'HABILITADO' if habilitado else 'DESABILITADO'}")
    
    # Merge de obras
    merge_obras = config.get('merge_obras', {})
    print(f"\n🏗️  MERGE DE OBRAS:")
    print(f"   Configurações: {len(merge_obras)}")
    
    total_obras_origem = 0
    for obra_destino, dados in merge_obras.items():
        obras_origem = dados.get('obras_para_somar', [])
        total_obras_origem += len(obras_origem)
        print(f"   Obra {obra_destino} ← {len(obras_origem)} obras: {obras_origem}")
    
    print(f"   Total obras origem: {total_obras_origem}")
    
    # Merge de apropriações
    merge_apropriacoes = config.get('merge_apropriacoes', {})
    print(f"\n🔧 MERGE DE APROPRIAÇÕES:")
    print(f"   Obras configuradas: {len(merge_apropriacoes)}")
    
    total_mapeamentos = 0
    total_centros_origem = 0
    
    for obra_id, mapeamentos in merge_apropriacoes.items():
        qtd_mapeamentos = len(mapeamentos)
        total_mapeamentos += qtd_mapeamentos
        
        centros_obra = sum(len(config.get('centros_para_somar', [])) 
                          for config in mapeamentos.values())
        total_centros_origem += centros_obra
        
        print(f"   Obra {obra_id}: {qtd_mapeamentos} mapeamentos, {centros_obra} centros origem")
    
    print(f"   Total mapeamentos: {total_mapeamentos}")
    print(f"   Total centros origem: {total_centros_origem}")
    
    # Validação e conflitos
    valido, erros = validar_config_merge(config, logger)
    conflitos = detectar_conflitos_merge(config)
    
    print(f"\n🔍 VALIDAÇÃO:")
    print(f"   Configuração válida: {'✅ Sim' if valido else '❌ Não'}")
    if erros:
        print(f"   Erros encontrados: {len(erros)}")
    
    print(f"   Conflitos detectados: {len(conflitos)}")
    if conflitos:
        for conflito in conflitos[:3]:  # Mostrar apenas 3 primeiros
            print(f"     - {conflito['description']}")
        if len(conflitos) > 3:
            print(f"     ... e mais {len(conflitos) - 3} conflitos")
    
    logger.info(f"Status do merge exibido: {len(merge_obras)} obras, {total_mapeamentos} mapeamentos")


def habilitar_desabilitar_sistema(logger):
    """Habilita/desabilita todo o sistema de merge"""
    config = load_merge_config()
    status_atual = config.get('habilitado', False)
    
    print(f"\n🔄 ALTERNAR STATUS DO SISTEMA")
    print("="*40)
    print(f"Status atual: {'HABILITADO' if status_atual else 'DESABILITADO'}")
    print(f"Novo status: {'DESABILITADO' if status_atual else 'HABILITADO'}")
    
    if not status_atual:
        print("\n⚠️  ATENÇÃO: Habilitar o sistema irá:")
        print("- Aplicar merge de obras conforme configurado")
        print("- Transformar códigos de apropriação")
        print("- Modificar os dados dos relatórios")
    else:
        print("\n⚠️  ATENÇÃO: Desabilitar o sistema irá:")
        print("- Ignorar todas as configurações de merge")
        print("- Manter dados originais sem transformação")
    
    confirmar = input("\n✓ Confirma a alteração? (s/N): ").strip().lower()
    
    if confirmar == 's':
        config['habilitado'] = not status_atual
        if save_merge_config(config):
            novo_status = "HABILITADO" if not status_atual else "DESABILITADO"
            print(f"✅ Sistema {novo_status} com sucesso")
            logger.info(f"Sistema de merge {novo_status.lower()}")
        else:
            print("❌ Erro ao salvar configuração")
    else:
        print("❌ Alteração cancelada")


def gerenciar_merge_obras(logger):
    """Menu para gerenciar merge de obras"""
    while True:
        config = load_merge_config()
        merge_obras = config.get('merge_obras', {})
        
        print("\n" + "="*60)
        print("🏗️  GERENCIAMENTO DE MERGE DE OBRAS")
        print("="*60)
        print(f"Configurações atuais: {len(merge_obras)}")
        print("1. Listar todas as configurações")
        print("2. Adicionar nova configuração")
        print("3. Editar configuração existente")
        print("4. Remover configuração")
        print("5. Validar configurações")
        print("0. Voltar")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == "1":
            _listar_configuracoes_obras(merge_obras)
        
        elif opcao == "2":
            _adicionar_configuracao_obra(config, logger)
        
        elif opcao == "3":
            _editar_configuracao_obra(config, logger)
        
        elif opcao == "4":
            _remover_configuracao_obra(config, logger)
        
        elif opcao == "5":
            _validar_configuracoes_obras(config, logger)
        
        elif opcao == "0":
            break
        
        else:
            print("❌ Opção inválida")


def _listar_configuracoes_obras(merge_obras):
    """Lista todas as configurações de merge de obras"""
    if not merge_obras:
        print("\n📋 Nenhuma configuração de merge de obras")
        return
    
    print(f"\n📋 CONFIGURAÇÕES DE MERGE DE OBRAS ({len(merge_obras)}):")
    print("="*50)
    
    for i, (obra_destino, config) in enumerate(merge_obras.items(), 1):
        obras_origem = config.get('obras_para_somar', [])
        observacoes = config.get('observacoes', 'N/A')
        
        print(f"\n{i}. Obra de Destino: {obra_destino}")
        print(f"   Obras Origem: {obras_origem} ({len(obras_origem)} obras)")
        print(f"   Fluxo: {' + '.join(map(str, obras_origem))} → {obra_destino}")
        print(f"   Observações: {observacoes}")


def _adicionar_configuracao_obra(config, logger):
    """Adiciona nova configuração de merge de obra"""
    print("\n➕ ADICIONAR CONFIGURAÇÃO DE MERGE")
    print("="*40)
    
    try:
        obra_destino = int(input("ID da obra de destino (que vai receber): "))
    except ValueError:
        print("❌ ID deve ser um número")
        return
    
    merge_obras = config.get('merge_obras', {})
    if str(obra_destino) in merge_obras:
        print(f"⚠️  Obra {obra_destino} já tem configuração")
        return
    
    print(f"\n✓ Obra {obra_destino} será a obra de DESTINO")
    print("Digite os IDs das obras ORIGEM (uma por vez):")
    print("(ENTER vazio para finalizar)")
    
    obras_origem = []
    contador = 1
    
    while True:
        try:
            entrada = input(f"Obra origem {contador}: ").strip()
            if not entrada:
                break
            
            obra_id = int(entrada)
            
            if obra_id == obra_destino:
                print("⚠️  Obra destino não pode ser origem de si mesma")
                continue
            
            if obra_id in obras_origem:
                print("⚠️  Obra já adicionada")
                continue
            
            obras_origem.append(obra_id)
            contador += 1
            
        except ValueError:
            print("❌ ID deve ser um número")
    
    if not obras_origem:
        print("❌ Pelo menos uma obra origem é necessária")
        return
    
    observacoes = input("Observações (opcional): ").strip()
    
    # Confirmar configuração
    print(f"\n📋 RESUMO DA CONFIGURAÇÃO:")
    print(f"   Destino: Obra {obra_destino}")
    print(f"   Origens: {obras_origem}")
    print(f"   Fluxo: {' + '.join(map(str, obras_origem))} → {obra_destino}")
    print(f"   Observações: {observacoes or 'Nenhuma'}")
    
    confirmar = input("\n✓ Confirma criação? (s/N): ").strip().lower()
    
    if confirmar == 's':
        if 'merge_obras' not in config:
            config['merge_obras'] = {}
        
        config['merge_obras'][str(obra_destino)] = {
            "obras_para_somar": obras_origem,
            "observacoes": observacoes or "Configuração criada via gerenciador V4"
        }
        
        if save_merge_config(config):
            print(f"✅ Configuração criada: {' + '.join(map(str, obras_origem))} → {obra_destino}")
            logger.info(f"Nova configuração de merge: obras {obras_origem} → {obra_destino}")
        else:
            print("❌ Erro ao salvar configuração")
    else:
        print("❌ Configuração cancelada")


def _editar_configuracao_obra(config, logger):
    """Edita configuração existente"""
    merge_obras = config.get('merge_obras', {})
    if not merge_obras:
        print("❌ Nenhuma configuração para editar")
        return
    
    print("\nConfigurações disponíveis:")
    obras_ids = list(merge_obras.keys())
    
    for i, obra_id in enumerate(obras_ids, 1):
        dados = merge_obras[obra_id]
        print(f"   {i}. Obra {obra_id} ← {dados.get('obras_para_somar', [])}")
    
    try:
        escolha = int(input("Número da configuração para editar: ")) - 1
        if not (0 <= escolha < len(obras_ids)):
            print("❌ Opção inválida")
            return
        
        obra_id = obras_ids[escolha]
        dados_atuais = merge_obras[obra_id]
        
        print(f"\n✏️  EDITANDO CONFIGURAÇÃO DA OBRA {obra_id}")
        print(f"Obras origem atuais: {dados_atuais.get('obras_para_somar', [])}")
        
        # Editar obras origem
        nova_entrada = input("Novas obras origem (ex: 210,215,220) ou ENTER para manter: ").strip()
        
        if nova_entrada:
            try:
                novas_obras = [int(x.strip()) for x in nova_entrada.split(',')]
                dados_atuais['obras_para_somar'] = novas_obras
                print(f"✅ Obras origem atualizadas: {novas_obras}")
            except ValueError:
                print("❌ Formato inválido")
                return
        
        # Editar observações
        obs_atuais = dados_atuais.get('observacoes', '')
        print(f"Observações atuais: {obs_atuais}")
        novas_obs = input("Novas observações ou ENTER para manter: ").strip()
        
        if novas_obs:
            dados_atuais['observacoes'] = novas_obs
        
        if save_merge_config(config):
            print(f"✅ Configuração da obra {obra_id} atualizada")
            logger.info(f"Configuração editada: obra {obra_id}")
        else:
            print("❌ Erro ao salvar")
        
    except ValueError:
        print("❌ Número inválido")


def _remover_configuracao_obra(config, logger):
    """Remove configuração de obra"""
    merge_obras = config.get('merge_obras', {})
    if not merge_obras:
        print("❌ Nenhuma configuração para remover")
        return
    
    print("\nConfigurações disponíveis:")
    obras_ids = list(merge_obras.keys())
    
    for i, obra_id in enumerate(obras_ids, 1):
        dados = merge_obras[obra_id]
        print(f"   {i}. Obra {obra_id} ← {dados.get('obras_para_somar', [])}")
    
    try:
        escolha = int(input("Número da configuração para remover: ")) - 1
        if not (0 <= escolha < len(obras_ids)):
            print("❌ Opção inválida")
            return
        
        obra_id = obras_ids[escolha]
        dados = merge_obras[obra_id]
        
        print(f"\n⚠️  REMOVER CONFIGURAÇÃO:")
        print(f"   Obra: {obra_id}")
        print(f"   Origens: {dados.get('obras_para_somar', [])}")
        
        confirmar = input("\n❗ Confirma remoção? (s/N): ").strip().lower()
        
        if confirmar == 's':
            del config['merge_obras'][obra_id]
            
            if save_merge_config(config):
                print(f"✅ Configuração da obra {obra_id} removida")
                logger.info(f"Configuração removida: obra {obra_id}")
            else:
                print("❌ Erro ao salvar")
        else:
            print("❌ Remoção cancelada")
        
    except ValueError:
        print("❌ Número inválido")


def _validar_configuracoes_obras(config, logger):
    """Valida configurações de obras"""
    print("\n🔍 VALIDANDO CONFIGURAÇÕES DE OBRAS")
    print("="*40)
    
    valido, erros = validar_config_merge(config, logger)
    conflitos = detectar_conflitos_merge(config)
    
    if valido and not conflitos:
        print("✅ Todas as configurações são válidas")
    else:
        if erros:
            print(f"❌ {len(erros)} erros encontrados:")
            for erro in erros:
                print(f"   - {erro}")
        
        if conflitos:
            print(f"⚠️  {len(conflitos)} conflitos detectados:")
            for conflito in conflitos:
                print(f"   - {conflito['description']}")


def testar_configuracao_completa(logger):
    """Testa toda a configuração de merge"""
    print("\n🧪 TESTE COMPLETO DA CONFIGURAÇÃO")
    print("="*50)
    
    config = load_merge_config()
    
    # Executar debug completo
    debug_merge_config(config, logger)
    
    # Gerar relatório
    relatorio = gerar_relatorio_merge(config)
    
    print(f"\n📊 RELATÓRIO DE CONFIGURAÇÃO:")
    print(f"   Sistema habilitado: {relatorio['config_summary']['merge_habilitado']}")
    print(f"   Mapeamentos de obras: {relatorio['config_summary']['mapeamentos_obras']}")
    print(f"   Obras origem total: {relatorio['config_summary']['obras_origem_total']}")
    print(f"   Mapeamentos apropriações: {relatorio['config_summary']['mapeamentos_apropriacoes']}")
    print(f"   Centros origem total: {relatorio['config_summary']['centros_origem_total']}")


def exportar_configuracao(logger):
    """Exporta configuração para arquivo"""
    print("\n📤 EXPORTAR CONFIGURAÇÃO")
    print("="*30)
    
    config = load_merge_config()
    
    # Gerar nome do arquivo
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo = f"merge_config_backup_{timestamp}.json"
    
    arquivo_path = Path(nome_arquivo)
    
    try:
        import json
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Configuração exportada: {arquivo_path}")
        print(f"   Tamanho: {arquivo_path.stat().st_size} bytes")
        logger.info(f"Configuração exportada para {arquivo_path}")
        
    except Exception as e:
        print(f"❌ Erro ao exportar: {str(e)}")
        logger.error(f"Erro na exportação: {str(e)}")


def main():
    """Menu principal"""
    # Configurar logger
    configs = load_all_configs()
    logger = get_main_logger(configs)
    
    logger.info("Gerenciador de merge iniciado")
    
    while True:
        print("\n" + "="*60)
        print("🔄 GERENCIADOR COMPLETO DE MERGE V4")
        print("="*60)
        print("1. Ver status do sistema")
        print("2. Habilitar/Desabilitar sistema")
        print("3. Gerenciar merge de OBRAS")
        print("4. Gerenciar merge de APROPRIAÇÕES")
        print("5. Testar configuração completa")
        print("6. Exportar configuração")
        print("7. Ver arquivo JSON completo")
        print("8. Debug detalhado")
        print("0. Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        try:
            if opcao == "1":
                mostrar_status_sistema(logger)
            
            elif opcao == "2":
                habilitar_desabilitar_sistema(logger)
            
            elif opcao == "3":
                gerenciar_merge_obras(logger)
            
            elif opcao == "4":
                print("🚧 Gerenciamento de apropriações será implementado")
                print("   Use o arquivo JSON diretamente por enquanto")
            
            elif opcao == "5":
                testar_configuracao_completa(logger)
            
            elif opcao == "6":
                exportar_configuracao(logger)
            
            elif opcao == "7":
                config = load_merge_config()
                print("\n📄 ARQUIVO JSON COMPLETO:")
                print("="*50)
                import json
                print(json.dumps(config, ensure_ascii=False, indent=2))
            
            elif opcao == "8":
                config = load_merge_config()
                debug_merge_config(config, logger)
            
            elif opcao == "0":
                print("👋 Saindo do gerenciador de merge...")
                logger.info("Gerenciador de merge finalizado")
                break
            
            else:
                print("❌ Opção inválida")
        
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            logger.error(f"Erro no gerenciador: {str(e)}")


if __name__ == '__main__':
    main()