# Pipeline de convocados

Este pacote cria snapshots derivados do `dataset/players_22.csv` para uma competição. A base original nunca é sobrescrita.

## Fluxo

1. Prepare um CSV de convocação com as colunas `pais,nome,posicao,fonte_url`.
2. Descubra quais convocados já existem na base:

```bash
python -m pipeline.cli discover \
  --dataset dataset/players_22.csv \
  --convocations artefatos/templates/convocacoes_copa_america_2024.csv \
  --aliases artefatos/templates/aliases.csv \
  --output artefatos/revisao/lacunas.csv
```

3. Gere um pacote de pesquisa com estatísticas por país e grupo de posição:

```bash
python -m pipeline.cli package \
  --dataset dataset/players_22.csv \
  --gaps artefatos/revisao/lacunas.csv \
  --pais Brazil \
  --data-referencia 2024-07-14 \
  --output artefatos/pesquisa/pacotes/brazil.json
```

4. Salve a resposta do modelo em JSON intermediário e valide:

```bash
python -m pipeline.cli validate \
  --input artefatos/templates/propostas_exemplo.json \
  --pais Brazil \
  --output artefatos/revisao/brazil_validacao.csv
```

5. Materialize somente propostas aprovadas:

```bash
python -m pipeline.cli materialize \
  --dataset dataset/players_22.csv \
  --input artefatos/templates/propostas_exemplo.json \
  --pais Brazil \
  --data-referencia 2024-07-14 \
  --registry artefatos/registry/player_ids.csv \
  --output artefatos/finais/brazil_2024.csv
```

O modelo deve devolver fontes e percentis, não IDs nem as 110 colunas do dataset. A materialização converte percentis em atributos usando a distribuição real do país/grupo de posição e aplica as regras de goleiro.

Os arquivos em `artefatos/templates/` são exemplos didáticos; as URLs `example.invalid` não constituem fontes de produção.

## Autoresearch por país

O estado global pode ser criado uma única vez:

```bash
python -m pipeline.cli init-run \
  --manifest artefatos/autoresearch/manifest.json \
  --edicao 2024 \
  --data-referencia 2024-07-14 \
  --paises Argentina Bolivia Brazil Canada Chile Colombia "Costa Rica" Ecuador Jamaica Mexico Panama Paraguay Peru "United States" Uruguay Venezuela
```

Cada ciclo prepara somente um país. As convocações reais ficam em `artefatos/convocacoes/<pais>.csv` (colunas `pais,nome,posicao,fonte_url,dob,clube`; geradas a partir da página de escalações da Copa América 2024). O pacote e o estado ficam persistidos no diretório indicado. Opcionalmente, `--escalacoes` acrescenta a escalação da última partida ao pacote (colunas `pais,data,fase,adversario,nome,posicao,ordem,fonte_url`; ver `artefatos/templates/escalacoes_exemplo.csv`):

```bash
python -m pipeline.cli prepare-country \
  --manifest artefatos/autoresearch/manifest.json \
  --pais Brazil \
  --dataset dataset/players_22.csv \
  --convocations artefatos/convocacoes/brazil.csv \
  --aliases artefatos/templates/aliases.csv \
  --escalacoes artefatos/escalacoes/copa_america_2024_ultima_partida.csv \
  --state-dir artefatos/autoresearch
```

O agente externo lê `artefatos/autoresearch/execucoes/brazil/pacote.json` e grava sua resposta original em `resposta_bruta.json`. Depois, a resposta é validada. Cada validação preserva versões (`resposta_bruta_v001.json`, `validacao_v001.csv`, ...). Se houver propostas inválidas e ainda restarem tentativas, o país vai para `validation_failed`; quando o limite de tentativas (`max_attempts` no manifesto, padrão 3) se esgota, ele transita para `review_required`:

```bash
python -m pipeline.cli validate-country \
  --manifest artefatos/autoresearch/manifest.json \
  --pais Brazil \
  --state-dir artefatos/autoresearch
```

