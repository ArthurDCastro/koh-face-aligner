# KOH - Keypoint-Oriented Harmonization

KOH é uma aplicação desktop multiplataforma para detecção automática de faces, alinhamento e padronização de imagens com foco em retratos. O projeto usa visão computacional para localizar a maior face da imagem, centralizá-la com base em proporções configuráveis e exportar o resultado em tamanhos padronizados. Também oferece remoção opcional de fundo por métodos rápidos ou baseados em IA.

## Visão geral

O fluxo principal do projeto é:

- detectar a face principal em uma imagem;
- centralizar e redimensionar a região facial com base em parâmetros como largura, altura e proporção da face;
- aplicar recorte e posicionamento para padronizar a composição;
- salvar a imagem final em diretório de saída;
- opcionalmente remover o fundo usando estratégias de processamento do projeto.

A interface gráfica permite processar várias imagens em lote a partir de arquivos ou pastas inteiras.

## Funcionalidades

- Detecção de rostos com YuNet;
- Seleção da maior face detectada;
- Ajuste de proporção facial e posicionamento horizontal/vertical;
- Processamento em lote de imagens;
- Exportação em JPG ou PNG;
- Remoção de fundo em modo `none`, `fast` e `ai`;
- Suporte a Windows e Linux via Python e OpenCV.

## Estrutura do projeto

- `src/main.py` — ponto de entrada da aplicação;
- `src/interface.py` — interface gráfica em PySide6;
- `src/processing.py` — pipeline principal de processamento;
- `src/detector.py` — detecção de faces com YuNet;
- `src/centralizer.py` — centralização e alinhamento facial;
- `src/segmentation.py` — remoção de fundo com MODNet;
- `src/background.py` — remoção rápida de fundo;
- `models/` — pesos ONNX dos modelos usados;
- `requirements.txt` — dependências do projeto.

## Requisitos

- Python 3.10+
- Pip
- Ambiente virtual recomendado

## Download dos executáveis

Os executáveis para **Windows** e **Linux (Ubuntu)** são gerados pelo GitHub Actions.

**[Acessar os downloads do KOH (GitHub Actions)](https://github.com/ArthurDCastro/koh-face-aligner/actions/workflows/build.yml)**

1. Abra o link acima e selecione a execução **Build KOH** mais recente concluída com sucesso.
2. Na seção **Artifacts**, baixe o pacote correspondente ao sistema:
   - **Windows:** `KOH-windows-x64` — extraia o ZIP e execute `KOH.exe`.
   - **Ubuntu (Linux):** `KOH-linux-x64` — extraia o pacote e execute `KOH/KOH` (se necessário, dê permissão com `chmod +x KOH/KOH`).

> Para baixar os artefatos, o GitHub pode exigir que você esteja conectado à sua conta. Os downloads aparecem apenas nas execuções que concluíram a etapa de publicação dos artefatos.

## Instalação

Clone o projeto e instale as dependências:

```bash
git clone https://github.com/ArthurDCastro/koh-face-aligner.git
cd koh-face-aligner
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Você também pode usar o script de instalação:

```bash
bash install.sh
```

## Execução

```bash
source .venv/bin/activate
python -m src.main
```

A interface abrirá e permitirá:

1. selecionar uma ou mais imagens;
2. escolher uma pasta de saída;
3. definir largura, altura, proporção facial e posição;
4. escolher o tipo de remoção de fundo;
5. iniciar o processamento em lote.

## Modelos utilizados e créditos

Este projeto utiliza modelos de inteligência artificial para detecção facial e remoção de fundo. Abaixo os modelos e as referências originais.

### 1) YuNet — detecção de faces

O detector de faces do projeto usa o modelo YuNet para localizar rostos em tempo real e com baixa latência.

- Artigo: Wu, W., Peng, H., Yu, S. "YuNet: A tiny millisecond-level face detector". Machine Intelligence Research, 2023.
- Referência bibliográfica:

```bibtex
@article{wu2023yunet,
  title={Yunet: A tiny millisecond-level face detector},
  author={Wu, Wei and Peng, Hanyang and Yu, Shiqi},
  journal={Machine Intelligence Research},
  volume={20},
  number={5},
  pages={656--665},
  year={2023},
  publisher={Springer}
}
```

O arquivo `models/face_detection_yunet_2023mar.onnx` corresponde a esse modelo de detecção facial usado pelo projeto.

### 2) MODNet — remoção de fundo/alpha matting de retrato

Para a remoção de fundo de retratos, o projeto usa o MODNet, um modelo de matting trimap-free focado em retratos.

- Artigo: Ke, Z., Sun, J., Li, K., Yan, Q., Lau, R. W. H. "MODNet: Real-Time Trimap-Free Portrait Matting via Objective Decomposition". AAAI, 2022.
- Referência bibliográfica:

```bibtex
@InProceedings{MODNet,
  author = {Zhanghan Ke and Jiayu Sun and Kaican Li and Qiong Yan and Rynson W.H. Lau},
  title = {MODNet: Real-Time Trimap-Free Portrait Matting via Objective Decomposition},
  booktitle = {AAAI},
  year = {2022},
}
```

O arquivo `models/modnet/modnet_photographic.onnx` é o peso do modelo MODNet usado para gerar a máscara alfa do retrato e remover o fundo.

### Créditos e uso

Os modelos acima são utilizados neste projeto com atribuição aos autores originais. Recomendamos manter as referências acadêmicas em qualquer material derivado ou documentação pública do projeto. Se houver redistribuição dos pesos ONNX em outros contextos, verifique também os termos específicos das implementações originais e dos repositórios oficiais dos autores.

## Tecnologias principais

- Python
- OpenCV / OpenCV Contrib
- PySide6
- NumPy
- ONNX Runtime
- PyInstaller

## Licença

Este repositório não inclui uma licença explícita no momento. Caso você tenha intenção de distribuir ou reutilizar o projeto comercialmente, verifique as condições dos modelos e bibliotecas utilizadas antes da publicação final.

## Observações

- O projeto foi desenvolvido para padronização de retratos e processamento em lote.
- O modelo `ai` do programa está implementado com MODNet, enquanto a interface pode apresentar rótulos mais genéricos ou antigos em alguns pontos.
- Para melhores resultados, use imagens com rosto bem visível e boa iluminação.
