
import cv2
import numpy as np


class Centralizador:
    """Padroniza a escala e a posição de faces em imagens."""

    def centralizar(
        self,
        imagem,
        face,
        largura,
        altura,
        proporcao_face,
        posicao_x=0.5,
        posicao_y=0.5,
        cor_fundo=(255, 255, 255),
    ):
        """
        Args:
            imagem: imagem original (numpy.ndarray).
            face: coordenadas (x, y, w, h) detectadas.
            largura: largura da imagem final em pixels.
            altura: altura da imagem final em pixels.
            proporcao_face: fração da largura final ocupada pela face.
            posicao_x: posição horizontal relativa do centro da face.
            posicao_y: posição vertical relativa do centro da face.
            cor_fundo: cor de preenchimento das bordas (BGR).

        Returns:
            Imagem centralizada (numpy.ndarray).
        """

        if imagem is None or imagem.size == 0:
            raise ValueError("Imagem inválida.")

        if largura <= 0 or altura <= 0:
            raise ValueError("Dimensões inválidas.")

        if not 0 < proporcao_face <= 1:
            raise ValueError("Proporção deve estar entre 0 e 1.")

        if not 0 <= posicao_x <= 1 or not 0 <= posicao_y <= 1:
            raise ValueError("Posições devem estar entre 0 e 1.")

        x, y, w, h = map(float, face[:4])

        if w <= 0 or h <= 0:
            raise ValueError("Dimensões da face inválidas.")

        # Centro da face original
        centro_x = x + w / 2
        centro_y = y + h / 2

        # Escala para atingir a proporção desejada
        escala = (largura * proporcao_face) / w

        # Centro desejado na imagem final
        destino_x = largura * posicao_x
        destino_y = altura * posicao_y

        # Translação necessária
        deslocamento_x = destino_x - escala * centro_x
        deslocamento_y = destino_y - escala * centro_y

        matriz = np.array([
            [escala, 0, deslocamento_x],
            [0, escala, deslocamento_y]
        ], dtype=np.float64)

        return cv2.warpAffine(
            imagem,
            matriz,
            (largura, altura),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=cor_fundo
        )
