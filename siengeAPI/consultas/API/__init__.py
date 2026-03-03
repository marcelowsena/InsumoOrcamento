from . import consultaapi, origem, soliccomp
from .consultaapi import formalink, puxaDados, consultaAPI
from .origem import (
    formataData,
    consultaPedidos,
    consultaItemPedido,
    consultaTodosPedidos,
    consultaItensPedidos,
    consultaContratos,
    consultaItensContratos,
    consultaCaucao,
    bulktitulos,
    consultaObradoTitulo,
    consultaEAP,
    consultaObras,
    consultaItensSC,
    consultaItensSolicitacoesSC,
    consultaDetalheSolicitacaoSC,
    consultaInsumosObra
)
from .soliccomp import (
    consultaSC,
    consultaTodasSC,
    reprovarSC,
    reprovarItemSC,
    autorizarSC,
    autorizarItemSC
)
