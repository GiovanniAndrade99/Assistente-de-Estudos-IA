"""Detector de frases que parecem instruções para a IA dentro dos PDFs.

Não bloqueia nada: os prompts (backend/prompts.py) já tratam o material como texto
e neutralizam as marcações. O alerta só avisa quem gerencia a disciplina para
conferir o arquivo (`documentos.alerta_instrucoes`). Busca em português e inglês.
"""
import re
import unicodedata

_PADROES = [
    # "ignore/desconsidere/esqueça as instruções (anteriores)"
    # ("ignora", indicativo, fica de fora: "o compilador ignora comentários" é texto comum)
    r"\b(ignore|ignorem|desconsiderem?|esque[cç]am?)\b.{0,30}\b(instru[cç](ao|oes)|regras|prompt)",
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|earlier|all|your)\b.{0,20}\b(instructions?|rules|prompts?)",
    # "a partir de agora você é / from now on you are"
    r"\ba partir de agora,? (voce|tu)\b",
    r"\bfrom now on,? you\b",
    # pedidos para revelar o prompt
    r"\b(revele|mostre|repita|imprima)\b.{0,30}\b(suas|as|o)\b.{0,15}\b(instru[cç](ao|oes)|prompt)",
    r"\b(reveal|print|repeat|show)\b.{0,20}\b(your|the)\b.{0,15}\b(system )?(prompt|instructions)",
    r"\b(prompt|instru[cç](ao|oes)) do sistema\b",
    r"\bsystem prompt\b",
    # troca de papel
    r"\b(aja|atue|finja ser|fa[cç]a de conta que [eé])\b.{0,20}\b(como|um|uma)\b.{0,30}\b(ia|assistente|modelo|chatbot)\b",
    r"\b(act as|pretend to be|you are now)\b.{0,20}\b(an? )?(ai|assistant|chatbot|model|dan)\b",
    r"\b(jailbreak|dan mode|developer mode|modo desenvolvedor)\b",
    # marcações de prompt dentro do texto
    r"<\s*/?\s*(trecho|documento|pergunta|system|instructions?)\b",
]
_REGEX = re.compile("|".join(f"(?:{p})" for p in _PADROES), re.IGNORECASE)


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def frases_suspeitas(texto: str, limite: int = 5) -> list[str]:
    """Trechos do texto que parecem comandos para a IA (no máximo `limite`)."""
    normalizado = _sem_acentos(texto).replace("\n", " ")
    return [m.group(0)[:120] for m, _ in zip(_REGEX.finditer(normalizado), range(limite))]


def contem_instrucoes(paginas) -> bool:
    """True se alguma página tiver frase que parece instrução para a IA."""
    return any(frases_suspeitas(texto, limite=1) for texto in paginas)
