# Comparação estatística (Issue #15)

- Times: 75 x 65 | partidas por cenário: 10000 | seeds 0..9999
- Moral: M=2, beta=0.05
- Faltas: p=0.05 por confronto | Lesões: p=0.05 por falta (só evento)

## Resumo

| Cenário | Gols A | Gols B | Gols/partida | Var A | Var B | Var saldo | Var total | Favorito vence | Tent./seq. | Faltas/jogo | Lesões/jogo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base (tudo desligado) | 1.544 | 0.866 | 2.410 | 1.324 | 0.821 | 2.349 | 1.941 | 54.2% | 1.312 | 0.00 | 0.00 |
| só moral | 1.558 | 0.858 | 2.416 | 1.394 | 0.832 | 2.496 | 1.956 | 54.6% | 1.311 | 0.00 | 0.00 |
| só faltas | 1.516 | 0.887 | 2.403 | 1.300 | 0.829 | 2.346 | 1.911 | 52.7% | 1.311 | 6.17 | 0.00 |
| faltas + lesões | 1.516 | 0.887 | 2.403 | 1.300 | 0.829 | 2.346 | 1.911 | 52.7% | 1.311 | 6.17 | 0.31 |
| tudo ligado | 1.531 | 0.878 | 2.409 | 1.371 | 0.848 | 2.509 | 1.930 | 53.2% | 1.310 | 6.18 | 0.31 |

## Hipótese: a variância do placar aumenta com a moral ativa

- Var do saldo: 2.349 -> 2.496
- Var dos gols totais: 1.941 -> 1.956
- Var gols A: 1.324 -> 1.394 | Var gols B: 0.821 -> 0.832

## Distribuição de placares: base (tudo desligado)

| Placar A x B | % das partidas |
|---|---|
| 1 x 0 | 13.4% |
| 1 x 1 | 13.4% |
| 2 x 0 | 11.5% |
| 2 x 1 | 10.6% |
| 0 x 0 | 6.9% |
| 0 x 1 | 6.9% |
| 3 x 0 | 6.4% |
| 1 x 2 | 5.7% |
| 3 x 1 | 4.9% |
| 2 x 2 | 4.4% |

## Distribuição de placares: só moral

| Placar A x B | % das partidas |
|---|---|
| 1 x 0 | 13.3% |
| 1 x 1 | 12.9% |
| 2 x 0 | 11.6% |
| 2 x 1 | 10.3% |
| 0 x 1 | 7.0% |
| 0 x 0 | 6.9% |
| 3 x 0 | 6.6% |
| 1 x 2 | 5.7% |
| 3 x 1 | 4.9% |
| 2 x 2 | 4.1% |

## Distribuição de placares: só faltas

| Placar A x B | % das partidas |
|---|---|
| 1 x 1 | 13.6% |
| 1 x 0 | 13.3% |
| 2 x 0 | 11.4% |
| 2 x 1 | 10.1% |
| 0 x 1 | 7.2% |
| 0 x 0 | 6.7% |
| 1 x 2 | 6.1% |
| 3 x 0 | 6.0% |
| 3 x 1 | 4.9% |
| 2 x 2 | 4.6% |

## Distribuição de placares: faltas + lesões

| Placar A x B | % das partidas |
|---|---|
| 1 x 1 | 13.6% |
| 1 x 0 | 13.3% |
| 2 x 0 | 11.4% |
| 2 x 1 | 10.1% |
| 0 x 1 | 7.2% |
| 0 x 0 | 6.7% |
| 1 x 2 | 6.1% |
| 3 x 0 | 6.0% |
| 3 x 1 | 4.9% |
| 2 x 2 | 4.6% |

## Distribuição de placares: tudo ligado

| Placar A x B | % das partidas |
|---|---|
| 1 x 0 | 13.2% |
| 1 x 1 | 13.1% |
| 2 x 0 | 11.6% |
| 2 x 1 | 9.5% |
| 0 x 1 | 7.4% |
| 0 x 0 | 6.7% |
| 3 x 0 | 6.6% |
| 1 x 2 | 5.9% |
| 3 x 1 | 4.9% |
| 2 x 2 | 4.4% |