Depois da validação, o snapshot é materializado e publicado. A publicação só é permitida quando o país está em `proposed` (todas as propostas aprovadas). Para publicar com jogadores pendentes de revisão manual é preciso autorizar explicitamente nos dois lugares — `allow_partial_publish: true` no manifesto **e** a flag `--allow-partial` no comando:

```bash
python -m pipeline.cli publish-country \
  --manifest artefatos/autoresearch/manifest.json \
  --pais Brazil \
  --dataset dataset/players_22.csv \
  --allow-partial \
  --state-dir artefatos/autoresearch
```

`next-country` mostra o próximo país pendente sem carregar o contexto de países anteriores — ele retoma estados intermediários (`researching`, `validation_failed`, `review_required`) antes de iniciar um país `pending`:

```bash
python -m pipeline.cli next-country \
  --manifest artefatos/autoresearch/manifest.json \
  --state-dir artefatos/autoresearch
```

Ao final (ou a qualquer momento), o resumo consolidado e o merge dos snapshots publicados:

```bash
python -m pipeline.cli report \
  --manifest artefatos/autoresearch/manifest.json \
  --state-dir artefatos/autoresearch \
  --output artefatos/autoresearch/resumo.csv

python -m pipeline.cli merge-final \
  --manifest artefatos/autoresearch/manifest.json \
  --state-dir artefatos/autoresearch \
  --output artefatos/autoresearch/copa_america_2024_completo.csv
```

O diretório `execucoes/<pais>/` é a fronteira de contexto de cada iteração. O manifesto e o registro de IDs são o estado compartilhado. Por padrão, o registry fica em `artefatos/autoresearch/registry/player_ids.csv` (criado pelo `init-run`) e é **versionado**: sem ele, `alocar_id` recomeçaria em -1 num clone limpo. A chave inclui a camada (`convocado_2024|pais|nome|dob` ou `historico|...`), para que as versões 2024 e lenda de uma pessoa não dividam o id. Qualquer subcomando aceita `--registry` para apontar outro caminho. Para reconstruí-lo a partir dos ids que já estão nos artefatos publicados: `python -m pipeline.cli rebuild-registry --convocados artefatos/autoresearch/copa_america_2024_completo.csv --historicos artefatos/autoresearch/historicos/historicos_completo.csv` (um id já usado por outra chave fica sem registro e ganha id novo no próximo `alocar_id`). O runner não chama um LLM diretamente: isso mantém pesquisa externa, resposta bruta e aprovação humana auditáveis.

## Camada histórica (lendas por seleção)

O mesmo ciclo é usado para os jogadores históricos das 16 seleções, num estado separado:

```text
artefatos/convocacoes/historicos/<pais>.csv     # entradas (pais, nome, posicao, fonte_url, dob, contexto)
artefatos/autoresearch/historicos/manifest.json # manifesto próprio
artefatos/autoresearch/historicos/execucoes/    # artefatos por país
```

Três diferenças em relação aos convocados de 2024:

1. **Registry compartilhado.** Toda a execução histórica usa
   `--registry artefatos/autoresearch/registry/player_ids.csv`, o mesmo da camada 2024.
   Assim os IDs negativos continuam de onde pararam e as duas camadas nunca colidem.
2. **Metadados de camada.** `pipeline/historico.py::marcar_propostas` aplica, de forma
   centralizada e idempotente, `is_historico=True`, `origem_registro="historico_estimado"`,
   `fonte_atributos="inferencia_llm_calibrada_historico"` e `validacao_via="wikidata"`.
3. **Idade de pico.** Para históricos, `age` recebe `27` — convenção de modelagem, não
   dado observado. Comparar eras é impreciso e a idade em 2024 seria absurda (Maradona
   sairia com 63). O campo `data_referencia` continua registrado para rastreio.

A fonte de cada jogador histórico é a página do Wikidata (`https://www.wikidata.org/wiki/<QID>`),
derivada de `fonte_validacao` nos arquivos históricos anteriores. Não há chamada de rede
no pipeline: as propostas entram como JSON versionado, igual à camada 2024.

### Ressalva metodológica (citar no relatório do trabalho)

Das 467 lendas, **30** têm `fonte_atributos="ea_fc_icon"` e **437** têm
`fonte_atributos="inferencia_llm_calibrada_historico"`. Nos dois casos os valores são
**estimados, não observados**.

