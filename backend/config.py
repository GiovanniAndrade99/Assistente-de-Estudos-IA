"""Configurações do projeto, lidas do arquivo .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
# Os testes definem CARREGAR_DOTENV=0 para não herdar a chave do Gemini e outros
# valores reais do .env local.
if os.getenv("CARREGAR_DOTENV", "1") != "0":
    load_dotenv(RAIZ / ".env")


def _bool(nome: str, padrao: bool) -> bool:
    valor = os.getenv(nome, "").strip().lower()
    if not valor:
        return padrao
    return valor in ("1", "true", "sim", "yes", "on")


# "production" liga cookie seguro (HTTPS) e cabeçalho HSTS; em dev (http://localhost)
# isso quebraria o teste local, então o padrão é "development".
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Dados fictícios (alunos e mensagens de exemplo) para demonstrar o chat e o calendário.
# Ligado por padrão só fora de produção: numa turma real eles confundiriam os alunos.
DADOS_DEMO = _bool("DADOS_DEMO", APP_ENV != "production")

TAMANHO_MAX_UPLOAD_MB = int(os.getenv("TAMANHO_MAX_UPLOAD_MB", "20"))
DURACAO_SESSAO_SEGUNDOS = 60 * 60 * 24 * 7  # 7 dias

# Rate limit de login/cadastro (proteção contra força bruta)
LIMITE_TENTATIVAS_LOGIN = 5           # falhas por e-mail na janela
JANELA_TENTATIVAS_LOGIN_MINUTOS = 15
# Por IP, a cada 15 minutos. Numa sala de aula muitos alunos saem pelo mesmo IP,
# então os números não podem ser baixos demais.
LIMITE_CADASTROS_POR_IP = int(os.getenv("LIMITE_CADASTROS_POR_IP", "10"))
LIMITE_LOGINS_POR_IP = int(os.getenv("LIMITE_LOGINS_POR_IP", "100"))

# Segredo do servidor para pseudonimizar (HMAC) IPs e e-mails guardados só para
# limitar tentativas. Obrigatório em produção; gere com:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
SEGREDO_APP = os.getenv("SEGREDO_APP", "")

# Retenção (LGPD, arts. 15 e 16): passado o prazo, os dados são apagados pela limpeza
# automática (aplicacao/retencao_service.py). 0 desliga a regra.
RETENCAO_HISTORICO_MESES = int(os.getenv("RETENCAO_HISTORICO_MESES", "12"))  # perguntas, notas e eventos
RETENCAO_MENSAGENS_MESES = int(os.getenv("RETENCAO_MENSAGENS_MESES", "12"))  # chat da turma
RETENCAO_CHAMADOS_MESES = int(os.getenv("RETENCAO_CHAMADOS_MESES", "12"))    # chamados já respondidos
RETENCAO_BACKUP_DIAS = int(os.getenv("RETENCAO_BACKUP_DIAS", "30"))
INTERVALO_LIMPEZA_HORAS = float(os.getenv("INTERVALO_LIMPEZA_HORAS", "6"))

# Transparência (LGPD, arts. 9º e 41): quem trata os dados e como falar com essa pessoa.
# Aparecem no aviso de privacidade (/privacidade.html). Obrigatórios em produção.
CONTROLADOR_NOME = os.getenv("CONTROLADOR_NOME", "")
CONTROLADOR_CONTATO = os.getenv("CONTROLADOR_CONTATO", "")      # e-mail ou endereço
ENCARREGADO_NOME = os.getenv("ENCARREGADO_NOME", "")
ENCARREGADO_EMAIL = os.getenv("ENCARREGADO_EMAIL", "")
# Mudou o aviso de privacidade? Troque a versão: todos confirmam a leitura de novo.
POLITICA_PRIVACIDADE_VERSAO = os.getenv("POLITICA_PRIVACIDADE_VERSAO", "2026-10-16")
# Os termos da API do Gemini exigem 18 anos ou mais e proíbem apps de acesso provável
# por menores. Só baixe este número se trocar de provedor de IA.
IDADE_MINIMA = int(os.getenv("IDADE_MINIMA", "18"))
# true só depois de ativar o faturamento no projeto do Gemini: no plano gratuito o
# Google pode usar o conteúdo enviado para melhorar produtos, com revisão humana.
GEMINI_PLANO_PAGO = _bool("GEMINI_PLANO_PAGO", False)

# E-mail transacional (confirmação de e-mail, recuperação e troca de senha). Qualquer
# provedor SMTP serve. Sem SMTP_HOST: em desenvolvimento o link vai só para o log;
# em produção esses recursos respondem 503.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORTA = int(os.getenv("SMTP_PORTA", "587"))        # 587 = STARTTLS; 465 = SSL direto
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
SMTP_SENHA = os.getenv("SMTP_SENHA", "")
SMTP_REMETENTE = os.getenv("SMTP_REMETENTE", "")
SMTP_PROVEDOR_NOME = os.getenv("SMTP_PROVEDOR_NOME", "")  # aparece no aviso de privacidade (operador)
# Endereço público do site, usado nos links dos e-mails
APP_URL_BASE = os.getenv("APP_URL_BASE", "http://localhost:8002").rstrip("/")

# Origens extras aceitas em requisições que alteram dados (separadas por vírgula),
# para quando o frontend for servido de outro endereço. A própria origem é sempre aceita.
ORIGENS_PERMITIDAS = [
    o.strip().rstrip("/") for o in os.getenv("ORIGENS_PERMITIDAS", "").split(",") if o.strip()
]

# Exigido no cadastro para criar conta de professor (ver .env.example).
CODIGO_PROFESSOR = os.getenv("CODIGO_PROFESSOR", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

# Modelos reserva: se o principal estiver sobrecarregado (503), sem cota (429)
# ou demorar demais, o app tenta o próximo da lista.
GEMINI_MODELOS_RESERVA = [
    m.strip() for m in os.getenv("GEMINI_MODELS_FALLBACK", "gemini-3.5-flash,gemini-3.1-flash-lite").split(",")
    if m.strip()
]
TEMPO_LIMITE_SEGUNDOS = 60  # por tentativa

# Onde ficam banco, PDFs e índice. Configurável para rodar uma cópia isolada (testes, avaliação).
PASTA_DADOS = Path(os.getenv("PASTA_DADOS", str(RAIZ / "data")))
PASTA_UPLOADS = PASTA_DADOS / "uploads"
PASTA_BACKUPS = Path(os.getenv("PASTA_BACKUPS", str(RAIZ / "backups")))
PASTA_INDICE = PASTA_DADOS / "indice"
PASTA_FRONTEND = RAIZ / "frontend"

# Parâmetros do RAG (bons candidatos para experimentar e comparar no relatório)
TAMANHO_TRECHO = 1000   # caracteres por trecho (chunk)
SOBREPOSICAO = 200      # caracteres repetidos entre trechos vizinhos
TOP_K = 5               # quantos trechos são enviados ao modelo por pergunta

PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)
PASTA_INDICE.mkdir(parents=True, exist_ok=True)


def problemas_de_configuracao() -> list[str]:
    """O que falta configurar. Em produção, qualquer item impede o servidor de subir."""
    problemas = []
    if not SEGREDO_APP:
        problemas.append("SEGREDO_APP não definido: IPs e e-mails do controle de tentativas ficariam sem segredo fixo.")
    if not CONTROLADOR_NOME or not CONTROLADOR_CONTATO:
        problemas.append("CONTROLADOR_NOME e CONTROLADOR_CONTATO são obrigatórios (LGPD, art. 9º).")
    if IDADE_MINIMA < 18:
        problemas.append("IDADE_MINIMA abaixo de 18: os termos da API do Gemini não permitem.")
    return problemas

