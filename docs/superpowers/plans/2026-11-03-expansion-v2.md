# Coin Commando V2 — implementação

Pedido: loja, armas e melhorias, mira livre com mouse, T lança faca comprada, ambientes diferentes, mais dificuldade e variedade. Mantém contratos de POO/Arcade/Peewee do PDF.

Decisões de implementação: inventário/dinheiro duram uma campanha; ranking não é gasto. Loja inicial, entre fases e em pontos de suprimento. AK inicial, SMG, escopeta e rifle de precisão; upgrades globais limitados; cinco facas por pacote; cura paga. Mouse controla direção e vetor de tiro/faca; teclado 1–4 troca arma. Arma separada do corpo para rotação visível, máquina de estados do jogador preservada. Fases selva/deserto/fundição/neve usam fundos próprios, cores de terreno e rotas diferentes. Dificuldade por pressão de tiros, minas/lasers telegrafados, emboscadas, chefe com segunda fase; dash defensivo com cooldown. Barris explosivos e combo tornam o combate mais dinâmico.

- [x] Regras de inventário, compra atômica, limite de upgrades e perfil de armas; testes saldo insuficiente/duplicatas.
- [x] Mira em coordenadas do mundo, rotação visual, tiros com dispersão/penetração, faca e dash; testes reais Arcade.
- [x] Loja clicável/teclado, pausa segura, persistência entre setores e retomada sem teclas presas.
- [x] Novos ambientes, rotas, hazards e emboscadas finitas; testes de cooldown, colisão e limites.
- [x] Testes de regressão, imagens de gameplay/loja, README atualizado, ZIP V2 salvo.

Revisão: mouse/câmera sem desenhar, origem do tiro perto de paredes, enter/escape na loja, falha de compra sem descontar saldo, armas preservadas na fase, inimigos de emboscada sem spawn sobre o jogador, projéteis/efeitos limitados.

Atualização de escopo pedida durante a execução: menu e telas subsequentes animados; botões com hover e seleção por disparo/impacto antes da ação. Implementado em ScreenMotion, inclusive loja e pausa.

Validação: 25 testes, incluindo travessia real de cada salto dos quatro mapas; revisão independente sem bloqueadores. A diferença da mira durante tremor foi compensada em coordenadas de câmera. A meta de moedas passa a 70% para reduzir retorno obrigatório e manter bônus opcionais para compras. Inventário dura uma campanha; persistência do ranking permanece inalterada.
