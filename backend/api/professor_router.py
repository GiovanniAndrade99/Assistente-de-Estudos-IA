from fastapi import APIRouter, Depends

from ..aplicacao import professor_service
from .dependencias import acesso_disciplina, somente_professor

# somente_professor barra alunos; acesso_disciplina barra professor de outra matéria
router = APIRouter(
    prefix="/api/professor",
    dependencies=[Depends(somente_professor), Depends(acesso_disciplina)],
)


@router.get("/perguntas")
def perguntas_dos_alunos(disciplina_id: int):
    return professor_service.perguntas_dos_alunos(disciplina_id)


@router.get("/notas")
def notas_dos_alunos(disciplina_id: int):
    return professor_service.notas_dos_alunos(disciplina_id)


@router.get("/alunos")
def alunos_da_disciplina(disciplina_id: int):
    return professor_service.alunos_da_disciplina(disciplina_id)
