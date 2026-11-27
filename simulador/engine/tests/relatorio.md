# Comparação estatística (Issue #15)

- Times: 75 x 74 | partidas por cenário: 1000 | seeds 0..999
- Moral: M=2, beta=0.05
- Faltas: p=0.05 por confronto | Lesões: p=0.05 por falta (só evento)

## Resumo

| Cenário | Gols A | Gols B | Gols/partida | Var A | Var B | Var saldo | Var total | Favorito vence (% partidas) | Empates | Tent./seq. | Faltas/jogo | Lesões/jogo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base (tudo desligado) | 1.221 | 1.111 | 2.332 | 1.080 | 1.007 | 2.294 | 1.880 | 40.2% | 25.1% | 1.297 | 0.00 | 0.00 |
| só moral | 1.218 | 1.117 | 2.335 | 1.096 | 1.015 | 2.357 | 1.867 | 40.0% | 24.7% | 1.296 | 0.00 | 0.00 |
| só faltas | 1.241 | 1.158 | 2.399 | 1.059 | 1.007 | 2.294 | 1.838 | 38.2% | 27.6% | 1.301 | 6.16 | 0.00 |
| faltas + lesões | 1.241 | 1.158 | 2.399 | 1.059 | 1.007 | 2.294 | 1.838 | 38.2% | 27.6% | 1.301 | 6.16 | 0.31 |
| tudo ligado | 1.241 | 1.155 | 2.396 | 1.097 | 1.075 | 2.501 | 1.843 | 38.6% | 26.5% | 1.301 | 6.17 | 0.31 |

## Hipótese: a variância do placar aumenta com a moral ativa

- Var do saldo: 2.294 -> 2.357
- Var dos gols totais: 1.880 -> 1.867
- Var gols A: 1.080 -> 1.096 | Var gols B: 1.007 -> 1.015

## Distribuição de placares: base (tudo desligado)

| Placar A x B | % das partidas |
|---|---|
| 1 x 1 | 13.4% |
| 1 x 0 | 11.9% |
| 0 x 1 | 10.7% |
| 2 x 1 | 9.4% |
| 1 x 2 | 8.8% |
| 2 x 0 | 7.5% |
| 0 x 0 | 7.2% |
| 0 x 2 | 6.6% |
| 3 x 1 | 4.6% |
| 2 x 2 | 3.9% |

## Distribuição de placares: só moral

| Placar A x B | % das partidas |
|---|---|
| 1 x 1 | 13.2% |
| 1 x 0 | 11.7% |
| 0 x 1 | 10.4% |
| 1 x 2 | 9.2% |
| 2 x 1 | 9.0% |
| 2 x 0 | 7.7% |
| 0 x 0 | 7.2% |
| 0 x 2 | 7.0% |
| 3 x 1 | 4.2% |
| 3 x 0 | 3.9% |

## Distribuição de placares: só faltas

| Placar A x B | % das partidas |
|---|---|
| 1 x 1 | 15.9% |
| 1 x 0 | 10.4% |
| 0 x 1 | 9.7% |
| 1 x 2 | 9.7% |
| 2 x 1 | 8.4% |
| 2 x 0 | 8.1% |
| 0 x 0 | 6.3% |
| 0 x 2 | 5.9% |
| 2 x 2 | 4.7% |
| 3 x 1 | 3.8% |

## Distribuição de placares: faltas + lesões

| Placar A x B | % das partidas |
|---|---|
| 1 x 1 | 15.9% |
| 1 x 0 | 10.4% |
| 0 x 1 | 9.7% |
| 1 x 2 | 9.7% |
| 2 x 1 | 8.4% |
| 2 x 0 | 8.1% |
| 0 x 0 | 6.3% |
| 0 x 2 | 5.9% |
| 2 x 2 | 4.7% |
| 3 x 1 | 3.8% |

## Distribuição de placares: tudo ligado

| Placar A x B | % das partidas |
|---|---|
| 1 x 1 | 15.6% |
| 1 x 0 | 10.1% |
| 0 x 1 | 9.7% |
| 1 x 2 | 9.7% |
| 2 x 0 | 8.9% |
| 2 x 1 | 8.0% |
| 0 x 0 | 6.3% |
| 0 x 2 | 6.1% |
| 2 x 2 | 4.0% |
| 3 x 0 | 3.9% |

## Comparação de ratings (dinâmicas desligadas)

- Partidas por combinação: 1000 | seeds 0..999

| Times A x B | Favorito vence (% partidas) | Empates | Gols A/jogo | Gols B/jogo | Gols/jogo |
|---|---|---|---|---|---|
| 70 x 0 | 100.0% | 0.0% | 6.324 | 0.000 | 6.324 |
| 70 x 10 | 100.0% | 0.0% | 5.208 | 0.000 | 5.208 |
| 70 x 20 | 99.2% | 0.8% | 4.215 | 0.024 | 4.239 |
| 70 x 30 | 95.9% | 3.8% | 3.334 | 0.096 | 3.430 |
| 70 x 40 | 89.9% | 8.6% | 2.709 | 0.249 | 2.958 |
| 70 x 50 | 73.5% | 16.7% | 2.073 | 0.567 | 2.640 |
| 70 x 60 | 54.5% | 25.3% | 1.567 | 0.864 | 2.431 |
| 70 x 65 | 45.9% | 26.3% | 1.364 | 0.980 | 2.344 |
| 70 x 68 | 43.1% | 25.5% | 1.259 | 1.063 | 2.322 |