Os atributos dos Icons do EA FC foram compilados de conhecimento público amplamente
replicado (wikis de comunidade, listas de Ultimate Team), **não** de uma fonte oficial
baixável: a sofifa.com — fonte usual desses dados — está atrás de Cloudflare e não foi
raspada. Os valores inferidos derivam da distribuição real do país/grupo de posição no
`dataset/players_22.csv`, mas a escolha do percentil é heurística nossa.

Além disso, os 9 atributos detalhados que o motor usa (e `goalkeeping_reflexes` dos
jogadores de linha) **não foram pesquisados** para nenhuma das 639 linhas enriquecidas:
são estimados por regressão sobre a base FIFA 22 (`pipeline/imputacao.py`, ver
[Catálogo final](#catálogo-final-pipelinecatalogopy)). A coluna `atributos_imputados`
lista, por linha, o que foi estimado.

## Posições (`pipeline/posicoes.py`)

O jogo só permite escalar um jogador nas posições que ele de fato joga, então cada um
precisa da principal **e** das secundárias, mais as 27 notas de posição específica
(`st`, `cb`, `cam`, …) que a base usa para decidir por limiar quem pode atuar onde.

- `CODIGOS_VALIDOS`: os 15 códigos que existem na base. A curadoria histórica usava
  `AM`/`DM`; `normalizar_codigo` converte para `CAM`/`CDM`.
- `injetar_secundarias(propostas, respostas)`: copia as posições secundárias pesquisadas
  para dentro da proposta, para que elas fluam pelo pipeline (validate → publish →
  materialize) em vez de serem aplicadas à mão sobre o snapshot publicado.
- `treinar_modelo(dataset)` + `prever_colunas(...)`: ajusta uma regressão por coluna de
  posição **na própria base** (que tem os 7 atributos e as 27 notas para 19 mil
  jogadores). Erro médio de ~1,5 ponto na escala 0-99, medido em 15k/4k. As colunas são
  preenchidas **só nas posições plausíveis**; as outras 24 ficam vazias de propósito —
  preencher as 27 sugeriria polivalência que o jogador não tem.
- Formato: gravamos inteiro puro, sem o bônus de química (`"+2"`) que a base carrega e
  que não temos como reproduzir.

Pesquisa de secundárias: 47% dos enriquecidos receberam 1–2 posições; os 53% restantes
ficaram só com a principal — espelhando a base real (49% com posição única). Quem ficou
sem secundária é especialista de verdade (um centroavante puro) ou jogador sem
documentação; nenhuma foi inventada.

## Filtro de praticabilidade (`pipeline/filtro.py`)

O pool completo (~5.000 jogadores para 16 seleções) é inviável num jogo. `filter-pool`
corta por **cota de posição por seleção** (padrão 5 GK / 12 DEF / 12 MID / 11 ATT),
mantendo os enriquecidos e os convocados de 2024 sempre — a cota é **piso**, não teto.
Com `person_key`, a cota conta pessoas distintas (as versões 2024 e lenda de um jogador
contam uma vez).

## Catálogo final (`pipeline/catalogo.py`)

`build-catalog` gera `artefatos/jogadores_copa_america_2024_filtrado.csv`, o arquivo que o
servidor carrega no MongoDB (`python -m api.seed`):

```bash
python -m pipeline.cli build-catalog \
  --pool artefatos/jogadores_copa_america_2024_pool.csv \
  --dataset dataset/players_22.csv \
  --convocacoes artefatos/convocacoes \
  --aliases artefatos/convocacoes/aliases_copa_america_2024.csv \
  --output artefatos/jogadores_copa_america_2024_filtrado.csv
```

1. **Ids** do registro versionado (as 15 lendas que dividiam o id com a versão 2024
   ganharam ids novos, -625 a -639). Em seguida entram as **datas de nascimento
   corrigidas** de `artefatos/correcoes/datas_nascimento.csv` (`--correcoes`; cada
   linha exige `fonte_url`). Uma data errada impede o `person_key` de ligar as versões
   2024 e lenda da mesma pessoa; corrija aqui, nunca na base FIFA 22. A correção é
   aplicada depois do registro, cuja chave inclui a data, para não trocar o id.
2. **Convocados**: cada nome de `convocacoes/<pais>.csv` é casado com o pool
   (`identity.py`). A camada histórica fica de fora (uma lenda nunca é o convocado), a
   pesquisa de 2024 é preferida à base, e se o nome exato só casar com outra pessoa
   (data diferente) o casamento por tokens é tentado. Convocado ambíguo ou ausente
   **interrompe** a execução com um relatório.
3. Colunas novas: `is_convocado_2024` e `person_key` (o `sofifa_id` da versão atual;
   cada lenda é casada com as linhas atuais da seleção pelas mesmas regras, com data de
   nascimento obrigatória).
4. Filtro de praticabilidade (acima), que sempre mantém os convocados.
5. **Imputação** (`imputacao.py`): uma regressão linear por atributo na base FIFA 22.
   Jogador de linha: `overall`, os 6 atributos principais e o grupo da posição; goleiro:
   `overall` e os 6 de goleiro. Valor arredondado e limitado a [0, 99]. Os atributos de
   linha dos goleiros continuam vazios (o motor os lê como 0).
6. **Validação** (`validation.validar_catalogo`): os 18 campos do motor em [0, 100], ids
   únicos, ao menos 3 GK / 8 DEF / 8 MID / 7 ATT pessoas distintas por seleção e todo
   convocado listado presente (Jamaica e Panamá listam 25). Qualquer erro interrompe.

Erro médio da imputação por atributo, num corte 15k/4k da base
(`python -m pipeline.cli avaliar-imputacao --dataset dataset/players_22.csv`):

| Atributo | Linha (3.757) | Goleiro (482) |
|---|---|---|
| attacking_heading_accuracy | 5,44 | 2,47 |
| movement_agility | 5,00 | 7,02 |
| movement_reactions | 3,03 | 2,22 |
| movement_balance | 6,43 | 7,91 |
| power_jumping | 7,48 | 8,22 |
| power_stamina | 5,60 | 4,98 |
| mentality_aggression | 6,02 | 5,21 |
| mentality_penalties | 5,52 | 4,32 |
| mentality_composure | 4,24 | 8,13 |
| goalkeeping_reflexes | 2,58 | — |

Resultado: 911 jogadores, 414 convocados (16 × 26, menos 1 de Jamaica e 1 de Panamá).

| Seleção | Convocados | Lendas | Total | GK | DEF | MID | ATT |
|---|---|---|---|---|---|---|---|
| Argentina | 26 | 76 | 102 | 9 | 22 | 33 | 38 |
| Bolivia | 26 | 18 | 45 | 5 | 12 | 17 | 11 |
| Brazil | 26 | 77 | 103 | 8 | 28 | 37 | 30 |
| Canada | 26 | 13 | 45 | 5 | 17 | 12 | 11 |
| Chile | 26 | 35 | 61 | 7 | 17 | 15 | 21 |
| Colombia | 26 | 29 | 55 | 6 | 14 | 17 | 18 |
| Costa Rica | 26 | 12 | 43 | 4 | 13 | 12 | 14 |
| Ecuador | 26 | 20 | 50 | 5 | 15 | 17 | 11 |
| Jamaica | 25 | 16 | 45 | 5 | 17 | 12 | 11 |
| Mexico | 26 | 32 | 58 | 6 | 12 | 21 | 19 |
| Panama | 25 | 11 | 41 | 5 | 12 | 12 | 11 |
| Paraguay | 26 | 25 | 52 | 5 | 12 | 20 | 11 |
| Peru | 26 | 27 | 53 | 5 | 13 | 18 | 16 |
| United States | 26 | 27 | 53 | 7 | 16 | 15 | 13 |
| Uruguay | 26 | 32 | 58 | 5 | 14 | 22 | 16 |
| Venezuela | 26 | 17 | 47 | 5 | 15 | 14 | 11 |

(GK/DEF/MID/ATT: pessoas distintas pela posição principal.)
