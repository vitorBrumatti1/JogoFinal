"""Jogador e sua máquina de estados: pulo > idle > caminhada."""

from pathlib import Path
import arcade
from models import BaseModel, Pontuacao, banco, inicializar_banco

BASE = Path(__file__).resolve().parent
ARQUIVO_SPRITESHEET = "assets/player.png"
LARGURA_FRAME, ALTURA_FRAME = 96, 128
COLUNAS_SPRITESHEET, TOTAL_FRAMES = 10, 10
TEMPO_POR_FRAME = 0.1


def asset(nome):
    return str(BASE / nome)


def garantir_spritesheet_jogador():
    if not (BASE / ARQUIVO_SPRITESHEET).is_file():
        raise FileNotFoundError("Assets ausentes. Extraia a pasta completa do jogo.")


class Jogador(arcade.Sprite):
    DIREITA, ESQUERDA = 1, -1

    def __init__(self):
        garantir_spritesheet_jogador()
        folha = arcade.load_spritesheet(asset(ARQUIVO_SPRITESHEET))
        quadros = folha.get_texture_grid(
            size=(LARGURA_FRAME, ALTURA_FRAME),
            columns=COLUNAS_SPRITESHEET,
            count=TOTAL_FRAMES,
        )
        self.textura_idle_direita = quadros[0]
        self.textura_pulo_direita = quadros[1]
        self.texturas_andando_direita = quadros[2:10]
        self.textura_idle_esquerda = quadros[0].flip_left_right()
        self.textura_pulo_esquerda = quadros[1].flip_left_right()
        self.texturas_andando_esquerda = [
            t.flip_left_right() for t in self.texturas_andando_direita
        ]
        super().__init__(self.textura_idle_direita, scale=0.55)
        self.grounded = None
        self.aim_facing = None
        self.virado_para = self.DIREITA
        self.frame_atual = 0
        self.tempo_animacao = 0.0
        self.tempo_piscando = 0.0
        self.tempo_total = 0.0

    def receber_dano(self):
        self.tempo_piscando = 0.9

    def update(self, delta_time=1 / 60):
        self.tempo_total += delta_time
        self.tempo_piscando = max(0.0, self.tempo_piscando - delta_time)
        self.alpha = (
            90 if self.tempo_piscando > 0 and int(self.tempo_total * 12) % 2 else 255
        )
        if self.change_x > 0:
            self.virado_para = self.DIREITA
        elif self.change_x < 0:
            self.virado_para = self.ESQUERDA
        if self.aim_facing is not None:
            self.virado_para = self.aim_facing
        direita = self.virado_para == self.DIREITA
        if abs(self.change_y) > 0.01 or self.grounded is False:
            self.texture = (
                self.textura_pulo_direita if direita else self.textura_pulo_esquerda
            )
            self.tempo_animacao = 0.0
            return
        if self.change_x == 0:
            self.frame_atual = 0
            self.tempo_animacao = 0.0
            self.texture = (
                self.textura_idle_direita if direita else self.textura_idle_esquerda
            )
            return
        self.tempo_animacao += delta_time
        while self.tempo_animacao >= TEMPO_POR_FRAME:
            self.tempo_animacao -= TEMPO_POR_FRAME
            self.frame_atual = (self.frame_atual + 1) % len(
                self.texturas_andando_direita
            )
        ciclo = (
            self.texturas_andando_direita if direita else self.texturas_andando_esquerda
        )
        self.texture = ciclo[self.frame_atual]
