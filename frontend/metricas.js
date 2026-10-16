// Tela "Métricas de uso" (só admin): contagens diárias anônimas e custo da API de IA.

const ROTULOS_METRICAS = {
  cadastro_aluno: "Cadastros de alunos", cadastro_professor: "Cadastros de professores", login: "Logins",
  pergunta_chat: "Perguntas ao assistente", primeira_pergunta: "Primeira pergunta (ativação)",
  resumo: "Resumos", flashcards: "Flashcards", simulado_gerado: "Simulados gerados",
  simulado_corrigido: "Simulados corrigidos", upload_pdf: "PDFs enviados", dados_exportados: "Dados exportados",
  conta_excluida: "Contas excluídas", chamadas_ia: "Chamadas à IA", tokens_entrada: "Tokens de entrada",
  tokens_saida: "Tokens de saída", respostas_do_cache: "Respostas do cache",
};
const COLUNAS_DIA = ["login", "pergunta_chat", "simulado_corrigido", "upload_pdf", "chamadas_ia", "tokens_entrada", "tokens_saida"];

const numero = (n) => (n || 0).toLocaleString("pt-BR");

TELAS.metricas = {
  abrir() {
    carregarMetricas();
  },
};

$("periodo-metricas").onchange = carregarMetricas;

async function carregarMetricas() {
  const dias = $("periodo-metricas").value;
  let dados;
  try {
    dados = await chamarApi(`/api/admin/metricas?dias=${dias}`);
  } catch (erro) {
    $("resumo-metricas").innerHTML = `<p class="erro">${escaparHtml(erro.message)}</p>`;
    return;
  }
  const t = dados.totais;
  const blocos = [
    ["Alunos", dados.contas.alunos], ["Professores", dados.contas.professores],
    ["Ativos nos últimos 7 dias", dados.contas.ativos_7_dias], ["Perguntas ao assistente", t.pergunta_chat],
    ["Simulados corrigidos", t.simulado_corrigido], ["Chamadas à IA", t.chamadas_ia],
    ["Tokens (entrada + saída)", (t.tokens_entrada || 0) + (t.tokens_saida || 0)],
  ];
  const ia = dados.ia_hoje;
  blocos.push(["Respostas do cache (sem custo)", t.respostas_do_cache], ["Tokens hoje", ia.tokens]);
  const limiteHoje = ia.teto || ia.alerta;
  const passouAlerta = ia.alerta && ia.tokens >= ia.alerta;
  $("resumo-metricas").innerHTML = blocos
    .map(([rotulo, valor]) => `<div class="bloco-metrica"><strong>${numero(valor)}</strong><span>${rotulo}</span></div>`)
    .join("") + `
    <p class="dica bloco-largo">
      ${passouAlerta ? `<span class="etiqueta laranja">Alerta: hoje já passou de ${numero(ia.alerta)} tokens</span> ` : ""}
      ${limiteHoje ? `Tokens hoje: ${numero(ia.tokens)} de ${numero(limiteHoje)} (${ia.teto ? "teto" : "alerta"}). ` : ""}
      Cota por pessoa em 24 h: ${ia.cota_aluno ? numero(ia.cota_aluno) : "sem limite"} pedidos (aluno),
      ${ia.cota_professor ? numero(ia.cota_professor) : "sem limite"} (professor). Ajuste no .env.
    </p>`;

  const tabela = $("tabela-metricas");
  if (!dados.por_dia.length) {
    tabela.innerHTML = `<tbody><tr><td>Sem uso registrado no período.</td></tr></tbody>`;
    return;
  }
  const cabecalho = `<thead><tr><th>Dia</th>${COLUNAS_DIA.map((c) => `<th>${ROTULOS_METRICAS[c]}</th>`).join("")}</tr></thead>`;
  const linhas = [...dados.por_dia].reverse().map((d) => {
    const dia = new Date(`${d.dia}T00:00:00`).toLocaleDateString("pt-BR");
    return `<tr><td>${dia}</td>${COLUNAS_DIA.map((c) => `<td class="numero">${numero(d[c])}</td>`).join("")}</tr>`;
  }).join("");
  tabela.innerHTML = `${cabecalho}<tbody>${linhas}</tbody>`;
}
