# MC857 - Simulador de Campeonato Esportivo

## Integrantes:
- Gabriel Frônio Carvalho - 216241
- João Emílio Ferreira - 247184
- Marcelo De Souza Corumba De Campos - 236730
- Vinícius Machado - 245446
- Tallyta Duarte - 188305

## Proposta

O projeto consiste no desenvolvimento de um simulador de campeonato de futebol baseado em dados reais de jogadores. Como principal fonte de dados, será utilizado o dataset EA Sports FC 24 Complete Player Dataset, disponível no Kaggle, que contém informações e atributos dos jogadores. Dados complementares poderão ser obtidos do Sofascore, principalmente para informações relacionadas a desempenho e estatísticas de partidas.

O usuário poderá escolher uma seleção participante, sua escalação inicial e a formação ou estratégia tática utilizada. A partir dessas informações, o sistema simulará as partidas do campeonato, considerando características individuais dos jogadores e fatores da equipe para determinar os acontecimentos da partida. Entre os eventos simulados estarão posse de bola, finalizações, gols, faltas e cartões, podendo as estatísticas serem apresentadas tanto para a partida completa quanto divididas em segmentos de aproximadamente 15 minutos, permitindo acompanhar a evolução do jogo.

O campeonato será simulado de acordo com suas respectivas fases, com os resultados das partidas determinando a classificação e o avanço das equipes. Durante o campeonato, o usuário poderá tomar decisões que alterem a configuração de sua equipe, como modificar a escalação ou a formação tática entre as partidas. Inicialmente, a interação durante uma partida ficará limitada à visualização de sua evolução, deixando alterações táticas e de escalação para o intervalo entre partidas. A simulação utilizará elementos probabilísticos influenciados pelos atributos dos jogadores, de modo que equipes e jogadores com características diferentes apresentem desempenhos distintos, mantendo, ao mesmo tempo, um certo grau de aleatoriedade nos resultados.

## App e API

O app (`simulador/app`, Android, iOS e web) não simula nada sozinho: seleções, jogadores, sorteio, partidas, classificação e chaveamento vêm da API em `simulador/server`, que por enquanto usa jogadores fictícios e um simulador aleatório no lugar do modelo (veja o [README do servidor](simulador/server/README.md)).

Por padrão o app usa a API publicada na AWS, atrás de um API Gateway que exige o header `x-api-key`. A chave não fica no repositório: peça-a ao grupo e coloque-a em `simulador/app/local.properties` (que não é versionado):

```properties
api.key=<chave do API Gateway>
# Opcional: outra API, por exemplo a local (no emulador Android, http://10.0.2.2:5000).
# api.baseUrl=http://127.0.0.1:5000
```

1. Android: abra `simulador/app` no Android Studio e rode. Também dá para usar `-PapiBaseUrl=...` e `-PapiKey=...` no Gradle.
2. iOS: abra `simulador/app/iosApp/iosApp.xcodeproj` no Xcode e rode.
3. Web: em `simulador/app`, rode `./gradlew wasmJsBrowserDevelopmentRun` e abra http://localhost:8080.

O web não chama a AWS direto: chama `/api` no próprio endereço, e quem serve a página repassa para a API com a chave. Localmente isso é feito pelo servidor de desenvolvimento (`composeApp/webpack.config.d/apiProxy.js`, que lê o mesmo `local.properties`); em produção, por uma edge function do Netlify (`netlify/edge-functions/api.ts`). Assim o navegador não precisa de CORS e a chave não vai para o bundle.

Para rodar a API localmente: em `simulador/server`, `uv run flask --app main run` (ou `docker compose up -d --build`), em http://127.0.0.1:5000.

Testes do app: `./gradlew testDebugUnitTest`. Com `API_BASE_URL` (e `API_KEY`, para a AWS) definidas, um teste adicional joga copas completas contra a API; `API_FAST_MODE=1` inclui copas do Modo Rápido e `API_CUPS` define quantas copas de cada modo (40 por padrão).

### Deploy do web (Netlify)

Uma vez só: crie o site e defina a chave como variável de ambiente dele.

```bash
cd simulador/app
npx netlify-cli login
npx netlify-cli sites:create
npx netlify-cli env:set API_KEY <chave do API Gateway>
```

A cada deploy (o `clean` evita subir arquivos `.wasm` de builds anteriores):

```bash
./gradlew clean :composeApp:wasmJsBrowserDistribution
npx netlify-cli deploy --prod
```

O site publicado fica em https://copa-america-mc857.netlify.app. A proteção por login do Netlify vale só para as prévias de deploy; a produção é pública.

O `netlify.toml` já aponta para a pasta gerada pelo build e para a edge function. `API_BASE_URL` também pode ser definida no site para usar outra API.

## Base de dados
https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset/data

https://www.kaggle.com/datasets/luisfucros/fifa-players?select=players_16.csv

<img width="1048" height="435" alt="image" src="https://github.com/user-attachments/assets/5c5734b4-2e71-4b54-9ca5-06626bc280a1" />

## Roteiro de demonstração (3 partidas)

Execute o app mobile pelo Android Studio com um emulador ou dispositivo Android conectado. Para mostrar três partidas seguidas:

1. Inicie o Modo Clássico, escolha Brasil e monte o elenco.
2. Faça o sorteio e abra a primeira partida da fase de grupos.
3. Na tela de resultado, destaque placar e eventos; avance para a fase de grupos.
4. Use “Jogar próxima partida” e repita o passo anterior mais duas vezes.
5. Após a terceira partida da seleção, mostre a classificação final do grupo e o chaveamento. As outras partidas do grupo são simuladas pela API.

O caminho garante três partidas da seleção independentemente de vitórias ou derrotas. A API precisa estar no ar; os placares vêm do simulador dela.

## Design
Para executá-lo é preciso ter o Node.js 20 ou superior instalado; com ele, basta entrar na pasta design, instalar as dependências com `npm install` e subir o servidor de desenvolvimento com `npm run dev`, que disponibiliza a aplicação em http://localhost:xxxx. 
