from fastapi import APIRouter, Depends
from fastapi.responses import Response

from ..aplicacao import professor_service
from .dependencias import professor_da_disciplina

router = APIRouter()


@router.get("/api/professor/perguntas")
def perguntas_dos_alunos(disciplina_id: int, professor: dict = Depends(professor_da_disciplina)):
    return professor_service.perguntas_dos_alunos(disciplina_id)


@router.get("/api/professor/notas")
def notas_dos_alunos(disciplina_id: int, professor: dict = Depends(professor_da_disciplina)):
    return professor_service.notas_dos_alunos(disciplina_id)


@router.get("/api/professor/temas")
def temas_das_duvidas(disciplina_id: int, professor: dict = Depends(professor_da_disciplina)):
    return professor_service.temas_das_duvidas(disciplina_id)


@router.get("/api/professor/reforcar")
def o_que_reforcar(disciplina_id: int, professor: dict = Depends(professor_da_disciplina)):
    return professor_service.o_que_reforcar(disciplina_id)


@router.get("/api/professor/notas.csv")
def notas_csv(disciplina_id: int, professor: dict = Depends(professor_da_disciplina)):
    return Response(
        professor_service.notas_csv(disciplina_id),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="notas-disciplina-{disciplina_id}.csv"',
                 "Cache-Control": "no-store"},
    )
