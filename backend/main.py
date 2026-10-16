"""API do Assistente de Estudos (FastAPI).

Rodar a partir da pasta raiz do projeto:
    uvicorn backend.main:app --port 8002
e abrir http://localhost:8002

Este arquivo é só a "montagem" da aplicação (app factory): configura logging,
registra as middlewares, inclui os routers e os exception handlers, e por
último monta o frontend estático. Toda a regra de negócio mora em
backend/aplicacao/*, e o acesso a dados em backend/infraestrutura/*.

O que antes rodava na importação (criar tabelas, dados de demonstração) fica no
`lifespan`, para os testes montarem a aplicação com um banco temporário sem
tocar em data/app.db.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .api import (
    admin_router, auth_router, chat_router, conta_router, disciplinas_router, documentos_router, estudo_router,
    ia_router, privacidade_router, professor_router, progresso_router, saude_router, suporte_router,
    turma_router,
)
from .aplicacao import demo_service, retencao_service
from .excecoes import registrar_handlers
from .infraestrutura import db
from .infraestrutura.logging_setup import configurar_logging
from .middlewares.observabilidade import ObservabilidadeMiddleware

ROUTERS = (
    saude_router.router,
    auth_router.router,
    disciplinas_router.router,
    documentos_router.router,
    chat_router.router,
    estudo_router.router,
    turma_router.router,
    professor_router.router,
    progresso_router.router,
    suporte_router.router,
    ia_router.router,
    privacidade_router.router,
    conta_router.router,
    admin_router.router,
)


logger = logging.getLogger("app")


def _conferir_configuracao() -> None:
    problemas = config.problemas_de_configuracao()
    if problemas and config.APP_ENV == "production":
        raise RuntimeError("Configuração incompleta para produção: " + " ".join(problemas))
    for problema in problemas:
        logger.warning("configuracao_incompleta", extra={"problema": problema})


def _preparar_dados() -> None:
    config.PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)
    db.criar_tabelas()
    if config.DADOS_DEMO:
        for disciplina in db.consultar("SELECT id FROM disciplinas"):
            demo_service.popular_dados_demo(disciplina["id"])


async def _limpeza_periodica() -> None:
    while True:
        await asyncio.sleep(config.INTERVALO_LIMPEZA_HORAS * 3600)
        try:
            await asyncio.to_thread(retencao_service.executar_limpeza)
        except Exception:
            logger.exception("limpeza_falhou")


def criar_app(iniciar_tarefas: bool = True) -> FastAPI:
    """Monta a aplicação. `iniciar_tarefas=False` é usado nos testes: não sobe
    tarefas de fundo (limpeza periódica, fila de indexação)."""

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        _conferir_configuracao()
        _preparar_dados()
        tarefas = []
        if iniciar_tarefas:
            await asyncio.to_thread(retencao_service.executar_limpeza)
            tarefas.append(asyncio.create_task(_limpeza_periodica()))
        try:
            yield
        finally:
            for tarefa in tarefas:
                tarefa.cancel()

    producao = config.APP_ENV == "production"
    app = FastAPI(
        title="Assistente de Estudos",
        lifespan=ciclo_de_vida,
        # Documentação automática da API só fora de produção: ela expõe todas as rotas.
        docs_url=None if producao else "/docs",
        redoc_url=None if producao else "/redoc",
        openapi_url=None if producao else "/openapi.json",
    )
    app.state.iniciar_tarefas = iniciar_tarefas
    app.add_middleware(ObservabilidadeMiddleware)
    registrar_handlers(app)
    for router in ROUTERS:
        app.include_router(router)

    # O próprio FastAPI serve o frontend (HTML/CSS/JS). Precisa ficar por último.
    app.mount("/", StaticFiles(directory=config.PASTA_FRONTEND, html=True), name="frontend")
    return app


configurar_logging(config.LOG_LEVEL)
app = criar_app()
