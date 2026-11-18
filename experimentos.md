# Diferença de nível entre os times

| Cenário | Gols/jogo | Vit. A | Empate | Vit. B | Tent./seq. | Continuação | Gol/tent. | Perda | Duelos A | MD3 A |
|---|---|---|---|---|---|---|---|---|---|---|
| 70 x 70 | 1.17 | 31.4% | 39.2% | 29.4% | 1.30 | 23.0% | 15.0% | 62.1% | 50.1% | 50.3% |
| 72 x 68 | 1.17 | 35.4% | 39.0% | 25.6% | 1.30 | 23.1% | 15.0% | 61.9% | 51.4% | 54.2% |
| 80 x 60 | 1.25 | 53.6% | 34.7% | 11.7% | 1.32 | 24.3% | 15.8% | 60.0% | 56.9% | 68.9% |
| 90 x 40 | 1.70 | 82.9% | 15.6% | 1.5% | 1.43 | 30.1% | 19.8% | 50.1% | 68.7% | 91.3% |
| 100 x 20 | 2.36 | 95.0% | 5.0% | 0.0% | 1.57 | 36.4% | 25.0% | 38.6% | 82.5% | 99.5% |

## Parâmetros

- **70 x 70**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=5
- **72 x 68**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=5
- **80 x 60**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=5
- **90 x 40**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=5
- **100 x 20**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=5

# Variação de parâmetros (70 x 70)

| Cenário | Gols/jogo | Vit. A | Empate | Vit. B | Tent./seq. | Continuação | Gol/tent. | Perda | Duelos A | MD3 A |
|---|---|---|---|---|---|---|---|---|---|---|
| padrão | 1.17 | 31.4% | 39.2% | 29.4% | 1.30 | 23.0% | 15.0% | 62.1% | 50.1% | 50.3% |
| g_max=0.60 | 1.95 | 36.4% | 28.8% | 34.8% | 1.30 | 23.2% | 25.0% | 51.8% | 50.0% | 50.2% |
| c_max=0.20 | 0.94 | 28.4% | 45.0% | 26.6% | 1.05 | 4.8% | 14.9% | 80.3% | 50.1% | 50.4% |
| r=0.40 | 1.13 | 31.0% | 40.3% | 28.7% | 1.26 | 20.4% | 14.9% | 64.6% | 50.1% | 50.3% |
| sem bônus | 1.16 | 30.9% | 39.5% | 29.6% | 1.30 | 23.1% | 14.9% | 62.0% | 50.0% | 50.0% |
| bônus=10 | 1.16 | 31.5% | 38.6% | 29.9% | 1.30 | 22.9% | 14.9% | 62.1% | 50.1% | 50.3% |

## Parâmetros

- **padrão**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=5
- **g_max=0.60**: n=4000, seed_base=0, g_max=0.5, c_max=0.5, r=0.75, bônus_recuperação=5
- **c_max=0.20**: n=4000, seed_base=0, g_max=0.3, c_max=0.1, r=0.75, bônus_recuperação=5
- **r=0.40**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.2, bônus_recuperação=5
- **sem bônus**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=0
- **bônus=10**: n=4000, seed_base=0, g_max=0.3, c_max=0.5, r=0.75, bônus_recuperação=10
