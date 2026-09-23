"""Conteúdo do curso de Ciência da Computação usado por popular_curso.py.

Cada disciplina tem: semestre, carga horária, ementa, o dia da semana das aulas
(0 = segunda ... 4 = sexta), as aulas (viram PDFs indexados no RAG) e uma atividade.
Cada aula tem seções de texto e uma lista de pontos-chave.
"""

DISCIPLINAS = [
    # ------------------------------------------------------------------ 1º semestre
    {
        "nome": "Algoritmos e Programação",
        "semestre": 1, "carga": 80, "dia": 0,
        "ementa": "Conceito de algoritmo, pseudocódigo, tipos de dados, variáveis, operadores, "
                  "estruturas de decisão e repetição, funções, vetores e matrizes.",
        "aulas": [
            {
                "titulo": "Algoritmos, lógica e pseudocódigo",
                "secoes": [
                    ("O que é um algoritmo",
                     "Um algoritmo é uma sequência finita e ordenada de passos bem definidos que resolve um "
                     "problema ou realiza uma tarefa. Todo algoritmo recebe zero ou mais entradas, produz pelo "
                     "menos uma saída e precisa terminar após um número finito de passos. Cada passo deve ser "
                     "preciso (sem ambiguidade) e executável. Uma receita de bolo é o exemplo clássico, mas em "
                     "computação os passos precisam ser tão exatos que uma máquina consiga segui-los sem interpretação."),
                    ("Formas de representação",
                     "Algoritmos podem ser descritos em linguagem natural, em fluxogramas ou em pseudocódigo. A "
                     "linguagem natural é fácil de ler, porém ambígua. O fluxograma usa símbolos gráficos: elipse "
                     "para início e fim, retângulo para processamento, losango para decisão e paralelogramo para "
                     "entrada e saída. O pseudocódigo (como o Portugol) mistura português com estruturas de "
                     "programação e é a forma mais próxima de uma linguagem real, como Python ou C."),
                    ("Variáveis, tipos e operadores",
                     "Uma variável é um espaço nomeado na memória que guarda um valor que pode mudar durante a "
                     "execução. Os tipos primitivos mais comuns são inteiro, real (ponto flutuante), caractere, "
                     "cadeia de caracteres (string) e lógico (verdadeiro ou falso). Os operadores se dividem em "
                     "aritméticos (+, -, *, /, resto da divisão), relacionais (>, <, =, diferente) e lógicos (E, OU, "
                     "NÃO). A precedência define a ordem de avaliação: primeiro os aritméticos, depois os "
                     "relacionais e por último os lógicos."),
                ],
                "pontos": [
                    "Algoritmo: sequência finita, ordenada e não ambígua de passos.",
                    "Propriedades: finitude, precisão, entradas, saídas e efetividade.",
                    "Representações: linguagem natural, fluxograma e pseudocódigo.",
                    "Tipos primitivos: inteiro, real, caractere, string e lógico.",
                ],
            },
            {
                "titulo": "Estruturas de decisão e repetição",
                "secoes": [
                    ("Estruturas de decisão",
                     "As estruturas de decisão (ou condicionais) permitem que o programa escolha entre caminhos "
                     "diferentes. O 'se-então' executa um bloco apenas quando a condição é verdadeira; o "
                     "'se-então-senão' oferece um bloco alternativo para quando ela é falsa. Condicionais podem "
                     "ser encadeadas (se, senão se, senão) ou aninhadas. Quando há muitos valores possíveis para "
                     "uma mesma variável, usa-se a estrutura de seleção múltipla ('escolha-caso', ou switch/match)."),
                    ("Estruturas de repetição",
                     "Laços de repetição executam um bloco várias vezes. O laço 'enquanto' (while) testa a condição "
                     "antes de cada execução e pode nunca executar. O 'repita-até' (do-while) testa no final e "
                     "executa pelo menos uma vez. O laço 'para' (for) é usado quando o número de repetições é "
                     "conhecido e controla uma variável contadora com valor inicial, final e passo."),
                    ("Contadores, acumuladores e laços infinitos",
                     "Um contador é uma variável incrementada de um valor fixo a cada volta, usada para contar "
                     "ocorrências. Um acumulador soma valores variáveis, como o total de notas para calcular uma "
                     "média. Ambos devem ser inicializados antes do laço. Um laço infinito ocorre quando a "
                     "condição de parada nunca se torna falsa, geralmente porque a variável de controle não é "
                     "atualizada dentro do laço."),
                ],
                "pontos": [
                    "se-então-senão escolhe entre dois caminhos; escolha-caso entre vários.",
                    "enquanto testa antes (pode executar zero vezes); repita-até testa depois (ao menos uma vez).",
                    "para é indicado quando o número de repetições é conhecido.",
                    "Contadores e acumuladores precisam ser inicializados antes do laço.",
                ],
            },
            {
                "titulo": "Funções, vetores e matrizes",
                "secoes": [
                    ("Modularização com funções",
                     "Funções (ou sub-rotinas) dividem um programa em partes menores e reutilizáveis. Uma função "
                     "recebe parâmetros, executa um bloco de código e pode devolver um valor de retorno; quando "
                     "não retorna nada, costuma ser chamada de procedimento. Modularizar reduz repetição de "
                     "código, facilita testes e torna o programa mais legível."),
                    ("Passagem de parâmetros e escopo",
                     "Na passagem por valor, a função recebe uma cópia do argumento e alterações não afetam a "
                     "variável original. Na passagem por referência, a função recebe o endereço da variável e "
                     "pode modificá-la. O escopo define onde uma variável é visível: variáveis locais existem só "
                     "dentro da função; variáveis globais são visíveis em todo o programa e devem ser evitadas, "
                     "pois dificultam a manutenção. Uma função recursiva é aquela que chama a si mesma e precisa "
                     "de um caso base para parar."),
                    ("Vetores e matrizes",
                     "Um vetor (array unidimensional) guarda vários valores do mesmo tipo em posições contíguas, "
                     "acessadas por um índice, que na maioria das linguagens começa em zero. Uma matriz é um "
                     "array bidimensional, acessado por linha e coluna, útil para tabelas e imagens. Percorrer um "
                     "vetor exige um laço; percorrer uma matriz exige dois laços aninhados. Acessar um índice fora "
                     "dos limites é um erro comum."),
                ],
                "pontos": [
                    "Funções recebem parâmetros e podem devolver um valor de retorno.",
                    "Por valor: cópia; por referência: a própria variável.",
                    "Recursão exige um caso base.",
                    "Vetores são acessados por índice (geralmente a partir de 0); matrizes por linha e coluna.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Lista 1: algoritmos com decisão e repetição",
            "descricao": "1) Escreva em pseudocódigo um algoritmo que leia 10 números e mostre o maior e o menor.\n"
                         "2) Faça um algoritmo que leia a nota de N alunos e calcule a média da turma usando um acumulador.\n"
                         "3) Explique a diferença entre os laços 'enquanto' e 'repita-até' com um exemplo.",
        },
    },
    {
        "nome": "Matemática Discreta",
        "semestre": 1, "carga": 60, "dia": 2,
        "ementa": "Lógica proposicional, teoria dos conjuntos, relações, funções, "
                  "técnicas de demonstração, indução matemática e princípios de contagem.",
        "aulas": [
            {
                "titulo": "Lógica proposicional",
                "secoes": [
                    ("Proposições e conectivos",
                     "Uma proposição é uma sentença declarativa que é verdadeira ou falsa, mas não ambas. "
                     "Proposições simples são combinadas por conectivos lógicos: negação (não p), conjunção "
                     "(p e q, verdadeira só se ambas forem verdadeiras), disjunção (p ou q, falsa só se ambas "
                     "forem falsas), condicional (se p então q, falsa apenas quando p é verdadeira e q é falsa) e "
                     "bicondicional (p se e somente se q, verdadeira quando p e q têm o mesmo valor)."),
                    ("Tabelas-verdade, tautologias e contradições",
                     "A tabela-verdade lista todos os valores possíveis de uma fórmula; com n proposições há 2 "
                     "elevado a n linhas. Uma tautologia é verdadeira em todas as linhas (por exemplo, p ou não p); "
                     "uma contradição é falsa em todas (p e não p); uma contingência é verdadeira em algumas "
                     "linhas e falsa em outras."),
                    ("Equivalências lógicas",
                     "Duas fórmulas são equivalentes quando têm a mesma tabela-verdade. As leis de De Morgan "
                     "dizem que não (p e q) equivale a (não p) ou (não q), e que não (p ou q) equivale a (não p) e "
                     "(não q). A condicional p então q equivale a (não p) ou q, e também à sua contrapositiva: "
                     "se não q então não p. Essas equivalências são usadas para simplificar condições em programas."),
                ],
                "pontos": [
                    "Proposição: sentença que é verdadeira ou falsa.",
                    "A condicional só é falsa quando o antecedente é V e o consequente é F.",
                    "Com n proposições, a tabela-verdade tem 2^n linhas.",
                    "De Morgan: não(p e q) = não p ou não q; não(p ou q) = não p e não q.",
                ],
            },
            {
                "titulo": "Conjuntos, relações e funções",
                "secoes": [
                    ("Conjuntos e operações",
                     "Um conjunto é uma coleção de elementos distintos, sem ordem. As operações básicas são união "
                     "(elementos em A ou em B), interseção (elementos em A e em B), diferença (em A e não em B) e "
                     "complemento (fora de A, em relação a um universo). O conjunto das partes de A contém todos "
                     "os subconjuntos de A e, se A tem n elementos, possui 2 elevado a n elementos. O produto "
                     "cartesiano A x B é o conjunto de todos os pares ordenados (a, b)."),
                    ("Relações",
                     "Uma relação de A em B é um subconjunto de A x B. Uma relação em um conjunto pode ser "
                     "reflexiva (todo elemento se relaciona consigo), simétrica (se a R b então b R a), "
                     "antissimétrica (se a R b e b R a, então a = b) e transitiva (se a R b e b R c, então a R c). "
                     "Uma relação de equivalência é reflexiva, simétrica e transitiva; uma relação de ordem "
                     "parcial é reflexiva, antissimétrica e transitiva, como 'menor ou igual'."),
                    ("Funções",
                     "Uma função f de A em B associa cada elemento de A a exatamente um elemento de B. A é o "
                     "domínio, B o contradomínio e o conjunto dos valores atingidos é a imagem. Uma função é "
                     "injetora quando elementos diferentes têm imagens diferentes, sobrejetora quando a imagem é "
                     "todo o contradomínio e bijetora quando é injetora e sobrejetora ao mesmo tempo; só funções "
                     "bijetoras têm inversa."),
                ],
                "pontos": [
                    "Conjunto das partes de um conjunto com n elementos tem 2^n elementos.",
                    "Equivalência: reflexiva, simétrica e transitiva.",
                    "Ordem parcial: reflexiva, antissimétrica e transitiva.",
                    "Bijetora = injetora + sobrejetora; só bijeções têm inversa.",
                ],
            },
            {
                "titulo": "Indução matemática e contagem",
                "secoes": [
                    ("Técnicas de demonstração",
                     "Na prova direta, parte-se das hipóteses e chega-se à conclusão por passos lógicos. Na prova "
                     "por contraposição, prova-se que 'não q implica não p'. Na prova por contradição (redução ao "
                     "absurdo), supõe-se que a afirmação é falsa e chega-se a uma contradição; é assim que se prova "
                     "que a raiz quadrada de 2 é irracional."),
                    ("Indução matemática",
                     "A indução prova que uma propriedade P(n) vale para todo natural n a partir de um valor "
                     "inicial. Ela tem dois passos: o caso base, que mostra que P vale para o primeiro valor, e o "
                     "passo indutivo, que mostra que, se P(k) é verdadeira (hipótese de indução), então P(k+1) "
                     "também é. Um exemplo clássico é provar que 1 + 2 + ... + n = n(n+1)/2. A indução está "
                     "diretamente ligada à recursão e à prova de correção de algoritmos."),
                    ("Princípios de contagem",
                     "O princípio multiplicativo diz que, se uma tarefa tem duas etapas com m e n possibilidades, "
                     "há m x n maneiras de realizá-la. O princípio aditivo soma as possibilidades de alternativas "
                     "que não podem ocorrer juntas. Permutações contam ordenações de n elementos (n!). Arranjos "
                     "contam escolhas ordenadas de k entre n: n!/(n-k)!. Combinações contam escolhas sem ordem: "
                     "n!/(k!(n-k)!). O princípio da casa dos pombos afirma que, se n+1 objetos são postos em n "
                     "caixas, alguma caixa terá pelo menos dois objetos."),
                ],
                "pontos": [
                    "Indução: caso base + passo indutivo (P(k) implica P(k+1)).",
                    "Permutação: n!; arranjo: n!/(n-k)!; combinação: n!/(k!(n-k)!).",
                    "Casa dos pombos: n+1 objetos em n caixas implica uma caixa com dois.",
                    "Contradição: supor a negação e chegar a um absurdo.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Lista de exercícios: lógica e indução",
            "descricao": "1) Construa a tabela-verdade de (p → q) ↔ (¬q → ¬p) e classifique a fórmula.\n"
                         "2) Prove por indução que 2 + 4 + ... + 2n = n(n+1).\n"
                         "3) Quantas senhas de 4 dígitos distintos existem? Justifique com o princípio multiplicativo.",
        },
    },
    # ------------------------------------------------------------------ 2º semestre
    {
        "nome": "Estruturas de Dados",
        "semestre": 2, "carga": 80, "dia": 1,
        "ementa": "Análise de complexidade, listas encadeadas, pilhas, filas, árvores, "
                  "árvores binárias de busca, tabelas hash e algoritmos de ordenação.",
        "aulas": [
            {
                "titulo": "Complexidade de algoritmos e listas",
                "secoes": [
                    ("Notação O grande",
                     "A análise de complexidade estima como o tempo ou a memória de um algoritmo cresce com o "
                     "tamanho da entrada n. A notação O grande descreve o limite superior do crescimento no pior "
                     "caso, ignorando constantes. As classes mais comuns, da mais eficiente para a menos eficiente, "
                     "são: O(1) constante, O(log n) logarítmica, O(n) linear, O(n log n), O(n²) quadrática e O(2^n) "
                     "exponencial. A busca binária em um vetor ordenado é O(log n); a busca sequencial é O(n)."),
                    ("Listas com vetores e listas encadeadas",
                     "Uma lista pode ser implementada com vetor (alocação sequencial) ou de forma encadeada. No "
                     "vetor, o acesso por índice é O(1), mas inserir ou remover no meio exige deslocar elementos, "
                     "custando O(n). Na lista encadeada, cada nó guarda um valor e um ponteiro para o próximo; "
                     "inserir ou remover após um nó conhecido é O(1), mas acessar o i-ésimo elemento exige "
                     "percorrer a lista, custando O(n)."),
                    ("Variações de listas encadeadas",
                     "Na lista duplamente encadeada, cada nó aponta para o próximo e para o anterior, permitindo "
                     "percorrer nos dois sentidos e remover um nó sem conhecer seu antecessor. Na lista circular, o "
                     "último nó aponta de volta para o primeiro. O uso de um nó sentinela (cabeça) simplifica o "
                     "tratamento de casos especiais como lista vazia."),
                ],
                "pontos": [
                    "O grande descreve o crescimento no pior caso, ignorando constantes.",
                    "Ordem: O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2^n).",
                    "Vetor: acesso O(1), inserção no meio O(n).",
                    "Lista encadeada: inserção após nó conhecido O(1), acesso por posição O(n).",
                ],
            },
            {
                "titulo": "Pilhas e filas",
                "secoes": [
                    ("Pilhas (LIFO)",
                     "A pilha segue a política LIFO (Last In, First Out): o último elemento inserido é o primeiro "
                     "a sair. As operações principais são empilhar (push), desempilhar (pop) e consultar o topo "
                     "(top ou peek), todas em O(1). Pilhas são usadas na pilha de chamadas de funções, no desfazer "
                     "(Ctrl+Z) de editores, na verificação de parênteses balanceados e na avaliação de expressões "
                     "em notação pós-fixa."),
                    ("Filas (FIFO)",
                     "A fila segue a política FIFO (First In, First Out): o primeiro a entrar é o primeiro a sair. "
                     "As operações são enfileirar (enqueue), no fim, e desenfileirar (dequeue), no início, ambas em "
                     "O(1) quando bem implementadas. Com vetor, usa-se a fila circular, em que os índices de início "
                     "e fim 'dão a volta' usando o resto da divisão pelo tamanho do vetor. Filas aparecem em "
                     "filas de impressão, no escalonamento de processos e na busca em largura em grafos."),
                    ("Deque e fila de prioridade",
                     "O deque (double-ended queue) permite inserir e remover nas duas extremidades. A fila de "
                     "prioridade remove sempre o elemento de maior (ou menor) prioridade, independentemente da "
                     "ordem de chegada; costuma ser implementada com um heap binário, que faz inserção e remoção "
                     "em O(log n)."),
                ],
                "pontos": [
                    "Pilha: LIFO, operações push/pop/top em O(1).",
                    "Fila: FIFO, enqueue no fim e dequeue no início.",
                    "Fila circular reaproveita o vetor usando o resto da divisão.",
                    "Fila de prioridade é implementada com heap: O(log n) por operação.",
                ],
            },
            {
                "titulo": "Árvores e tabelas hash",
                "secoes": [
                    ("Árvores binárias",
                     "Uma árvore é uma estrutura hierárquica formada por nós; o nó do topo é a raiz e os nós sem "
                     "filhos são folhas. Na árvore binária, cada nó tem no máximo dois filhos. A altura é o maior "
                     "caminho da raiz até uma folha. Os percursos clássicos são: pré-ordem (raiz, esquerda, "
                     "direita), em ordem (esquerda, raiz, direita) e pós-ordem (esquerda, direita, raiz)."),
                    ("Árvore binária de busca",
                     "Na árvore binária de busca (ABB), para cada nó, os valores da subárvore esquerda são menores e "
                     "os da direita são maiores. Assim, busca, inserção e remoção custam O(h), onde h é a altura. "
                     "Se a árvore estiver balanceada, h é O(log n); se os dados forem inseridos já ordenados, ela "
                     "degenera em uma lista e h vira O(n). Árvores AVL e rubro-negras fazem rotações para manter o "
                     "balanceamento. O percurso em ordem de uma ABB lista os valores em ordem crescente."),
                    ("Tabelas hash",
                     "A tabela hash usa uma função de espalhamento (hash) para transformar a chave em um índice do "
                     "vetor, permitindo busca, inserção e remoção em O(1) no caso médio. Quando duas chaves caem no "
                     "mesmo índice ocorre uma colisão, tratada por encadeamento (uma lista em cada posição) ou por "
                     "endereçamento aberto (procurar outra posição livre, como na sondagem linear). O fator de "
                     "carga é a razão entre elementos e posições; quando fica alto, a tabela é redimensionada."),
                ],
                "pontos": [
                    "Percursos: pré-ordem, em ordem e pós-ordem.",
                    "ABB: esquerda menor, direita maior; operações em O(altura).",
                    "AVL e rubro-negra mantêm a altura em O(log n).",
                    "Hash: O(1) no caso médio; colisões por encadeamento ou endereçamento aberto.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Trabalho: implementação de pilha e fila",
            "descricao": "Implemente, na linguagem de sua preferência, uma pilha e uma fila circular usando vetor.\n"
                         "Use a pilha para verificar se uma expressão tem parênteses balanceados.\n"
                         "Informe a complexidade de cada operação e cole aqui o código e a saída de testes.",
        },
    },
    {
        "nome": "Arquitetura de Computadores",
        "semestre": 2, "carga": 60, "dia": 3,
        "ementa": "Sistemas de numeração, representação de dados, portas lógicas, modelo de von Neumann, "
                  "organização da CPU, conjunto de instruções, pipeline e hierarquia de memória.",
        "aulas": [
            {
                "titulo": "Sistemas de numeração e representação de dados",
                "secoes": [
                    ("Bases numéricas",
                     "Computadores representam informação em binário (base 2), usando apenas os dígitos 0 e 1, "
                     "chamados bits; 8 bits formam um byte. Para converter de decimal para binário, divide-se o "
                     "número sucessivamente por 2 e leem-se os restos de baixo para cima: 13 em decimal é 1101 em "
                     "binário. A base hexadecimal (16) usa os dígitos 0 a 9 e A a F, e cada dígito hexadecimal "
                     "corresponde a exatamente 4 bits, o que a torna uma forma compacta de escrever binário."),
                    ("Números negativos e ponto flutuante",
                     "Inteiros com sinal são representados em complemento de dois: para obter o negativo, "
                     "invertem-se todos os bits e soma-se 1. Com n bits, representam-se valores de -2^(n-1) a "
                     "2^(n-1) - 1; em 8 bits, de -128 a 127. Ultrapassar esse intervalo causa overflow. Números "
                     "reais seguem o padrão IEEE 754, que divide os bits em sinal, expoente e mantissa; por isso "
                     "valores como 0,1 não têm representação exata em binário."),
                    ("Caracteres e portas lógicas",
                     "Caracteres são codificados como números: a tabela ASCII usa 7 bits (128 símbolos), e o "
                     "Unicode, com a codificação UTF-8, representa praticamente todos os alfabetos usando de 1 a 4 "
                     "bytes por caractere. No nível do hardware, os bits são processados por portas lógicas (AND, "
                     "OR, NOT, NAND, NOR, XOR), que combinadas formam somadores, multiplexadores e registradores."),
                ],
                "pontos": [
                    "Cada dígito hexadecimal equivale a 4 bits.",
                    "Complemento de dois: inverter os bits e somar 1.",
                    "8 bits com sinal: de -128 a 127.",
                    "IEEE 754: sinal, expoente e mantissa; UTF-8 usa de 1 a 4 bytes.",
                ],
            },
            {
                "titulo": "Modelo de von Neumann e a CPU",
                "secoes": [
                    ("Arquitetura de von Neumann",
                     "Na arquitetura de von Neumann, dados e instruções ficam na mesma memória e compartilham o "
                     "mesmo barramento. Seus componentes são a unidade central de processamento (CPU), a memória "
                     "principal, os dispositivos de entrada e saída e os barramentos de dados, endereços e "
                     "controle. Como instruções e dados disputam o mesmo caminho, surge o 'gargalo de von "
                     "Neumann'. A arquitetura Harvard, usada em muitos microcontroladores, separa as memórias de "
                     "instruções e de dados."),
                    ("Componentes da CPU e ciclo de instrução",
                     "A CPU contém a unidade de controle (UC), que interpreta as instruções e coordena os demais "
                     "componentes; a unidade lógica e aritmética (ULA), que faz cálculos e comparações; e os "
                     "registradores, memórias muito rápidas, como o contador de programa (PC), que guarda o "
                     "endereço da próxima instrução, e o registrador de instrução (IR). O ciclo de instrução tem as "
                     "etapas de busca (fetch), decodificação (decode) e execução (execute)."),
                    ("RISC, CISC e pipeline",
                     "Arquiteturas CISC (como x86) têm muitas instruções complexas e de tamanho variável; "
                     "arquiteturas RISC (como ARM e RISC-V) têm poucas instruções simples, de tamanho fixo, "
                     "executadas em geralmente um ciclo. O pipeline divide a execução em estágios e sobrepõe "
                     "instruções diferentes, como uma linha de montagem, aumentando a vazão. Conflitos (hazards) "
                     "estruturais, de dados e de controle podem forçar paradas no pipeline."),
                ],
                "pontos": [
                    "Von Neumann: dados e instruções na mesma memória.",
                    "CPU = unidade de controle + ULA + registradores.",
                    "Ciclo de instrução: busca, decodificação e execução.",
                    "RISC: instruções simples e fixas; CISC: instruções complexas e variáveis.",
                ],
            },
            {
                "titulo": "Hierarquia de memória",
                "secoes": [
                    ("Níveis da hierarquia",
                     "A memória é organizada em níveis que equilibram velocidade, capacidade e custo. Do mais rápido "
                     "e caro para o mais lento e barato: registradores, memória cache (L1, L2 e L3), memória "
                     "principal (RAM) e armazenamento secundário (SSD e disco rígido). A RAM é volátil, ou seja, "
                     "perde os dados sem energia; SSDs e discos são não voláteis."),
                    ("Memória cache e localidade",
                     "A cache guarda cópias dos dados usados com mais frequência, perto da CPU. Ela funciona por "
                     "causa do princípio da localidade: a localidade temporal diz que um dado acessado agora "
                     "provavelmente será acessado de novo em breve; a localidade espacial diz que dados próximos na "
                     "memória tendem a ser acessados juntos. Quando o dado está na cache há um acerto (hit); caso "
                     "contrário, uma falha (miss). O mapeamento pode ser direto, associativo ou associativo por "
                     "conjunto, e políticas como LRU escolhem qual bloco substituir."),
                    ("Memória virtual",
                     "A memória virtual permite que cada programa enxergue um espaço de endereçamento maior que a "
                     "RAM física, usando o disco como extensão. O espaço é dividido em páginas, e a unidade de "
                     "gerência de memória (MMU) traduz endereços virtuais em físicos usando a tabela de páginas; a "
                     "TLB é uma cache dessas traduções. Quando a página não está na RAM ocorre uma falta de página "
                     "(page fault) e ela é trazida do disco."),
                ],
                "pontos": [
                    "Hierarquia: registradores > cache > RAM > SSD/disco.",
                    "Localidade temporal e espacial explicam a eficiência da cache.",
                    "Hit: dado na cache; miss: precisa buscar no nível inferior.",
                    "MMU traduz endereços virtuais; TLB é cache de traduções.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Exercícios de conversão e representação",
            "descricao": "1) Converta 173 para binário e hexadecimal, mostrando os cálculos.\n"
                         "2) Represente -45 em complemento de dois com 8 bits.\n"
                         "3) Explique, com um exemplo de laço sobre um vetor, como a localidade espacial melhora o uso da cache.",
        },
    },
    # ------------------------------------------------------------------ 3º semestre
    {
        "nome": "Programação Orientada a Objetos",
        "semestre": 3, "carga": 80, "dia": 0,
        "ementa": "Classes, objetos, encapsulamento, herança, polimorfismo, "
                  "classes abstratas, interfaces, princípios SOLID e padrões de projeto.",
        "aulas": [
            {
                "titulo": "Classes, objetos e encapsulamento",
                "secoes": [
                    ("Classes e objetos",
                     "Na programação orientada a objetos (POO), o programa é organizado em objetos que combinam "
                     "dados (atributos) e comportamentos (métodos). Uma classe é o molde que define quais atributos "
                     "e métodos os objetos terão; um objeto é uma instância concreta de uma classe. Por exemplo, a "
                     "classe ContaBancaria define os atributos titular e saldo e os métodos depositar e sacar; cada "
                     "conta criada é um objeto com seus próprios valores."),
                    ("Construtores e estado",
                     "O construtor é um método especial executado na criação do objeto, usado para inicializar seus "
                     "atributos (em Python, __init__; em Java, um método com o nome da classe). O estado de um "
                     "objeto é o conjunto dos valores de seus atributos em um momento. Atributos de instância "
                     "pertencem a cada objeto; atributos de classe (estáticos) são compartilhados por todos."),
                    ("Encapsulamento",
                     "O encapsulamento esconde os detalhes internos do objeto e expõe apenas uma interface "
                     "controlada. Modificadores de acesso definem a visibilidade: público (acessível de qualquer "
                     "lugar), privado (só dentro da classe) e protegido (na classe e nas subclasses). Em vez de "
                     "alterar o saldo diretamente, outras partes do código chamam depositar e sacar, que podem "
                     "validar os valores. Métodos getters e setters dão acesso controlado aos atributos."),
                ],
                "pontos": [
                    "Classe é o molde; objeto é a instância.",
                    "Atributos guardam o estado; métodos definem o comportamento.",
                    "Construtor inicializa o objeto na criação.",
                    "Encapsulamento: esconder detalhes e expor uma interface controlada.",
                ],
            },
            {
                "titulo": "Herança, polimorfismo e abstração",
                "secoes": [
                    ("Herança",
                     "A herança permite criar uma classe (subclasse ou filha) a partir de outra (superclasse ou "
                     "mãe), reaproveitando atributos e métodos e acrescentando ou modificando comportamentos. Ela "
                     "representa uma relação 'é um': um Cachorro é um Animal. O uso excessivo de herança cria "
                     "hierarquias rígidas; por isso, recomenda-se preferir composição (relação 'tem um') quando "
                     "possível."),
                    ("Polimorfismo",
                     "Polimorfismo é a capacidade de um mesmo método se comportar de formas diferentes conforme o "
                     "objeto. Na sobrescrita (override), a subclasse redefine um método herdado: o método "
                     "emitirSom de Cachorro late e o de Gato mia, e o código que chama animal.emitirSom() não "
                     "precisa saber o tipo exato. Na sobrecarga (overload), existem métodos com o mesmo nome e "
                     "parâmetros diferentes na mesma classe."),
                    ("Classes abstratas e interfaces",
                     "Uma classe abstrata não pode ser instanciada e pode conter métodos abstratos, sem "
                     "implementação, que as subclasses são obrigadas a implementar. Uma interface define apenas um "
                     "contrato, um conjunto de métodos que a classe que a implementa deve oferecer. Em Java, uma "
                     "classe herda de apenas uma superclasse, mas pode implementar várias interfaces."),
                ],
                "pontos": [
                    "Herança representa 'é um'; composição representa 'tem um'.",
                    "Sobrescrita: subclasse redefine método; sobrecarga: mesmo nome, parâmetros diferentes.",
                    "Classe abstrata não pode ser instanciada.",
                    "Interface é um contrato de métodos.",
                ],
            },
            {
                "titulo": "Princípios SOLID e padrões de projeto",
                "secoes": [
                    ("Princípios SOLID",
                     "SOLID reúne cinco princípios de bom design orientado a objetos. S, responsabilidade única: "
                     "cada classe deve ter um único motivo para mudar. O, aberto/fechado: classes abertas para "
                     "extensão e fechadas para modificação. L, substituição de Liskov: objetos de uma subclasse "
                     "devem poder substituir os da superclasse sem quebrar o programa. I, segregação de "
                     "interfaces: preferir várias interfaces pequenas a uma grande. D, inversão de dependência: "
                     "depender de abstrações, não de implementações concretas."),
                    ("Padrões de projeto",
                     "Padrões de projeto são soluções reutilizáveis para problemas recorrentes, catalogadas pela "
                     "'Gangue dos Quatro' (GoF) em três grupos. Criacionais, como Singleton (garante uma única "
                     "instância) e Factory Method (delega a criação de objetos). Estruturais, como Adapter (adapta "
                     "uma interface a outra) e Decorator (acrescenta comportamento dinamicamente). "
                     "Comportamentais, como Observer (notifica vários objetos quando um estado muda) e Strategy "
                     "(troca algoritmos em tempo de execução)."),
                    ("Acoplamento e coesão",
                     "Um bom projeto busca baixo acoplamento (classes pouco dependentes umas das outras) e alta "
                     "coesão (cada classe com responsabilidades bem relacionadas). Isso facilita manutenção, testes "
                     "e reaproveitamento de código."),
                ],
                "pontos": [
                    "SOLID: responsabilidade única, aberto/fechado, Liskov, segregação de interfaces, inversão de dependência.",
                    "Padrões GoF: criacionais, estruturais e comportamentais.",
                    "Observer notifica dependentes; Strategy troca algoritmos.",
                    "Objetivo: baixo acoplamento e alta coesão.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Projeto: sistema de biblioteca orientado a objetos",
            "descricao": "Modele as classes Livro, Usuario e Emprestimo, usando encapsulamento.\n"
                         "Crie uma hierarquia com herança (por exemplo, Aluno e Professor como tipos de Usuario, com prazos diferentes).\n"
                         "Explique onde usou polimorfismo e qual princípio SOLID seu projeto respeita.",
        },
    },
    {
        "nome": "Banco de Dados",
        "semestre": 3, "carga": 80, "dia": 2,
        "ementa": "Sistemas gerenciadores de banco de dados, modelo entidade-relacionamento, "
                  "modelo relacional, normalização, SQL e transações.",
        "aulas": [
            {
                "titulo": "Modelagem entidade-relacionamento",
                "secoes": [
                    ("Banco de dados e SGBD",
                     "Um banco de dados é uma coleção organizada de dados relacionados. O sistema gerenciador de "
                     "banco de dados (SGBD), como PostgreSQL, MySQL e SQLite, controla o armazenamento, o acesso "
                     "concorrente, a segurança e a integridade dos dados. O projeto de um banco passa por três "
                     "etapas: modelo conceitual (independente de tecnologia), modelo lógico (por exemplo, o modelo "
                     "relacional) e modelo físico (tabelas, tipos e índices de um SGBD específico)."),
                    ("Entidades, atributos e relacionamentos",
                     "O modelo entidade-relacionamento (ER), proposto por Peter Chen, é usado no projeto conceitual. "
                     "Entidades representam objetos do mundo real (Aluno, Disciplina) e são desenhadas como "
                     "retângulos. Atributos descrevem as entidades (nome, matrícula); o atributo identificador "
                     "distingue cada ocorrência. Relacionamentos, desenhados como losangos, associam entidades "
                     "(Aluno cursa Disciplina)."),
                    ("Cardinalidade",
                     "A cardinalidade indica quantas ocorrências de uma entidade se associam a outra: um-para-um "
                     "(1:1), como pessoa e CPF; um-para-muitos (1:N), como professor e turmas que ele leciona; e "
                     "muitos-para-muitos (N:N), como alunos e disciplinas. Ao passar para o modelo relacional, um "
                     "relacionamento N:N vira uma tabela associativa com as chaves das duas entidades."),
                ],
                "pontos": [
                    "Modelos: conceitual, lógico e físico.",
                    "ER: entidades (retângulos), atributos e relacionamentos (losangos).",
                    "Cardinalidades 1:1, 1:N e N:N.",
                    "N:N vira uma tabela associativa no modelo relacional.",
                ],
            },
            {
                "titulo": "Modelo relacional e normalização",
                "secoes": [
                    ("Tabelas e chaves",
                     "No modelo relacional, proposto por Edgar Codd, os dados ficam em relações (tabelas) formadas "
                     "por tuplas (linhas) e atributos (colunas). A chave primária identifica cada linha de forma "
                     "única e não pode ser nula. A chave estrangeira é uma coluna que referencia a chave primária "
                     "de outra tabela, garantindo a integridade referencial: não é possível cadastrar uma matrícula "
                     "para um aluno inexistente."),
                    ("Anomalias e dependência funcional",
                     "Tabelas mal projetadas guardam dados repetidos e sofrem anomalias de inserção, atualização e "
                     "exclusão. A normalização elimina essas redundâncias com base em dependências funcionais: "
                     "diz-se que A determina B quando, para cada valor de A, existe um único valor de B."),
                    ("Formas normais",
                     "Primeira forma normal (1FN): todos os atributos são atômicos, sem listas ou grupos repetidos "
                     "em uma célula. Segunda forma normal (2FN): está na 1FN e nenhum atributo não chave depende "
                     "de apenas parte de uma chave primária composta. Terceira forma normal (3FN): está na 2FN e "
                     "não há dependências transitivas, ou seja, atributos não chave não dependem de outros "
                     "atributos não chave. A forma normal de Boyce-Codd (FNBC) é uma versão mais rigorosa da 3FN."),
                ],
                "pontos": [
                    "Chave primária: única e não nula; chave estrangeira: referencia outra tabela.",
                    "1FN: valores atômicos.",
                    "2FN: sem dependência parcial da chave composta.",
                    "3FN: sem dependência transitiva.",
                ],
            },
            {
                "titulo": "SQL e transações",
                "secoes": [
                    ("Comandos DDL e DML",
                     "SQL (Structured Query Language) é a linguagem padrão dos bancos relacionais. A DDL (linguagem "
                     "de definição de dados) cria e altera a estrutura: CREATE TABLE, ALTER TABLE e DROP TABLE. A "
                     "DML (linguagem de manipulação de dados) trabalha com os registros: INSERT insere, UPDATE "
                     "altera, DELETE remove e SELECT consulta. Um UPDATE ou DELETE sem cláusula WHERE afeta todas "
                     "as linhas da tabela."),
                    ("Consultas",
                     "O SELECT escolhe colunas; o FROM indica as tabelas; o WHERE filtra linhas; o ORDER BY ordena. "
                     "Funções de agregação como COUNT, SUM, AVG, MIN e MAX são usadas com GROUP BY, e o HAVING "
                     "filtra os grupos depois da agregação. O INNER JOIN retorna apenas as linhas com "
                     "correspondência nas duas tabelas; o LEFT JOIN retorna todas as linhas da tabela da esquerda, "
                     "preenchendo com NULL quando não há correspondência. Índices aceleram buscas, mas tornam "
                     "inserções mais lentas."),
                    ("Transações e propriedades ACID",
                     "Uma transação é um conjunto de operações tratado como uma unidade: ou tudo é gravado (COMMIT) "
                     "ou nada é (ROLLBACK). As propriedades ACID garantem confiabilidade: atomicidade (tudo ou nada), "
                     "consistência (o banco passa de um estado válido para outro), isolamento (transações "
                     "concorrentes não interferem entre si) e durabilidade (dados confirmados não se perdem, mesmo "
                     "após falhas). Uma transferência bancária, que debita uma conta e credita outra, é o exemplo "
                     "clássico."),
                ],
                "pontos": [
                    "DDL: CREATE, ALTER, DROP; DML: INSERT, UPDATE, DELETE, SELECT.",
                    "WHERE filtra linhas; HAVING filtra grupos.",
                    "INNER JOIN: só correspondências; LEFT JOIN: tudo da esquerda.",
                    "ACID: atomicidade, consistência, isolamento e durabilidade.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Modelagem de um sistema acadêmico",
            "descricao": "1) Faça o modelo ER com as entidades Aluno, Professor, Disciplina e Turma, indicando cardinalidades.\n"
                         "2) Converta para o modelo relacional, mostrando chaves primárias e estrangeiras, na 3FN.\n"
                         "3) Escreva uma consulta SQL que liste a média de notas por disciplina, só das disciplinas com mais de 10 alunos.",
        },
    },
    # ------------------------------------------------------------------ 4º semestre
    {
        "nome": "Sistemas Operacionais",
        "semestre": 4, "carga": 80, "dia": 1,
        "ementa": "Funções do sistema operacional, processos e threads, escalonamento, "
                  "sincronização, deadlocks, gerência de memória e sistemas de arquivos.",
        "aulas": [
            {
                "titulo": "Processos e threads",
                "secoes": [
                    ("Papel do sistema operacional",
                     "O sistema operacional (SO) é o software que gerencia o hardware e oferece serviços aos "
                     "programas. Ele atua como gerente de recursos (CPU, memória, dispositivos) e como máquina "
                     "estendida, escondendo detalhes do hardware. O núcleo (kernel) executa em modo privilegiado "
                     "(modo kernel), e os programas comuns em modo usuário; eles pedem serviços ao SO por meio de "
                     "chamadas de sistema (system calls)."),
                    ("Processos",
                     "Um processo é um programa em execução, com seu próprio espaço de memória, registradores e "
                     "recursos abertos, descritos no bloco de controle de processo (PCB). Um processo passa pelos "
                     "estados novo, pronto (esperando a CPU), executando, bloqueado (esperando um evento, como "
                     "leitura de disco) e terminado. A troca de contexto salva o estado do processo atual e "
                     "carrega o do próximo, e tem um custo."),
                    ("Threads",
                     "Uma thread é uma linha de execução dentro de um processo. Threads do mesmo processo "
                     "compartilham memória e arquivos abertos, mas cada uma tem sua própria pilha e seus "
                     "registradores. Criar e trocar threads é mais barato que processos, e elas permitem "
                     "aproveitar vários núcleos da CPU. O compartilhamento de memória, porém, exige cuidado com "
                     "condições de corrida."),
                ],
                "pontos": [
                    "Kernel roda em modo privilegiado; programas usam system calls.",
                    "Estados: novo, pronto, executando, bloqueado e terminado.",
                    "PCB descreve o processo; troca de contexto tem custo.",
                    "Threads do mesmo processo compartilham a memória.",
                ],
            },
            {
                "titulo": "Escalonamento de processos",
                "secoes": [
                    ("Objetivos do escalonador",
                     "O escalonador decide qual processo pronto usará a CPU. No escalonamento preemptivo, o SO pode "
                     "interromper um processo em execução; no não preemptivo, o processo só libera a CPU quando "
                     "termina ou bloqueia. Os critérios avaliados incluem uso da CPU, vazão (processos concluídos "
                     "por unidade de tempo), tempo de espera, tempo de retorno (turnaround) e tempo de resposta."),
                    ("Algoritmos clássicos",
                     "FCFS (First Come, First Served) atende por ordem de chegada; é simples, mas processos longos "
                     "fazem os curtos esperarem (efeito comboio). SJF (Shortest Job First) escolhe o processo com "
                     "menor tempo de execução e minimiza o tempo médio de espera, mas exige conhecer a duração e "
                     "pode causar inanição (starvation) dos longos. Round Robin dá a cada processo uma fatia de "
                     "tempo (quantum) em rodízio; é justo e bom para sistemas interativos, e o quantum não pode ser "
                     "nem muito pequeno (muitas trocas de contexto) nem muito grande (vira FCFS)."),
                    ("Prioridades",
                     "No escalonamento por prioridade, a CPU vai para o processo de maior prioridade. Para evitar a "
                     "inanição, usa-se o envelhecimento (aging), que aumenta gradualmente a prioridade dos "
                     "processos que esperam muito. Filas multinível separam processos por tipo, como interativos e "
                     "em lote."),
                ],
                "pontos": [
                    "Preemptivo: o SO pode interromper o processo.",
                    "FCFS sofre efeito comboio; SJF minimiza espera média, mas pode causar inanição.",
                    "Round Robin usa quantum em rodízio.",
                    "Aging evita inanição no escalonamento por prioridade.",
                ],
            },
            {
                "titulo": "Concorrência, deadlocks e memória",
                "secoes": [
                    ("Sincronização",
                     "Uma condição de corrida ocorre quando o resultado depende da ordem em que threads acessam "
                     "dados compartilhados. O trecho de código que acessa esses dados é a região crítica, e deve "
                     "ser executado com exclusão mútua. Mecanismos de sincronização incluem mutex (trava que só uma "
                     "thread pode segurar), semáforos (contadores com operações wait e signal, de Dijkstra) e "
                     "monitores."),
                    ("Deadlock",
                     "Deadlock (impasse) é quando processos ficam bloqueados para sempre, cada um esperando um "
                     "recurso que outro segura. Coffman definiu quatro condições necessárias e simultâneas: "
                     "exclusão mútua, posse e espera, não preempção e espera circular. As estratégias são "
                     "prevenir (quebrar uma das condições, por exemplo impondo uma ordem global para pedir "
                     "recursos), evitar (como o algoritmo do banqueiro), detectar e recuperar, ou ignorar o "
                     "problema (algoritmo do avestruz)."),
                    ("Gerência de memória",
                     "O SO aloca memória aos processos e os isola entre si. Na paginação, a memória lógica é "
                     "dividida em páginas e a física em quadros (frames) do mesmo tamanho, eliminando a "
                     "fragmentação externa. Quando falta memória, algoritmos de substituição de páginas escolhem "
                     "qual página tirar da RAM: FIFO, LRU (a usada há mais tempo) e o ótimo (teórico). Thrashing é "
                     "quando o sistema passa mais tempo trocando páginas do que executando."),
                ],
                "pontos": [
                    "Região crítica precisa de exclusão mútua (mutex, semáforo, monitor).",
                    "Deadlock: exclusão mútua, posse e espera, não preempção e espera circular.",
                    "Algoritmo do banqueiro evita deadlocks.",
                    "Paginação: páginas e quadros; LRU substitui a página usada há mais tempo.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Simulação de escalonamento",
            "descricao": "Considere os processos P1 (chegada 0, duração 8), P2 (chegada 1, duração 4), P3 (chegada 2, duração 9) e P4 (chegada 3, duração 5).\n"
                         "Monte o diagrama de Gantt e calcule o tempo médio de espera para FCFS, SJF não preemptivo e Round Robin com quantum 3.\n"
                         "Qual algoritmo foi melhor neste caso e por quê?",
        },
    },
    {
        "nome": "Redes de Computadores",
        "semestre": 4, "carga": 80, "dia": 3,
        "ementa": "Modelos de referência OSI e TCP/IP, camada física e de enlace, endereçamento IP, "
                  "roteamento, protocolos de transporte TCP e UDP e protocolos de aplicação.",
        "aulas": [
            {
                "titulo": "Modelos OSI e TCP-IP",
                "secoes": [
                    ("Por que dividir em camadas",
                     "Redes são organizadas em camadas: cada camada oferece serviços à camada de cima e usa os "
                     "serviços da camada de baixo, o que simplifica o projeto e permite trocar tecnologias sem "
                     "afetar o resto. Ao enviar dados, cada camada acrescenta seu cabeçalho, em um processo chamado "
                     "encapsulamento; no destino, os cabeçalhos são retirados na ordem inversa."),
                    ("Modelo OSI",
                     "O modelo OSI, da ISO, tem sete camadas: física (transmissão de bits no meio), enlace "
                     "(quadros entre nós vizinhos, endereços MAC), rede (pacotes entre redes, endereços IP e "
                     "roteamento), transporte (comunicação fim a fim entre processos), sessão (controle de "
                     "diálogo), apresentação (formato, compressão e criptografia) e aplicação (serviços ao usuário)."),
                    ("Modelo TCP/IP",
                     "O modelo TCP/IP, usado na Internet, tem quatro camadas: acesso à rede (física e enlace), "
                     "internet (IP), transporte (TCP e UDP) e aplicação (que agrupa sessão, apresentação e "
                     "aplicação do OSI). As unidades de dados recebem nomes diferentes: bits na camada física, "
                     "quadros no enlace, pacotes na rede e segmentos no transporte. Equipamentos típicos são o "
                     "hub (camada 1), o switch (camada 2) e o roteador (camada 3)."),
                ],
                "pontos": [
                    "OSI: física, enlace, rede, transporte, sessão, apresentação e aplicação.",
                    "TCP/IP: acesso à rede, internet, transporte e aplicação.",
                    "Encapsulamento: cada camada acrescenta seu cabeçalho.",
                    "Hub: camada 1; switch: camada 2; roteador: camada 3.",
                ],
            },
            {
                "titulo": "Camada de rede e endereçamento IP",
                "secoes": [
                    ("Endereços IPv4",
                     "O IPv4 usa endereços de 32 bits, escritos como quatro números de 0 a 255 separados por "
                     "pontos, como 192.168.1.10. Cada endereço tem uma parte de rede e uma parte de host, "
                     "separadas pela máscara de sub-rede. Na notação CIDR, /24 indica que os primeiros 24 bits são "
                     "da rede, o que corresponde à máscara 255.255.255.0 e permite 254 hosts (2^8 - 2, descontando "
                     "o endereço de rede e o de broadcast)."),
                    ("Endereços privados, NAT e IPv6",
                     "As faixas 10.0.0.0/8, 172.16.0.0/12 e 192.168.0.0/16 são privadas e não são roteadas na "
                     "Internet. O NAT (tradução de endereços de rede) permite que vários dispositivos com IPs "
                     "privados compartilhem um único IP público. Como os endereços IPv4 se esgotaram, foi criado o "
                     "IPv6, com endereços de 128 bits escritos em hexadecimal, como 2001:db8::1."),
                    ("Roteamento e protocolos auxiliares",
                     "Roteadores encaminham pacotes consultando a tabela de roteamento, que indica o próximo salto "
                     "para cada rede de destino. As rotas podem ser estáticas ou aprendidas por protocolos "
                     "dinâmicos, como RIP (vetor de distâncias), OSPF (estado de enlace, usa o algoritmo de "
                     "Dijkstra) e BGP (entre sistemas autônomos na Internet). Protocolos auxiliares incluem o ARP "
                     "(descobre o MAC a partir do IP), o DHCP (atribui IPs automaticamente) e o ICMP (mensagens de "
                     "controle, usado pelo ping)."),
                ],
                "pontos": [
                    "IPv4: 32 bits; IPv6: 128 bits.",
                    "/24 = máscara 255.255.255.0 = 254 hosts.",
                    "Faixas privadas: 10/8, 172.16/12 e 192.168/16; NAT compartilha um IP público.",
                    "ARP: IP para MAC; DHCP: atribui IPs; ICMP: usado pelo ping.",
                ],
            },
            {
                "titulo": "Camada de transporte e aplicação",
                "secoes": [
                    ("Portas e multiplexação",
                     "A camada de transporte entrega dados ao processo certo usando números de porta de 16 bits. "
                     "Algumas portas conhecidas: 80 (HTTP), 443 (HTTPS), 22 (SSH), 25 (SMTP) e 53 (DNS). O par "
                     "endereço IP e porta forma um socket."),
                    ("TCP e UDP",
                     "O TCP é orientado à conexão e confiável. A conexão é aberta com o three-way handshake (SYN, "
                     "SYN-ACK, ACK). Ele numera os segmentos, confirma o recebimento, retransmite o que se perdeu, "
                     "entrega os dados em ordem e faz controle de fluxo (janela deslizante) e de congestionamento. "
                     "O UDP não tem conexão nem garantia de entrega ou ordem, mas tem cabeçalho menor e menos "
                     "atraso; por isso é usado em streaming, jogos online, chamadas de voz e no DNS."),
                    ("Protocolos de aplicação",
                     "O HTTP é o protocolo da Web, baseado em requisição e resposta, com métodos como GET, POST, "
                     "PUT e DELETE e códigos de status como 200 (OK), 404 (não encontrado) e 500 (erro no "
                     "servidor). O HTTPS é o HTTP protegido por TLS, que criptografa a comunicação. O DNS traduz "
                     "nomes de domínio em endereços IP. Outros exemplos são SMTP (envio de e-mail) e FTP "
                     "(transferência de arquivos)."),
                ],
                "pontos": [
                    "Portas: 80 HTTP, 443 HTTPS, 22 SSH, 53 DNS.",
                    "TCP: confiável, com conexão (three-way handshake: SYN, SYN-ACK, ACK).",
                    "UDP: sem conexão, menor atraso; usado em streaming, jogos e DNS.",
                    "HTTP: 200 OK, 404 não encontrado, 500 erro no servidor.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Exercícios de sub-redes",
            "descricao": "1) Para a rede 192.168.10.0/26, informe a máscara decimal, o número de hosts, o endereço de broadcast e a faixa utilizável.\n"
                         "2) Divida a rede 10.0.0.0/24 em 4 sub-redes iguais.\n"
                         "3) Explique por que o DNS usa UDP na maioria das consultas.",
        },
    },
    # ------------------------------------------------------------------ 5º semestre
    {
        "nome": "Engenharia de Software",
        "semestre": 5, "carga": 80, "dia": 0,
        "ementa": "Processos de desenvolvimento, métodos ágeis, engenharia de requisitos, "
                  "UML, qualidade, testes de software e controle de versão.",
        "aulas": [
            {
                "titulo": "Processos de software e métodos ágeis",
                "secoes": [
                    ("Modelos de processo",
                     "Um processo de software organiza as atividades de especificação, projeto, implementação, "
                     "validação e evolução. No modelo cascata, as fases acontecem em sequência e só se avança "
                     "quando a anterior termina; funciona para requisitos estáveis, mas lida mal com mudanças. "
                     "Modelos incrementais e iterativos entregam o sistema em partes, e o modelo espiral, de Boehm, "
                     "enfatiza a análise de riscos a cada ciclo."),
                    ("Manifesto Ágil",
                     "O Manifesto Ágil (2001) valoriza indivíduos e interações mais que processos e ferramentas, "
                     "software funcionando mais que documentação abrangente, colaboração com o cliente mais que "
                     "negociação de contratos e responder a mudanças mais que seguir um plano. Métodos ágeis fazem "
                     "entregas curtas e frequentes, com feedback contínuo do cliente."),
                    ("Scrum e Kanban",
                     "No Scrum, o trabalho é feito em sprints de uma a quatro semanas. Os papéis são o Product Owner "
                     "(define e prioriza o Product Backlog), o Scrum Master (facilita o processo e remove "
                     "impedimentos) e os desenvolvedores. Os eventos são o planejamento da sprint, a daily (reunião "
                     "diária de 15 minutos), a revisão da sprint e a retrospectiva. O Kanban visualiza o fluxo em um "
                     "quadro com colunas (a fazer, fazendo, feito) e limita o trabalho em andamento (WIP)."),
                ],
                "pontos": [
                    "Cascata: fases sequenciais; ruim para requisitos que mudam.",
                    "Espiral foca em análise de riscos.",
                    "Scrum: Product Owner, Scrum Master e desenvolvedores; sprints de 1 a 4 semanas.",
                    "Kanban limita o trabalho em andamento (WIP).",
                ],
            },
            {
                "titulo": "Engenharia de requisitos e UML",
                "secoes": [
                    ("Requisitos funcionais e não funcionais",
                     "Requisitos descrevem o que o sistema deve fazer e sob quais restrições. Requisitos funcionais "
                     "definem funcionalidades, como 'o aluno deve poder enviar uma atividade'. Requisitos não "
                     "funcionais definem qualidades e restrições, como desempenho, segurança, usabilidade e "
                     "disponibilidade: 'a página deve carregar em menos de 2 segundos'."),
                    ("Levantamento e histórias de usuário",
                     "Técnicas de levantamento incluem entrevistas, questionários, observação, workshops e "
                     "prototipação. Em métodos ágeis, os requisitos são escritos como histórias de usuário no "
                     "formato 'Como [papel], quero [funcionalidade] para [benefício]', com critérios de aceitação "
                     "que definem quando a história está pronta. Boas histórias seguem o acrônimo INVEST: "
                     "independentes, negociáveis, valiosas, estimáveis, pequenas e testáveis."),
                    ("UML",
                     "A UML (Linguagem de Modelagem Unificada) padroniza diagramas de software. O diagrama de casos "
                     "de uso mostra atores e as funcionalidades que usam. O diagrama de classes mostra classes, "
                     "atributos, métodos e relacionamentos (associação, herança, agregação e composição). O "
                     "diagrama de sequência mostra a troca de mensagens entre objetos ao longo do tempo, e o "
                     "diagrama de atividades representa fluxos de trabalho."),
                ],
                "pontos": [
                    "Funcional: o que o sistema faz; não funcional: qualidades e restrições.",
                    "História de usuário: Como [papel], quero [algo] para [benefício].",
                    "INVEST: independente, negociável, valiosa, estimável, pequena e testável.",
                    "UML: casos de uso, classes, sequência e atividades.",
                ],
            },
            {
                "titulo": "Qualidade e testes de software",
                "secoes": [
                    ("Verificação e validação",
                     "Verificação pergunta 'estamos construindo o produto corretamente?', ou seja, se ele atende à "
                     "especificação. Validação pergunta 'estamos construindo o produto certo?', se ele atende às "
                     "necessidades reais do usuário. Testes mostram a presença de defeitos, mas não podem provar "
                     "sua ausência."),
                    ("Níveis e técnicas de teste",
                     "Os níveis de teste são: unidade (funções ou classes isoladas), integração (módulos "
                     "trabalhando juntos), sistema (o sistema completo) e aceitação (feito com o cliente). A "
                     "pirâmide de testes recomenda muitos testes de unidade, menos de integração e poucos de ponta "
                     "a ponta. No teste de caixa-preta, os casos são criados a partir da especificação, com "
                     "técnicas como partição de equivalência e análise de valor limite; no teste de caixa-branca, "
                     "a partir do código, buscando cobertura de comandos e de desvios."),
                    ("TDD, integração contínua e versionamento",
                     "No desenvolvimento guiado por testes (TDD), escreve-se primeiro um teste que falha, depois o "
                     "código mínimo para ele passar e então se refatora (ciclo vermelho, verde, refatorar). Na "
                     "integração contínua (CI), cada alteração enviada ao repositório dispara a compilação e os "
                     "testes automaticamente. O Git é o sistema de controle de versão mais usado, com commits, "
                     "branches e merges."),
                ],
                "pontos": [
                    "Verificação: produto correto; validação: produto certo.",
                    "Níveis: unidade, integração, sistema e aceitação.",
                    "Caixa-preta: especificação; caixa-branca: código.",
                    "TDD: vermelho, verde, refatorar.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Documento de requisitos do Assistente de Estudos",
            "descricao": "1) Liste 5 requisitos funcionais e 3 não funcionais do sistema Assistente de Estudos.\n"
                         "2) Escreva 3 histórias de usuário com critérios de aceitação.\n"
                         "3) Proponha casos de teste de caixa-preta (com valores limite) para a nota de uma atividade, que vai de 0 a 10.",
        },
    },
    {
        "nome": "Teoria da Computação",
        "semestre": 5, "carga": 60, "dia": 2,
        "ementa": "Linguagens formais, autômatos finitos, expressões regulares, gramáticas livres de contexto, "
                  "autômatos de pilha, máquinas de Turing, decidibilidade e classes de complexidade.",
        "aulas": [
            {
                "titulo": "Autômatos finitos e linguagens regulares",
                "secoes": [
                    ("Alfabetos, cadeias e linguagens",
                     "Um alfabeto é um conjunto finito de símbolos, como {0, 1}. Uma cadeia (palavra) é uma "
                     "sequência finita de símbolos do alfabeto; a cadeia vazia é representada por épsilon. Uma "
                     "linguagem é um conjunto de cadeias, por exemplo, o conjunto das cadeias binárias que terminam "
                     "em 1."),
                    ("Autômatos finitos",
                     "Um autômato finito determinístico (AFD) é formado por um conjunto finito de estados, um "
                     "alfabeto, uma função de transição, um estado inicial e um conjunto de estados finais. Ele lê "
                     "a entrada símbolo a símbolo e, para cada estado e símbolo, há exatamente uma transição; a "
                     "cadeia é aceita se a leitura termina em um estado final. No autômato não determinístico "
                     "(AFN), pode haver várias transições ou nenhuma para um mesmo símbolo, além de transições "
                     "vazias. AFD e AFN reconhecem exatamente as mesmas linguagens: todo AFN pode ser convertido em "
                     "AFD pela construção de subconjuntos."),
                    ("Expressões regulares e limites",
                     "As linguagens reconhecidas por autômatos finitos são as linguagens regulares, que também podem "
                     "ser descritas por expressões regulares com união, concatenação e fecho de Kleene (estrela). "
                     "Autômatos finitos não têm memória além do estado atual, por isso não reconhecem linguagens "
                     "como a^n b^n (mesmo número de a's e b's). O lema do bombeamento é usado para provar que uma "
                     "linguagem não é regular. Na prática, analisadores léxicos de compiladores usam autômatos finitos."),
                ],
                "pontos": [
                    "AFD: exatamente uma transição por estado e símbolo.",
                    "AFD e AFN têm o mesmo poder (construção de subconjuntos).",
                    "Linguagens regulares = autômatos finitos = expressões regulares.",
                    "a^n b^n não é regular (lema do bombeamento).",
                ],
            },
            {
                "titulo": "Gramáticas livres de contexto e autômatos de pilha",
                "secoes": [
                    ("Gramáticas",
                     "Uma gramática é formada por variáveis (não terminais), terminais, regras de produção e uma "
                     "variável inicial. Em uma gramática livre de contexto (GLC), o lado esquerdo de cada regra tem "
                     "uma única variável, como S -> aSb | vazio, que gera a linguagem a^n b^n. GLCs descrevem a "
                     "sintaxe de linguagens de programação, como expressões com parênteses aninhados."),
                    ("Derivações e ambiguidade",
                     "Uma derivação aplica regras a partir da variável inicial até obter apenas terminais, e pode "
                     "ser representada por uma árvore de derivação. Uma gramática é ambígua quando uma mesma cadeia "
                     "tem duas árvores de derivação diferentes; em expressões aritméticas, isso causa dúvidas de "
                     "precedência, resolvidas reescrevendo a gramática com níveis para soma e multiplicação."),
                    ("Autômatos de pilha e hierarquia de Chomsky",
                     "O autômato de pilha é um autômato finito com uma pilha como memória auxiliar, e reconhece "
                     "exatamente as linguagens livres de contexto. A hierarquia de Chomsky organiza as linguagens "
                     "em quatro níveis, cada um contendo o anterior: regulares (tipo 3, autômatos finitos), livres "
                     "de contexto (tipo 2, autômatos de pilha), sensíveis ao contexto (tipo 1, autômatos linearmente "
                     "limitados) e recursivamente enumeráveis (tipo 0, máquinas de Turing)."),
                ],
                "pontos": [
                    "GLC: lado esquerdo de cada regra é uma única variável.",
                    "Ambígua: uma cadeia com duas árvores de derivação.",
                    "Autômato de pilha reconhece linguagens livres de contexto.",
                    "Chomsky: tipo 3 regular, 2 livre de contexto, 1 sensível ao contexto, 0 recursivamente enumerável.",
                ],
            },
            {
                "titulo": "Máquinas de Turing, decidibilidade e complexidade",
                "secoes": [
                    ("Máquina de Turing",
                     "Proposta por Alan Turing em 1936, a máquina de Turing tem uma fita infinita dividida em "
                     "células, uma cabeça que lê, escreve e se move para a esquerda ou para a direita, e um "
                     "conjunto finito de estados. Apesar da simplicidade, ela é capaz de simular qualquer algoritmo. "
                     "A tese de Church-Turing afirma que tudo o que é computável por um procedimento efetivo pode "
                     "ser computado por uma máquina de Turing."),
                    ("Decidibilidade",
                     "Um problema é decidível quando existe uma máquina de Turing que sempre para e responde "
                     "corretamente sim ou não. O problema da parada (dado um programa e uma entrada, saber se ele "
                     "termina) é indecidível: Turing provou, por diagonalização, que nenhum algoritmo resolve esse "
                     "problema para todos os casos. Por redução, muitos outros problemas também são indecidíveis, "
                     "como saber se dois programas quaisquer são equivalentes."),
                    ("Classes P e NP",
                     "A classe P contém os problemas resolvíveis em tempo polinomial por uma máquina "
                     "determinística, como ordenação e caminho mínimo. A classe NP contém os problemas cujas "
                     "soluções podem ser verificadas em tempo polinomial. Problemas NP-completos, como o SAT "
                     "(satisfatibilidade booleana, o primeiro, provado por Cook), o caixeiro-viajante na versão de "
                     "decisão e a coloração de grafos, são os mais difíceis de NP: se um deles tiver solução "
                     "polinomial, então P = NP, questão ainda em aberto."),
                ],
                "pontos": [
                    "Tese de Church-Turing: máquina de Turing captura a noção de algoritmo.",
                    "Problema da parada é indecidível.",
                    "P: resolver em tempo polinomial; NP: verificar em tempo polinomial.",
                    "SAT foi o primeiro problema NP-completo (Cook); P = NP está em aberto.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Lista: autômatos e gramáticas",
            "descricao": "1) Desenhe um AFD que aceite cadeias binárias com número par de zeros.\n"
                         "2) Escreva uma expressão regular para cadeias sobre {a, b} que contenham 'ab' como subcadeia.\n"
                         "3) Dê uma gramática livre de contexto para parênteses balanceados e mostre a árvore de derivação de (()()).",
        },
    },
    # ------------------------------------------------------------------ 6º semestre
    {
        "nome": "Inteligência Artificial",
        "semestre": 6, "carga": 80, "dia": 4,
        "ementa": "Agentes inteligentes, busca em espaço de estados, busca heurística, "
                  "aprendizado de máquina, redes neurais, modelos de linguagem e ética em IA.",
        "aulas": [
            {
                "titulo": "Agentes inteligentes e busca",
                "secoes": [
                    ("Agentes",
                     "Um agente inteligente percebe o ambiente por sensores e age sobre ele por atuadores, buscando "
                     "maximizar uma medida de desempenho. Ambientes podem ser totalmente ou parcialmente "
                     "observáveis, determinísticos ou estocásticos, estáticos ou dinâmicos. Um problema de busca é "
                     "definido por estado inicial, ações possíveis, modelo de transição, teste de objetivo e custo "
                     "do caminho."),
                    ("Busca sem informação",
                     "A busca em largura (BFS) expande primeiro os nós mais rasos, usando uma fila; é completa e "
                     "encontra o caminho com menos passos, mas consome muita memória. A busca em profundidade (DFS) "
                     "usa uma pilha e vai o mais fundo possível antes de voltar; gasta pouca memória, mas pode não "
                     "encontrar a solução ótima. A busca de custo uniforme expande o nó de menor custo acumulado e "
                     "é ótima quando os custos são positivos."),
                    ("Busca heurística",
                     "Uma heurística h(n) estima o custo do nó n até o objetivo, como a distância em linha reta em "
                     "um mapa. A busca gulosa expande o nó com menor h(n). O algoritmo A* expande o nó com menor "
                     "f(n) = g(n) + h(n), em que g(n) é o custo já percorrido; se a heurística for admissível "
                     "(nunca superestima o custo real), o A* encontra a solução ótima. Em jogos de dois jogadores, "
                     "usa-se o algoritmo minimax com poda alfa-beta."),
                ],
                "pontos": [
                    "Agente: sensores, atuadores e medida de desempenho.",
                    "BFS usa fila e acha o caminho com menos passos; DFS usa pilha.",
                    "A*: f(n) = g(n) + h(n); ótimo com heurística admissível.",
                    "Jogos: minimax com poda alfa-beta.",
                ],
            },
            {
                "titulo": "Aprendizado de máquina",
                "secoes": [
                    ("Tipos de aprendizado",
                     "Aprendizado de máquina é a área que permite aos computadores aprender padrões a partir de "
                     "dados, sem serem programados explicitamente para cada regra. No aprendizado supervisionado, os "
                     "exemplos têm rótulos: classificação prevê categorias (spam ou não spam) e regressão prevê "
                     "valores numéricos (preço de um imóvel). No não supervisionado, não há rótulos, e o objetivo é "
                     "encontrar estrutura, como no agrupamento (k-means). No aprendizado por reforço, um agente "
                     "aprende por tentativa e erro, recebendo recompensas."),
                    ("Algoritmos clássicos",
                     "A regressão linear ajusta uma reta aos dados minimizando o erro quadrático. A regressão "
                     "logística estima probabilidades para classificação. Árvores de decisão fazem perguntas "
                     "sucessivas sobre os atributos, e florestas aleatórias combinam muitas árvores. O k-vizinhos "
                     "mais próximos (k-NN) classifica um exemplo pela maioria entre os k exemplos mais parecidos."),
                    ("Avaliação e overfitting",
                     "Os dados são divididos em treino e teste (e muitas vezes validação) para medir o desempenho "
                     "em exemplos novos. Overfitting (sobreajuste) ocorre quando o modelo decora o treino e "
                     "generaliza mal; underfitting, quando é simples demais. Validação cruzada e regularização "
                     "ajudam a controlar o problema. Métricas de classificação incluem acurácia, precisão (dos "
                     "previstos como positivos, quantos são), revocação ou recall (dos positivos reais, quantos "
                     "foram encontrados) e F1, a média harmônica das duas."),
                ],
                "pontos": [
                    "Supervisionado: classificação e regressão; não supervisionado: agrupamento.",
                    "Reforço: aprendizado por recompensas.",
                    "Overfitting: decora o treino e generaliza mal.",
                    "Precisão, revocação (recall) e F1.",
                ],
            },
            {
                "titulo": "Redes neurais e modelos de linguagem",
                "secoes": [
                    ("Redes neurais",
                     "Um neurônio artificial calcula uma soma ponderada das entradas, soma um viés e aplica uma "
                     "função de ativação, como ReLU ou sigmoide. Redes neurais organizam neurônios em camadas: "
                     "entrada, camadas ocultas e saída. O treinamento ajusta os pesos para minimizar uma função de "
                     "perda, usando o gradiente descendente e o algoritmo de retropropagação (backpropagation), que "
                     "calcula os gradientes da saída para a entrada. Redes com muitas camadas formam o aprendizado "
                     "profundo (deep learning)."),
                    ("Arquiteturas",
                     "Redes convolucionais (CNNs) usam filtros que percorrem a imagem e são a base da visão "
                     "computacional. Redes recorrentes (RNNs e LSTMs) processam sequências passo a passo. A "
                     "arquitetura Transformer, apresentada em 2017 no artigo 'Attention Is All You Need', usa o "
                     "mecanismo de atenção para relacionar todas as palavras de uma sequência em paralelo e é a base "
                     "dos grandes modelos de linguagem."),
                    ("Modelos de linguagem, embeddings e RAG",
                     "Grandes modelos de linguagem (LLMs) são Transformers treinados em enormes volumes de texto "
                     "para prever o próximo token; o texto é dividido em tokens, e cada token vira um vetor. "
                     "Embeddings são vetores que representam o significado de textos: textos parecidos têm vetores "
                     "próximos, o que se mede pela similaridade de cosseno. LLMs podem 'alucinar', gerando "
                     "informações falsas com aparência correta. A técnica RAG (geração aumentada por recuperação) "
                     "reduz esse problema: busca os trechos mais relevantes de uma base de documentos por "
                     "similaridade de embeddings e os coloca no prompt, para que o modelo responda com base neles "
                     "e cite as fontes. É exatamente a técnica usada neste Assistente de Estudos."),
                ],
                "pontos": [
                    "Neurônio: soma ponderada + viés + função de ativação.",
                    "Treino: gradiente descendente e retropropagação.",
                    "Transformer usa atenção; é a base dos LLMs.",
                    "RAG: busca trechos por embeddings e os envia no prompt para reduzir alucinações.",
                ],
            },
        ],
        "atividade": {
            "titulo": "Estudo de caso: busca A* e avaliação de modelos",
            "descricao": "1) Em um mapa com 5 cidades (invente as distâncias), execute o A* passo a passo mostrando g, h e f.\n"
                         "2) Um classificador de spam teve 80 verdadeiros positivos, 20 falsos positivos e 10 falsos negativos. Calcule precisão, revocação e F1.\n"
                         "3) Explique como o RAG reduz alucinações de um modelo de linguagem.",
        },
    },
]
