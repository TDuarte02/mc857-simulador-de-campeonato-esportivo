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

## Modelo probabilístico inicial

Como ainda não há uma base de partidas e escalações, o placar é simulado a partir de perfis agregados por seleção, derivados de `players_data.csv` (FIFA 22). Para cada país, os jogadores são selecionados pela posição principal e por pontuações construídas a partir dos atributos: até 2 atacantes, 4 meio-campistas e 4 defensores; o goleiro é escolhido por `goalkeeping_reflexes`. Haiti tem 10 jogadores disponíveis e, por isso, um defensor a menos. Ataque combina finalização, velocidade, drible e passe; meio-campo combina passe, drible e físico; defesa combina defesa e físico. Os perfis resultantes estão em `app/composeApp/src/commonMain/kotlin/com/mc857/copaamerica/domain/data/NationalTeamAttributes.kt`.

O modelo calcula gols esperados com esses quatro atributos e sorteia gols por uma distribuição de Poisson. Os pesos e a média-base são heurísticas iniciais, ainda não calibradas nem avaliadas contra resultados reais. Os placares são reprodutíveis para o mesmo confronto para evitar mudanças durante recomposições da interface. A escalação mockada da aplicação não participa do cálculo; os atributos do time vêm do perfil agregado da seleção.

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
5. Após a terceira partida da seleção, mostre a classificação final do grupo e o chaveamento. As outras partidas do grupo são simuladas automaticamente.

O caminho garante três partidas da seleção independentemente de vitórias ou derrotas. Os placares dependem dos perfis agregados das equipes e do sorteio dos grupos; a escalação escolhida não altera o modelo nesta versão.

## Design
Para executá-lo é preciso ter o Node.js 20 ou superior instalado; com ele, basta entrar na pasta design, instalar as dependências com `npm install` e subir o servidor de desenvolvimento com `npm run dev`, que disponibiliza a aplicação em http://localhost:xxxx. 
