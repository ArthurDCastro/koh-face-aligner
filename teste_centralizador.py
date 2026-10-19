
from pathlib import Path

import cv2

from src.detector import DetectorYuNet
from src.centralizador import Centralizador


# Configurações
IMAGEM_ENTRADA = Path("tests/test1/GASP6177.JPG")
IMAGEM_SAIDA = Path("resultado.jpg")

LARGURA = 800
ALTURA = 800
PROPORCAO_FACE = 0.25
POSICAO_X = 0.50
POSICAO_Y = 0.40


def main():
    # Carregar imagem
    imagem = cv2.imread(str(IMAGEM_ENTRADA))

    if imagem is None:
        print(f"Erro ao carregar: {IMAGEM_ENTRADA}")
        return

    # Detectar faces
    detector = DetectorYuNet()
    faces = detector.detectar(imagem)

    print(f"Faces detectadas: {len(faces)}")

    if not faces:
        print("Nenhuma face encontrada.")
        return

    # Selecionar a maior face
    face = max(faces, key=lambda f: f[2] * f[3])

    print(f"Face selecionada: {face}")

    # Centralizar
    centralizador = Centralizador()

    resultado = centralizador.centralizar(
        imagem=imagem,
        face=face,
        largura=LARGURA,
        altura=ALTURA,
        proporcao_face=PROPORCAO_FACE,
        posicao_x=POSICAO_X,
        posicao_y=POSICAO_Y,
    )

    # Salvar resultado
    if not cv2.imwrite(str(IMAGEM_SAIDA), resultado):
        raise RuntimeError("Erro ao salvar imagem.")

    print(f"Imagem salva em: {IMAGEM_SAIDA}")

    # Visualizar original e resultado
    cv2.imshow("Centralizada", resultado)

    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
