# Deploy na AWS

Duas instâncias **t3.micro** numa VPC própria:

- a **da API** (subnet pública) roda a API (gunicorn, com o motor) em Docker;
- a **do banco** (subnet privada, sem rota para a internet) roda só o **MongoDB**, com autenticação, e aceita conexões apenas da instância da API.

Na frente fica um **API Gateway** (REST) que exige a chave de API do app.

```
app --x-api-key--> API Gateway (REST, plano de uso)
    --HTTP + X-Origin-Verify--> instância da API :80 (copa-api)
        --rede privada, usuário/senha--> instância do banco :27017 (mongod)
```

| Arquivo | O que é |
|---|---|
| `ecr.yaml` | Stack `copa-ecr`: repositório da imagem e bucket privado com os RPMs do MongoDB e a senha do banco |
| `copa.yaml` | Stack `copa`: VPC, as duas instâncias, endpoint S3, papéis IAM, API Gateway, chave e plano de uso |
| `deploy.sh` | Cria/atualiza tudo e publica o código atual |
| `teardown.sh` | Apaga tudo, inclusive o banco (pede confirmação) |
| `common.sh` | Opções e funções em comum dos dois scripts (é carregado por eles, não se roda sozinho) |

## Por que este desenho

A conta está num plano gratuito, e a política da organização bloqueia o DocumentDB (`rds:CreateDBCluster`). Para não gerar custo por hora, ficaram de fora o NAT gateway, o load balancer, o Fargate e os endpoints de interface.

**Instância do banco, isolada:**

- não tem IP público, e a subnet dela não tem rota para a internet: a única saída é o endpoint S3 (gateway, gratuito);
- instala o MongoDB 8.0 offline, a partir de RPMs fixados por SHA-256 que o `deploy.sh` confere e sobe para o bucket. Todas as dependências já vêm na imagem base do Amazon Linux 2023;
- o MongoDB exige usuário e senha (`copa`, só `readWrite` no banco `copa`);
- a porta 27017 só aceita conexões do security group da instância da API;
- a senha é gerada pelo `deploy.sh`, nunca impressa, e fica no SSM (para a API) e no bucket (para a instância do banco, que não alcança o SSM).

**Instância da API:**

- o API Gateway confere a chave e acrescenta o cabeçalho secreto `X-Origin-Verify`;
- a API recusa (`403`) qualquer requisição sem esse cabeçalho, então chamar o IP público direto não adianta nada;
- não há SSH: a administração é feita pelo SSM.

**Custo:**

- `t3.micro` com créditos de CPU em `standard` (o modo padrão, `unlimited`, cobra as rajadas de CPU);
- 20 + 10 GB de gp3 (exatamente os 30 GB gratuitos);
- o ECR guarda só as 3 imagens mais recentes;
- a segunda instância passa das 750 horas/mês do free tier: cerca de US$ 7–8/mês pelas horas extras, ou consumo dos créditos do plano gratuito. O resto fica dentro dos limites gratuitos.

## Regras da conta

- **Só o perfil `unicamp`**, nunca o `default`. O perfil é obrigatório nos scripts, que recusam o `default`. Passe também `--account 391016433274` para que eles confiram a conta antes de mexer em qualquer coisa.
- **Só `us-east-2`** (o padrão dos scripts). A política da organização nega as outras regiões, inclusive a `us-east-1`, que é a região configurada no perfil.

## Deploy

Requer AWS CLI v2 (logado com `aws login --profile unicamp`), Docker e bash. Roda no Linux, no WSL, no macOS e no Git Bash do Windows.

```bash
simulador/infra/aws/deploy.sh --profile unicamp --account 391016433274
```

| Opção | |
|---|---|
| `--profile <nome>` | Perfil do AWS CLI. Obrigatório; também pode ser passado sozinho (`deploy.sh unicamp`). O `default` é recusado |
| `--region <região>` | Padrão: `us-east-2` |
| `--account <id>` | Se informado, aborta caso o perfil aponte para outra conta |

No WSL, o AWS CLI precisa estar instalado no próprio Linux. As credenciais podem ser as do Windows se `~/.aws` apontar para `/mnt/c/Users/<você>/.aws`.

1. stack `copa-ecr`, build da imagem (`--target aws` do Dockerfile) e push;
2. cria o segredo de origem no SSM (só na primeira vez; ele nunca é impresso);
3. RPMs do MongoDB (baixados e conferidos uma vez) e a senha do banco no bucket;
4. stack `copa`. No primeiro boot, a instância do banco instala e configura o MongoDB; a da API instala o Docker, espera o banco, carrega o catálogo (`python -m api.seed`, sem efeito se ele já estiver carregado) e sobe a API;
5. nos deploys seguintes, a imagem nova é aplicada pelo SSM (`/opt/copa/set-image.sh`), sem recriar a instância (o banco, que fica na outra instância, não é afetado);
6. espera a API responder **pelo API Gateway, com a chave**, e imprime a URL.

## Como o app chama

```
GET https://<id>.execute-api.us-east-2.amazonaws.com/v1/squads
x-api-key: <chave>
```

Sem a chave, ou com uma chave errada, a resposta é `403` do gateway. Para ler a chave:

```bash
aws apigateway get-api-key --api-key <ApiKeyId> --include-value --query value --output text --profile unicamp --region us-east-2
```

Limites do plano de uso: 20 req/s, rajada de 40, 100.000 req/mês.

**A chave não é um segredo forte:** ela vai dentro do app e pode ser extraída. Ela identifica o app e limita o uso; não autentica usuários.

## Testes funcionais contra a AWS

```bash
cd simulador/server
API_BASE_URL=https://<id>.execute-api.us-east-2.amazonaws.com/v1 API_KEY=<chave> uv run pytest tests/functional
```

Os 4 testes que leem o banco direto são pulados (o MongoDB não é exposto).

## Diagnóstico

```bash
aws ssm send-command --instance-ids <InstanceId> --document-name AWS-RunShellScript \
  --parameters 'commands=["tail -n 50 /var/log/copa-bootstrap.log; docker ps; docker logs --tail 50 copa-api"]' \
  --profile unicamp --region us-east-2
```

## Limpeza

```bash
simulador/infra/aws/teardown.sh --profile unicamp --account 391016433274
```

Aceita as mesmas opções do `deploy.sh`.

Apaga as duas stacks (as instâncias e o banco, a API, a chave, as imagens e o bucket, que é esvaziado antes) e os dois segredos no SSM.

## Limitações

- **Sem alta disponibilidade:** uma instância de cada. Se a instância do banco for recriada (por uma mudança no `copa.yaml` que exija substituição), os dados são perdidos; o catálogo é recarregado sozinho, mas as sessões não voltam.
- **Sem acesso administrativo ao banco:** a instância do banco não alcança o SSM (seria preciso um endpoint de interface, que é pago). Para diagnosticar, entre na instância da API pelo SSM e use a imagem da API (`pymongo`) para falar com o banco.
- **1 GB de RAM em cada instância** (mais 1 GB de swap): suficiente para o uso do trabalho.
- **`/docs` pelo gateway:** a página carrega, mas o "Try it out" não funciona (o navegador não manda a chave). Use o `/docs` local.
- **O Dockerfile ainda tem as configurações do DocumentDB**, para o caso de a conta passar a permitir o serviço; na instância, o `run.sh` as desliga.
