# Direção visual e fontes

Referência fornecida pelo usuário: plataforma lateral arcade, céu azul claro, ruínas com musgo, pontes e ação legível. A referência orienta linguagem e composição; os assets não são extraídos dela.

Imagens geradas com a ferramenta de imagens integrada:
- `ruins.png`: cenário lateral 16-bit, céu azul, montanhas e cascatas distantes, ruínas militares cobertas por vegetação, espaço aberto para jogabilidade, sem personagens/UI/texto.
- `player-source.png`: dez poses em grade 5×2, herói original de bandana vermelha, colete verde e AK-47; idle, salto e oito poses de caminhada; fundo transparente.
- `enemies-source.png`: soldado com uniforme bege, drone de rotor com sensor vermelho e tanque guardião; vista lateral; fundo removido por edição de imagem.

`tools/pack_sprites.py` recorta as células e normaliza dimensões. `stone-source.png`: parede frontal de ruínas em pixel art com musgo, fendas e relevos, sem perspectiva; empacotada em tiles de 48px.

Tiles auxiliares e áudios são sintetizados pelo script versionado `tools/build_assets.py`. Sprites e ilustração completos acompanham o projeto; não há dependência de APIs durante o jogo.

## Expansão V2
- `desert.png`: deserto industrial ao pôr do sol, mesas, depósitos e ferrovia, centro aberto, pixel art lateral.
- `foundry.png`: fundição com vigas, correntes, tubulações, laranja de fornalhas e aço azul, sem plataformas de colisão no fundo.
- `snow.png`: montanhas e fortaleza gelada ao crepúsculo, radares, pinheiros e neve, centro aberto.
- `player-body-source.png`: dez poses do soldado original com mãos próximas ao peito e sem arma, mesma ordem de animação; recorte transparente produzido com edição de imagem.
O arsenal separado é desenhado por peças vetoriais pequenas em `world_fx.draw_gun`, permitindo rotação e diferenças entre quatro armas. As bordas de terreno recebem areia, metal ou neve conforme o ambiente.

## Arcade Edition V3 — 10/11/2026
`arcade-menu.png` foi produzido com edição de imagem integrada a partir da referência anexada: remoção de logo, HUD, botões, personagens e itens; preservação de cidade noturna, vigas e plataformas. Logo, alfabeto bitmap 5×7, ícones, botões e HUD são desenhados em código; sprites da campanha compõem a cena animada. A arte de fundo não contém botões falsos.
`arcade_style.py` aplica textura de scanlines em uma única chamada e desenha a moldura de gabinete. `combat.py` contém as granadas e os efeitos de disparo/impacto separados da física de acerto.
