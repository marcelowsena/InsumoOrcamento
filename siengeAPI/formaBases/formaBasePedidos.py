from consultas.API import origem
import json
#pedidosCompra = origem.consultaPedidos()

#basePedTeste = json.dump(pedidosCompra, open('basePedidos.json', mode='w', encoding='utf-8'))

basePed = json.load(open('basePedidos.json', mode='r', encoding='utf-8'))

pedidos = 0
for obra in basePed:
    for ped in basePed[obra]:
        pedidos += 1

print(pedidos)