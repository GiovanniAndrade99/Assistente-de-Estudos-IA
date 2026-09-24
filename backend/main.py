"""API do Assistente de Estudos (FastAPI).

Rodar a partir da pasta raiz do projeto:
    uvicorn backend.main:app --reload --port 8002
e abrir http://localhost:8002

Este arquivo é só a "montagem" da aplicação (app factory): configura logging,
registra a middleware de observabilidade, inclui os routers e os exception
handlers, e por último monta o frontend estático. Toda a regra de negócio
mora em backend/aplicacao/*, e o acesso a dados em backend/infraestrutura/*.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .api import (
    auth_router, chat_router, disciplinas_router, documentos_router, estudo_router,
    ia_router, professor_router, progresso_router, saude_router, suporte_router, turma_router,
)
from .aplicacao import demo_service
from .excecoes import registrar_handlers
from .infraestrutura import db
from .infraestrutura.logging_setup import configurar_logging
from .middlewares.observabilidade import ObservabilidadeMiddleware

configurar_logging(config.LOG_LEVEL)
db.criar_tabelas()
for _disciplina in db.consultar("SELECT id FROM disciplinas"):
    demo_service.popular_dados_demo(_disciplina["id"])

app = FastAPI(title="Assistente de Estudos")
app.add_middleware(ObservabilidadeMiddleware)
registrar_handlers(app)

for router in (
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
):
    app.include_router(router)

# O próprio FastAPI serve o frontend (HTML/CSS/JS). Precisa ficar por último.
app.mount("/", StaticFiles(directory=config.PASTA_FRONTEND, html=True), name="frontend")
