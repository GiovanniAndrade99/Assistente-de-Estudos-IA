from fastapi import APIRouter, Depends

from ..aplicacao import professor_service
from .dependencias import professor_da_disciplina

# professor_da_disciplina barra alunos e professor de outra matéria
router = APIRouter(prefix="/api/professor", dependencies=[Depends(professor_da_disciplina)])


@router.get("/perguntas")
def perguntas_dos_alunos(disciplina_id: int):
    return professor_service.perguntas_dos_alunos(disciplina_id)


@router.get("/notas")
def notas_dos_alunos(disciplina_id: int):
    return professor_service.notas_dos_alunos(disciplina_id)


@router.get("/alunos")
def alunos_da_disciplina(disciplina_id: int):
    return professor_service.alunos_da_disciplina(disciplina_id)
