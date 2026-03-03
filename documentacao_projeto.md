# Sistema de Análise Insumos x Orçamento V4

## 📋 Visão Geral

Sistema Python para análise integrada de dados do Sienge, combinando:
- **Insumos de obras** (apropriados, pendentes, orçados)
- **Títulos a pagar** (notas fiscais, provisões, duplicatas)
- **Hierarquia WBS** (estrutura de apropriação em 4 níveis)
- **Merge inteligente** (consolidação de obras e centros de custo)

**Resultado:** Relatórios Excel unificados com visão completa financeira e operacional.

---

## 🏗️ Arquitetura

```
InsumosXOrçamento_V5/
├── main.py                    # Orchestrator principal
├── teste_titulos_api.py       # Teste isolado de títulos
├── src/
│   ├── api/                   # Integração com APIs
│   │   ├── api_client.py      # Cliente API Sienge (obras)
│   │   ├── budget_api.py      # API de orçamentos (WBS)
│   │   └── titulos_api.py     # API de títulos
│   ├── config/                # Configurações
│   │   ├── settings.py        # Configurações centralizadas
│   │   ├── filtros_obras.json # Filtros de obras
│   │   ├── filtros_titulos.json # Filtros de títulos
│   │   └── merge_centros_custo.json # Configuração de merge
│   ├── core/                  # Lógica de negócio
│   │   ├── data_processor.py  # Processa dados de obras
│   │   ├── titulos_processor.py # Processa títulos
│   │   ├── merge_engine.py    # Engine de merge
│   │   └── excel_generator.py # Geração de Excel
│   ├── data/                  # Dados e cache
│   │   ├── cache/             # Cache de APIs
│   │   ├── logs/              # Logs do sistema
│   │   └── reports/           # Relatórios gerados
│   └── utils/
│       └── logger.py          # Sistema de logs
└── tools/                     # Ferramentas de gestão
    ├── manage_building_units.py
    ├── manage_filters.py
    └── manage_merge_centros.py
```

---

## 🔧 Funcionalidades Principais

### 1. **Busca de Dados**
- **Obras:** API bulk-data Sienge (recursos, apropriações, orçamentos)
- **Títulos:** Biblioteca siengeAPI (títulos a pagar com apropriações)
- **Cache inteligente** para obras (24h), sem cache para títulos
- **Filtros configuráveis** por JSON

### 2. **Processamento de Dados**
- **Três tipos de lançamentos:**
  - `APROPRIADO`: Recursos já apropriados às obras
  - `PENDENTE`: Recursos pendentes de apropriação + títulos a pagar
  - `ORÇADO`: Itens do orçamento sem apropriação real

### 3. **Merge Inteligente**
- **Merge de obras:** Consolida múltiplas obras em uma obra destino
- **Merge de centros:** Transforma códigos de apropriação
- **Ordem correta:** Dados → Merge → WBS (hierarquia da obra destino)

### 4. **Hierarquia WBS**
- **4 níveis hierárquicos** extraídos dos códigos de apropriação
- **Estrutura:** `05.002.001.001` → Nível_1, Nível_2, Nível_3, Nível_4
- **Descrições:** Busca automática no orçamento das obras

### 5. **Relatórios Excel**
- **Aba Lançamentos:** Dados detalhados com hierarquia
- **Aba Resumo por Obra:** Totalizações
- **Aba Metadados:** Informações da execução
- **Formato padronizado** com 23 colunas fixas

---

## 🚀 Como Usar

### **Uso Básico**
```bash
# Relatório completo (obras + títulos)
python main.py --export-excel

# Apenas obras (sem títulos)
python main.py --export-excel --disable-titulos

# Excel simples (só dados, sem abas extras)
python main.py --export-excel --simple
```

### **Filtros e Opções**
```bash
# Filtros de obras
python main.py --export-excel --filter "- Obra"

# Building Units específicos
python main.py --export-excel --building-units 1,2

# Período específico
python main.py --export-excel --start-date 2024-01-01 --end-date 2024-12-31

# Desabilitar merge
python main.py --export-excel --disable-merge
```

### **Ferramentas de Gestão**
```bash
# Gerenciar filtros de obras
python tools/manage_filters.py

# Configurar Building Units
python tools/manage_building_units.py

# Configurar merge
python tools/manage_merge_centros.py

# Testar apenas títulos
python teste_titulos_api.py
```

---

## ⚙️ Configuração

### **Variáveis de Ambiente (.env)**
```env
# API Sienge
SIENGE_USER=seu_usuario
SIENGE_PASSWORD=sua_senha
SIENGE_SUBDOMAIN=seu_subdominio

# Cache
CACHE_ENABLED=true
CACHE_VALIDITY_HOURS=24

# Building Units
BUILDING_UNIT_FILTER_ENABLED=true
BUILDING_UNIT_IDS_ALLOWED=1,2
```

