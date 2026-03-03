"""
Sistema de Logs V4 - Sistema Insumos x Orçamento
Logging estruturado e funcional para debug e monitoramento
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from functools import wraps


def setup_logger(name: str, log_dir: Path, level: str = 'INFO') -> logging.Logger:
    """
    Configura logger com arquivo e console
    Returns: logger configurado
    """
    log_dir.mkdir(exist_ok=True)
    
    # Criar logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Evitar duplicação de handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Formato detalhado
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para arquivo
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def create_system_logger(configs: Dict) -> logging.Logger:
    """Cria logger principal do sistema"""
    log_dir = configs['paths']['data'] / 'logs'
    return setup_logger('insumos_orcamento', log_dir, 'INFO')


def log_api_request(logger: logging.Logger, url: str, params: Dict = None, 
                   response_time: float = None, status: str = 'success') -> None:
    """Log estruturado para requisições API"""
    log_data = {
        'type': 'api_request',
        'url': url,
        'params': params or {},
        'response_time_ms': round(response_time * 1000, 2) if response_time else None,
        'status': status,
        'timestamp': datetime.now().isoformat()
    }
    
    if status == 'success':
        logger.info(f"API Request Success: {json.dumps(log_data, ensure_ascii=False)}")
    else:
        logger.error(f"API Request Failed: {json.dumps(log_data, ensure_ascii=False)}")


def log_cache_operation(logger: logging.Logger, operation: str, key: str, 
                       hit: bool = None, size_mb: float = None) -> None:
    """Log para operações de cache"""
    log_data = {
        'type': 'cache_operation',
        'operation': operation,  # 'read', 'write', 'cleanup'
        'key': key,
        'hit': hit,
        'size_mb': size_mb,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Cache {operation.title()}: {json.dumps(log_data, ensure_ascii=False)}")


def log_filter_application(logger: logging.Logger, filtro_tipo: str, 
                          total_antes: int, total_depois: int, criterios: Dict) -> None:
    """Log para aplicação de filtros"""
    excluidos = total_antes - total_depois
    percentual = (excluidos / total_antes * 100) if total_antes > 0 else 0
    
    log_data = {
        'type': 'filter_application',
        'filter_type': filtro_tipo,
        'before_count': total_antes,
        'after_count': total_depois,
        'excluded_count': excluidos,
        'excluded_percentage': round(percentual, 2),
        'criteria': criterios,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Filter Applied: {json.dumps(log_data, ensure_ascii=False)}")


def log_merge_operation(logger: logging.Logger, obra_origem: int, obra_destino: int,
                       recursos_transferidos: int, valor_total: float) -> None:
    """Log para operações de merge"""
    log_data = {
        'type': 'merge_operation',
        'obra_origem': obra_origem,
        'obra_destino': obra_destino,
        'recursos_transferidos': recursos_transferidos,
        'valor_total': valor_total,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Merge Operation: {json.dumps(log_data, ensure_ascii=False)}")


def log_excel_generation(logger: logging.Logger, arquivo: Path, total_registros: int,
                        tempo_geracao: float) -> None:
    """Log para geração de Excel"""
    log_data = {
        'type': 'excel_generation',
        'file_path': str(arquivo),
        'total_records': total_registros,
        'generation_time_seconds': round(tempo_geracao, 2),
        'file_size_mb': round(arquivo.stat().st_size / (1024 * 1024), 2) if arquivo.exists() else 0,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Excel Generated: {json.dumps(log_data, ensure_ascii=False)}")


def log_processing_summary(logger: logging.Logger, total_obras: int, sucessos: int, 
                          erros: int, tempo_total: float) -> None:
    """Log para resumo de processamento"""
    taxa_sucesso = (sucessos / total_obras * 100) if total_obras > 0 else 0
    
    log_data = {
        'type': 'processing_summary',
        'total_obras': total_obras,
        'successful': sucessos,
        'failed': erros,
        'success_rate_percentage': round(taxa_sucesso, 2),
        'total_time_seconds': round(tempo_total, 2),
        'avg_time_per_obra': round(tempo_total / total_obras, 2) if total_obras > 0 else 0,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Processing Summary: {json.dumps(log_data, ensure_ascii=False)}")


def log_error_details(logger: logging.Logger, error: Exception, context: Dict = None) -> None:
    """Log detalhado para erros"""
    log_data = {
        'type': 'error_details',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context or {},
        'timestamp': datetime.now().isoformat()
    }
    
    logger.error(f"Error Details: {json.dumps(log_data, ensure_ascii=False)}")


def log_config_validation(logger: logging.Logger, config_type: str, 
                         is_valid: bool, errors: List[str] = None) -> None:
    """Log para validação de configurações"""
    log_data = {
        'type': 'config_validation',
        'config_type': config_type,
        'is_valid': is_valid,
        'errors': errors or [],
        'timestamp': datetime.now().isoformat()
    }
    
    if is_valid:
        logger.info(f"Config Valid: {json.dumps(log_data, ensure_ascii=False)}")
    else:
        logger.error(f"Config Invalid: {json.dumps(log_data, ensure_ascii=False)}")


def timing_decorator(logger: logging.Logger):
    """Decorator para medir tempo de execução de funções"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                log_data = {
                    'type': 'function_timing',
                    'function_name': func.__name__,
                    'duration_seconds': round(duration, 3),
                    'status': 'success',
                    'timestamp': start_time.isoformat()
                }
                
                logger.debug(f"Function Timing: {json.dumps(log_data, ensure_ascii=False)}")
                return result
                
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                log_data = {
                    'type': 'function_timing',
                    'function_name': func.__name__,
                    'duration_seconds': round(duration, 3),
                    'status': 'error',
                    'error': str(e),
                    'timestamp': start_time.isoformat()
                }
                
                logger.error(f"Function Error: {json.dumps(log_data, ensure_ascii=False)}")
                raise
                
        return wrapper
    return decorator


