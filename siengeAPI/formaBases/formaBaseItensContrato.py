from consultas.API import origem
import json, csv
import datetime

baseInicial = open('bases\\baseInContratosPreco.json', mode='r', encoding='utf-8')

baseContratos = open('bases\\baseContratosItens.json', mode='r', encoding='utf-8')

contratosIniciais = json.load(baseInicial)
contratos = json.load(baseContratos)

buildingUnitsId = [1, 2, 3, 4]
dados = {}

baseContratosItensArq = open('bases\\baseContratosItens2.json', mode='w', encoding='utf-8')

contagem = 0
inicio = datetime.datetime.now()
arqcsv = csv.writer(open('contratos.csv', mode='w', encoding='utf-8', newline=''), delimiter=';')
arqcsv.writerow(['obra', 'contrato', 'tipoDoc', 'status', 'valorContrato', 'valordositens'])

for x in contratos:
    contrato = contratos[x]['contrato']
    itenscontrato = contratos[x]['itens']    
    dadosContrato = {
        "documentId=": contrato['documentId'],
        "&contractNumber=": contrato['contractNumber'],
        "&buildingId=": contrato['buildings'][0]['buildingId'],
    }

    valorTotalContrato = contrato['totalLaborValue'] + contrato['totalMaterialValue']
    valorTotalDosItens = 0
    
    for item in itenscontrato:

        if item['laborPrice'] == None:
            valorMo = 0
        else:
            valorMo = item['laborPrice']
        
        if item['materialPrice'] == None:
            valorMaterial = 0
        else:
            valorMaterial = item['materialPrice']
        
        valorUnit = valorMo + valorMaterial

        if item['quantity'] == None:
            quantidade = 0
        else:
            quantidade = item['quantity']

        valorTotalDosItens += round(valorUnit*quantidade, 2)
    
    print('Valor Contrato:', valorTotalContrato, '- Valor dos itens:', round(valorTotalDosItens,2))
    arqcsv.writerow([dadosContrato['&buildingId='], 
                     dadosContrato['&contractNumber='], 
                     dadosContrato['documentId='],
                     contrato['status'],
                     str(valorTotalContrato).replace('.', ','),
                     str(valorTotalDosItens).replace('.', ',')])
    
    for bUID in buildingUnitsId:
        if contrato not in contratosIniciais:
            try:

                consulta = origem.consultaItensContratos(contrato, bUID)

                if 'status' not in consulta:
                    
                    contagem += 1

                    if divmod(contagem, 10)[1] == 0:

                        tempoPassado = datetime.datetime.now()-inicio
                        tempoMedio = tempoPassado/contagem
                        faltantes = len(contratos)-contagem
                        print(contagem, 'contratos puxados! Faltam', faltantes)
                        print('Previsao de acabar em ', round(((faltantes*tempoMedio).seconds)/60, 2), 'minutos')

                    dados[str(len(dados.keys()))] = {
                        'contrato': contrato,
                        'itens': consulta,
                    }

                    break
            except:

                print('Erro! Salvar consultas já feitas')
                json.dump(dados, baseContratosItensArq)
                exit()

print(contagem, 'consultas realizadas com sucesso!')

baseConsultada = []

for chave in contratos:

    contrato = contratos[chave]['contrato']
    baseConsultada.append(contrato)


#for contrato in contratosIniciais:
#    if contrato not in baseConsultada:
#        print(contrato)
#    else:
#        print('contrato achado')
#json.dump(dados, baseContratosItensArq)