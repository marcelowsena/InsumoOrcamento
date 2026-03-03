# SiengeAPI

Biblioteca Python para integração com a API do Sienge, facilitando consultas e manipulação de dados.

## Instalação

### Instalação Local
```bash
pip install -e .
```

### Instalação via Git
```bash
pip install git+https://github.com/seu-usuario/siengeapi.git
```

## Uso Básico

```python
from siengeapi import consultas, bases

# Consultar NFEs
nfes = consultas.nf.consultaNFES()

# Carregar base de credores
credores = bases.carregabases.credor()

# Atualizar bases
from siengeapi.bases import atualizaBases
atualizaBases.contratos(dados_contratos)
```

## Principais Módulos

- **consultas.API.origem**: Consultas de pedidos, contratos, EAP
- **consultas.nf**: Consultas de notas fiscais e títulos
- **consultas.credores**: Gestão de credores
- **bases.carregabases**: Carregamento de bases locais
- **bases.atualizaBases**: Atualização de bases

## Estrutura de Dados

### Consultas de Contrato
```python
contrato = consultas.API.origem.consultaContratos()
itens = consultas.API.origem.consultaItensContratos(contrato, building_unit_id)
```

### NFEs e Pagamentos
```python
nfes = consultas.nf.consultaNFES(data_inicial)
pagamentos = consultas.nf.consultaPgtsNFE(chave_nfe)
```

## Configuração

1. Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

2. Configure suas credenciais no arquivo `.env`:
```bash
SIENGE_USER=seu_usuario_aqui
SIENGE_PASSWORD=sua_senha_aqui
SIENGE_BASE_URL=https://api.sienge.com.br/trust/public/api/v1
```

**Importante**: Nunca commite o arquivo `.env` no Git!