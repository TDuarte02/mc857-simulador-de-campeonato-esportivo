# Design — app do simulador

Interface do simulador de campeonato (React + TypeScript + Vite + Tailwind v4).
Cobre escolha de seleção, montagem de elenco, sorteio, fase de grupos,
mata-mata e duelo multiplayer 1v1.

Estética "programa de jogo vintage": papel creme, tinta, dourado, Barlow
Condensed + JetBrains Mono. Moldura mobile fixa de 390×844.

## Rodar

```bash
cd design
npm install
npm run dev
```

Abre em `http://localhost:5173`.

## Build

```bash
npm run build     # gera em dist/
npm run preview   # serve o build
```

## Estrutura

- `src/App.tsx` — o app inteiro (telas + fluxo de navegação)
- `src/index.css` — tema e classes vintage (`.retro-paper`, `.ticket-stripe`…)
- `.figma/make/site.json` — importado pelo `vite.config.ts`; não remover
