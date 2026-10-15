"""Erros com mensagem pensada para quem usa o sistema.

`ErroDeUso` vai para o frontend com a mensagem como está. Qualquer outro
ValueError/RuntimeError vira uma mensagem genérica (excecoes.py), porque o texto
de exceções de bibliotecas pode trazer caminhos do servidor e outros detalhes
internos.
"""


class ErroDeUso(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
