# Tutorial do KOH - Como o aplicativo funciona

**Idioma:** 🇺🇸 [English](koh-tutorial-en.md) · 🇧🇷 **Português** · 🇪🇸 [Español](koh-tutorial-es.md)

Este tutorial explica, em linguagem clara, como o KOH funciona, quais parâmetros ele usa e como cada parte da interface influencia o resultado final.

> Observação: o aplicativo foi pensado para padronizar retratos, detectando a face principal, centralizando-a e exportando uma imagem final em dimensões definidas.

## 1. Visão geral do fluxo

O processo principal do app é:

1. receber uma ou mais imagens;
2. localizar a maior face presente;
3. ajustar a escala e a posição da face dentro de uma imagem final;
4. aplicar o tipo de fundo desejado;
5. salvar o resultado em uma pasta de saída.

Em termos simples, o programa tenta transformar qualquer rosto detectado em uma composição padronizada, mantendo a face no lugar certo e com proporções consistentes.

## 2. O que o app faz no fundo

A lógica principal está dividida em algumas etapas:

- detecção facial com YuNet;
- seleção da maior face detectada;
- alinhamento e redimensionamento com base na proporção da face;
- recorte e posicionamento na imagem final;
- remoção opcional de fundo.

A execução do processamento é feita com pipeline de imagem em OpenCV e, em lote, o app pode processar várias fotos em sequência.

## 3. Como a interface está organizada

A janela principal da aplicação contém as seguintes áreas:

### 3.1 Área de entrada de imagens

Aqui você seleciona as fotos que serão processadas.

- botão "Add Images" para enviar arquivos individuais;
- botão "Add Folder" para carregar uma pasta inteira;
- botão "Clear" para remover a seleção atual;
- lista de arquivos selecionados para confirmar o lote.

Espaço para imagem ilustrativa:

```md
![Imagem ilustrativa: seleção de imagens no KOH](./images/placeholder-input-images.png)
```

> Insira aqui uma imagem mostrando a lista de fotos e os botões de seleção.

### 3.2 Configurações de saída

Nesta seção você define como a imagem final será montada:

- Width: largura da imagem final em pixels;
- Height: altura da imagem final em pixels;
- Face Ratio: quanto a face ocupa na largura final;
- Position X: deslocamento horizontal da face;
- Position Y: deslocamento vertical da face;
- Background Removal: tipo de fundo a ser aplicado.

Esses parâmetros influenciam diretamente o resultado visual.

Espaço para imagem ilustrativa:

```md
![Imagem ilustrativa: configurações de saída do KOH](./images/placeholder-output-settings.png)
```

> Insira aqui uma screenshot ou mockup dos campos de configuração.

### 3.3 Pasta de saída

Você escolhe a pasta onde as imagens processadas serão salvas.

O app cria automaticamente o diretório se ele ainda não existir e salva os arquivos processados dentro dele.

Espaço para imagem ilustrativa:

```md
![Imagem ilustrativa: seleção da pasta de saída](./images/placeholder-output-folder.png)
```

> Insira aqui uma imagem da seleção de diretório de destino.

### 3.4 Barra de progresso e status

Ao iniciar o processamento, a interface mostra:

- progresso por imagem;
- status geral do processamento;
- mensagens de sucesso ou erro;
- último estado do lote.

Espaço para imagem ilustrativa:

```md
![Imagem ilustrativa: barra de progresso do processamento](./images/placeholder-progress.png)
```

> Insira aqui uma imagem da barra de progresso em execução.

## 4. O que cada característica faz

### 4.1 Width (largura)

Define a largura final da imagem exportada.

Se a imagem for muito estreita, a face pode parecer comprimida. Se for muito larga, o rosto pode parecer pequeno em relação ao quadro.

### 4.2 Height (altura)

Define a altura final da imagem.

Ela influencia a distância vertical entre a face e os limites da imagem. Em retratos, esse valor é importante para manter a cabeça e o peito bem enquadrados.

### 4.3 Face Ratio

Este controle define a proporção da face em relação à largura final da imagem.

Exemplo:

- valor baixo: a face ocupa menos espaço;
- valor alto: a face ocupa mais espaço e fica maior no quadro.

