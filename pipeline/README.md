# Pipeline de convocados

Este pacote cria snapshots derivados do `players_22.csv` para uma competição. A base original nunca é sobrescrita.

## Fluxo

1. Prepare um CSV de convocação com as colunas `pais,nome,posicao,fonte_url`.
2. Descubra quais convocados já existem na base:

```bash
python -m pipeline.cli discover \
  --dataset players_22.csv \
  --convocations dados/templates/convocacoes_copa_america_2024.csv \
  --aliases dados/templates/aliases.csv \
  --output dados/revisao/lacunas.csv
```

3. Gere um pacote de pesquisa com estatísticas por país e grupo de posição:

```bash
python -m pipeline.cli package \
  --dataset players_22.csv \
  --gaps dados/revisao/lacunas.csv \
  --pais Brazil \
  --data-referencia 2024-07-14 \
  --output dados/pesquisa/pacotes/brazil.json
```

4. Salve a resposta do modelo em JSON intermediário e valide:

```bash
python -m pipeline.cli validate \
  --input dados/templates/propostas_exemplo.json \
  --pais Brazil \
  --output dados/revisao/brazil_validacao.csv
```

5. Materialize somente propostas aprovadas:

```bash
python -m pipeline.cli materialize \
  --dataset players_22.csv \
  --input dados/templates/propostas_exemplo.json \
  --pais Brazil \
  --data-referencia 2024-07-14 \
  --registry dados/registry/player_ids.csv \
  --output dados/finais/brazil_2024.csv
```

O modelo deve devolver fontes e percentis, não IDs nem as 110 colunas do dataset. A materialização converte percentis em atributos usando a distribuição real do país/grupo de posição e aplica as regras de goleiro.

Os arquivos em `dados/templates/` são exemplos didáticos; as URLs `example.invalid` não constituem fontes de produção.

## Autoresearch por país

O estado global pode ser criado uma única vez:

```bash
python -m pipeline.cli init-run \
  --manifest dados/autoresearch/manifest.json \
  --edicao 2024 \
  --data-referencia 2024-07-14 \
  --paises Argentina Bolivia Brazil Canada Chile Colombia "Costa Rica" Ecuador Jamaica Mexico Panama Paraguay Peru "United States" Uruguay Venezuela
```

Cada ciclo prepara somente um país. As convocações reais ficam em `dados/convocacoes/<pais>.csv` (colunas `pais,nome,posicao,fonte_url,dob,clube`; geradas a partir da página de escalações da Copa América 2024). O pacote e o estado ficam persistidos no diretório indicado. Opcionalmente, `--escalacoes` acrescenta a escalação da última partida ao pacote (colunas `pais,data,fase,adversario,nome,posicao,ordem,fonte_url`; ver `dados/templates/escalacoes_exemplo.csv`):

```bash
python -m pipeline.cli prepare-country \
  --manifest dados/autoresearch/manifest.json \
  --pais Brazil \
  --dataset players_22.csv \
  --convocations dados/convocacoes/brazil.csv \
  --aliases dados/templates/aliases.csv \
  --escalacoes dados/escalacoes/copa_america_2024_ultima_partida.csv \
  --state-dir dados/autoresearch
```

O agente externo lê `dados/autoresearch/execucoes/brazil/pacote.json` e grava sua resposta original em `resposta_bruta.json`. Depois, a resposta é validada. Cada validação preserva versões (`resposta_bruta_v001.json`, `validacao_v001.csv`, ...). Se houver propostas inválidas e ainda restarem tentativas, o país vai para `validation_failed`; quando o limite de tentativas (`max_attempts` no manifesto, padrão 3) se esgota, ele transita para `review_required`:

```bash
python -m pipeline.cli validate-country \
  --manifest dados/autoresearch/manifest.json \
  --pais Brazil \
  --state-dir dados/autoresearch
```

Depois da validação, o snapshot é materializado e publicado. A publicação só é permitida quando o país está em `proposed` (todas as propostas aprovadas). Para publicar com jogadores pendentes de revisão manual é preciso autorizar explicitamente nos dois lugares — `allow_partial_publish: true` no manifesto **e** a flag `--allow-partial` no comando:

```bash
python -m pipeline.cli publish-country \
  --manifest dados/autoresearch/manifest.json \
  --pais Brazil \
  --dataset players_22.csv \
  --allow-partial \
  --state-dir dados/autoresearch
```

`next-country` mostra o próximo país pendente sem carregar o contexto de países anteriores — ele retoma estados intermediários (`researching`, `validation_failed`, `review_required`) antes de iniciar um país `pending`:

```bash
python -m pipeline.cli next-country \
  --manifest dados/autoresearch/manifest.json \
  --state-dir dados/autoresearch
```

Ao final (ou a qualquer momento), o resumo consolidado e o merge dos snapshots publicados:

```bash
python -m pipeline.cli report \
  --manifest dados/autoresearch/manifest.json \
  --state-dir dados/autoresearch \
  --output dados/autoresearch/resumo.csv

python -m pipeline.cli merge-final \
  --manifest dados/autoresearch/manifest.json \
  --state-dir dados/autoresearch \
  --output dados/autoresearch/copa_america_2024_completo.csv
```

O diretório `execucoes/<pais>/` é a fronteira de contexto de cada iteração. O manifesto e o registro de IDs são o estado compartilhado. Por padrão, o registry fica em `dados/autoresearch/registry/player_ids.csv` (criado pelo `init-run`, ignorado pelo git); qualquer subcomando aceita `--registry` para apontar outro caminho. O runner não chama um LLM diretamente: isso mantém pesquisa externa, resposta bruta e aprovação humana auditáveis.
