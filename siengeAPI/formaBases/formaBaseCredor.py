from consultas import credores
import json

basein = credores.importaCredores()

destbase = open('baseInCredor.json', mode='w', encoding='utf-8')

json.dump(basein, destbase)

print('Base salva!')
print('------------------------------')