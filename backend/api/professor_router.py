from fastapi import APIRouter, Depends

from ..aplicacao import professor_service
from .dependencias import professor_da_disciplina

router = APIRouter()


@router.get("/api/professor/perguntas")
def perguntas_dos_alunos(disciplina_id: int, professor: dict = Depends(professor_da_disciplina)):
    return professor_service.perguntas_dos_alunos(disciplina_id)


@router.get("/api/professor/notas")
def notas_dos_alunos(disciplina_id: int, professor: dict = Depends(professor_da_disciplina)):
    return professor_service.notas_dos_alunos(disciplina_id)
