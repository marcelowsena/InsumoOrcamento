import datetime
import os

def monitoraProgresso(inicio, tamanhoConsulta, progresso, intervalo, mensagem=''):
    if divmod(progresso, intervalo)[1] == 0:
        os.system('cls')
        tempoPassado = datetime.datetime.now()-inicio
        tempoMedio = tempoPassado/progresso
        faltantes = tamanhoConsulta-progresso

        print(mensagem)
        print(progresso, 'itens consultados/processados ! Faltam', faltantes)
        

        tempoRestante = round(((faltantes*tempoMedio).seconds)/60, 2)
        minutos = str(int(divmod(tempoRestante, 1)[0]))
        segundos = str(int(round(divmod(tempoRestante, 1)[1]*60, 0)))

        print('Previsao de acabar em ', minutos+':'+segundos)