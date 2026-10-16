// Preenche o aviso de privacidade com os dados desta instalação (GET /api/privacidade):
// controlador, encarregado, prazos de retenção e plano do provedor de IA.

function campo(nome) {
  return document.querySelector(`[data-campo="${nome}"]`);
}

function texto(nome, valor) {
  const el = campo(nome);
  if (el) el.textContent = valor;
}

function linhaRetencao(dado, prazo) {
  const tr = document.createElement("tr");
  for (const valor of [dado, prazo]) {
    const td = document.createElement("td");
    td.textContent = valor;
    tr.appendChild(td);
  }
  return tr;
}

function meses(n) {
  return n > 0 ? `${n} ${n === 1 ? "mês" : "meses"}` : "Enquanto a conta existir";
}

async function preencher() {
  let dados;
  try {
    const resposta = await fetch("/api/privacidade");
    if (!resposta.ok) throw new Error();
    dados = await resposta.json();
  } catch {
    return;  // sem a API, o texto fixo do aviso continua valendo
  }

  texto("versao", dados.versao);
  texto("idade", dados.idade_minima);
  texto("prazo", dados.prazo_resposta_dias);
  texto("sessao-dias", dados.retencao.sessao_dias);

  const { controlador, encarregado } = dados;
  texto("controlador", controlador.nome
    ? `${controlador.nome}${controlador.contato ? ` · ${controlador.contato}` : ""}`
    : "Ainda não informado pelo responsável por este servidor.");
  texto("encarregado", encarregado.nome || encarregado.email
    ? [encarregado.nome, encarregado.email].filter(Boolean).join(" · ")
    : "Não indicado. Use o Suporte ou o contato do controlador.");
  texto("contato-direitos", encarregado.email || controlador.contato || "use o Suporte do sistema.");
  document.getElementById("aviso-config").hidden = Boolean(controlador.nome);

  texto("plano-ia", dados.provedor_ia.plano_pago
    ? "Este servidor usa o plano pago da API Gemini: o Google não usa o conteúdo enviado para melhorar seus produtos e o trata conforme seus termos de processamento de dados."
    : "Atenção: este servidor usa o plano gratuito da API Gemini. Nesse plano o Google pode usar o conteúdo enviado para melhorar seus produtos, inclusive com revisão humana. Não coloque dados pessoais seus ou de outras pessoas nas perguntas nem nos PDFs.");

  if (dados.provedor_email) {
    const el = campo("provedor-email");
    el.textContent = `E-mails da conta (confirmação e recuperação de senha) são enviados por ${dados.provedor_email}, que recebe seu nome e e-mail só para a entrega.`;
    el.hidden = false;
  }

  const r = dados.retencao;
  document.getElementById("tabela-retencao").append(
    linhaRetencao("Sessão de login", `${r.sessao_dias} dias, ou até você sair`),
    linhaRetencao("Pseudônimos de e-mail das tentativas de login", `${r.tentativas_login_minutos} minutos`),
    linhaRetencao("Pseudônimos de IP e contadores de uso", "1 dia"),
    linhaRetencao("Perguntas ao assistente, notas de simulado e eventos", meses(r.historico_meses)),
    linhaRetencao("Trilha até a prova", `${meses(r.historico_meses)} depois da data-alvo, ou até você apagar`),
    linhaRetencao("Seu baralho de flashcards", "Até você apagar os cartões ou excluir a conta"),
    linhaRetencao("Mensagens do chat da turma", meses(r.mensagens_meses)),
    linhaRetencao("Chamados de suporte já respondidos", meses(r.chamados_meses)),
    linhaRetencao("Cópias de segurança (backups)", `${r.backup_dias} dias`),
    linhaRetencao("Respostas da IA guardadas para perguntas repetidas (sem identificar quem perguntou)",
      `${r.cache_respostas_dias} dias, ou até o material da disciplina mudar`),
  );
}

preencher();
