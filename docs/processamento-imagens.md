# Processamento de imagens para PDFs escaneados

## Proposta

Adicionar ao Assistente de Estudos uma etapa para recuperar texto de páginas de PDF que são imagens. O processamento melhora a página antes do OCR (reconhecimento óptico de caracteres); o texto reconhecido segue para a indexação RAG, com o número original da página preservado.

## Objetivo

Permitir que o chat, os resumos, os flashcards e os simulados também usem conteúdo de PDFs escaneados ou fotografados, que hoje não fornecem texto ao extrator do PyMuPDF.

## Fundamentos

- **Imagem digital:** uma página rasterizada é uma matriz de pixels. Uma imagem em escala de cinza tem um valor de intensidade por pixel; uma imagem colorida geralmente tem canais vermelho, verde e azul.
- **Escala de cinza:** reduz a imagem a intensidades de claro e escuro e simplifica as etapas seguintes.
- **Redução de ruído:** filtros suavizam pequenas variações causadas por papel, câmera ou digitalização. Um filtro mediano é uma opção para ruído pontual.
- **Binarização:** transforma intensidades em pixels claros e escuros para separar texto do fundo. O limiar adaptativo calcula o limiar em regiões locais e pode funcionar melhor quando a iluminação varia.
- **Correção geométrica:** corrige rotação e inclinação da página. Para fotografias oblíquas, uma transformação de perspectiva pode aproximar a página de uma vista frontal.
- **OCR:** analisa os padrões de pixels e produz caracteres e palavras. O pré-processamento pode ajudar, mas não garante reconhecimento perfeito.

## Fluxo proposto

1. Extrair o texto normalmente com PyMuPDF.
2. Para páginas sem texto extraível, renderizar a página como imagem em resolução configurável.
3. Gerar uma cópia em escala de cinza, reduzir ruído, corrigir inclinação e aplicar binarização.
4. Executar OCR na imagem tratada.
5. Guardar o texto com o número da página e encaminhá-lo à divisão em trechos e à indexação vetorial já existentes.
6. Se o OCR não produzir texto, informar que aquela página não pôde ser reconhecida, sem interromper a indexação das demais páginas.

## Especificações técnicas iniciais

| Item | Proposta inicial |
|---|---|
| Linguagem | Python, compatível com o backend FastAPI existente |
| PDF e renderização | PyMuPDF, já presente no projeto |
| Processamento | OpenCV: tons de cinza, filtro, correção de inclinação e limiarização |
| OCR | Tesseract via `pytesseract`; requer instalação do executável Tesseract e do pacote de idioma português (`por`) no computador que executa o servidor |
| Resolução de renderização | Começar em 300 DPI, configurável para equilibrar legibilidade, memória e tempo |
| Integração | Na extração por página do pipeline de indexação em `backend/rag.py` |
| Rastreabilidade | Preservar nome do arquivo e número original da página nos trechos RAG |
| Falhas | Retornar erro claro se OCR não estiver instalado; ignorar uma página ilegível e continuar com as demais |

As bibliotecas e configurações finais devem ser confirmadas durante a implementação. O executável Tesseract é uma dependência externa ao `requirements.txt` e precisa ser documentado separadamente.

## Experimento com ângulos diferentes

Usar a mesma página de texto em quatro condições: vista frontal, rotação leve, fotografia oblíqua e iluminação desigual. Para cada condição, salvar a imagem original e a imagem processada e comparar o texto reconhecido. Registrar os erros de reconhecimento antes e depois do processamento; uma medida possível é a taxa de erro por caractere (CER).

## Critérios para considerar a primeira versão pronta

- PDFs com texto continuam usando a extração atual.
- Páginas escaneadas passam pelo OCR e seus textos entram na busca RAG.
- As fontes continuam indicando o arquivo e a página corretos.
- A demonstração apresenta imagens originais e processadas, além do texto reconhecido.
- O relatório registra parâmetros, limitações e resultados do experimento com páginas em ângulos diferentes.

## Limitações esperadas

OCR pode errar em escrita manual, fórmulas, tabelas, baixa resolução, páginas muito inclinadas e fotografias com sombras ou perspectiva forte. Esses casos devem ser mostrados na avaliação como limites do método, não tratados como garantias de reconhecimento.