No código, a face é escalada para alcançar a proporção desejada.

### 4.4 Position X

Define a posição horizontal da face dentro da imagem final.

- 50%: centro horizontal;
- valores menores: face mais à esquerda;
- valores maiores: face mais à direita.

### 4.5 Position Y

Define a posição vertical da face dentro da imagem final.

- 40% é o valor padrão, o que normalmente deixa o rosto mais alto que o centro absoluto;
- valores menores: rosto mais acima;
- valores maiores: rosto mais abaixo.

### 4.6 Background Removal

A remoção de fundo pode ser configurada em três modos:

#### Disabled

Sem remoção de fundo. O resultado final mantém o fundo original da imagem, mas o rosto ainda é centralizado e redimensionado.

#### Fast

Usa um algoritmo rápido baseado em segmentação e heurísticas para isolar o sujeito e remover o fundo de forma mais simples.

#### AI

Usa MODNet, um modelo de IA especializado em matting de retrato. Esse modo tende a produzir melhor separação entre rosto e fundo, especialmente em imagens com iluminação e contraste mais desafiadores.

## 5. Como o algoritmo detecta e centraliza a face

O aplicativo usa o detector YuNet para localizar rostos.

### Passo a passo

1. a imagem é carregada;
2. o detector procura rostos;
3. a maior face detectada é escolhida;
4. o centro do rosto é calculado;
5. a imagem é escalada com base na proporção configurada;
6. a face é deslocada para a posição X/Y alvo;
7. o resultado é exportado.

Em termos matemáticos, o programa aplica uma transformação afim para mover e escalar a face dentro do quadro final. Esse processo mantém a composição padronizada mesmo quando a pessoa aparece em diferentes tamanhos ou posições na imagem original.

## 6. O que acontece em cada imagem processada

Para cada arquivo do lote, o app:

- valida a imagem;
- carrega o arquivo;
- detecta a face principal;
- ajusta a composição;
- aplica a remoção de fundo, se configurado;
- salva a imagem final na pasta de saída.

Se nenhuma face for detectada, o processamento é registrado como erro e o arquivo não é salvo.

## 7. Exportação do resultado

Os arquivos finais são salvos com nomes no formato:

- `koh_<nome-da-imagem>.jpg` quando o fundo não é removido;
- `koh_<nome-da-imagem>.png` quando a remoção de fundo está ativa.

Esses nomes ajudam a identificar rapidamente que a imagem foi processada pelo KOH.

## 8. Como o processamento em lote funciona

O app pode receber:

- várias imagens ao mesmo tempo;
- uma pasta inteira com imagens;
- uma combinação de arquivos e diretórios.

Em seguida, ele percorre cada item da fila e processa um por um. O progresso é atualizado para mostrar o avanço total do lote.

Espaço para imagem ilustrativa:

```md
![Imagem ilustrativa: processamento em lote do KOH](./images/placeholder-batch-processing.png)
```

> Insira aqui uma imagem mostrando o processamento em sequência de várias imagens.

## 9. Dicas para obter bons resultados

- use fotos com rosto bem visível;
- prefira boa iluminação;
- evite rostos parcialmente ocultos;
- teste valores de Face Ratio e Position Y para o estilo desejado;
- se a imagem tiver fundo muito complexo, o modo AI costuma entregar resultados mais limpos.

## 10. Resumo rápido

O KOH é um app para padronizar retratos e exportar resultados visuais consistentes.

Ele funciona basicamente assim:

- detecta o rosto;
- centraliza e redimensiona o rosto na imagem final;
- ajusta posição e proporção;
- remove o fundo quando necessário;
- salva imagens prontas para uso.

Se você entendeu esses controles, já sabe o suficiente para começar a usar o aplicativo com bons resultados.

## 11. Próximos passos

- teste com uma imagem simples para observar o efeito de Face Ratio;
- altere Position X e Position Y para mudar o enquadramento;
- compare Disabled, Fast e AI para ver a diferença de fundo;
- experimente um lote completo para avaliar a padronização do resultado.

---

Se quiser, este tutorial pode ser complementado com:

- manual de uso guiado passo a passo;
- checklist de configurações por tipo de retrato;
- exemplos antes/depois para cada modo de fundo.