def log_building_unit_filter(logger: logging.Logger, building_unit_id: int, 
                           incluido: bool, criterio: str) -> None:
    """Log para filtros de Building Unit"""
    log_data = {
        'type': 'building_unit_filter',
        'building_unit_id': building_unit_id,
        'included': incluido,
        'criteria': criterio,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.debug(f"Building Unit Filter: {json.dumps(log_data, ensure_ascii=False)}")


def create_progress_logger(logger: logging.Logger, total_items: int, 
                          operation_name: str) -> callable:
    """
    Cria função de callback para log de progresso
    Returns: função callback(current, total, item_name)
    """
    def log_progress(current: int, total: int, item_name: str) -> None:
        if current == 1 or current % 10 == 0 or current == total:
            percentual = (current / total * 100) if total > 0 else 0
            
            log_data = {
                'type': 'progress_update',
                'operation': operation_name,
                'current': current,
                'total': total,
                'percentage': round(percentual, 1),
                'current_item': item_name,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Progress: {json.dumps(log_data, ensure_ascii=False)}")
    
    return log_progress


def analyze_log_file(log_file: Path) -> Dict:
    """
    Analisa arquivo de log e retorna estatísticas
    Returns: dict com estatísticas
    """
    if not log_file.exists():
        return {'error': 'Log file not found'}
    
    stats = {
        'total_lines': 0,
        'api_requests': 0,
        'cache_operations': 0,
        'errors': 0,
        'merge_operations': 0,
        'processing_time_total': 0,
        'most_common_errors': {},
        'api_success_rate': 0
    }
    
    api_total = 0
    api_success = 0
    error_counts = {}
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                stats['total_lines'] += 1
                
                if 'API Request' in line:
                    api_total += 1
                    if 'Success' in line:
                        api_success += 1
                
                if 'Cache' in line:
                    stats['cache_operations'] += 1
                
                if 'ERROR' in line:
                    stats['errors'] += 1
                    # Extrair tipo de erro
                    try:
                        if 'error_type' in line:
                            error_data = json.loads(line.split('Error Details: ')[1])
                            error_type = error_data.get('error_type', 'Unknown')
                            error_counts[error_type] = error_counts.get(error_type, 0) + 1
                    except:
                        pass
                
                if 'Merge Operation' in line:
                    stats['merge_operations'] += 1
        
        stats['api_requests'] = api_total
        stats['api_success_rate'] = (api_success / api_total * 100) if api_total > 0 else 0
        stats['most_common_errors'] = dict(sorted(error_counts.items(), 
                                                 key=lambda x: x[1], reverse=True)[:5])
        
    except Exception as e:
        stats['analysis_error'] = str(e)
    
    return stats


def cleanup_old_logs(log_dir: Path, days_to_keep: int = 30) -> Tuple[int, int]:
    """
    Remove logs antigos
    Returns: (arquivos_removidos, arquivos_mantidos)
    """
    if not log_dir.exists():
        return 0, 0
    
    cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
    removidos = 0
    mantidos = 0
    
    for log_file in log_dir.glob("*.log"):
        try:
            if log_file.stat().st_mtime < cutoff_date:
                log_file.unlink()
                removidos += 1
            else:
                mantidos += 1
        except:
            mantidos += 1
    
    return removidos, mantidos


# Funções de conveniência para uso direto
def get_main_logger(configs: Dict) -> logging.Logger:
    """Obtém logger principal configurado"""
    return create_system_logger(configs)


def log_startup(logger: logging.Logger, configs: Dict) -> None:
    """Log de inicialização do sistema"""
    startup_data = {
        'type': 'system_startup',
        'api_user': configs['api']['user'],
        'api_subdomain': configs['api']['subdomain'],
        'cache_enabled': configs['cache']['enabled'],
        'building_units_filter': configs['building_units']['filter_enabled'],
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"System Startup: {json.dumps(startup_data, ensure_ascii=False)}")


if __name__ == '__main__':
    # Teste do sistema de logs
    from settings import load_all_configs
    
    configs = load_all_configs()
    logger = get_main_logger(configs)
    
    # Teste de diferentes tipos de log
    log_startup(logger, configs)
    log_api_request(logger, "https://api.test.com", {"param": "value"}, 0.5, "success")
    log_cache_operation(logger, "read", "test_key", True, 1.5)
    log_filter_application(logger, "obras", 100, 85, {"modo": "excluir"})
    
    print("Sistema de logs testado com sucesso!")