### **Filtros de Obras (JSON)**
```json
{
  "modo": "excluir",
  "filtros": {
    "por_id": {"valores": [9920, 9921]},
    "por_nome_contem": {"valores": ["teste"]},
    "por_empresa": {"valores": []}
  }
}
```

### **Filtros de Títulos (JSON)**
```json
{
  "periodo": {
    "data_inicio": "2000-01-01",
    "data_fim": "2080-12-31"
  },
  "filtros": {
    "tipos_documento": {
      "valores": ["NFS", "PCT", "DUP", "BOL"]
    }
  }
}
```

---

## 📊 Estrutura dos Dados

### **Colunas do Excel (23 colunas fixas)**
| Coluna | Descrição | Origem |
|--------|-----------|---------|
| `Building_ID` | ID da obra | API |
| `Obra` | Nome da obra | API |
| `Insumo_ID` | ID do recurso/título | API/Gerado |
| `Insumo` | Nome do insumo/fornecedor | API |
| `Código_Recurso` | Código do recurso | API |
| `Categoria` | Categoria do recurso | API |
| `Tipo_Documento` | APROPRIADO/PENDENTE/ORÇADO | Processado |
| `Apropriação_Completa` | Código + descrição | Processado |
| `Código_Apropriação` | Código WBS | API |
| **`Nível_1`** | **1º nível hierárquico** | **WBS** |
| **`Nível_2`** | **2º nível hierárquico** | **WBS** |
| **`Nível_3`** | **3º nível hierárquico** | **WBS** |
| **`Nível_4`** | **4º nível hierárquico** | **WBS** |
| `Quantidade` | Quantidade do recurso | API |
| `Valor_Unitário` | Valor por unidade | Calculado |
| `Valor_Total` | Valor total | API |
| `Data` | Data do documento | API |
| `Status` | Status do lançamento | Processado |

### **Tipos de Lançamentos**
- **APROPRIADO:** Recursos já consumidos nas obras
- **PENDENTE:** Recursos em processo + títulos a pagar
- **ORÇADO:** Previsão orçamentária sem consumo real

---

## 🔄 Fluxo de Processamento

### **1. Coleta de Dados**
```
API Sienge → Obras → Recursos → Apropriações
siengeAPI → Títulos → Apropriações para obras
```

### **2. Processamento (Ordem Crítica)**
```
1. Processar dados brutos (obras + títulos)
2. Aplicar merge de obras (consolida obras origem → destino)
3. Aplicar merge de centros (transforma códigos)
4. Buscar WBS das obras finais (após merge)
5. Enriquecer com hierarquia (níveis 1-4)
6. Gerar Excel
```

### **3. Merge Inteligente**
- **Obras:** Move apenas lançamentos APROPRIADOS para obra destino
- **Centros:** Transforma códigos conforme mapeamento
- **WBS:** Usa estrutura da obra destino (pós-merge)

---

## 🛠️ Dependências Principais

```python
# APIs e HTTP
requests
siengeAPI  # Biblioteca específica do cliente

# Excel e dados
openpyxl
pandas (implícito)

# Configuração
python-dotenv
pathlib

# Logs e utilitários
logging
datetime
typing
```

---

## 📝 Logs e Debug

### **Níveis de Log**
```bash
# Normal
python main.py --export-excel

# Detalhado
python main.py --export-excel --verbose

# Apenas erros
python main.py --export-excel --quiet
```

### **Arquivos de Log**
- `src/data/logs/insumos_orcamento_YYYYMMDD.log`
- Rotação diária automática
- Logs estruturados em JSON para análise

---

## 🎯 Casos de Uso

### **1. Análise Financeira**
- Comparar apropriado vs orçado por obra
- Identificar títulos pendentes por obra
- Análise de custos por categoria

### **2. Controle de Obras**
- Acompanhamento por Building Unit
- Hierarquia de apropriações (4 níveis)
- Merge de obras para consolidação

### **3. Fluxo de Caixa**
- Títulos a pagar por vencimento
- Apropriações pendentes
- Previsão de desembolsos

---

## ⚠️ Limitações e Observações

1. **Cache de títulos desabilitado** (base muito pesada)
2. **Building Units filtráveis** (padrão: apenas ID 1)
3. **Merge irreversível** (sempre usar em cópia dos dados)
4. **WBS dependente** do orçamento das obras
5. **Biblioteca siengeAPI** necessária para títulos

---

## 🔮 Roadmap/Melhorias Futuras

- [ ] Interface web para configuração
- [ ] API REST para integração externa
- [ ] Dashboard em tempo real
- [ ] Alertas automáticos por email
- [ ] Integração com Power BI
- [ ] Histórico de execuções
- [ ] Backup automático de configurações

---

**Última atualização:** Julho 2025  
**Versão:** 4.0 com Títulos Integrados