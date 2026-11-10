# Coin Commando

Jogo de ação e plataforma 2D feito com Python Arcade para a atividade de Programação Orientada a Objetos do IFPR — Campus Paranavaí.

Quatro fases em ambientes diferentes, mira livre, AK-47, armas e melhorias na loja, drones com granadas, chefe final e ranking local. Interface com animações, efeitos e filtro de fliperama.

## Requisitos

- Python 3.10 ou superior
- OpenGL 3.3 ou superior

## Executar

No Windows, dentro da pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

No Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Mantenha a pasta `assets` junto aos arquivos Python. O banco `ranking.db` é criado automaticamente na primeira execução e não é versionado. A pasta do projeto precisa permitir escrita.

## Controles

| Comando | Ação |
|---|---|
| A/D ou setas | Andar |
| Espaço/W/seta para cima | Pular |
| Mouse | Mirar |
| Botão esquerdo/J/X | Disparar |
| R durante a partida | Recarregar |
| T | Lançar faca comprada na loja |
| Shift | Dash |
| 1–4 | Equipar arma adquirida |
| B | Loja no início ou perto da saída |
| P/Esc | Pausar/retomar |
| M na pausa | Voltar ao menu |
| F8 | Alternar som |
| F9 | Reduzir efeitos de tela |
| R no menu ou resultado | Abrir ranking |

Colete pelo menos **70% das moedas** e alcance a saída. Na última fase, derrote também o guardião. Créditos compram armas, facas, melhorias e vida; equipamentos duram uma campanha. Ao terminar, digite seu nome e pressione Enter para registrar a pontuação.

Plataformas suspensas sustentam personagens e granadas. Chão e coberturas explícitas bloqueiam tiros. Soldados precisam estar virados para o jogador e ter linha de visão para disparar.

## Estrutura

- `main.py`: entrada do jogo.
- `game.py`: telas, física e integração do combate.
- `actors.py`, `campaign.py`, `level_design.py`: animações, regras e fases.
- `combat.py`, `weapon_art.py`: projéteis, coberturas e armas.
- `effects.py`, `world_fx.py`, `polish.py`: efeitos e apresentação.
- `arcade_style.py`, `ui_fx.py`, `sound.py`: interface e áudio.
- `models.py`: persistência Peewee/SQLite.
- `assets/`: imagens e sons usados em execução.
- `tests/`: testes automatizados; `.github/workflows/`: integração contínua.

## Testes

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

Os testes gráficos usam Arcade real em modo headless. No Linux, exigem EGL/OpenGL; o workflow do GitHub instala essas dependências. Os testes de persistência usam banco temporário.

## Atividade de POO

O projeto utiliza `PhysicsEnginePlatformer` e `can_jump()`, `Bloco` derivado de `Sprite`, `SpriteList`, spritesheet com quadros de 96×128 e animação a cada 100 ms. O ranking utiliza modelos Peewee, captura de nome, consulta Top 10 no construtor e exibição com `enumerate`/`draw_text`.

As imagens foram geradas para o projeto e adaptadas para o motor; os efeitos sonoros foram sintetizados localmente. A validação automatizada não substitui testar áudio e sensação de combate no computador de apresentação.

Desenvolvido por **Vitor Rufino Brumatti — 3º Info / IFPR**.
