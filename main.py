"""Execute: python main.py (Python 3.10+, Arcade 3.3.3)."""

import arcade
from actors import BaseModel, Pontuacao, Jogador, inicializar_banco
from game import Bloco, TelaJogo, TelaMenu, TelaRanking, TelaGameOver, GameWindow


def main():
    inicializar_banco()
    window = GameWindow()
    window.show_view(TelaMenu())
    arcade.run()


if __name__ == "__main__":
    main()
