import { useState } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────
type Screen  = 'home'|'team-selection'|'participant-selection'|'squad-builder'|'draw-setup'|'round-one'|'group-stage'|'bracket'|'pre-match'|'match-result'|'elimination'|'phase-overview'|'multiplayer'|'mp-team'|'mp-lineup'|'mp-match'
type GameMode = 'quick'|'normal'
type PosF    = 'ALL'|'GK'|'DEF'|'MID'|'FW'
type SlotCat = 'GK'|'DEF'|'MID'|'FW'
type SlotRole = 'GOL'|'ZAG'|'LD'|'LE'|'VOL'|'MC'|'MEI'|'PD'|'PE'|'CA'
type FormKey = '4-4-2'|'4-3-3'|'3-5-2'|'4-2-3-1'
type Phase   = 'group'|'qf'|'sf'|'third'|'final'
type TournamentFormat = 8 | 12 | 16

interface TeamData { id: string; name: string; flag: string; conf: 'CONMEBOL'|'CONCACAF' }
interface Player   { id: number; name: string; rating: number; era: string; pos: SlotCat; role: SlotRole; image?: string }

type SquadView = 'grid'|'list'
type SquadSort = 'rating'|'name'
type CardStatus = 'yellow'|'red'
type MatchEvent = { min: number; type: 'goal'|'yellow'; team: 'team'|'rival'; player: string; score: string }

const FIRST_MATCH_CARDS: Record<string, CardStatus> = {
  Ronaldo: 'yellow',
  Ronaldinho: 'red',
}

const POSITION_LABELS: Record<PosF, string> = {
  ALL: 'TODOS', GK: 'GOL', DEF: 'ZAG', MID: 'MEI', FW: 'ATA',
}
interface SlotCfg  { label: string; cat: SlotCat; x: number; y: number }
interface FSlot    extends SlotCfg { player: Player }
interface PoolTeam { name: string; flag: string }
interface Stadium  { name: string; city: string; country: string; cap: string }
interface GroupStanding { team: PoolTeam; p: number; w: number; d: number; l: number; gf: number; ga: number; pts: number; yellow: number; red: number }
interface GroupMatch {
  id: string
  home: PoolTeam
  away: PoolTeam
  status: 'pending'|'played'
  homeGoals: number|null
  awayGoals: number|null
  homeYellow: number
  awayYellow: number
  homeRed: number
  awayRed: number
}
interface TournamentGroup { name: string; teams: PoolTeam[]; standings: GroupStanding[]; matches: GroupMatch[] }

// Um confronto do mata-mata. Os dois lados e quem avançou ficam nulos até o
// confronto ser decidido — é isso que faz a chave ir se completando.
interface KnockoutTie {
  home: PoolTeam | null
  away: PoolTeam | null
  homeGoals: number | null
  awayGoals: number | null
  winner: PoolTeam | null
}
interface Knockout {
  qf: KnockoutTie[]
  sf: KnockoutTie[]
  third: KnockoutTie
  final: KnockoutTie
}
interface DrawnBracket {
  format: TournamentFormat
  participants: PoolTeam[]
  groups: TournamentGroup[]
  qf: [PoolTeam, PoolTeam][]
  ko: Knockout
}

const FORMAT_LABELS: Record<TournamentFormat, string> = {
  8: 'Modo rápido',
  12: 'Formato tradicional',
  16: 'Modo clássico',
}
const FORMAT_DESCRIPTIONS: Record<TournamentFormat, string> = {
  8: 'Quartas diretamente',
  12: '3 grupos de 4 · quartas',
  16: '4 grupos de 4 · quartas',
}

// ── Team pool (20 nations) ────────────────────────────────────────────────────
const TEAMS: TeamData[] = [
  { id:'argentina',   name:'Argentina',          flag:'🇦🇷', conf:'CONMEBOL' },
  { id:'bolivia',     name:'Bolívia',            flag:'🇧🇴', conf:'CONMEBOL' },
  { id:'brazil',      name:'Brasil',             flag:'🇧🇷', conf:'CONMEBOL' },
  { id:'colombia',    name:'Colômbia',           flag:'🇨🇴', conf:'CONMEBOL' },
  { id:'chile',       name:'Chile',              flag:'🇨🇱', conf:'CONMEBOL' },
  { id:'ecuador',     name:'Equador',            flag:'🇪🇨', conf:'CONMEBOL' },
  { id:'paraguay',    name:'Paraguai',           flag:'🇵🇾', conf:'CONMEBOL' },
  { id:'venezuela',   name:'Venezuela',          flag:'🇻🇪', conf:'CONMEBOL' },
  { id:'uruguay',     name:'Uruguai',            flag:'🇺🇾', conf:'CONMEBOL' },
  { id:'usa',         name:'Estados Unidos',     flag:'🇺🇸', conf:'CONCACAF' },
  { id:'mexico',      name:'México',             flag:'🇲🇽', conf:'CONCACAF' },
  { id:'costa_rica',  name:'Costa Rica',         flag:'🇨🇷', conf:'CONCACAF' },
  { id:'panama',      name:'Panamá',             flag:'🇵🇦', conf:'CONCACAF' },
  { id:'haiti',       name:'Haiti',              flag:'🇭🇹', conf:'CONCACAF' },
  { id:'jamaica',     name:'Jamaica',             flag:'🇯🇲', conf:'CONCACAF' },
  { id:'peru',        name:'Peru',               flag:'🇵🇪', conf:'CONMEBOL' },
]

// ── 52-player historic pool ───────────────────────────────────────────────────
const POOL: Player[] = [
  // GKs (6)
  { id:1,    name:'Gilmar',               rating:91, era:'1950–66',   pos:'GK',     role:'GOL' },
  { id:2,    name:'Taffarel',             rating:89, era:'1988–98',   pos:'GK',     role:'GOL' },
  { id:3,    name:'Marcos',               rating:84, era:'1990–06',   pos:'GK',     role:'GOL' },
  { id:4,    name:'Dida',                 rating:87, era:'1995–06',   pos:'GK',     role:'GOL' },
  { id:5,    name:'Cássio',               rating:82, era:'2011–23',   pos:'GK',     role:'GOL' },
  { id:6,    name:'Weverton',             rating:81, era:'2015–22',   pos:'GK',     role:'GOL' },
  // DEFs (14)
  { id:7,    name:'Cafu',                 rating:93, era:'1990–06',   pos:'DEF',    role:'LD' },
  { id:8,    name:'Roberto Carlos',       rating:94, era:'1992–06',   pos:'DEF',    role:'LE' },
  { id:9,    name:'Lúcio',                rating:90, era:'2000–10',   pos:'DEF',    role:'ZAG' },
  { id:10,   name:'Aldair',               rating:88, era:'1989–02',   pos:'DEF',    role:'ZAG' },
  { id:11,   name:'Júnior',               rating:87, era:'1979–88',   pos:'DEF',    role:'LE' },
  { id:12,   name:'Carlos Alberto',       rating:92, era:'1964–77',   pos:'DEF',    role:'LD' },
  { id:13,   name:'Bellini',              rating:85, era:'1952–66',   pos:'DEF',    role:'ZAG' },
  { id:14,   name:'Thiago Silva',         rating:91, era:'2008–21',   pos:'DEF',    role:'ZAG' },
  { id:15,   name:'Maicon',               rating:89, era:'2003–14',   pos:'DEF',    role:'LD' },
  { id:16,   name:'David Luiz',           rating:86, era:'2010–21',   pos:'DEF',    role:'ZAG' },
  { id:17,   name:'Marcelo',              rating:88, era:'2006–18',   pos:'DEF',    role:'LE' },
  { id:18,   name:'Djalma Santos',        rating:90, era:'1952–68',   pos:'DEF',    role:'LD' },
  { id:19,   name:'Nilton Santos',        rating:91, era:'1949–64',   pos:'DEF',    role:'LE' },
  { id:20,   name:'Roque Júnior',         rating:84, era:'1999–06',   pos:'DEF',    role:'ZAG' },
  // MIDs (16)
  { id:21,   name:'Zico',                 rating:97, era:'1976–88',   pos:'MID',    role:'MEI' },
  { id:22,   name:'Sócrates',             rating:93, era:'1979–86',   pos:'MID',    role:'MC' },
  { id:23,   name:'Falcão',               rating:93, era:'1976–86',   pos:'MID',    role:'VOL' },
  { id:24,   name:'Rivaldo',              rating:95, era:'1993–06',   pos:'MID',    role:'MEI' },
  { id:25,   name:'Gerson',               rating:91, era:'1961–72',   pos:'MID',    role:'MC' },
  { id:26,   name:'Kaká',                 rating:93, era:'2002–13',   pos:'MID',    role:'MEI' },
  { id:27,   name:'Didi',                 rating:92, era:'1952–66',   pos:'MID',    role:'MC' },
  { id:28,   name:'Clodoaldo',            rating:87, era:'1969–74',   pos:'MID',    role:'VOL' },
  { id:29,   name:'Rivelino',             rating:93, era:'1965–78',   pos:'MID',    role:'MEI' },
  { id:30,   name:'Cerezo',               rating:88, era:'1978–88',   pos:'MID',    role:'MC' },
  { id:31,   name:'Oscar',                rating:85, era:'2011–16',   pos:'MID',    role:'MEI' },
  { id:32,   name:'Lucas Paquetá',        rating:84, era:'2018–',     pos:'MID',    role:'MEI' },
  { id:33,   name:'Serginho',             rating:84, era:'1974–82',   pos:'MID',    role:'MEI' },
  { id:34,   name:'Jorginho',             rating:83, era:'1983–92',   pos:'MID',    role:'VOL' },
  { id:35,   name:'Leandro',              rating:83, era:'1979–88',   pos:'MID',    role:'LD' },
  { id:36,   name:'Nené',                 rating:82, era:'1972–78',   pos:'MID',    role:'MEI' },
  // FWs (16)
  { id:37,   name:'Pelé',                 rating:99, era:'1957–71',   pos:'FW',     role:'CA' },
  { id:38,   name:'Ronaldo',              rating:98, era:'1994–06',   pos:'FW',     role:'CA' },
  { id:39,   name:'Ronaldinho',           rating:97, era:'1999–10',   pos:'FW',     role:'PE' },
  { id:40,   name:'Garrincha',            rating:97, era:'1955–66',   pos:'FW',     role:'PD' },
  { id:41,   name:'Romário',              rating:96, era:'1987–98',   pos:'FW',     role:'CA' },
  { id:42,   name:'Jairzinho',            rating:93, era:'1964–74',   pos:'FW',     role:'PD' },
  { id:43,   name:'Neymar',               rating:93, era:'2010–23',   pos:'FW',     role:'PE' },
  { id:44,   name:'Tostão',               rating:91, era:'1966–72',   pos:'FW',     role:'CA' },
  { id:45,   name:'Leônidas',             rating:91, era:'1932–46',   pos:'FW',     role:'CA' },
  { id:46,   name:'Bebeto',               rating:90, era:'1985–98',   pos:'FW',     role:'CA' },
  { id:47,   name:'Vavá',                 rating:89, era:'1952–62',   pos:'FW',     role:'CA' },
  { id:48,   name:'Careca',               rating:88, era:'1982–92',   pos:'FW',     role:'CA' },
  { id:49,   name:'Ademir',               rating:88, era:'1945–53',   pos:'FW',     role:'CA' },
  { id:50,   name:'Dadá Maravilha',       rating:85, era:'1965–76',   pos:'FW',     role:'CA' },
  { id:51,   name:'Robinho',              rating:84, era:'2003–14',   pos:'FW',     role:'PE' },
  { id:52,   name:'Élber',                rating:83, era:'1994–04',   pos:'FW',     role:'CA' }
]

// ── Stadiums ──────────────────────────────────────────────────────────────────
const STADIUMS: Stadium[] = [
  { name:'Maracanã',           city:'Rio de Janeiro', country:'Brasil',       cap:'78.838'  },
  { name:'Estádio Azteca',      city:'Cidade do México',country:'México',      cap:'87.523'  },
  { name:'Hard Rock Stadium',  city:'Miami, FL',      country:'Estados Unidos',cap:'65.326'  },
  { name:'MetLife Stadium',    city:'East Rutherford',country:'Estados Unidos',cap:'82.500'  },
  { name:'Rose Bowl',          city:'Pasadena, CA',   country:'Estados Unidos',cap:'92.542'  },
  { name:'AT&T Stadium',       city:'Arlington, TX',  country:'Estados Unidos',cap:'80.000'  },
  { name:'Monumental',         city:'Buenos Aires',   country:'Argentina',    cap:'84.567'  },
  { name:'NRG Stadium',        city:'Houston, TX',    country:'Estados Unidos',cap:'72.220'  },
  { name:'Allegiant Stadium',  city:'Las Vegas, NV',  country:'Estados Unidos',cap:'65.000'  },
  { name:"Levi's Stadium",     city:'Santa Clara, CA',country:'Estados Unidos',cap:'68.500'  },
]

// ── Formation configs ─────────────────────────────────────────────────────────
const FORMATIONS: Record<FormKey, SlotCfg[]> = {
  '4-4-2': [
    { label:'GOL', cat:'GK',  x:50, y:90 },
    { label:'LE',  cat:'DEF', x:12, y:69 }, { label:'ZAG', cat:'DEF', x:37, y:69 },
    { label:'ZAG', cat:'DEF', x:63, y:69 }, { label:'LD',  cat:'DEF', x:88, y:69 },
    { label:'VOL', cat:'MID', x:50, y:53 }, { label:'MC',  cat:'MID', x:50, y:43 },
    { label:'MEI', cat:'MID', x:50, y:33 }, { label:'MEI', cat:'MID', x:50, y:33 },
    { label:'PE',  cat:'FW',  x:22, y:20 }, { label:'PD',  cat:'FW',  x:78, y:20 },
  ],
  '4-3-3': [
    { label:'GK', cat:'GK',  x:50, y:88 },
    { label:'RB', cat:'DEF', x:14, y:71 }, { label:'CB', cat:'DEF', x:34, y:71 },
    { label:'CB', cat:'DEF', x:66, y:71 }, { label:'LB', cat:'DEF', x:86, y:71 },
    { label:'CM', cat:'MID', x:24, y:50 }, { label:'CM', cat:'MID', x:50, y:50 },
    { label:'CM', cat:'MID', x:76, y:50 },
    { label:'RW', cat:'FW',  x:18, y:24 }, { label:'ST', cat:'FW',  x:50, y:21 },
    { label:'LW', cat:'FW',  x:82, y:24 },
  ],
  '3-5-2': [
    { label:'GK', cat:'GK',  x:50, y:88 },
    { label:'CB', cat:'DEF', x:22, y:70 }, { label:'CB', cat:'DEF', x:50, y:70 },
    { label:'CB', cat:'DEF', x:78, y:70 },
    { label:'RM', cat:'MID', x:10, y:49 }, { label:'CM', cat:'MID', x:30, y:51 },
    { label:'CM', cat:'MID', x:50, y:53 }, { label:'CM', cat:'MID', x:70, y:51 },
    { label:'LM', cat:'MID', x:90, y:49 },
    { label:'ST', cat:'FW',  x:34, y:24 }, { label:'ST', cat:'FW',  x:66, y:24 },
  ],
  '4-2-3-1': [
    { label:'GK',  cat:'GK',  x:50, y:88 },
    { label:'RB',  cat:'DEF', x:14, y:72 }, { label:'CB', cat:'DEF', x:34, y:72 },
    { label:'CB',  cat:'DEF', x:66, y:72 }, { label:'LB', cat:'DEF', x:86, y:72 },
    { label:'DM',  cat:'MID', x:34, y:57 }, { label:'DM', cat:'MID', x:66, y:57 },
    { label:'RAM', cat:'MID', x:17, y:37 }, { label:'CAM',cat:'MID', x:50, y:37 },
    { label:'LAM', cat:'MID', x:83, y:37 },
    { label:'ST',  cat:'FW',  x:50, y:20 },
  ],
}


// ── Utilities ─────────────────────────────────────────────────────────────────
const rc = (r: number) =>
  r >= 95 ? '#B8860B' :
  r >= 90 ? '#B45309' :
  r >= 85 ? '#6B7A2E' :
  '#8A7B5E'
const shuffle = <T,>(a: T[]): T[] => [...a].sort(() => Math.random() - 0.5)

// ── Multiplayer (sala local) ───────────────────────────────────────────────────
// O estado da sala vive só no aparelho por enquanto: ainda não há canal de rede,
// então o confronto é resolvido aqui mesmo.
const ROOM_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
const makeRoomCode = () =>
  Array.from({ length: 6 }, () => ROOM_ALPHABET[Math.floor(Math.random() * ROOM_ALPHABET.length)]).join('')

// "Força" estável de uma seleção a partir do nome — a base não guarda nota de time.
function teamStrength(name: string) {
  let h = 0
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 997
  return 80 + (h % 14)
}

// Força do time da usuária a partir de quem entrou em campo (ou dos 11 melhores).
function lineupStrength(lineup: (Player|null)[], squad: Player[]) {
  const fielded = lineup.filter((player): player is Player => Boolean(player))
  const pool = fielded.length ? fielded : [...squad].sort((a, b) => b.rating - a.rating).slice(0, 11)
  if (!pool.length) return 85
  return pool.reduce((acc, player) => acc + player.rating, 0) / pool.length
}

// Placar do confronto: cada lado marca conforme a própria força contra a do
// rival. É simulado no aparelho — é o que substitui a rede por enquanto.
function simulateMpMatch(myStrength: number, rivalStrength: number) {
  const goals = (attack: number, defence: number) => {
    const edge = (attack - defence) / 12 + 1.3
    return Math.max(0, Math.min(5, Math.round(Math.random() * 3 + edge)))
  }
  return { mine: goals(myStrength, rivalStrength), rival: goals(rivalStrength, myStrength) }
}

// O adversário entra com uma seleção sorteada pelo app, sempre diferente da sua.
const pickRivalTeam = (mine: TeamData): PoolTeam => {
  const others = TEAMS.filter(item => item.name !== mine.name)
  const pick = others[Math.floor(Math.random() * others.length)]
  return { name: pick.name, flag: pick.flag }
}

function defaultSquad() {
  const s = (pos: SlotCat, n: number) =>
    [...POOL].filter(p => p.pos === pos).sort((a,b) => b.rating - a.rating).slice(0, n)
  return [...s('GK',3), ...s('DEF',8), ...s('MID',8), ...s('FW',7)]
}

function buildFormation(fk: FormKey, squad: Player[]): FSlot[] {
  const byPos: Record<SlotCat, Player[]> = {
    GK:  [...squad].filter(p=>p.pos==='GK').sort((a,b)=>b.rating-a.rating),
    DEF: [...squad].filter(p=>p.pos==='DEF').sort((a,b)=>b.rating-a.rating),
    MID: [...squad].filter(p=>p.pos==='MID').sort((a,b)=>b.rating-a.rating),
    FW:  [...squad].filter(p=>p.pos==='FW').sort((a,b)=>b.rating-a.rating),
  }
  const idx: Record<SlotCat, number> = { GK:0, DEF:0, MID:0, FW:0 }
  return FORMATIONS[fk].map(s => ({
    ...s,
    player: byPos[s.cat][idx[s.cat]++] ?? byPos.GK[0],
  }))
}

function getBench(fk: FormKey, squad: Player[]): Player[] {
  const ids = new Set(buildFormation(fk, squad).map(f => f.player?.id))
  return squad.filter(p => !ids.has(p.id)).sort((a,b) => b.rating - a.rating)
}

const FIELD_FORMATIONS: Record<FormKey, SlotCfg[]> = {
  '4-4-2': [
    { label:'CA',  cat:'FW',  x:36, y:17 }, { label:'CA',  cat:'FW',  x:64, y:17 },
    { label:'MEI', cat:'MID', x:14, y:40 }, { label:'MC',  cat:'MID', x:38, y:44 }, { label:'MC', cat:'MID', x:62, y:44 }, { label:'VOL', cat:'MID', x:86, y:40 },
    { label:'LE',  cat:'DEF', x:12, y:70 }, { label:'ZAG', cat:'DEF', x:37, y:70 }, { label:'ZAG', cat:'DEF', x:63, y:70 }, { label:'LD', cat:'DEF', x:88, y:70 },
    { label:'GOL', cat:'GK',  x:50, y:89 },
  ],
  '4-3-3': [
    { label:'PE',  cat:'FW',  x:18, y:18 }, { label:'CA',  cat:'FW',  x:50, y:14 }, { label:'PD',  cat:'FW',  x:82, y:18 },
    { label:'MEI', cat:'MID', x:25, y:40 }, { label:'MC',  cat:'MID', x:50, y:34 }, { label:'VOL', cat:'MID', x:75, y:40 },
    { label:'LE',  cat:'DEF', x:12, y:70 }, { label:'ZAG', cat:'DEF', x:37, y:70 }, { label:'ZAG', cat:'DEF', x:63, y:70 }, { label:'LD', cat:'DEF', x:88, y:70 },
    { label:'GOL', cat:'GK',  x:50, y:89 },
  ],
  '3-5-2': [
    { label:'CA',  cat:'FW',  x:36, y:16 }, { label:'CA',  cat:'FW',  x:64, y:16 },
    { label:'PE',  cat:'MID', x:10, y:39 }, { label:'MEI', cat:'MID', x:30, y:34 }, { label:'MC', cat:'MID', x:50, y:29 }, { label:'MC', cat:'MID', x:70, y:34 }, { label:'PD', cat:'MID', x:90, y:39 },
    { label:'ZAG', cat:'DEF', x:22, y:70 }, { label:'ZAG', cat:'DEF', x:50, y:70 }, { label:'ZAG', cat:'DEF', x:78, y:70 },
    { label:'GOL', cat:'GK', x:50, y:89 },
  ],
  '4-2-3-1': [
    { label:'CA',  cat:'FW',  x:50, y:14 },
    { label:'PE',  cat:'MID', x:18, y:32 }, { label:'MEI', cat:'MID', x:50, y:27 }, { label:'PD', cat:'MID', x:82, y:32 },
    { label:'VOL', cat:'MID', x:36, y:47 }, { label:'VOL', cat:'MID', x:64, y:47 },
    { label:'LE', cat:'DEF', x:12, y:70 }, { label:'ZAG', cat:'DEF', x:37, y:70 }, { label:'ZAG', cat:'DEF', x:63, y:70 }, { label:'LD', cat:'DEF', x:88, y:70 },
    { label:'GOL', cat:'GK', x:50, y:89 },
  ],
}

function buildFieldLineup(squad: Player[], formKey: FormKey = '4-4-2'): FSlot[] {
  const byPos: Record<SlotCat, Player[]> = {
    GK: [...squad].filter(p => p.pos === 'GK').sort((a,b) => b.rating - a.rating),
    DEF: [...squad].filter(p => p.pos === 'DEF').sort((a,b) => b.rating - a.rating),
    MID: [...squad].filter(p => p.pos === 'MID').sort((a,b) => b.rating - a.rating),
    FW: [...squad].filter(p => p.pos === 'FW').sort((a,b) => b.rating - a.rating),
  }
  const idx: Record<SlotCat, number> = { GK:0, DEF:0, MID:0, FW:0 }
  const fallback = squad[0] ?? defaultSquad()[0]
  return FIELD_FORMATIONS[formKey].map(slot => ({ ...slot, player: byPos[slot.cat][idx[slot.cat]++] ?? fallback }))
}

// Reposiciona quem já estava escalado quando a formação muda: mantém os
// jogadores por setor em vez de zerar o campo inteiro.
function remapLineup(previous: (Player|null)[], nextSlots: SlotCfg[]): (Player|null)[] {
  const byCat: Record<SlotCat, Player[]> = { GK:[], DEF:[], MID:[], FW:[] }
  previous.forEach(player => { if (player) byCat[player.pos].push(player) })
  const used = new Set<number>()
  return nextSlots.map(slot => {
    const found = byCat[slot.cat].find(player => !used.has(player.id))
    if (!found) return null
    used.add(found.id)
    return found
  })
}

const ROLE_SECTOR: Record<SlotRole, SlotCat> = {
  GOL:'GK', ZAG:'DEF', LD:'DEF', LE:'DEF', VOL:'MID', MC:'MID', MEI:'MID', PE:'FW', PD:'FW', CA:'FW',
}

function roleTag(role: SlotRole) {
  const colors: Record<SlotCat,string> = { GK:'#B45309', DEF:'#2563EB', MID:'#059669', FW:'#B91C1C' }
  return (
    <span
      style={{ color:'#FFFDF5', backgroundColor: colors[ROLE_SECTOR[role]] }}
      className="text-xs font-mono font-bold rounded-md px-1.5 py-0.5 leading-none shrink-0 tracking-wide">
      {role}
    </span>
  )
}

function PlayerAvatar({ player, compact = false }: { player: Player; compact?: boolean }) {
  return player.image ? (
    <img
      src={player.image}
      alt=""
      className={`${compact ? 'w-10 h-10' : 'w-full h-20'} rounded-lg object-cover bg-[#EFE7D2]`}/>
  ) : (
    <div className={`${compact ? 'w-10 h-10' : 'w-full h-20'} rounded-lg bg-[#EFE7D2] border border-[#C9BFA6] flex items-center justify-center`}>
      <span className={`${compact ? 'text-lg' : 'text-3xl'} opacity-40`}>⚽</span>
    </div>
  )
}

// Papel secundário derivado do principal — o "joga também em…" dos cards.
const SECONDARY_ROLE: Partial<Record<SlotRole, string>> = {
  CA:'MA', PD:'CA', PE:'CA', MEI:'MC', MC:'VOL', VOL:'ZAG', ZAG:'VOL', LD:'ZAG', LE:'ZAG',
}
function secondaryRole(role: SlotRole): string | null {
  return SECONDARY_ROLE[role] ?? null
}

// Atributos derivados da nota e do setor: atacantes/meias mostram finalização,
// velocidade e passe; zagueiros/volantes, desarme, força e cabeceio. Goleiros
// não têm linha de atributos. Os deltas são fixos por setor para os valores
// parecerem coerentes com o rating (Pelé 99 → FIN 98, VEL 92, PAS 90).
function playerAttrs(player: Player): { keys: [string,string,string]; values: [number,number,number] } | null {
  if (player.pos === 'GK') return null
  if (['ZAG','LD','LE','VOL'].includes(player.role)) {
    return { keys:['DES','FOR','CAB'], values:[player.rating-1, player.rating-4, player.rating-6] }
  }
  return { keys:['FIN','VEL','PAS'], values:[player.rating-1, player.rating-7, player.rating-9] }
}

// ── Convocação automática ──────────────────────────────────────────────────────
const SQUAD_TOTALS: Record<SlotCat, number> = { GK:3, DEF:8, MID:8, FW:7 }
// Convocação "atual" fixa: os 26 nomes mais recentes. É preenchida fora do
// código (a lista de convocados de verdade não está na base, que só tem 52
// brasileiros históricos). Enquanto vazia, o preset cai no fallback de nota.
const CURRENT_SQUAD_NAMES: string[] = []

// Monta um elenco válido (3/8/8/7) dando prioridade a uma lista por posição; o
// que sobrar em cada posição é completado com os de maior nota, sem repetir.
function squadByPriority(priority: Player[], priorityPerPos: Partial<Record<SlotCat, number>>): Player[] {
  const drawn: Player[] = []
  ;(['GK','DEF','MID','FW'] as SlotCat[]).forEach(pos => {
    const cap = priorityPerPos[pos] ?? SQUAD_TOTALS[pos]
    const prio = priority.filter(p => p.pos === pos).slice(0, cap)
    const used = new Set(prio.map(p => p.id))
    const fill = POOL
      .filter(p => p.pos === pos && !used.has(p.id))
      .sort((a, b) => b.rating - a.rating)
      .slice(0, SQUAD_TOTALS[pos] - prio.length)
    drawn.push(...prio, ...fill)
  })
  return drawn
}

const currentSquad = () => {
  const byName = new Map(POOL.map(p => [p.name, p]))
  const named = CURRENT_SQUAD_NAMES.map(name => byName.get(name)).filter((p): p is Player => Boolean(p))
  return squadByPriority(named, SQUAD_TOTALS)
}
const legendsSquad = () => squadByPriority([...POOL].sort((a, b) => b.rating - a.rating), SQUAD_TOTALS)
// 18 atuais + 8 lendas: metade+ do elenco vem da convocação fixa, o resto das
// maiores notas da história que ficaram de fora.
const balancedSquad = () => squadByPriority(currentSquad(), { GK:2, DEF:6, MID:5, FW:5 })
const randomSquad = () => {
  const positions: SlotCat[] = ['GK','DEF','MID','FW']
  return positions.flatMap(pos => shuffle(POOL.filter(player => player.pos === pos)).slice(0, SQUAD_TOTALS[pos]))
}

function groupCount(format: TournamentFormat) {
  return format === 12 ? 3 : format === 16 ? 4 : 0
}

function makeGroups(participants: PoolTeam[], format: TournamentFormat): TournamentGroup[] {
  return Array.from({ length: groupCount(format) }, (_, i) => {
    const teams = participants.slice(i * 4, i * 4 + 4)
    const standings = teams.map(team => ({
      team, p:0, w:0, d:0, l:0, gf:0, ga:0, pts:0, yellow:0, red:0,
    }))
    const matches: GroupMatch[] = []
    for (let a = 0; a < teams.length; a++) {
      for (let b = a + 1; b < teams.length; b++) {
        matches.push({
          id:`G${i + 1}-${a + 1}-${b + 1}`,
          home:teams[a], away:teams[b], status:'pending',
          homeGoals:null, awayGoals:null,
          homeYellow:0, awayYellow:0, homeRed:0, awayRed:0,
        })
      }
    }
    return { name:String.fromCharCode(65 + i), teams, standings, matches }
  })
}

function applyGroupResult(group: TournamentGroup, match: GroupMatch, homeGoals: number, awayGoals: number): TournamentGroup {
  const standings = group.standings.map(row => ({ ...row }))
  const home = standings.find(row => row.team.name === match.home.name)!
  const away = standings.find(row => row.team.name === match.away.name)!
  home.p += 1; away.p += 1
  home.gf += homeGoals; home.ga += awayGoals
  away.gf += awayGoals; away.ga += homeGoals
  home.yellow += match.homeYellow; away.yellow += match.awayYellow
  home.red += match.homeRed; away.red += match.awayRed
  if (homeGoals > awayGoals) { home.w += 1; away.l += 1; home.pts += 3 }
  else if (homeGoals < awayGoals) { away.w += 1; home.l += 1; away.pts += 3 }
  else { home.d += 1; away.d += 1; home.pts += 1; away.pts += 1 }
  const matches = group.matches.map(item => item.id === match.id
    ? {
        ...item,
        ...match,
        status:'played' as const,
        homeGoals,
        awayGoals,
      }
    : item)
  return { ...group, standings, matches }
}

function simulateGroupMatches(groups: TournamentGroup[]) {
  return groups.map(group => group.matches.reduce((current, match, index) => {
    if (match.status === 'played') return current
    const homeGoals = (index + group.name.charCodeAt(0)) % 3
    const awayGoals = (index * 2 + group.name.charCodeAt(0)) % 2
    return applyGroupResult(current, groupMatchCards(match), homeGoals, awayGoals)
  }, group))
}

function groupMatchLabel(match: GroupMatch) {
  return `${match.home.flag} ${match.home.name} × ${match.away.name} ${match.away.flag}`
}

function groupMatchScore(match: GroupMatch): [number, number] {
  const seed = match.id.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return [seed % 3, Math.floor(seed / 3) % 3]
}

function groupMatchCards(match: GroupMatch): GroupMatch {
  const seed = match.id.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return {
    ...match,
    homeYellow: seed % 4 === 0 ? 1 : 0,
    awayYellow: seed % 5 === 0 ? 1 : 0,
    homeRed: seed % 11 === 0 ? 1 : 0,
    awayRed: seed % 13 === 0 ? 1 : 0,
  }
}

function groupTieBreakers() {
  return [
    'Saldo de gols',
    'Gols marcados',
    'Confronto direto: pontos, saldo e gols',
    'Menos cartões vermelhos',
    'Menos cartões amarelos',
    'Sorteio',
  ]
}

function compareStandings(a: GroupStanding, b: GroupStanding) {
  return b.pts - a.pts
    || (b.gf - b.ga) - (a.gf - a.ga)
    || b.gf - a.gf
    || a.red - b.red
    || a.yellow - b.yellow
    || a.team.name.localeCompare(b.team.name, 'pt-BR')
}

function rankGroups(groups: TournamentGroup[]) {
  return groups.map(group => ({
    ...group,
    standings: [...group.standings].sort(compareStandings),
  }))
}

function knockoutScore(team: PoolTeam, opponent: PoolTeam, penalties = false) {
  return penalties ? `${team.name} ${team.flag}  1 (4) – (3) 1  ${opponent.name} ${opponent.flag}` : `${team.name} ${team.flag}  2 – 1  ${opponent.name} ${opponent.flag}`
}

function qualifiedForQuarterfinals(groups: TournamentGroup[]) {
  const ranked = rankGroups(groups)
  if (ranked.length === 4) {
    return ranked.flatMap(group => group.standings.slice(0, 2).map(s => s.team))
  }
  const direct = ranked.flatMap(group => group.standings.slice(0, 2).map(s => s.team))
  const bestThirds = ranked
    .flatMap(group => group.standings.slice(2, 3))
    .sort(compareStandings)
    .slice(0, 2)
    .map(s => s.team)
  return [...direct, ...bestThirds]
}

function makeQuarterfinals(groups: TournamentGroup[]): [PoolTeam, PoolTeam][] {
  const qualified = qualifiedForQuarterfinals(groups)
  if (groups.length === 4) {
    return [
      [qualified[0], qualified[7]],
      [qualified[1], qualified[6]],
      [qualified[2], qualified[5]],
      [qualified[3], qualified[4]],
    ]
  }
  return [
    [qualified[0], qualified[3]],
    [qualified[1], qualified[4]],
    [qualified[2], qualified[5]],
    [qualified[6], qualified[7]],
  ]
}

function emptyTie(home: PoolTeam|null = null, away: PoolTeam|null = null): KnockoutTie {
  return { home, away, homeGoals: null, awayGoals: null, winner: null }
}

function makeKnockout(qf: [PoolTeam, PoolTeam][]): Knockout {
  return {
    qf: qf.map(([home, away]) => emptyTie(home, away)),
    sf: [emptyTie(), emptyTie()],
    third: emptyTie(),
    final: emptyTie(),
  }
}

// Placar determinístico a partir dos dois nomes: o mesmo confronto dá sempre o
// mesmo resultado, então a chave não muda quando a tela é reaberta.
function tieSeed(a: PoolTeam, b: PoolTeam) {
  return `${a.name}×${b.name}`.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
}

// Decide um confronto que a usuária não joga. Empate vai para os pênaltis, e o
// desempate também sai da semente. Confrontos já decididos ou com um lado em
// aberto passam direto.
function simulateTie(tie: KnockoutTie): KnockoutTie {
  if (!tie.home || !tie.away || tie.winner) return tie
  const seed = tieSeed(tie.home, tie.away)
  const homeGoals = seed % 3
  const awayGoals = Math.floor(seed / 3) % 3
  const winner = homeGoals === awayGoals
    ? (seed % 2 === 0 ? tie.home : tie.away)
    : (homeGoals > awayGoals ? tie.home : tie.away)
  return { ...tie, homeGoals, awayGoals, winner }
}

function tieLoser(tie: KnockoutTie): PoolTeam|null {
  if (!tie.winner) return null
  return tie.winner.name === tie.home?.name ? tie.away : tie.home
}

// Mantém o confronto se os dois lados continuam os mesmos; se algum trocou, ele
// volta a ser um confronto em aberto em vez de guardar um resultado inválido.
function carryOver(tie: KnockoutTie, home: PoolTeam|null, away: PoolTeam|null): KnockoutTie {
  if (home?.name === tie.home?.name && away?.name === tie.away?.name) return tie
  return emptyTie(home, away)
}

// Repassa quem avançou: vencedores das quartas vão para a semi, vencedores da
// semi para a final e perdedores para a disputa de 3º lugar.
function propagateKnockout(ko: Knockout): Knockout {
  const sf = ko.sf.map((tie, index) =>
    carryOver(tie, ko.qf[index * 2]?.winner ?? null, ko.qf[index * 2 + 1]?.winner ?? null))
  return {
    ...ko,
    sf,
    final: carryOver(ko.final, sf[0].winner, sf[1].winner),
    third: carryOver(ko.third, tieLoser(sf[0]), tieLoser(sf[1])),
  }
}

// Monta o confronto da usuária respeitando de que lado ela caiu na chave, em
// vez de assumir que ela é sempre o mandante.
function decideTie(tie: KnockoutTie, winner: PoolTeam, winnerGoals: number, loserGoals: number): KnockoutTie {
  const winnerIsHome = tie.home?.name === winner.name
  return {
    ...tie,
    homeGoals: winnerIsHome ? winnerGoals : loserGoals,
    awayGoals: winnerIsHome ? loserGoals : winnerGoals,
    winner,
  }
}

// Resolve uma fase inteira: o confronto da usuária entra como veio e os outros
// são simulados. Depois propaga quem avançou para a fase seguinte.
function settleRound(ko: Knockout, round: 'qf'|'sf', userIndex: number, userTie: KnockoutTie): Knockout {
  const ties = ko[round].map((tie, index) => index === userIndex ? userTie : simulateTie(tie))
  return propagateKnockout({ ...ko, [round]: ties })
}

// Com a usuária eliminada, simula final e disputa de 3º lugar de uma vez para a
// chave fechar com campeão e terceiro lugar definidos.
function finishKnockout(ko: Knockout): Knockout {
  const filled = propagateKnockout(ko)
  return { ...filled, final: simulateTie(filled.final), third: simulateTie(filled.third) }
}

function makeDrawnBracket(team: PoolTeam, shuffled: PoolTeam[], format: TournamentFormat): DrawnBracket {
  const participants = [team, ...shuffled]
  const groups = format === 12 || format === 16 ? makeGroups(participants, format) : []
  const qf: [PoolTeam, PoolTeam][] = format === 8 ? [
    [team, shuffled[0]], [shuffled[1], shuffled[2]],
    [shuffled[3], shuffled[4]], [shuffled[5], shuffled[6]],
  ] : []
  return { format, participants, groups, qf, ko: makeKnockout(qf) }
}

function completeGroupStage(bracket: DrawnBracket): DrawnBracket {
  const groups = simulateGroupMatches(bracket.groups)
  const qf = makeQuarterfinals(groups)
  return { ...bracket, groups, qf, ko: makeKnockout(qf) }
}

// ── TopBar ────────────────────────────────────────────────────────────────────
function TopBar({ title, sub, onBack, onReset }: {
  title: string; sub?: string; onBack?: () => void; onReset?: () => void
}) {
  return (
    <div className="flex items-center gap-2 px-4 pt-4 pb-3 shrink-0 border-b-2 border-double border-[#C9BFA6] bg-[#F6F1E5]">
      {onBack && (
        <button onClick={onBack}
          className="w-9 h-9 rounded-xl bg-[#FFFDF5] border-2 border-[#172033] flex items-center justify-center shrink-0 active:scale-90 transition-transform"
          style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.16)' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8L10 13" stroke="#172033" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      )}
      <div className="flex-1 min-w-0">
        {sub && (
          <p className="flex items-center gap-1.5 font-mono text-xs text-[#8A6D1F] uppercase tracking-[0.12em] mb-0.5">
            <span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>{sub}
          </p>
        )}
        <h2 className="font-display text-2xl font-900 uppercase text-[#172033] leading-none truncate">{title}</h2>
      </div>
      {onReset && (
        <button onClick={onReset}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#FFFDF5] border-2 border-[#172033] active:scale-95 transition-transform"
          style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.16)' }}>
          <span className="text-base text-[#8A6D1F]">↺</span>
          <span className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-widest">Novo</span>
        </button>
      )}
    </div>
  )
}

// ── Screen 1: Team Selection ──────────────────────────────────────────────────
function TeamSelection({ onNext, onBack }: { onNext: (t: TeamData) => void; onBack: () => void }) {
  const [sel, setSel]         = useState<string|null>(null)
  const [search, setSearch]   = useState('')
  const [conf, setConf]       = useState<'ALL'|'CONMEBOL'|'CONCACAF'>('ALL')

  const filtered = TEAMS.filter(t =>
    t.name.toLowerCase().includes(search.toLowerCase()) &&
    (conf === 'ALL' || t.conf === conf)
  )
  const team = TEAMS.find(t => t.id === sel)

  return (
    <div className="flex flex-col h-full animate-fade-in retro-paper">
      <div className="flex items-center gap-3 px-5 pt-5 pb-2 shrink-0">
        <button onClick={onBack} aria-label="Voltar para os modos de jogo"
          className="w-9 h-9 rounded-xl bg-[#FFFDF5] border-2 border-[#172033] flex items-center justify-center active:scale-90 transition-transform"
          style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.16)' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8L10 13" stroke="#172033" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <p className="font-mono text-sm tracking-widest text-[#8A6D1F] uppercase">Modos de jogo</p>
      </div>
      <div className="px-5 pt-3 pb-4 shrink-0">
        <p className="flex items-center gap-1.5 font-mono text-xs tracking-[0.12em] text-[#8A6D1F] uppercase mb-1.5">
          <span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Copa América
        </p>
        <h1 className="font-display text-5xl font-900 uppercase leading-[0.85] text-[#172033]"
          style={{ textShadow: '2px 2px 0 rgba(184,134,11,0.20)' }}>
          Escolha seu <span className="text-[#B8860B]">país</span>
        </h1>
        <p className="font-mono text-sm text-[#6B5B3E] mt-2">16 seleções disponíveis</p>
      </div>

      <div className="px-5 pb-3 shrink-0">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="6" cy="6" r="4.5" stroke="#8A6D1F" strokeWidth="1.4"/>
            <path d="M10 10L12.5 12.5" stroke="#8A6D1F" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar seleções…"
            className="w-full bg-[#FFFDF5] border-2 border-[#172033] rounded-xl pl-8 pr-4 py-3 text-sm text-[#172033] placeholder-gray-600 outline-none focus:border-[#B8860B] transition-colors"
            style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.10)' }}/>
        </div>
      </div>

      <div className="flex gap-2 px-5 pb-3 shrink-0">
        {(['ALL','CONMEBOL','CONCACAF'] as const).map(c => (
          <button key={c} onClick={() => setConf(c)}
            className={`px-3 py-1.5 rounded-lg font-mono text-sm font-700 uppercase tracking-widest border-2 transition-all ${
              conf===c ? 'bg-[#172033] text-[#F6F1E5] border-[#172033]' : 'bg-[#FFFDF5] text-[#6B5B3E] border-[#C9BFA6]'
            }`}>{c === 'ALL' ? 'TODAS' : c}</button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-4">
        <div className="grid grid-cols-4 gap-2">
          {filtered.map(t => {
            const isSel = sel === t.id
            return (
              <button key={t.id} onClick={() => setSel(t.id)}
                className={`relative rounded-2xl p-2.5 flex flex-col items-center gap-1.5 border-2 transition-all active:scale-95 ${
                  isSel ? 'bg-[#FFF7E6] border-[#B8860B]' : 'bg-[#FFFDF5] border-[#C9BFA6]'
                }`}
                style={{ boxShadow: isSel ? '2px 2px 0 rgba(184,134,11,0.35)' : '2px 2px 0 rgba(23,32,51,0.10)' }}>
                {isSel && (
                  <span className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-[#B8860B] border-2 border-[#172033] flex items-center justify-center text-xs font-bold leading-none text-[#172033]">✓</span>
                )}
                <span className="text-2xl leading-none">{t.flag}</span>
                <span className="font-display text-xs font-800 uppercase leading-tight text-center text-[#172033]">{t.name}</span>
                <span className={`font-mono text-xs font-700 tracking-widest ${t.conf==='CONMEBOL'?'text-[#8A6D1F]':'text-[#2563EB]'}`}>{t.conf}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="px-5 pb-8 pt-3 shrink-0 border-t-2 border-double border-[#C9BFA6]">
        <button disabled={!sel} onClick={() => team && onNext(team)}
          className={`w-full py-4 rounded-2xl font-display text-lg font-900 uppercase tracking-widest border-2 transition-all ${
            sel ? 'bg-[#D97706] text-[#FFFDF5] border-[#172033] active:scale-95' : 'bg-[#EFE7D2] text-[#8A7B5E] border-[#C9BFA6] cursor-not-allowed'
          }`}
          style={sel ? { boxShadow: '3px 3px 0 rgba(23,32,51,0.22)' } : {}}>
          {sel ? `Confirmar · ${team?.name}` : 'Selecione uma seleção'}
        </button>
      </div>
    </div>
  )
}

// ── Screen 2: Squad Builder (52-player pool) ──────────────────────────────────
function GameModeSelection({ onSelect, onBack, onReset }: {
  onSelect: (mode: GameMode) => void
  onBack: () => void
  onReset: () => void
}) {
  const modes: { key: GameMode; title: string; subtitle: string; description: string }[] = [
    {
      key:'quick',
      title:'Modo rápido',
      subtitle:'8 seleções · mata-mata direto',
      description:'Quartas de final, semifinal e final. A disputa pelo 3º lugar acontece quando necessário.',
    },
    {
      key:'normal',
      title:'Modo normal',
      subtitle:'12 seleções · 3 grupos',
      description:'Três grupos com quatro seleções. Os dois primeiros e os dois melhores terceiros avançam.',
    },
  ]

  return (
    <div className="flex flex-col h-full animate-fade-in retro-paper">
      <TopBar title="Modo de jogo" sub="Escolha como jogar" onBack={onBack} onReset={onReset}/>
      <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4">
        <p className="flex items-center gap-1.5 font-mono text-xs text-[#172033] font-700 uppercase tracking-[0.24em] mb-3">
          <span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Selecione sua experiência
        </p>
        <div className="grid grid-rows-2 gap-3 h-[calc(100%-28px)] min-h-[560px]">
          {modes.map(mode => {
            const quick = mode.key === 'quick'
            const bar = quick ? 'bg-[#D97706]' : 'bg-[#2563EB]'
            const kick = quick ? 'text-[#B45309]' : 'text-[#2563EB]'
            return (
              <div
                key={mode.key}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(mode.key)}
                onKeyDown={event => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onSelect(mode.key)
                  }
                }}
                className="relative overflow-hidden text-left rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] transition-all active:scale-[0.98] cursor-pointer"
                style={{ boxShadow: '3px 3px 0 rgba(23,32,51,0.16)' }}
              >
                <div className={`h-2 ${bar} ticket-stripe`}/>
                <div className="flex flex-col justify-between h-[calc(100%-8px)] p-5">
                  <div>
                    <p className={`font-mono text-sm font-700 tracking-[0.22em] uppercase ${kick}`}>
                      {quick ? 'Mata-mata direto' : 'Fase de grupos'}
                    </p>
                    <p className="font-display text-3xl font-900 uppercase text-[#172033] leading-none mt-2">{mode.title}</p>
                    <p className="font-mono text-sm font-700 uppercase tracking-wider mt-2 text-[#8A6D1F]">{mode.subtitle}</p>
                  </div>

                  <div className="flex items-center justify-center flex-1 min-h-[64px]">
                    <span className="font-display text-6xl font-900 text-[#172033]/8 uppercase leading-none">{quick ? '8' : '12'}</span>
                  </div>

                  <div className="ticket-perf mb-3"/>
                  <p className="font-mono text-sm text-[#6B5B3E] leading-relaxed">{mode.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function ParticipantSelection({ team, onNext, onBack, onReset }: {
  team: TeamData
  onNext: (participants: PoolTeam[]) => void
  onBack: () => void
  onReset: () => void
}) {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(() => new Set([team.name]))
  const required = 8
  const drawRandomParticipants = () => {
    const available = TEAMS.filter(item => item.name !== team.name)
    const drawn = shuffle(available).slice(0, required - 1)
    setSelected(new Set([team.name, ...drawn.map(item => item.name)]))
    setOpen(false)
  }
  const toggle = (name: string) => {
    if (name === team.name) return
    setSelected(previous => {
      const next = new Set(previous)
      if (next.has(name)) next.delete(name)
      else if (next.size < required) next.add(name)
      return next
    })
  }
  const participants = TEAMS.filter(item => selected.has(item.name)).map(item => ({ name:item.name, flag:item.flag }))

  return (
    <div className="flex flex-col h-full animate-fade-in retro-paper">
      <TopBar title="Participantes" sub="Modo rápido · 8 seleções" onBack={onBack} onReset={onReset}/>
      <div className="flex-1 overflow-y-auto px-5 py-5">
        <div className="rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] overflow-hidden mb-4" style={{ boxShadow: '3px 3px 0 rgba(23,32,51,0.16)' }}>
          <div className="h-2 bg-[#D97706] ticket-stripe"/>
          <div className="p-4">
            <p className="flex items-center gap-1.5 font-mono text-xs text-[#8A6D1F] uppercase tracking-widest">
              <span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Cabeça de chave
            </p>
            <p className="font-display text-xl font-900 uppercase text-[#172033] mt-1">{team.flag} {team.name}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setOpen(value => !value)} className="flex-1 flex items-center justify-between rounded-xl border-2 border-[#172033] bg-[#FFFDF5] px-4 py-3 text-left" style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.12)' }}>
            <span><span className="font-mono text-xs text-[#8A6D1F] uppercase tracking-widest block">Seleções participantes</span><span className="font-display text-base font-800 uppercase text-[#172033]">{selected.size} de {required} selecionadas</span></span>
            <span className="text-[#B8860B] text-lg">{open ? '⌃' : '⌄'}</span>
          </button>
          <button onClick={drawRandomParticipants} aria-label="Sortear 8 seleções" title="Sortear 8 seleções" className="w-14 shrink-0 rounded-xl border-2 border-[#172033] bg-[#172033] text-[#F6F1E5] flex items-center justify-center active:scale-95 transition-transform" style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.20)' }}>
            <span className="font-display text-2xl leading-none">↻</span>
          </button>
        </div>
        {open && <div className="mt-2 rounded-xl border-2 border-[#C9BFA6] bg-[#FFFDF5] p-2 grid grid-cols-2 gap-1.5">{TEAMS.map(item => { const isSelected = selected.has(item.name); const disabled = !isSelected && selected.size >= required; return <button key={item.id} onClick={() => toggle(item.name)} disabled={item.name === team.name || disabled} className={`flex items-center gap-2 rounded-lg px-2.5 py-2 text-left border-2 ${isSelected ? 'bg-[#FFF7E6] border-[#B8860B] text-[#172033]' : disabled ? 'opacity-35 border-transparent' : 'bg-[#F6F1E5] border-transparent text-[#6B5B3E]'}`}><span>{item.flag}</span><span className="font-display text-sm font-700 uppercase truncate">{item.name}</span>{isSelected && <span className="ml-auto text-[#059669]">✓</span>}</button> })}</div>}
        <div className="mt-4 space-y-2">{participants.map(item => <div key={item.name} className="flex items-center gap-2 rounded-xl border-2 border-[#C9BFA6] bg-[#FFFDF5] px-3 py-2.5"><span className="text-lg">{item.flag}</span><span className="font-display text-sm font-700 uppercase text-[#172033]">{item.name}</span>{item.name === team.name && <span className="ml-auto font-mono text-xs font-700 text-[#8A6D1F] uppercase">Cabeça</span>}</div>)}</div>
      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 border-t-2 border-double border-[#C9BFA6]"><button disabled={selected.size !== required} onClick={() => onNext(participants)} className={`w-full py-4 rounded-2xl font-display text-lg font-900 uppercase tracking-widest border-2 ${selected.size === required ? 'bg-[#D97706] text-[#FFFDF5] border-[#172033] active:scale-95' : 'bg-[#EFE7D2] text-[#8A7B5E] border-[#C9BFA6]'}`} style={selected.size === required ? { boxShadow: '3px 3px 0 rgba(23,32,51,0.22)' } : {}}>{selected.size === required ? 'Confirmar participantes' : `Escolha mais ${required - selected.size}`}</button></div>
    </div>
  )
}

function SquadBuilder({ team, onNext, onBack, onReset }: {
  team: TeamData; onNext: (squad: Player[]) => void; onBack: () => void; onReset: () => void
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [filter, setFilter]     = useState<PosF>('ALL')
  const [search, setSearch]     = useState('')
  const [view, setView]         = useState<SquadView>('grid')
  const [sort, setSort]         = useState<SquadSort>('rating')
  const [sortOpen, setSortOpen] = useState(false)
  const [presetOpen, setPresetOpen] = useState(false)

  const counts = {
    GK:  [...selected].filter(id => POOL.find(p=>p.id===id)?.pos==='GK').length,
    DEF: [...selected].filter(id => POOL.find(p=>p.id===id)?.pos==='DEF').length,
    MID: [...selected].filter(id => POOL.find(p=>p.id===id)?.pos==='MID').length,
    FW:  [...selected].filter(id => POOL.find(p=>p.id===id)?.pos==='FW').length,
  }
  const totals = { GK:3, DEF:8, MID:8, FW:7 }
  const complete = counts.GK===3 && counts.DEF===8 && counts.MID===8 && counts.FW===7

  const applySquad = (players: Player[]) => setSelected(new Set(players.map(player => player.id)))
  // As convocações automáticas que substituem o dado: cada uma preenche o elenco
  // inteiro de uma vez e a usuária ainda pode ajustar na mão depois.
  const presets: { label: string; hint: string; apply: () => void }[] = [
    { label: 'Elenco Atual', hint: 'Os 26 convocados mais recentes', apply: () => applySquad(currentSquad()) },
    { label: 'Seleção das Lendas', hint: 'Os 26 maiores da história', apply: () => applySquad(legendsSquad()) },
    { label: 'Elenco Equilibrado', hint: '18 atuais + 8 lendas', apply: () => applySquad(balancedSquad()) },
    { label: 'Aleatório', hint: 'Sorteia cada posição', apply: () => applySquad(randomSquad()) },
  ]

  const toggle = (p: Player) => {
    setSelected(prev => {
      const n = new Set(prev)
      if (n.has(p.id)) {
        n.delete(p.id)
      } else {
        const posCount = [...n].filter(id => POOL.find(x=>x.id===id)?.pos===p.pos).length
        if (posCount < totals[p.pos]) n.add(p.id)
      }
      return n
    })
  }

  const visible = POOL.filter(p =>
    (filter==='ALL' || p.pos===filter) &&
    p.name.toLowerCase().includes(search.toLowerCase())
  ).sort((a, b) => sort === 'rating'
    ? b.rating - a.rating || a.name.localeCompare(b.name, 'pt-BR')
    : a.name.localeCompare(b.name, 'pt-BR')
  )

  const squad = POOL.filter(p => selected.has(p.id))

  return (
    <div className="flex flex-col h-full animate-fade-in retro-paper">
      <TopBar title="Montar elenco" sub={`${team.flag} ${team.name} · Todos os tempos`} onBack={onBack} onReset={onReset} />

      {/* Search + position filters */}
      <div className="px-4 pt-3 pb-2 shrink-0 bg-[#F6F1E5] border-b-2 border-double border-[#C9BFA6]">
        <div className="relative mb-2">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2" width="11" height="11" viewBox="0 0 14 14" fill="none">
            <circle cx="6" cy="6" r="4.5" stroke="#8A6D1F" strokeWidth="1.3"/>
            <path d="M10 10L12.5 12.5" stroke="#8A6D1F" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
          <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar jogadores…"
            className="w-full bg-[#FFFDF5] border-2 border-[#172033] rounded-lg pl-7 pr-3 py-2 text-base text-[#172033] outline-none" style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.10)' }}/>
        </div>

        <div className="flex gap-1 min-w-0">
          {(['ALL','GK','DEF','MID','FW'] as PosF[]).map(tab => {
            const label = tab === 'ALL' ? POSITION_LABELS.ALL : `${POSITION_LABELS[tab]} ${counts[tab]}/${totals[tab]}`
            return (
              <button key={tab} onClick={() => setFilter(tab)}
                className={`flex-1 min-w-0 py-1.5 rounded-lg font-display text-xs font-800 uppercase transition-colors border-2 ${
                  filter===tab ? 'bg-[#172033] text-[#F6F1E5] border-[#172033]' : 'bg-[#FFFDF5] text-[#6B5B3E] border-[#C9BFA6]'
                }`}>{label}</button>
            )
          })}
        </div>

        <div className="relative mt-2 flex items-center gap-2">
          <button onClick={() => setSortOpen(open => !open)}
            className="flex-1 min-w-0 flex items-center justify-between rounded-lg bg-[#FFFDF5] border-2 border-[#C9BFA6] px-3 py-2 text-left">
            <span className="font-mono text-xs text-[#8A6D1F] uppercase tracking-widest">Ordenar por</span>
            <span className="font-display text-sm font-800 uppercase text-[#172033] truncate ml-2">
              {sort === 'rating' ? 'Nota: maior primeiro' : 'Nome: A–Z'} <span className="text-[#8A6D1F] ml-1">⌄</span>
            </span>
          </button>
          <div className="flex rounded-lg bg-[#FFFDF5] border-2 border-[#C9BFA6] p-0.5 shrink-0">
            <button onClick={() => setView('grid')} aria-label="Visualização em grade"
              className={`w-8 h-7 rounded-md flex items-center justify-center ${view==='grid'?'bg-[#172033] text-[#F6F1E5]':'text-[#8A6D1F]'}`}>
              <span className="text-base">▦</span>
            </button>
            <button onClick={() => setView('list')} aria-label="Visualização em lista"
              className={`w-8 h-7 rounded-md flex items-center justify-center ${view==='list'?'bg-[#172033] text-[#F6F1E5]':'text-[#8A6D1F]'}`}>
              <span className="text-base">☷</span>
            </button>
          </div>
          {sortOpen && (
            <div className="absolute left-0 right-16 top-full z-20 mt-1 rounded-lg bg-[#FFFDF5] border-2 border-[#172033] p-1" style={{ boxShadow: '3px 3px 0 rgba(23,32,51,0.18)' }}>
              {([['rating','Nota: maior primeiro'], ['name','Nome: A–Z']] as [SquadSort, string][]).map(([value, label]) => (
                <button key={value} onClick={() => { setSort(value); setSortOpen(false) }}
                  className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-left ${sort === value ? 'bg-[#FFF7E6] text-[#B8860B]' : 'text-[#6B5B3E]'}`}>
                  <span className="font-display text-sm font-700 uppercase">{label}</span>
                  {sort === value && <span className="text-sm">✓</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Player grid */}
      <div className="flex-1 overflow-y-auto px-4 py-2">
        <p className="flex items-center gap-1.5 font-mono text-xs text-[#8A6D1F] uppercase tracking-widest mb-2"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>{visible.length} jogadores · Toque para selecionar</p>
        <div className={view === 'grid' ? 'grid grid-cols-2 gap-2' : 'flex flex-col gap-2'}>
          {visible.map(player => {
            const isSel = selected.has(player.id)
            const posCount = [...selected].filter(id => POOL.find(p=>p.id===id)?.pos===player.pos).length
            const canAdd = !isSel && posCount < totals[player.pos]
            return (
              <button key={player.id} onClick={() => toggle(player)}
                className={`text-left border-2 transition-all duration-150 active:scale-[0.97] ${
                  view === 'grid' ? 'rounded-xl p-2.5' : 'rounded-xl p-2 flex items-center gap-2.5'
                } ${
                  isSel      ? 'bg-[#FFF7E6] border-[#B8860B]' :
                  !canAdd    ? 'bg-[#FFFDF5] border-[#C9BFA6] opacity-45' :
                  'bg-[#FFFDF5] border-[#C9BFA6]'
                }`} style={isSel ? { boxShadow: '2px 2px 0 rgba(184,134,11,0.35)' } : {}}>
                <div className={view === 'list' ? 'relative shrink-0' : 'relative'}>
                  <PlayerAvatar player={player} compact={view === 'list'} />
                  {isSel && (
                    <span className="absolute top-1 left-1 z-10 w-4 h-4 rounded-full bg-[#B8860B] border-2 border-[#FFFDF5] inline-flex items-center justify-center text-[10px] font-bold leading-none text-[#FFFDF5]">✓</span>
                  )}
                  {view === 'grid' && (
                    <span className="absolute bottom-1 right-1 z-10 rounded-md bg-[#172033]/90 px-1.5 py-0.5 flex items-center gap-0.5">
                      {player.rating > 90 && <span className="text-[10px] leading-none">⭐</span>}
                      <span className="font-mono text-xs font-700 leading-none text-[#F6F1E5]">{player.rating}</span>
                    </span>
                  )}
                </div>
                <div className={view === 'list' ? 'flex-1 min-w-0' : 'mt-1.5'}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-display text-base font-800 uppercase leading-tight text-[#172033] truncate">{player.name}</p>
                    {view === 'list' && (
                      <span className="flex items-center gap-1 shrink-0">
                        {player.rating > 90 && <span className="text-[#B8860B] text-xs leading-none">⭐</span>}
                        <span className="font-mono text-sm font-700" style={{color:rc(player.rating)}}>{player.rating}</span>
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between gap-1 mt-0.5 min-w-0">
                    <p className="font-mono text-[10px] text-[#6B5B3E] shrink-0">{player.era}</p>
                    <div className="flex items-center gap-1 shrink-0">
                      {roleTag(player.role)}
                      {secondaryRole(player.role) && <span className="font-mono text-[10px] text-[#8A6D1F] shrink-0">({secondaryRole(player.role)})</span>}
                    </div>
                  </div>
                  {(() => {
                    const attrs = playerAttrs(player)
                    return attrs && (
                      <p className="font-mono text-[10px] text-[#8A7B5E] mt-1 truncate">
                        {attrs.keys[0]} <span className="font-700 text-[#172033]">{attrs.values[0]}</span> · {attrs.keys[1]} <span className="font-700 text-[#172033]">{attrs.values[1]}</span> · {attrs.keys[2]} <span className="font-700 text-[#172033]">{attrs.values[2]}</span>
                      </p>
                    )
                  })()}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        <button disabled={!complete} onClick={() => onNext(squad)}
          className={`w-full py-4 rounded-2xl font-display text-lg font-900 uppercase tracking-widest transition-all border-2 ${
            complete ? 'bg-[#D97706] text-[#FFFDF5] border-[#172033] active:scale-95' : 'bg-[#EFE7D2] text-[#8A7B5E] border-[#C9BFA6] cursor-not-allowed'
          }`} style={complete ? { boxShadow: '3px 3px 0 rgba(23,32,51,0.22)' } : {}}>
          {complete ? 'Confirmar elenco · 26/26' : `${selected.size}/26 selecionados`}
        </button>
      </div>
      <button
        onClick={() => setPresetOpen(true)}
        aria-label="Preencher elenco automaticamente"
        title="Montar elenco automático"
        className="absolute bottom-32 right-5 z-10 flex h-12 w-12 items-center justify-center rounded-full border-2 border-[#172033] bg-[#D97706] text-2xl text-[#FFFDF5] transition-transform active:scale-90"
        style={{ boxShadow: '3px 3px 0 rgba(23,32,51,0.24)' }}
      >
        <span aria-hidden="true" className="block leading-none -mt-0.5">✨</span>
      </button>
      {presetOpen && (
        <div
          onClick={() => setPresetOpen(false)}
          className="absolute inset-0 z-30 flex items-end justify-center bg-black/45 animate-fade-in">
          <div
            onClick={event => event.stopPropagation()}
            className="w-full rounded-t-2xl border-2 border-b-0 border-[#172033] bg-[#FFFDF5] p-5 pb-8"
            style={{ boxShadow: '0 -4px 0 rgba(23,32,51,0.25)' }}>
            <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-[#C9BFA6]"/>
            <p className="font-mono text-sm font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5 mb-3"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Montar elenco automaticamente</p>
            <div className="space-y-2">
              {presets.map(item => (
                <button key={item.label} onClick={() => { item.apply(); setPresetOpen(false) }}
                  className="w-full flex items-center justify-between rounded-xl border-2 border-[#C9BFA6] bg-[#FFFDF5] px-4 py-3 text-left active:scale-[0.98] transition-transform"
                  style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.10)' }}>
                  <div className="min-w-0">
                    <p className="font-display text-base font-800 uppercase text-[#172033]">{item.label}</p>
                    <p className="font-mono text-xs text-[#8A7B5E] mt-0.5">{item.hint}</p>
                  </div>
                  <span className="text-[#B8860B] text-lg shrink-0 ml-3">▶</span>
                </button>
              ))}
            </div>
            <p className="font-mono text-xs text-[#6B5B3E] mt-3 text-center">Você ainda pode personalizar os jogadores depois.</p>
          </div>
        </div>
      )}
    </div>
  )
}

// Um lado da chave durante o sorteio: só ganha nome quando a seleção sai do globo.
interface BracketSide { flag: string; name: string; ready: boolean }

// ── Chave do mata-mata ────────────────────────────────────────────────────────

// Em que confronto da fase está a seleção da usuária. No modo clássico as
// quartas saem da classificação dos grupos, então ela pode cair em qualquer
// posição — não dá para assumir a primeira.
function koIndexOf(ties: KnockoutTie[], teamName: string) {
  return ties.findIndex(tie => tie.home?.name === teamName || tie.away?.name === teamName)
}

// Em que ponto do torneio a chave está, do ponto de vista da seleção da usuária.
function koStageLabel(ko: Knockout, teamName: string) {
  if (ko.final.winner) return 'Torneio encerrado'
  if (koIndexOf(ko.sf, teamName) >= 0) return 'Semifinal'
  return 'Quartas de final'
}

// Um confronto da chave: duas linhas, uma por seleção. Quem avançou fica em
// âmbar e o lado ainda indefinido aparece apagado, como "A definir".
function TieCard({ tie, label, highlightName, emptyLabel = 'A definir' }: {
  tie: KnockoutTie; label: string; highlightName?: string; emptyLabel?: string
}) {
  const row = (side: PoolTeam|null, goals: number|null) => {
    const isWinner = Boolean(tie.winner) && tie.winner?.name === side?.name
    const isUser   = Boolean(side) && side?.name === highlightName
    return (
      <div className={`flex items-center gap-1 px-1.5 py-1 ${isWinner ? 'bg-[#FFF7E6]' : ''}`}>
        <span className="text-sm leading-none shrink-0">{side ? side.flag : '🎱'}</span>
        <span className={`flex-1 min-w-0 truncate font-display text-xs font-800 uppercase ${
          isWinner ? 'text-[#B8860B]' : !side ? 'text-[#8A7B5E]' : isUser ? 'text-[#B8860B]' : 'text-[#172033]'
        }`}>{side?.name ?? emptyLabel}</span>
        <span className={`font-mono text-xs font-700 shrink-0 ${isWinner ? 'text-[#B8860B]' : 'text-[#8A6D1F]'}`}>
          {goals ?? '–'}
        </span>
      </div>
    )
  }
  const isUserTie = tie.home?.name === highlightName || tie.away?.name === highlightName
  return (
    <div className={`w-[100px] shrink-0 rounded-lg border-2 overflow-hidden bg-[#FFFDF5] ${
      isUserTie ? 'border-[#B8860B]' : 'border-[#C9BFA6]'}`} style={isUserTie ? { boxShadow: '2px 2px 0 rgba(184,134,11,0.30)' } : {}}>
      <p className={`px-1.5 py-0.5 font-mono text-xs font-700 uppercase tracking-wider border-b-2 truncate ${
        isUserTie ? 'bg-[#FFF7E6] border-[#B8860B]/30 text-[#B8860B]' : 'bg-[#F6F1E5] border-[#E4DCC6] text-[#8A6D1F]'
      }`}>{label}</p>
      {row(tie.home, tie.homeGoals)}
      <div className="h-px bg-[#E4DCC6]"/>
      {row(tie.away, tie.awayGoals)}
    </div>
  )
}

// Cada confronto fica centralizado na sua faixa. É isso que faz o cartão encostar
// exatamente no meio das linhas de ligação da coluna vizinha.
function TieColumn({ ties, labels, highlightName, emptyLabel }: {
  ties: KnockoutTie[]; labels: string[]; highlightName?: string; emptyLabel?: string
}) {
  return (
    <div className="flex flex-col h-full shrink-0">
      {ties.map((tie, index) => (
        <div key={index} className="flex-1 flex items-center">
          <TieCard tie={tie} label={labels[index]} highlightName={highlightName} emptyLabel={emptyLabel}/>
        </div>
      ))}
    </div>
  )
}

// O "]" que liga cada dupla de confrontos ao confronto seguinte: entradas em 25%
// e 75% da célula e saída no meio.
function ConnectorColumn({ count }: { count: number }) {
  return (
    <div className="flex flex-col h-full w-5 shrink-0">
      {Array.from({ length: Math.floor(count / 2) }, (_, index) => (
        <div key={index} className="relative flex-1">
          <span className="absolute left-0 right-1/2 top-1/4 h-px bg-[#C9BFA6]"/>
          <span className="absolute left-0 right-1/2 top-3/4 h-px bg-[#C9BFA6]"/>
          <span className="absolute left-1/2 top-1/4 bottom-1/4 w-px bg-[#C9BFA6]"/>
          <span className="absolute left-1/2 right-0 top-1/2 h-px bg-[#C9BFA6]"/>
        </div>
      ))}
    </div>
  )
}

// A chave inteira: quartas à esquerda, semifinal no meio, final à direita. Nasce
// só com as quartas preenchidas e vai ganhando as fases seguintes conforme os
// jogos acontecem.
// `emptyLabel` vale só para as quartas — é a fase que se sorteia. Semifinal e
// final não são sorteadas: saem do resultado, então ficam sempre "A definir".
function BracketTree({ ko, highlightName, emptyLabel }: { ko: Knockout; highlightName: string; emptyLabel?: string }) {
  return (
    <div className="overflow-x-auto mb-4">
      <div className="flex items-stretch h-[380px] w-max">
        <TieColumn ties={ko.qf} highlightName={highlightName} emptyLabel={emptyLabel}
          labels={['Quartas 1','Quartas 2','Quartas 3','Quartas 4']}/>
        <ConnectorColumn count={ko.qf.length}/>
        <TieColumn ties={ko.sf} highlightName={highlightName} labels={['Semifinal 1','Semifinal 2']}/>
        <ConnectorColumn count={ko.sf.length}/>
        <TieColumn ties={[ko.final]} highlightName={highlightName} labels={['Final']}/>
      </div>
    </div>
  )
}

// "Brasil 🇧🇷  2 – 1  México 🇲🇽"
function tieLine(tie: KnockoutTie) {
  return `${tie.home?.name} ${tie.home?.flag}  ${tie.homeGoals} – ${tie.awayGoals}  ${tie.away?.name} ${tie.away?.flag}`
}

// Blocos de pódio, compartilhados pela tela de chaveamento e pela de eliminado.
function KnockoutSummary({ ko }: { ko: Knockout }) {
  if (!ko.third.winner && !ko.final.winner) return null
  return (
    <div className="space-y-2 mb-4">
      {ko.third.winner && (
        <div className="rounded-xl bg-[#FFFDF5] border-2 border-[#C9BFA6] px-4 py-3 animate-fade-in" style={{ boxShadow: '3px 3px 0 rgba(23,32,51,0.16)' }}>
          <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-widest mb-0.5">🥉 Disputa pelo 3º lugar</p>
          <p className="font-display text-sm font-800 uppercase text-[#172033]">{tieLine(ko.third)}</p>
        </div>
      )}
      {ko.final.winner && (
        <div className="rounded-xl bg-[#FFFDF5] border-2 border-[#C9BFA6] px-4 py-3 animate-fade-in" style={{ boxShadow: '3px 3px 0 rgba(23,32,51,0.16)' }}>
          <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-widest mb-0.5">🏆 Final</p>
          <p className="font-display text-sm font-800 uppercase text-[#172033]">{tieLine(ko.final)}</p>
        </div>
      )}
    </div>
  )
}

// ── Screen 3: Draw Setup (groups and bracket draw) ────────────────────────────
function DrawSetup({ team, mode, initialParticipants, onNext, onBack, onReset }: {
  team: TeamData
  mode: GameMode
  initialParticipants?: PoolTeam[]
  onNext: (b: DrawnBracket) => void
  onBack: () => void
  onReset: () => void
}) {
  const format: TournamentFormat = mode === 'quick' ? 8 : 16
  const [bState, setBState] = useState<'idle'|'drawing'|'done'>('idle')
  const [showInfo, setShowInfo] = useState(false)
  const [revealed, setRevealed] = useState<number[]>([])
  const [shuffled, setShuffled] = useState<PoolTeam[]>([])
  const participantCount = format
  const participants = initialParticipants ?? [
    { name: team.name, flag: team.flag },
    ...TEAMS.filter(item => item.name !== team.name).slice(0, participantCount - 1).map(item => ({ name: item.name, flag: item.flag })),
  ]
  const selectedPool = participants.filter(item => item.name !== team.name)

  const runDraw = () => {
    if (bState !== 'idle') return
    const selected = shuffle(selectedPool)
    setShuffled(selected)
    setRevealed([])
    setBState('drawing')
    selected.forEach((_, i) => setTimeout(() => {
      setRevealed(previous => [...previous, i])
      if (i === selected.length - 1) setBState('done')
    }, 180 + i * 80))
  }

  const bracket = makeDrawnBracket({ name: team.name, flag: team.flag }, shuffled, format)

  // Um lado da chave só ganha nome depois que a seleção sai do globo. A
  // seleção da usuária já entra preenchida, junto com o cabeça de chave.
  const drawSide = (item: PoolTeam): BracketSide => {
    if (item.name === team.name) return { flag: item.flag, name: item.name, ready: true }
    const index = shuffled.findIndex(candidate => candidate.name === item.name)
    return index >= 0 && revealed.includes(index)
      ? { flag: item.flag, name: item.name, ready: true }
      : { flag: '🎱', name: 'A sortear', ready: false }
  }

  // A chave do sorteio no mesmo formato da tela de chaveamento: cada lado mostra
  // "A sortear" até a seleção sair do globo, e a semi/final ficam por definir.
  // Antes de sortear a chave ainda nem existe, então só a seleção da usuária
  // (sempre o cabeça do Jogo 1) aparece preenchida.
  const drawKo: Knockout = {
    qf: Array.from({ length: 4 }, (_, index) => {
      const pair = bracket.qf[index] ?? []
      const ready = (item?: PoolTeam) => item && drawSide(item).ready ? item : null
      return { home: ready(pair[0]), away: ready(pair[1]), homeGoals: null, awayGoals: null, winner: null }
    }),
    sf: [emptyTie(), emptyTie()],
    third: emptyTie(),
    final: emptyTie(),
  }

  return (
    <div className="relative flex flex-col h-full animate-fade-in">
      <TopBar title="Sorteio do torneio" sub={mode === 'quick' ? 'Modo Rápido' : 'Modo Clássico'} onBack={onBack} onReset={onReset} />
      <div className="flex-1 overflow-y-auto px-5 py-4 retro-paper">
        <div className="rounded-2xl bg-[#FFFDF5] border-2 border-[#172033] p-4 mb-4 flex items-center gap-3" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.16)' }}>
          <div className="w-12 h-12 rounded-xl bg-[#EFE7D2] border border-[#C9BFA6] flex items-center justify-center text-2xl">{team.flag}</div>
          <div className="flex-1">
            <p className="font-mono text-xs text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Sua seleção</p>
            <p className="font-display text-xl font-900 uppercase text-[#172033]">{team.name}</p>
          </div>
        </div>
        {mode === 'normal' ? (
          <div className="grid grid-cols-2 gap-2.5 mb-4">
            {Array.from({ length: 4 }, (_, groupIndex) => {
              const groupStart = groupIndex * 4
              return (
                <div key={groupIndex} className="rounded-2xl border-2 border-[#C9BFA6] bg-[#FFFDF5] overflow-hidden" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.16)' }}>
                  <div className="px-3 py-2 bg-[#FFF7E6] border-b-2 border-[#C9BFA6]"><p className="font-mono text-sm font-700 text-[#8A6D1F] uppercase tracking-[0.12em]">Grupo {String.fromCharCode(65 + groupIndex)}</p></div>
                  <div className="p-2 space-y-1.5">
                    {Array.from({ length: 4 }, (_, slot) => {
                      const isHead = groupIndex === 0 && slot === 0
                      const index = groupStart + slot - 1
                      const item = isHead ? { name: team.name, flag: team.flag } : shuffled[index]
                      const visible = isHead || Boolean(item && revealed.includes(index))
                      return <div key={slot} className={`flex items-center gap-1.5 rounded-lg px-1.5 py-1.5 ${isHead ? 'bg-[#FFF7E6] border border-[#B8860B]' : 'bg-[#F6F1E5]'}`}><span className="text-base">{visible ? item?.flag : '🎱'}</span><span className="font-display text-xs font-800 uppercase text-[#172033] truncate">{visible ? item?.name : 'A sortear'}</span></div>
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="mb-4 animate-fade-in">
            {bState !== 'idle' && (
              <div className="flex items-center justify-between mb-3 px-1">
                <p className="font-mono text-sm font-700 text-[#172033] uppercase tracking-[0.24em]">Chave sorteada</p>
                <p className="font-mono text-xs text-[#8A7B5E]">{revealed.length}/{shuffled.length} sorteadas</p>
              </div>
            )}
            <BracketTree ko={drawKo} highlightName={team.name} emptyLabel="A sortear"/>
          </div>
        )}
      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 border-t-2 border-double border-[#C9BFA6] bg-[#F6F1E5]">
        {bState === 'idle' ? <button onClick={runDraw} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>Sortear {mode === 'quick' ? 'chave' : 'grupos'}</button> : bState === 'drawing' ? <button disabled className="w-full py-4 rounded-2xl bg-[#EFE7D2] text-[#8A7B5E] border-2 border-[#C9BFA6] font-display text-lg font-900 uppercase tracking-widest">Sorteando…</button> : <button onClick={() => onNext(bracket)} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>Ir para escalação</button>}
      </div>
      <button
        onClick={() => setShowInfo(true)}
        aria-label="Informações do formato do torneio"
        title="Informações do formato"
        className="absolute bottom-32 right-5 z-20 flex h-9 w-9 items-center justify-center rounded-full border-2 border-[#172033] bg-[#D97706] font-display text-base font-900 text-[#FFFDF5] transition-transform active:scale-90"
        style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.24)' }}
      >
        <span aria-hidden="true" className="block leading-none">i</span>
      </button>
      {showInfo && (
        <div
          onClick={() => setShowInfo(false)}
          className="absolute inset-0 z-30 flex items-end justify-center bg-black/45 px-4 pb-6 animate-fade-in">
          <div
            onClick={event => event.stopPropagation()}
            className="w-full rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] p-5" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>
            <p className="font-mono text-sm font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>
              {mode === 'quick' ? 'Mata-mata' : 'Fase de grupos'}
            </p>
            <p className="font-display text-2xl font-900 uppercase leading-tight text-[#172033] mt-2">
              {mode === 'quick' ? '8 seleções em jogo único' : '4 grupos de 4 seleções'}
            </p>
            <p className="font-mono text-sm leading-relaxed text-[#6B5B3E] mt-2">
              {mode === 'quick'
                ? 'Quartas, semifinal, disputa de 3º lugar e final. Empate vai direto para os pênaltis.'
                : 'As duas melhores de cada grupo avançam para as quartas. Empate no mata-mata vai direto para os pênaltis.'}
            </p>
            <button
              onClick={() => setShowInfo(false)}
              className="mt-4 w-full rounded-2xl bg-[#172033] py-3 font-display text-sm font-900 uppercase tracking-widest text-[#F6F1E5]" style={{ boxShadow:'2px 2px 0 rgba(23,32,51,0.20)' }}>
              Entendi
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function RoundOneSetup({ stadium, onDraw, onNext, onBack, onReset }: {
  stadium: Stadium|null
  onDraw: () => void
  onNext: () => void
  onBack: () => void
  onReset: () => void
}) {
  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar title="Rodada 1" sub="Sorteio do estádio" onBack={onBack} onReset={onReset}/>
      <div className="flex-1 px-5 py-5 retro-paper">
        <div className="rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] p-5 text-center" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.16)' }}>
          <div className="text-5xl mb-3">🏟️</div>
          <p className="font-mono text-sm font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center justify-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Estádio da primeira partida</p>
          {!stadium ? <><p className="font-display text-xl font-900 uppercase text-[#172033] mt-2">Onde será o jogo?</p><p className="font-mono text-sm text-[#6B5B3E] mt-1">Sorteie o estádio antes de montar a escalação.</p></> : <><p className="font-display text-2xl font-900 uppercase text-[#172033] mt-2">{stadium.name}</p><p className="font-mono text-sm text-[#6B5B3E] mt-1">{stadium.city} · {stadium.country} · {stadium.cap} lugares</p></>}
        </div>
      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 border-t-2 border-double border-[#C9BFA6] bg-[#F6F1E5]">{!stadium ? <button onClick={onDraw} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>Sortear estádio</button> : <button onClick={onNext} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>Continuar para o torneio</button>}</div>
    </div>
  )
}

// ── Screen 4: Group Stage ─────────────────────────────────────────────────────
function GroupStage({ bracket, team, currentMatchId, onPlayNext, onQuarterfinals, onBack, onReset }: {
  bracket: DrawnBracket
  team: TeamData
  currentMatchId: string | null
  onPlayNext: (match: GroupMatch) => void
  onQuarterfinals: () => void
  onBack: () => void
  onReset: () => void
}) {
  const userName = team.name
  const userGroup = bracket.groups.find(group => group.teams.some(item => item.name === userName))
  const userMatches = userGroup?.matches.filter(match => match.home.name === userName || match.away.name === userName) ?? []
  const nextMatch = userMatches.find(match => match.status === 'pending')
  const groupsComplete = bracket.groups.length > 0 && bracket.groups.every(group => group.matches.every(match => match.status === 'played'))
  const rankedGroups = rankGroups(bracket.groups)
  const [showTiebreak, setShowTiebreak] = useState(false)

  return (
    <div className="relative flex flex-col h-full animate-fade-in">
      <TopBar title="Fase de grupos" sub={`${FORMAT_LABELS[bracket.format]} · ${groupCount(bracket.format)} grupos de 4`} onBack={onBack} onReset={onReset}/>
      <div className="flex-1 overflow-y-auto px-5 py-4 retro-paper">
        {!groupsComplete && userGroup && (
          <div className="rounded-2xl border-2 border-[#B8860B] bg-[#FFFDF5] overflow-hidden mb-4" style={{ boxShadow:'2px 2px 0 rgba(184,134,11,0.35)' }}>
            <div className="px-3 py-2 bg-[#FFF7E6] border-b-2 border-[#C9BFA6] flex items-center justify-between">
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em]">Seu grupo · Grupo {userGroup.name}</p>
              <span className="font-mono text-xs text-[#8A7B5E]">{userMatches.filter(match => match.status === 'played').length}/3 partidas</span>
            </div>
            <div className="divide-y-2 divide-[#E4DCC6]">
              {userMatches.map((match, index) => (
                <div key={match.id} className="px-3 py-2.5 flex items-center gap-2">
                  <span className="font-mono text-xs text-[#8A7B5E] w-5">J{index + 1}</span>
                  <span className="flex-1 font-display text-sm font-800 uppercase text-[#172033] truncate">{groupMatchLabel(match)}</span>
                  {match.status === 'played' ? (
                    <span className="font-mono text-sm font-700 text-[#059669]">{match.homeGoals}–{match.awayGoals}</span>
                  ) : match.id === nextMatch?.id ? (
                    <span className="font-mono text-xs font-700 text-[#B8860B] uppercase">Próximo</span>
                  ) : (
                    <span className="font-mono text-xs text-[#8A6D1F] uppercase">Pendente</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mb-2">
          <p className="font-mono text-xs font-700 text-[#172033] uppercase tracking-[0.24em]">Classificação {groupsComplete ? 'final' : 'provisória'}</p>
        </div>
        {rankedGroups.map(group => (
          <div key={group.name} className="rounded-2xl border-2 border-[#C9BFA6] bg-[#FFFDF5] overflow-hidden mb-3" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.16)' }}>
            <div className="px-3 py-2 bg-[#FFF7E6] border-b-2 border-[#C9BFA6] flex items-center justify-between">
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em]">Grupo {group.name}</p>
              {group.name === userGroup?.name && (
                <span className="font-mono text-xs text-[#8A7B5E]">{userMatches.filter(match => match.status === 'played').length}/3 jogos seus</span>
              )}
            </div>
            {group.standings.map((standing, index) => {
              // Os dois primeiros de cada grupo vão às quartas, mas só depois da
              // fase de grupos encerrada a classificação é definitiva: a barra
              // verde e o selo "Classificado" só aparecem com todos os jogos feitos.
              const qualified = groupsComplete && index < 2
              const isUser = standing.team.name === userName
              // No fim da fase, a linha da usuária ganha o status em destaque:
              // verde se passou, vermelho se caiu.
              const eliminated = groupsComplete && isUser && !qualified
              return (
                <div key={standing.team.name} className={`flex items-center gap-2 pl-2.5 pr-3 py-2.5 border-b-2 border-[#E4DCC6] last:border-0 border-l-4 ${
                  qualified ? 'border-l-[#059669]' : eliminated ? 'border-l-[#B91C1C]' : 'border-l-transparent'
                } ${isUser && groupsComplete ? (qualified ? 'bg-[#EAF3EC]' : 'bg-[#F7EBEB]') : isUser ? 'bg-[#FFF7E6]' : qualified ? 'bg-[#EAF3EC]' : ''}`}>
                  <span className={`font-mono text-xs w-3 ${qualified ? 'text-[#059669] font-700' : eliminated ? 'text-[#B91C1C] font-700' : 'text-[#8A7B5E]'}`}>{index + 1}</span>
                  <span className="text-base">{standing.team.flag}</span>
                  <span className={`flex-1 font-display text-sm font-800 uppercase truncate ${isUser ? 'text-[#B8860B]' : 'text-[#172033]'}`}>{standing.team.name}</span>
                  {qualified && (
                    <span className="font-mono text-xs font-700 text-[#059669] uppercase tracking-wide shrink-0">Classificado</span>
                  )}
                  {eliminated && (
                    <span className="font-mono text-xs font-700 text-[#B91C1C] uppercase tracking-wide shrink-0">Eliminado</span>
                  )}
                  <span className="font-mono text-xs text-[#8A7B5E]">{standing.p}J</span>
                  <span className="font-mono text-xs text-[#8A7B5E]">{standing.w}V {standing.d}E {standing.l}D</span>
                  <span className="font-mono text-sm font-700 text-[#172033] w-5 text-right">{standing.pts}</span>
                </div>
              )
            })}
          </div>
        ))}

      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        {nextMatch && !groupsComplete ? (
          <button onClick={() => onPlayNext(nextMatch)} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest active:scale-95 transition-transform" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>
            Jogar próxima partida
          </button>
        ) : groupsComplete ? (
          <button onClick={onQuarterfinals} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest active:scale-95 transition-transform" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>
            Ver quartas de final
          </button>
        ) : (
          <div className="rounded-2xl border-2 border-[#059669] bg-[#EAF3EC] px-4 py-3 text-center">
            <p className="font-mono text-xs text-[#059669] uppercase tracking-widest">Processando classificação</p>
          </div>
        )}
      </div>
      <button
        onClick={() => setShowTiebreak(true)}
        aria-label="Critérios de desempate"
        title="Critérios de desempate"
        className="absolute bottom-32 right-5 z-20 flex h-11 w-11 items-center justify-center rounded-full border-2 border-[#172033] bg-[#D97706] font-display text-xl font-900 text-[#FFFDF5] transition-transform active:scale-90"
        style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.24)' }}>
        <span aria-hidden="true" className="block leading-none">i</span>
      </button>
      {showTiebreak && (
        <div
          onClick={() => setShowTiebreak(false)}
          className="absolute inset-0 z-30 flex items-end justify-center bg-black/45 px-4 pb-6 animate-fade-in">
          <div
            onClick={event => event.stopPropagation()}
            className="w-full rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] p-5" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>
            <p className="font-mono text-sm font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Critérios de desempate</p>
            <p className="font-display text-2xl font-900 uppercase leading-tight text-[#172033] mt-2">Quem passa na frente</p>
            <p className="font-mono text-sm text-[#6B5B3E] mt-2 leading-relaxed">Os 2 primeiros de cada grupo avançam para as quartas.</p>
            <div className="mt-3 space-y-1.5">
              {groupTieBreakers().map((criterion, index) => (
                <div key={criterion} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#FFF7E6] border border-[#B8860B] font-mono text-xs font-700 text-[#8A6D1F]">{index + 1}</span>
                  <span className="font-mono text-sm text-[#6B5B3E]">{criterion}</span>
                </div>
              ))}
            </div>
            <button
              onClick={() => setShowTiebreak(false)}
              className="mt-4 w-full rounded-2xl bg-[#172033] py-3 font-display text-sm font-900 uppercase tracking-widest text-[#F6F1E5]" style={{ boxShadow:'2px 2px 0 rgba(23,32,51,0.20)' }}>
              Entendi
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Screen 5: Tournament Bracket ─────────────────────────────────────────────
function TournamentBracket({ team, bracket, onAdvance, onSummary, onBack, onReset }: {
  team: TeamData; bracket: DrawnBracket
  onAdvance: () => void; onSummary: () => void
  onBack: () => void; onReset: () => void
}) {
  const ko = bracket.ko
  // A tela acompanha a fase atual da usuária: antes das quartas mostra o
  // confronto das quartas; depois, quando ela avança, o da semifinal.
  const inSf = koIndexOf(ko.sf, team.name) >= 0
  const stageTies = inSf ? ko.sf : ko.qf
  const userIndex = koIndexOf(stageTies, team.name)
  const userTie = userIndex >= 0 ? stageTies[userIndex] : null
  const rival = userTie ? (userTie.home?.name === team.name ? userTie.away : userTie.home) : null
  const stageLabel = koStageLabel(ko, team.name)

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar title="Chaveamento" sub={`${stageLabel} · ${FORMAT_LABELS[bracket.format]}`} onBack={onBack} onReset={onReset} />
      <div className="flex-1 overflow-y-auto px-4 py-4 retro-paper">
        <div className="flex items-center justify-between mb-3 px-1">
          <p className="font-mono text-xs font-700 text-[#172033] uppercase tracking-[0.24em]">{stageLabel}</p>
          <p className="font-mono text-xs text-[#8A7B5E] uppercase tracking-widest">{inSf ? ko.sf.length : ko.qf.length} jogos</p>
        </div>
        <BracketTree ko={ko} highlightName={team.name}/>
        <KnockoutSummary ko={ko}/>
        {rival && !ko.final.winner && (
          <div className="rounded-2xl bg-[#FFFDF5] border-2 border-[#B8860B] p-4" style={{ boxShadow:'2px 2px 0 rgba(184,134,11,0.35)' }}>
            <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] mb-2 flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Seu confronto</p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><span className="text-2xl">{team.flag}</span><p className="font-display text-sm font-800 uppercase text-[#172033]">{team.name}</p></div>
              <span className="font-display text-xl font-900 text-[#B8860B]">VS</span>
              <div className="flex items-center gap-2"><p className="font-display text-sm font-800 uppercase text-[#172033]">{rival.name}</p><span className="text-2xl">{rival.flag}</span></div>
            </div>
          </div>
        )}
      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        {/* Com o torneio encerrado não há próxima partida para escalar: o botão
            leva ao resumo da fase. */}
        {ko.final.winner ? (
          <button onClick={onSummary} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest active:scale-95 transition-transform" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>
            Ver resumo da fase
          </button>
        ) : (
          <button onClick={onAdvance} className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest active:scale-95 transition-transform" style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' }}>
            Avançar para a partida
          </button>
        )}
      </div>
    </div>
  )
}

// ── Screen 5: Pre-Match Lineup (fixed field) ──────────────────────────────────
function PreMatchLineup({ team, opponent, squad, stadium, phase, cards, lineup, formKey, onLineupChange, onFormKeyChange, onNext, onBack, onReset }: {
  team: TeamData; opponent: PoolTeam; squad: Player[]
  stadium: Stadium|null; phase: Phase
  cards: Record<number, CardStatus>
  lineup: (Player|null)[]
  formKey: FormKey
  onLineupChange: (next: (Player|null)[]) => void
  onFormKeyChange: (next: FormKey) => void
  onNext: () => void; onBack: () => void; onReset: () => void
}) {
  const effectiveSquad = squad.length ? squad : defaultSquad()
  const slots = FIELD_FORMATIONS[formKey]
  const sized: (Player|null)[] = slots.map((_, index) => lineup[index] ?? null)
  const [activeSlot, setActiveSlot] = useState<number|null>(null)

  const suspendedIds = new Set(effectiveSquad.filter(player => cards[player.id] === 'red').map(player => player.id))
  const yellowCardIds = new Set(effectiveSquad.filter(player => cards[player.id] === 'yellow').map(player => player.id))
  const availableSquad = effectiveSquad.filter(player => !suspendedIds.has(player.id))
  const selectedIds = new Set(sized.filter((player): player is Player => Boolean(player)).map(player => player.id))
  const selectedCount = sized.filter(Boolean).length

  const changeFormation = (next: FormKey) => {
    onFormKeyChange(next)
    onLineupChange(remapLineup(sized, FIELD_FORMATIONS[next]))
    setActiveSlot(null)
  }

  const cardFor = (player: Player|null) =>
    player && suspendedIds.has(player.id) ? 'red' : player && yellowCardIds.has(player.id) ? 'yellow' : null
  const eligiblePlayers = activeSlot === null ? [] : (() => {
    const cat = slots[activeSlot].cat
    return [
      ...availableSquad.filter(player => player.pos === cat && !selectedIds.has(player.id)),
      // Suspensos ficam na lista, no fim e sem poder escolher, para a ausência
      // deles não virar um mistério.
      ...effectiveSquad.filter(player => player.pos === cat && suspendedIds.has(player.id)),
    ].sort((a, b) =>
      (suspendedIds.has(a.id) ? 1 : 0) - (suspendedIds.has(b.id) ? 1 : 0) || b.rating - a.rating
    )
  })()

  const choosePlayer = (player: Player) => {
    if (activeSlot === null) return
    onLineupChange(sized.map((current, index) => index === activeSlot ? player : current))
    setActiveSlot(null)
  }

  // Sorteia um titular para cada posição do campo, sem repetir ninguém e sem
  // escalar quem está suspenso.
  const fillRandomLineup = () => {
    const used = new Set<number>()
    const drawn = slots.map(slot => {
      const candidates = availableSquad.filter(player => player.pos === slot.cat && !used.has(player.id))
      if (!candidates.length) return null
      const picked = candidates[Math.floor(Math.random() * candidates.length)]
      used.add(picked.id)
      return picked
    })
    onLineupChange(drawn)
    setActiveSlot(null)
  }

  const hasPreviousLineup = lineup.some(Boolean)

  return (
    <div className="relative flex flex-col h-full animate-fade-in">
      <TopBar title="Escalação" sub={hasPreviousLineup ? 'Ajuste a escalação' : 'Monte seus titulares'} onBack={onBack} onReset={onReset} />
      <div className="px-5 py-3 shrink-0 border-b-2 border-double border-[#C9BFA6] bg-[#F6F1E5]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2"><span className="text-xl">{team.flag}</span><p className="font-display text-base font-800 uppercase text-[#B8860B]">{team.name}</p></div>
          <div className="font-display text-lg font-900 text-[#172033]">VS</div>
          <div className="flex items-center gap-2"><p className="font-display text-base font-800 uppercase text-[#6B5B3E]">{opponent.name}</p><span className="text-xl">{opponent.flag}</span></div>
        </div>
        <div className="flex gap-1.5 justify-center mt-3">
          {(['4-4-2','4-3-3','3-5-2','4-2-3-1'] as FormKey[]).map(next => (
            <button key={next} onClick={() => changeFormation(next)} className={`shrink-0 rounded-full px-3 py-1.5 font-mono text-xs font-700 uppercase tracking-wider transition-all border-2 ${formKey === next ? 'bg-[#D97706] text-[#FFFDF5] border-[#172033]' : 'bg-[#FFFDF5] text-[#6B5B3E] border-[#C9BFA6]'}`}>
              {next}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3 retro-paper">
        <div className="rounded-2xl overflow-hidden border-2 border-[#172033]" style={{ background:'linear-gradient(180deg,#1d7a42 0%,#176b39 50%,#145b32 100%)', boxShadow:'3px 3px 0 rgba(23,32,51,0.16)' }}>
          <div className="relative" style={{ paddingBottom:'136%' }}>
            <svg className="absolute inset-0 w-full h-full opacity-55" viewBox="0 0 100 136" preserveAspectRatio="none">
              <rect x="4" y="4" width="92" height="128" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="0.6"/>
              <line x1="4" y1="68" x2="96" y2="68" stroke="rgba(255,255,255,0.28)" strokeWidth="0.5"/>
              <circle cx="50" cy="68" r="10" fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="0.5"/>
              <rect x="26" y="4" width="48" height="17" fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="0.5"/>
              <rect x="26" y="115" width="48" height="17" fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="0.5"/>
            </svg>
            {slots.map((slot, index) => {
              const player = sized[index]
              const card = cardFor(player)
              return <button key={`${slot.label}-${index}`} onClick={() => setActiveSlot(index)} className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center" style={{ left:`${slot.x}%`, top:`${slot.y}%` }}>
                <div className={`relative flex h-11 w-11 items-center justify-center rounded-full transition-all ${player ? 'border-2 border-[#172033] bg-[#D97706] shadow-[0_3px_9px_rgba(0,0,0,0.3)]' : 'border-2 border-dashed border-white/90 bg-white/10'}`}>
                  <span className={`font-display text-xs font-900 ${player ? 'text-[#FFFDF5]' : 'text-white'}`}>{slot.label}</span>
                  {card && (
                    <span className="absolute -right-2.5 -top-2.5 text-base leading-none drop-shadow-[0_1px_2px_rgba(0,0,0,0.45)]">
                      {card === 'red' ? '🟥' : '🟨'}
                    </span>
                  )}
                </div>
                {player && <span className="mt-1 max-w-[62px] truncate font-display text-xs font-800 uppercase text-white">{player.name}</span>}
              </button>
            })}
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between px-1">
          <p className="font-mono text-xs text-[#8A7B5E] uppercase tracking-widest">{hasPreviousLineup ? 'Toque para trocar quem quiser' : 'Toque em uma posição para escolher'}</p>
          <p className="font-mono text-xs font-700 text-[#059669]">{selectedCount} / 11</p>
        </div>
      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        <button disabled={selectedCount < 11} onClick={onNext} className={`w-full py-4 rounded-2xl font-display text-lg font-900 uppercase tracking-widest transition-all border-2 ${selectedCount === 11 ? 'bg-[#D97706] text-[#FFFDF5] border-[#172033] active:scale-95' : 'bg-[#EFE7D2] text-[#8A7B5E] border-[#C9BFA6] cursor-not-allowed'}`} style={selectedCount === 11 ? { boxShadow:'3px 3px 0 rgba(23,32,51,0.22)' } : undefined}>
          {selectedCount === 11 ? 'Simular partida' : `Escale ${11 - selectedCount} jogador${11 - selectedCount === 1 ? '' : 'es'}`}
        </button>
      </div>
      <button
        onClick={fillRandomLineup}
        aria-label="Escalar time aleatoriamente"
        title="Escalar time aleatoriamente"
        className="absolute bottom-32 right-5 z-20 flex h-12 w-12 items-center justify-center rounded-full border-2 border-[#172033] bg-[#D97706] text-2xl text-[#FFFDF5] transition-transform active:scale-90"
        style={{ boxShadow:'3px 3px 0 rgba(23,32,51,0.24)' }}>
        <span aria-hidden="true" className="block leading-none -mt-0.5">⚄</span>
      </button>
      {activeSlot !== null && (
        <div className="absolute inset-0 z-50">
          <div className="absolute inset-0 bg-black/45" onClick={() => setActiveSlot(null)} />
          <div className="absolute bottom-0 left-0 right-0 max-h-[65%] overflow-hidden rounded-t-3xl border-t-2 border-[#172033] bg-[#FFFDF5] shadow-2xl">
            <div className="flex justify-center pt-3"><div className="h-1 w-10 rounded-full bg-[#C9BFA6]" /></div>
            <div className="flex items-center justify-between border-b-2 border-double border-[#C9BFA6] px-5 py-3">
              <div><p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Escolha o jogador</p><p className="font-display text-lg font-900 uppercase text-[#172033]">Posição {slots[activeSlot].label}</p></div>
              <button onClick={() => setActiveSlot(null)} className="text-2xl text-[#8A7B5E]">×</button>
            </div>
            <div className="max-h-[45vh] overflow-y-auto px-5 py-3 pb-7">
              {eligiblePlayers.length === 0 ? <p className="py-8 text-center font-mono text-sm text-[#6B5B3E]">Nenhum jogador disponível para esta posição.</p> : eligiblePlayers.map(player => {
                const isSuspended = suspendedIds.has(player.id)
                const hasYellow   = yellowCardIds.has(player.id)
                return (
                  <button
                    key={player.id}
                    disabled={isSuspended}
                    onClick={() => choosePlayer(player)}
                    className={`mb-2 flex w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-left transition-all ${
                      isSuspended
                        ? 'border-[#E0B4B4] bg-[#F7EBEB] opacity-70 cursor-not-allowed'
                        : 'border-[#C9BFA6] bg-[#F6F1E5] active:scale-[0.98]'
                    }`}>
                    <span className={`flex-1 font-display text-sm font-800 uppercase ${isSuspended ? 'text-[#B0A488] line-through' : 'text-[#172033]'}`}>{player.name}</span>
                    {hasYellow && <span className="text-sm" title="Cartão amarelo">🟨</span>}
                    {isSuspended
                      ? <span className="font-mono text-xs uppercase tracking-widest text-[#B91C1C]">🟥 suspenso</span>
                      : <span className="flex items-center gap-1 shrink-0">
                          <span className="font-display text-sm font-800 text-[#8A6D1F]">{player.role}</span>
                          {secondaryRole(player.role) && <span className="font-mono text-[10px] text-[#8A7B5E]">({secondaryRole(player.role)})</span>}
                        </span>}
                    <span className="font-mono text-sm font-700" style={{ color: isSuspended ? '#B0A488' : rc(player.rating) }}>{player.rating}</span>
                    <span className="font-mono text-xs uppercase text-[#8A7B5E]">{player.era}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Screen 6: Match Result ────────────────────────────────────────────────────
// Narrativa da partida gerada a partir do placar exibido, para o placar parcial
// sempre bater com o final: um evento por gol, na ordem cronológica aproximada,
// e um amarelo para cada lado. Os artilheiros saem do elenco que entrou em
// campo; o adversário, sem elenco detalhado, é creditado pela posição.
function buildMatchEvents(teamGoals: number, opponentGoals: number, squad: Player[]): MatchEvent[] {
  const outfield = squad.filter(p => p.pos !== 'GK')
  const teamScorer = (i: number) => outfield.length ? outfield[(i * 3) % outfield.length].name : 'Atacante'
  const rivalScorer = (i: number) => ['Atacante', 'Meia', 'Volante'][i % 3]

  const goals: { side: 'team'|'rival'; minute: number }[] = []
  for (let i = 0; i < Math.max(teamGoals, opponentGoals); i++) {
    if (i < teamGoals)        goals.push({ side:'team',  minute: 12 + i * 15 + (i % 2) * 4 })
    if (i < opponentGoals)    goals.push({ side:'rival', minute: 22 + i * 18 + (i % 2) * 5 })
  }
  goals.sort((a, b) => a.minute - b.minute)

  const events: MatchEvent[] = []
  let t = 0, o = 0
  goals.forEach(g => {
    if (g.side === 'team') t++
    else o++
    events.push({
      min: g.minute,
      type: 'goal',
      team: g.side,
      player: g.side === 'team' ? teamScorer(t - 1) : rivalScorer(o - 1),
      score: `${t} – ${o}`,
    })
  })
  const final = `${t} – ${o}`
  events.push({ min: 62, type:'yellow', team:'team',  player: teamScorer(2),  score: final })
  events.push({ min: 68, type:'yellow', team:'rival', player: rivalScorer(2), score: final })
  return events.sort((a, b) => a.min - b.min)
}

function MatchResult({ team, opponent, phase, groupMatch, squad, onNext, onBack, onReset }: {
  team: TeamData
  opponent: PoolTeam
  phase: Phase
  groupMatch?: GroupMatch
  squad?: Player[]
  onNext: () => void
  onBack: () => void
  onReset: () => void
}) {
  const isGroupMatch = phase === 'group' && Boolean(groupMatch)
  const isSemiFinal = phase === 'sf'
  const isThirdPlace = phase === 'third'
  const resultLabel = isGroupMatch ? 'Fase de grupos'
    : isSemiFinal ? 'Semifinal'
    : isThirdPlace ? 'Disputa de 3º lugar'
    : 'Quartas de final'
  const groupScore = groupMatch ? groupMatchScore(groupMatch) : [2, 1]
  const teamIsHome = groupMatch?.home.name === team.name
  const teamGoals = isGroupMatch ? (teamIsHome ? groupScore[0] : groupScore[1]) : isSemiFinal ? 1 : 2
  const opponentGoals = isGroupMatch ? (teamIsHome ? groupScore[1] : groupScore[0]) : isSemiFinal ? 2 : 1
  const didWin = teamGoals > opponentGoals
  const didLose = teamGoals < opponentGoals
  // Estatísticas coerentes com o placar: em vitória o time domina o jogo; em
  // derrota, o domínio é do adversário; empate fica equilibrado.
  const stats = didWin
    ? [['14–8','CHUTES'],['62%–38%','POSSE'],['2.4–0.9','xG']]
    : didLose
      ? [['8–14','CHUTES'],['38%–62%','POSSE'],['0.9–2.4','xG']]
      : [['11–11','CHUTES'],['50%–50%','POSSE'],['1.4–1.4','xG']]
  const events = buildMatchEvents(teamGoals, opponentGoals, squad ?? [])

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar title="Fim de jogo" sub={`Resultado · ${resultLabel}`} onBack={onBack} onReset={onReset}/>

      <div className="px-5 py-5 shrink-0 border-b-2 border-double border-[#C9BFA6]"
        style={{background:`linear-gradient(180deg,rgba(${didWin ? '5,150,105' : didLose ? '185,28,28' : '184,134,11'},0.08) 0%,transparent 100%)`}}>
        <div className="flex justify-center mb-3">
          <span className={`font-mono text-xs font-700 uppercase tracking-[0.2em] px-3 py-1 rounded-full border-2 ${
            didWin ? 'border-[#059669] bg-[#EAF3EC] text-[#047857]'
            : didLose ? 'border-[#B91C1C] bg-[#F7EBEB] text-[#B91C1C]'
            : 'border-[#B8860B] bg-[#FFF7E6] text-[#8A6D1F]'
          }`}>
            {didWin ? 'Vitória' : didLose ? 'Derrota' : 'Empate'} · {resultLabel}
          </span>
        </div>
        <div className="flex items-center">
          <div className="flex-1 text-center">
            <span className="text-4xl">{team.flag}</span>
            <p className="font-display text-sm font-800 uppercase text-[#B8860B] mt-1">{team.name}</p>
          </div>
          <div className="flex-1 text-center">
            <div className="font-display text-6xl font-900 text-[#172033] leading-none">
              <span>{teamGoals}</span><span className="text-[#8A7B5E] mx-1 text-4xl">–</span><span className={didLose ? 'text-[#B91C1C]' : 'text-[#6B5B3E]'}>{opponentGoals}</span>
            </div>
            <p className="font-mono text-xs font-700 text-[#8A6D1F] tracking-[0.24em] mt-1">FIM DE JOGO</p>
          </div>
          <div className="flex-1 text-center">
            <span className="text-4xl">{opponent.flag}</span>
            <p className="font-display text-sm font-800 uppercase text-[#6B5B3E] mt-1">{opponent.name}</p>
          </div>
        </div>
        <div className="flex justify-center gap-4 mt-4 pt-4 border-t-2 border-[#E4DCC6]">
          {stats.map(([v,l])=>(
            <div key={l} className="text-center">
              <p className="font-mono text-xs font-700 text-[#8A7B5E] uppercase tracking-[0.12em]">{l}</p>
              <p className="font-display text-xs font-700 text-[#172033] mt-0.5">{v}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 retro-paper">
        <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] mb-4 flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Eventos da partida</p>
        <div className="relative">
          <div className="absolute left-[13px] top-0 bottom-0 w-px bg-[#E4DCC6]"/>
          <div className="space-y-3">
            {events.map((ev, i) => {
              const isBra = ev.team === 'team'
              const icon = ev.type==='goal'?'⚽':'🟨'
              return (
                <div key={i} className="flex gap-3 items-start">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 z-10 border-2 ${
                    ev.type==='goal' && isBra ? 'bg-[#EAF3EC] border-[#059669]' : 'bg-[#FFFDF5] border-[#C9BFA6]'
                  }`}>{icon}</div>
                  <div className={`flex-1 rounded-xl px-3 py-2.5 border-2 ${
                    ev.type==='goal' && isBra ? 'bg-[#EAF3EC] border-[#059669]'
                    : ev.type==='goal' ? 'bg-[#FFFDF5] border-[#C9BFA6]' : 'bg-transparent border-transparent'
                  }`}>
                    <div className="flex justify-between items-baseline">
                      <span className="font-display text-sm font-800 uppercase text-[#172033]">{ev.player}</span>
                      {ev.type==='goal' && <span className="font-mono text-xs text-[#B8860B] font-700">{ev.score}</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="font-mono text-xs text-[#8A7B5E]">{ev.min}'</span>
                      <span className="font-mono text-xs font-700" style={{color:isBra?'#059669':'#8A7B5E'}}>
                        {isBra?`${team.flag} ${team.name}`:`${opponent.flag} ${opponent.name}`}
                      </span>
                      <span className="font-mono text-xs text-[#8A7B5E] uppercase">{ev.type === 'goal' ? 'Gol' : 'Amarelo'}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        <button onClick={onNext}
          className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-800 uppercase tracking-widest active:scale-95 transition-transform"
          style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
          {isGroupMatch ? 'Voltar para a fase de grupos' : 'Ver resumo da fase'}
        </button>
      </div>
    </div>
  )
}

// ── Screen 7: Phase Overview ──────────────────────────────────────────────────
// Uma linha de placar do mata-mata: quem venceu em destaque, jogo da usuária em âmbar.
function ResultRow({ tie, highlightName }: { tie: KnockoutTie; highlightName: string }) {
  const isUserTie = tie.home?.name === highlightName || tie.away?.name === highlightName
  const end = (side: PoolTeam|null, align: 'left'|'right') => {
    const isWinner = Boolean(tie.winner) && tie.winner?.name === side?.name
    const flag = <span className={`text-lg shrink-0 ${isWinner ? '' : 'opacity-40'}`}>{side?.flag ?? '🎱'}</span>
    const name = <span className={`font-display text-sm font-800 uppercase truncate ${isWinner ? 'text-[#172033]' : 'text-[#8A7B5E]'}`}>{side?.name ?? 'A definir'}</span>
    return (
      <div className={`flex-1 flex items-center gap-1.5 min-w-0 ${align === 'right' ? 'justify-end' : ''}`}>
        {align === 'left' && flag}
        {name}
        {align === 'right' && flag}
      </div>
    )
  }
  return (
    <div className={`rounded-xl border-2 overflow-hidden ${isUserTie ? 'border-[#B8860B] bg-[#FFF7E6]' : 'border-[#C9BFA6] bg-[#FFFDF5]'}`}>
      {isUserTie && (
        <div className="px-3 py-0.5 bg-[#FFF7E6] border-b-2 border-[#C9BFA6]">
          <span className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em]">Seu jogo</span>
        </div>
      )}
      <div className="flex items-center gap-2 px-3 py-2.5">
        {end(tie.home, 'left')}
        <span className="font-mono text-sm font-700 text-[#172033] shrink-0">{tie.homeGoals ?? '-'} – {tie.awayGoals ?? '-'}</span>
        {end(tie.away, 'right')}
      </div>
    </div>
  )
}

// O jogo da usuária num confronto, já do ponto de vista dela: quem era o
// adversário e como terminou.
function tieForTeam(tie: KnockoutTie, teamName: string) {
  if (tie.home?.name !== teamName && tie.away?.name !== teamName) return null
  const isHome = tie.home?.name === teamName
  return {
    rival: (isHome ? tie.away : tie.home) as PoolTeam | null,
    goals:      (isHome ? tie.homeGoals : tie.awayGoals) ?? 0,
    rivalGoals: (isHome ? tie.awayGoals : tie.homeGoals) ?? 0,
    won:  tie.winner?.name === teamName,
    drew: false,
  }
}

// A campanha da usuária: os jogos de grupo (no modo clássico) e cada fase do
// mata-mata que ela disputou, na ordem em que aconteceram.
function userCampaign(bracket: DrawnBracket, teamName: string) {
  const ko = bracket.ko
  const fromGroup = bracket.groups
    .flatMap(group => group.matches)
    .filter(match => match.status === 'played' && (match.home.name === teamName || match.away.name === teamName))
    .map(match => {
      const isHome = match.home.name === teamName
      const goals      = (isHome ? match.homeGoals : match.awayGoals) ?? 0
      const rivalGoals = (isHome ? match.awayGoals : match.homeGoals) ?? 0
      return {
        label: 'Grupos',
        rival: (isHome ? match.away : match.home) as PoolTeam | null,
        goals, rivalGoals,
        won: goals > rivalGoals,
        drew: goals === rivalGoals,
      }
    })

  const fromKnockout = [
    { label: 'Quartas',    tie: ko.qf[koIndexOf(ko.qf, teamName)] },
    { label: 'Semifinal',  tie: ko.sf[koIndexOf(ko.sf, teamName)] },
    { label: '3º lugar',   tie: ko.third },
    { label: 'Final',      tie: ko.final },
  ].flatMap(entry => {
    const result = entry.tie ? tieForTeam(entry.tie, teamName) : null
    return result ? [{ label: entry.label, ...result }] : []
  })

  return [...fromGroup, ...fromKnockout]
}

// Fechamento do torneio: pódio, resultados de cada fase e prêmios individuais,
// tudo lido da chave já resolvida — nada de time fixo no código.
function PhaseOverview({ team, bracket, ctaLabel, onNext, onBack, onReset }: {
  team: TeamData; bracket: DrawnBracket
  ctaLabel?: string; onNext?: () => void
  onBack: () => void; onReset: () => void
}) {
  const ko = bracket.ko
  const champion = ko.final.winner
  const over = Boolean(champion)
  const [shared, setShared] = useState<'idle'|'copied'|'failed'>('idle')

  const rounds = [
    { label: 'Quartas de final',    ties: ko.qf },
    { label: 'Semifinais',          ties: ko.sf },
    { label: 'Disputa de 3º lugar', ties: [ko.third] },
    { label: 'Final',               ties: [ko.final] },
  ].filter(round => round.ties.some(tie => tie.winner))

  const podium = [
    { medal: '🥇', label: 'Campeão',      side: champion },
    { medal: '🥈', label: 'Vice-campeão', side: tieLoser(ko.final) },
    { medal: '🥉', label: '3º lugar',     side: ko.third.winner },
  ].filter((row): row is { medal: string; label: string; side: PoolTeam } => Boolean(row.side))

  const campaign = userCampaign(bracket, team.name)
  const record = campaign.reduce(
    (acc, game) => game.drew ? { ...acc, d: acc.d + 1 } : game.won ? { ...acc, w: acc.w + 1 } : { ...acc, l: acc.l + 1 },
    { w: 0, d: 0, l: 0 })

  // Até onde o torneio foi: é isso que o subtítulo anuncia.
  const sub = over ? 'Torneio encerrado'
    : ko.sf.every(tie => tie.winner) ? 'Semifinais concluídas'
    : 'Quartas de final concluídas'

  const shareLines = champion ? [
    '🏆 Copa América Histórica',
    `🥇 ${champion.flag} ${champion.name}`,
    `🥈 ${tieLoser(ko.final)?.flag ?? ''} ${tieLoser(ko.final)?.name ?? ''}`.trim(),
    `🥉 ${ko.third.winner?.flag ?? ''} ${ko.third.winner?.name ?? ''}`.trim(),
    '',
    `Minha campanha com ${team.flag} ${team.name} (${record.w}V ${record.d}E ${record.l}D):`,
    ...campaign.map(game => `• ${game.label} — ${game.goals}–${game.rivalGoals} ${game.rival?.flag ?? ''} ${game.rival?.name ?? ''}`.trim()),
  ] : []

  // Compartilha pelo menu do sistema quando existe (celular); se não houver, ou
  // se ela cancelar, copia o resumo em texto para a área de transferência.
  const handleShare = async () => {
    const text = shareLines.join('\n')
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Copa América Histórica', text })
        return
      } catch {
        // Cancelou o menu: segue para a cópia.
      }
    }
    try {
      await navigator.clipboard.writeText(text)
      setShared('copied')
    } catch {
      setShared('failed')
    }
    window.setTimeout(() => setShared('idle'), 2400)
  }

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar title="Resumo da fase" sub={`${sub} · ${FORMAT_LABELS[bracket.format]}`} onBack={onBack} onReset={onReset}/>

      <div className="flex-1 overflow-y-auto px-5 py-4 retro-paper">
        {/* Cartão do campeão: é ele que se compartilha, então fica no topo. */}
        {champion && (
          <div className="rounded-2xl overflow-hidden border-2 border-[#B8860B] mb-5 animate-slide-up"
            style={{background:'linear-gradient(135deg,rgba(184,134,11,0.18),rgba(184,134,11,0.05))',boxShadow:'3px 3px 0 rgba(184,134,11,0.35)'}}>
            <div className="px-5 py-5 text-center">
              <div className="text-5xl mb-2">🏆</div>
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em]">Campeão da Copa América</p>
              <div className="flex items-center justify-center gap-2 mt-2">
                <span className="text-3xl">{champion.flag}</span>
                <h2 className="font-display text-4xl font-900 uppercase text-[#B8860B] leading-none">{champion.name}</h2>
              </div>
              <p className="font-display text-sm text-[#6B5B3E] mt-1 uppercase">Melhor seleção histórica</p>
              <button onClick={handleShare}
                className="w-full mt-4 py-3 rounded-xl bg-[#172033] text-[#F6F1E5] border-2 border-[#172033] font-display text-sm font-800 uppercase tracking-widest active:scale-95 transition-transform"
                style={{boxShadow:'2px 2px 0 rgba(23,32,51,0.20)'}}>
                {shared === 'copied' ? '✓ Resumo copiado' : shared === 'failed' ? 'Não deu para copiar' : 'Compartilhar resultado'}
              </button>
            </div>
          </div>
        )}

        <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] mb-3 flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Pódio</p>
        <div className="rounded-2xl border-2 border-[#C9BFA6] bg-[#FFFDF5] overflow-hidden mb-5" style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
          {podium.map((row, index) => (
            <div key={row.label} className={`flex items-center gap-2.5 px-3 py-3 ${index ? 'border-t-2 border-[#E4DCC6]' : ''}`}>
              <span className="text-xl shrink-0">{row.medal}</span>
              <span className="text-lg shrink-0">{row.side.flag}</span>
              <span className="flex-1 min-w-0 truncate font-display text-sm font-800 uppercase text-[#172033]">{row.side.name}</span>
              <span className="font-mono text-xs text-[#8A7B5E] uppercase tracking-[0.12em] shrink-0">{row.label}</span>
            </div>
          ))}
        </div>

        {campaign.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-2">
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Sua campanha</p>
              <p className="font-mono text-xs font-700 text-[#6B5B3E] uppercase tracking-[0.12em]">{record.w}V {record.d}E {record.l}D</p>
            </div>
            <div className="rounded-2xl border-2 border-[#C9BFA6] bg-[#FFFDF5] overflow-hidden mb-5" style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
              {campaign.map((game, index) => (
                <div key={index} className={`flex items-center gap-2 px-3 py-2.5 ${index ? 'border-t-2 border-[#E4DCC6]' : ''}`}>
                  <span className={`font-mono text-xs font-700 w-3 text-center shrink-0 ${
                    game.drew ? 'text-[#8A7B5E]' : game.won ? 'text-[#059669]' : 'text-[#B91C1C]'}`}>
                    {game.drew ? 'E' : game.won ? 'V' : 'D'}
                  </span>
                  <span className="font-mono text-xs text-[#8A7B5E] uppercase tracking-[0.12em] w-[58px] shrink-0">{game.label}</span>
                  <span className="flex-1 min-w-0 truncate font-display text-sm font-700 uppercase text-[#6B5B3E]">{game.rival?.flag} {game.rival?.name ?? 'A definir'}</span>
                  <span className="font-mono text-sm font-700 text-[#172033] shrink-0">{game.goals}–{game.rivalGoals}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {rounds.map(round => (
          <div key={round.label} className="mb-5">
            <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] mb-2 flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>{round.label}</p>
            <div className="space-y-2">
              {round.ties.filter(tie => tie.winner).map((tie, index) => (
                <ResultRow key={index} tie={tie} highlightName={team.name}/>
              ))}
            </div>
          </div>
        ))}

      </div>

      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        {/* Entre fases o resumo continua o torneio; no fim dele, só resta recomeçar. */}
        {ctaLabel && onNext ? (
          <>
            <button onClick={onNext}
              className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-800 uppercase tracking-widest active:scale-95 transition-transform mb-2"
              style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
              {ctaLabel}
            </button>
            <button onClick={onReset}
              className="w-full py-3 rounded-2xl bg-[#FFFDF5] border-2 border-[#C9BFA6] font-display text-sm font-700 uppercase text-[#6B5B3E] active:scale-95 transition-transform">
              Novo torneio
            </button>
          </>
        ) : (
          <button onClick={onReset}
            className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-800 uppercase tracking-widest active:scale-95 transition-transform"
            style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
            Novo torneio
          </button>
        )}
      </div>
    </div>
  )
}

// ── Screen 8: Elimination ─────────────────────────────────────────────────────
function Elimination({ team, bracket, onPlayThird, onSimulateRest, onSeeResults, onBack, onReset }: {
  team: TeamData; bracket: DrawnBracket
  onPlayThird: () => void; onSimulateRest: () => void; onSeeResults: () => void
  onBack: () => void; onReset: () => void
}) {
  const ko = bracket.ko
  const sfTie = ko.sf[koIndexOf(ko.sf, team.name)]
  const teamIsHome = sfTie?.home?.name === team.name
  const teamGoals  = (teamIsHome ? sfTie?.homeGoals : sfTie?.awayGoals) ?? 1
  const rivalGoals = (teamIsHome ? sfTie?.awayGoals : sfTie?.homeGoals) ?? 2
  const rival   = teamIsHome ? sfTie?.away : sfTie?.home
  const champion = ko.final.winner
  // Prêmios derivados da campanha real do campeão no mata-mata: gols feitos e
  // sofridos nas fases que ele jogou — nada de craque inventado no código.
  const champTies = [ko.sf, [ko.final]].flat().filter(tie => tie.winner?.name === champion?.name)
  const champGoals = champTies.reduce((acc, tie) => acc + (tie.home?.name === champion?.name ? tie.homeGoals ?? 0 : tie.awayGoals ?? 0), 0)
  const champAgainst = champTies.reduce((acc, tie) => acc + (tie.home?.name === champion?.name ? tie.awayGoals ?? 0 : tie.homeGoals ?? 0), 0)
  const awards = [
    ['Artilheiro',     `${champGoals} ${champGoals === 1 ? 'gol' : 'gols'}`],
    ['Melhor goleiro', `${champAgainst} ${champAgainst === 1 ? 'sofrido' : 'sofridos'}`],
    ['Bola de ouro',   champion?.name ?? '—'],
  ]
  // Perder a semifinal não encerra o torneio: ainda há a disputa de 3º lugar,
  // que a usuária escolhe jogar ou deixar simular.
  const tournamentOver = Boolean(ko.third.winner)
  const inThird = ko.third.home?.name === team.name || ko.third.away?.name === team.name
  const thirdRival = inThird
    ? (ko.third.home?.name === team.name ? ko.third.away : ko.third.home)
    : null

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar title="Eliminado" sub={tournamentOver ? 'Semifinal · Torneio encerrado' : 'Semifinal · Disputa de 3º lugar'} onBack={onBack}/>

      {/* Defeat result */}
      <div className="px-5 py-5 shrink-0 border-b-2 border-[#C9BFA6]"
        style={{background:'linear-gradient(180deg,rgba(185,28,28,0.10) 0%,transparent 100%)'}}>
        <div className="flex items-center">
          <div className="flex-1 text-center opacity-60">
            <span className="text-4xl grayscale">{team.flag}</span>
            <p className="font-display text-sm font-800 uppercase text-[#8A7B5E] mt-1">{team.name}</p>
          </div>
          <div className="flex-1 text-center">
            <div className="font-display text-5xl font-900 leading-none">
              <span className="text-[#8A7B5E]">{teamGoals}</span>
              <span className="text-[#6B5B3E] mx-1 text-3xl">–</span>
              <span className="text-[#B91C1C]">{rivalGoals}</span>
            </div>
            <p className="font-mono text-xs font-700 text-[#6B5B3E] mt-1.5 tracking-widest">SEMIFINAL · ELIMINADO</p>
          </div>
          <div className="flex-1 text-center">
            <span className="text-4xl">{rival?.flag ?? '🎱'}</span>
            <p className="font-display text-sm font-800 uppercase text-[#172033] mt-1">{rival?.name ?? 'A definir'}</p>
          </div>
        </div>
        <p className="font-mono text-xs font-700 text-[#B91C1C] text-center mt-2">
          {rival ? `${rival.name} avançou para a final` : 'Torneio encerrado para a sua seleção'}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="flex items-center justify-between mb-3 px-1">
          <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Como ficou o chaveamento</p>
        </div>
        <BracketTree ko={ko} highlightName={team.name}/>
        <KnockoutSummary ko={ko}/>

        {/* O 3º lugar é da usuária e não se simula sozinho: ela entra em campo.
            A final, que não é dela, é resolvida quando esta partida termina. */}
        {!tournamentOver && (
          <div className="rounded-2xl border-2 border-[#C9BFA6] bg-[#FFFDF5] p-5 mb-4 animate-slide-up" style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
            <div className="flex items-start gap-3 mb-4">
              <div className="w-12 h-12 rounded-2xl bg-[#F6F1E5] border-2 border-[#C9BFA6] flex items-center justify-center text-2xl shrink-0">🥉</div>
              <div>
                <p className="font-display text-lg font-800 uppercase text-[#172033] leading-tight">Disputa pelo 3º lugar</p>
                <p className="font-mono text-xs text-[#6B5B3E] mt-1">
                  {inThird
                    ? `Você pega ${thirdRival?.name ?? 'o adversário'} na disputa pelo terceiro lugar. A final fica por conta da simulação.`
                    : 'Simule o restante do torneio para conhecer o campeão.'}
                </p>
              </div>
            </div>
            {inThird ? (
              <button onClick={onPlayThird}
                className="w-full py-3.5 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-base font-800 uppercase tracking-widest active:scale-95 transition-transform"
                style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
                Disputar o 3º lugar
              </button>
            ) : (
              <button onClick={onSimulateRest}
                className="w-full py-3.5 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-base font-800 uppercase tracking-widest active:scale-95 transition-transform"
                style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
                Simular o restante do torneio
              </button>
            )}
          </div>
        )}

        {/* Champion banner */}
        {tournamentOver && champion && (
          <div className="rounded-2xl overflow-hidden border-2 border-[#B8860B] mb-5 animate-slide-up"
            style={{background:'linear-gradient(135deg,rgba(184,134,11,0.18),rgba(184,134,11,0.05))',boxShadow:'3px 3px 0 rgba(184,134,11,0.35)'}}>
            <div className="px-5 py-5 text-center">
              <div className="text-5xl mb-2">🏆</div>
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em]">Campeão da Copa América</p>
              <div className="flex items-center justify-center gap-2 mt-2">
                <span className="text-3xl">{champion.flag}</span>
                <h2 className="font-display text-4xl font-900 uppercase text-[#B8860B] leading-none">{champion.name}</h2>
              </div>
              <p className="font-display text-sm text-[#6B5B3E] mt-1 uppercase">Melhor seleção histórica</p>
              <div className="mt-4 pt-4 border-t-2 border-[#E4DCC6] grid grid-cols-3 gap-3">
                {awards.map(([l,v])=>(
                  <div key={l} className="text-center">
                    <p className="font-mono text-xs text-[#8A7B5E] uppercase tracking-[0.12em]">{l}</p>
                    <p className="font-display text-sm font-700 text-[#172033] mt-0.5">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* New Tournament — prominent CTA */}
        <button onClick={onReset}
          className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-800 uppercase tracking-widest active:scale-95 transition-transform mb-2 pulse-gold"
          style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
          Novo torneio
        </button>
        <button onClick={onSeeResults}
          className="w-full py-3 rounded-2xl bg-[#FFFDF5] border-2 border-[#C9BFA6] font-display text-sm font-700 uppercase text-[#6B5B3E] active:scale-95 transition-transform">
          Ver resultados
        </button>
      </div>
    </div>
  )
}

// ── Screen 9: Home ─────────────────────────────────────────────────────────────
function HomeScreen({ onClassic, onQuick, onMultiplayer }: {
  onClassic: () => void
  onQuick: () => void
  onMultiplayer: () => void
}) {
  const tickets = [
    {
      onClick: onClassic, title: 'Modo clássico', desc: '16 seleções. Conquiste o continente.',
      bar: 'bg-[#D97706]', jogar: 'text-[#B45309]', border: 'border-[#D97706]', bg: 'bg-[#FFF7E6]',
    },
    {
      onClick: onQuick, title: 'Modo rápido', desc: '8 seleções. Mata-mata direto.',
      bar: 'bg-[#059669]', jogar: 'text-[#047857]', border: 'border-[#059669]', bg: 'bg-[#EAF8EF]',
    },
    {
      onClick: onMultiplayer, title: 'Multiplayer', desc: '1vs1. Quem escala melhor?',
      bar: 'bg-[#2563EB]', jogar: 'text-[#1D4ED8]', border: 'border-[#2563EB]', bg: 'bg-[#EAF3FF]',
    },
  ]

  return (
    <div className="flex flex-col h-full animate-fade-in overflow-hidden retro-paper">
      {/* Masthead — title + profile on one line */}
      <div className="px-5 pt-5 pb-3 shrink-0">
        <div className="stagger-up flex items-center justify-between gap-3">
          <h1 className="font-display text-[2.75rem] font-900 uppercase leading-[0.85] text-[#172033] min-w-0"
            style={{ textShadow: '2px 2px 0 rgba(184,134,11,0.20)' }}>
            Copa <span className="text-[#B8860B]">América</span>
          </h1>
          <div className="shrink-0 w-10 h-10 rounded-full border-2 border-[#B8860B] bg-[#FFFDF5] flex items-center justify-center"
            style={{ boxShadow: '2px 2px 0 rgba(23,32,51,0.14)' }}>
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-label="Perfil de usuário">
              <circle cx="12" cy="8" r="3.5" stroke="#B8860B" strokeWidth="2.2"/>
              <path d="M5 20c.8-3.4 3.2-5.2 7-5.2s6.2 1.8 7 5.2" stroke="#B8860B" strokeWidth="2.2" strokeLinecap="round"/>
            </svg>
          </div>
        </div>

        {/* Kicker */}
        <div className="stagger-up mt-2.5" style={{ animationDelay: '0.06s' }}>
          <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.16em] text-center flex items-center justify-center gap-2">
            <span className="text-[#B8860B]">◆</span>Campeonato das seleções históricas<span className="text-[#B8860B]">◆</span>
          </p>
        </div>
      </div>

      {/* Classic scoreboard */}
      <div className="px-5 pb-3 shrink-0 stagger-up" style={{ animationDelay: '0.12s' }}>
        <div className="rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] overflow-hidden"
          style={{ boxShadow: '3px 3px 0 rgba(23,32,51,0.16)' }}>
          <div className="px-4 py-2 bg-linear-to-b from-[#212A40] to-[#131B2C] flex items-center justify-between gap-2">
            <p className="font-mono text-xs font-700 text-[#F6F1E5] uppercase tracking-[0.18em]">Suas estatísticas</p>
            <p className="font-mono text-xs font-700 text-[#B8860B] uppercase tracking-[0.18em]">Temporada 2026</p>
          </div>
          <div className="h-0.5 bg-[#B8860B]"/>
          <div className="grid grid-cols-2 divide-x-2 divide-[#E4DCC6]">
            <div className="px-4 py-2.5 text-center">
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-widest">Single player</p>
              <p className="font-display text-4xl font-900 text-[#172033] leading-none mt-1">0</p>
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-widest mt-1">Vitórias</p>
            </div>
            <div className="px-4 py-2.5 text-center">
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-widest">Multiplayer</p>
              <p className="font-display text-4xl font-900 text-[#172033] leading-none mt-1">0</p>
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-widest mt-1">Vitórias</p>
            </div>
          </div>
        </div>
      </div>

      {/* Section title */}
      <div className="px-5 mb-2.5 shrink-0 stagger-up" style={{ animationDelay: '0.16s' }}>
        <div className="flex items-center gap-2.5">
          <span className="text-[#B8860B] text-sm leading-none">◆</span>
          <p className="font-mono text-xs font-700 text-[#172033] uppercase tracking-[0.2em]">Selecione seu modo de jogo</p>
          <span className="flex-1 border-t-2 border-double border-[#C9BFA6]"/>
        </div>
      </div>

      {/* Mode tickets */}
      <div className="flex-1 min-h-0 px-5 flex flex-col gap-3">
        {tickets.map((t, i) => (
          <button key={i} onClick={t.onClick}
            className={`stagger-up group flex-1 w-full text-left rounded-2xl border-2 ${t.border} ${t.bg} overflow-hidden flex flex-col active:scale-[0.98] transition-transform`}
            style={{ animationDelay: `${0.2 + i * 0.08}s`, boxShadow: '3px 3px 0 rgba(23,32,51,0.12)' }}>
            <div className={`h-2.5 ${t.bar} ticket-stripe shrink-0`}/>
            <div className="px-5 py-3 flex-1 flex flex-col justify-center">
              <p className="font-display text-2xl font-900 uppercase text-[#172033] leading-none">{t.title}</p>
              <p className="font-mono text-sm text-[#6B5B3E] mt-1.5 leading-snug">{t.desc}</p>
            </div>
            <div className="mx-5 border-t-2 border-dotted border-[#C9BFA6] py-2 flex justify-end shrink-0">
              <span className={`font-mono text-sm font-700 ${t.jogar} uppercase tracking-widest transition-transform duration-200 group-hover:translate-x-1`}>▶ Jogar</span>
            </div>
          </button>
        ))}
      </div>

      {/* Footer */}
      <div className="px-5 pb-5 pt-3 shrink-0 stagger-up" style={{ animationDelay: '0.44s' }}>
        <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.2em] text-center">Boa sorte, treinador!</p>
      </div>
    </div>
  )
}

// ── Screen 10: Multiplayer ────────────────────────────────────────────────────
function MultiplayerScreen({ onBack, onReset, onEnter }: {
  onBack: () => void; onReset: () => void
  onEnter: (room: { code: string; host: boolean }) => void
}) {
  const [step, setStep]     = useState<'menu'|'create'|'join'>('menu')
  const [code, setCode]     = useState('')
  const [typed, setTyped]   = useState('')
  const [shared, setShared] = useState<'idle'|'copied'|'failed'>('idle')

  const joinCode = typed.trim().toUpperCase()

  const startCreate = () => { setCode(makeRoomCode()); setShared('idle'); setStep('create') }
  const startJoin   = () => { setTyped(''); setShared('idle'); setStep('join') }

  // Compartilha pelo menu do sistema quando existe (celular); se não houver, ou
  // se ela cancelar, copia o link da sala para a área de transferência.
  const shareRoom = async () => {
    const url = `${window.location.origin}${window.location.pathname}?sala=${code}`
    const text = `Entra na minha sala da Copa América Histórica: ${url}`
    if (navigator.share) {
      try {
        await navigator.share({ title: 'Copa América — Sala', text })
        return
      } catch {
        // Cancelou o menu: segue para a cópia.
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setShared('copied')
    } catch {
      setShared('failed')
    }
    window.setTimeout(() => setShared('idle'), 2400)
  }
  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setShared('copied')
    } catch {
      setShared('failed')
    }
    window.setTimeout(() => setShared('idle'), 2400)
  }

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar title="Multiplayer" sub="Jogue com outra pessoa" onBack={step === 'menu' ? onBack : () => setStep('menu')} onReset={onReset}/>
      <div className="flex-1 overflow-y-auto px-5 py-5 retro-paper">

        {step === 'menu' && (
          <>
            <div className="rounded-2xl border-2 border-[#C9BFA6] bg-[#FFFDF5] p-5 text-center mb-4" style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
              <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center justify-center gap-1.5"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Modo multiplayer<span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/></p>
              <h2 className="font-display text-2xl font-900 uppercase text-[#172033] mt-1">Duelo 1 vs 1</h2>
              <p className="font-mono text-sm text-[#6B5B3E] leading-relaxed mt-2">Crie uma sala e mande o link, ou entre com o código que te passaram. Cada um escolhe a seleção, escala e joga.</p>
            </div>
            <div className="space-y-2.5">
              <button onClick={startCreate}
                className="w-full flex items-center justify-between gap-3 rounded-2xl border-2 border-[#172033] bg-[#D97706] px-4 py-4 text-left active:scale-[0.98] transition-transform"
                style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
                <div className="min-w-0">
                  <p className="font-display text-lg font-900 uppercase text-[#FFFDF5] leading-none">Criar sala</p>
                  <p className="font-mono text-xs text-[#FFFDF5] mt-1 opacity-80">Gera um código e um link para convidar</p>
                </div>
                <span className="text-[#FFFDF5] text-lg shrink-0">▶</span>
              </button>
              <button onClick={startJoin}
                className="w-full flex items-center justify-between gap-3 rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] px-4 py-4 text-left active:scale-[0.98] transition-transform"
                style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
                <div className="min-w-0">
                  <p className="font-display text-lg font-900 uppercase text-[#172033] leading-none">Entrar em sala</p>
                  <p className="font-mono text-xs text-[#6B5B3E] mt-1">Use o código ou a senha da sala</p>
                </div>
                <span className="text-[#B8860B] text-lg shrink-0">▶</span>
              </button>
            </div>
          </>
        )}

        {step === 'create' && (
          <>
            <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5 mb-3"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Sala criada</p>
            <div className="rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] p-5 text-center mb-4" style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
              <p className="font-mono text-xs text-[#8A6D1F] uppercase tracking-widest">Código da sala</p>
              <p className="font-display text-4xl font-900 uppercase text-[#172033] tracking-[0.3em] mt-2">{code}</p>
            </div>
            <div className="space-y-2.5">
              <button onClick={shareRoom}
                className="w-full py-3.5 rounded-2xl bg-[#2563EB] text-[#FFFDF5] border-2 border-[#172033] font-display text-sm font-800 uppercase tracking-widest active:scale-95 transition-transform"
                style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>
                {shared === 'copied' ? '✓ Link copiado' : shared === 'failed' ? 'Não deu para copiar' : 'Compartilhar link'}
              </button>
              <button onClick={copyCode}
                className="w-full py-3 rounded-2xl bg-[#FFFDF5] border-2 border-[#C9BFA6] font-display text-sm font-700 uppercase text-[#6B5B3E] active:scale-95 transition-transform">
                Copiar código
              </button>
            </div>
            <p className="font-mono text-xs text-[#8A7B5E] mt-3 text-center">Mande o link ou o código para o adversário entrar na sala.</p>
          </>
        )}

        {step === 'join' && (
          <>
            <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5 mb-3"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Entrar em sala</p>
            <div className="rounded-2xl border-2 border-[#172033] bg-[#FFFDF5] p-5 mb-4" style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
              <label className="font-mono text-xs text-[#8A6D1F] uppercase tracking-widest">Código ou senha</label>
              <input value={typed} onChange={event => setTyped(event.target.value.toUpperCase())} maxLength={6} placeholder="ABC123"
                className="w-full mt-2 bg-[#F6F1E5] border-2 border-[#172033] rounded-lg px-3 py-3 text-center font-display text-2xl font-900 uppercase tracking-[0.3em] text-[#172033] outline-none placeholder:text-[#C9BFA6]"/>
            </div>
            <p className="font-mono text-xs text-[#8A7B5E] text-center">Peça o código para quem criou a sala.</p>
          </>
        )}

      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        {step === 'menu' ? (
          <button onClick={onBack} className="w-full py-4 rounded-2xl bg-[#FFFDF5] border-2 border-[#C9BFA6] font-display text-lg font-800 uppercase text-[#6B5B3E] active:scale-95 transition-transform">Voltar aos modos</button>
        ) : step === 'create' ? (
          <button onClick={() => onEnter({ code, host: true })}
            className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-900 uppercase tracking-widest active:scale-95 transition-transform"
            style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>Escolher seleção</button>
        ) : (
          <button disabled={joinCode.length < 4} onClick={() => onEnter({ code: joinCode, host: false })}
            className={`w-full py-4 rounded-2xl font-display text-lg font-900 uppercase tracking-widest border-2 ${
              joinCode.length >= 4 ? 'bg-[#D97706] text-[#FFFDF5] border-[#172033] active:scale-95' : 'bg-[#EFE7D2] text-[#8A7B5E] border-[#C9BFA6]'
            }`} style={joinCode.length >= 4 ? {boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'} : {}}>
            Entrar na sala
          </button>
        )}
      </div>
    </div>
  )
}

// Resultado do duelo 1v1 e o placar acumulado da sala: dá para continuar jogando
// quantas vezes quiser, somando vitórias, empates e derrotas.
function MultiplayerMatch({ team, rival, match, score, room, onRematch, onLeave, onBack, onReset }: {
  team: TeamData; rival: PoolTeam
  match: { mine: number; rival: number }
  score: { w: number; d: number; l: number }
  room: { code: string; host: boolean } | null
  onRematch: () => void; onLeave: () => void
  onBack: () => void; onReset: () => void
}) {
  const didWin  = match.mine > match.rival
  const didDraw = match.mine === match.rival
  const outcome = didWin ? 'Vitória' : didDraw ? 'Empate' : 'Derrota'
  const played  = score.w + score.d + score.l
  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar title="Duelo 1v1" sub={room ? `Sala ${room.code} · Partida ${played}` : 'Primeira partida'} onBack={onBack} onReset={onReset}/>
      <div className="flex-1 overflow-y-auto retro-paper">
        <div className="px-5 py-5 border-b-2 border-double border-[#C9BFA6]"
          style={{background:`linear-gradient(180deg,rgba(${didWin ? '5,150,105' : didDraw ? '184,134,11' : '185,28,28'},0.08) 0%,transparent 100%)`}}>
          <div className="flex justify-center mb-3">
            <span className={`font-mono text-xs font-700 uppercase tracking-[0.2em] px-3 py-1 rounded-full border-2 ${
              didWin ? 'border-[#059669] bg-[#EAF3EC] text-[#047857]'
              : didDraw ? 'border-[#B8860B] bg-[#FFF7E6] text-[#8A6D1F]'
              : 'border-[#B91C1C] bg-[#F7EBEB] text-[#B91C1C]'
            }`}>{outcome}</span>
          </div>
          <div className="flex items-center">
            <div className="flex-1 text-center min-w-0">
              <span className="text-4xl">{team.flag}</span>
              <p className="font-display text-sm font-800 uppercase text-[#B8860B] mt-1 truncate">{team.name}</p>
            </div>
            <div className="flex-1 text-center">
              <div className="font-display text-6xl font-900 text-[#172033] leading-none">
                <span>{match.mine}</span><span className="text-[#8A7B5E] mx-1 text-4xl">–</span><span className={didWin ? 'text-[#6B5B3E]' : 'text-[#B91C1C]'}>{match.rival}</span>
              </div>
              <p className="font-mono text-xs font-700 text-[#8A6D1F] tracking-[0.24em] mt-1">FIM DA PARTIDA</p>
            </div>
            <div className="flex-1 text-center min-w-0">
              <span className="text-4xl">{rival.flag}</span>
              <p className="font-display text-sm font-800 uppercase text-[#6B5B3E] mt-1 truncate">{rival.name}</p>
            </div>
          </div>
        </div>

        <div className="px-5 py-5">
          <p className="font-mono text-xs font-700 text-[#8A6D1F] uppercase tracking-[0.12em] flex items-center gap-1.5 mb-3"><span className="w-1.5 h-1.5 bg-[#B8860B] rotate-45 shrink-0"/>Placar da sala</p>
          <div className="rounded-2xl border-2 border-[#C9BFA6] bg-[#FFFDF5] overflow-hidden" style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.16)'}}>
            <div className="grid grid-cols-3 divide-x-2 divide-[#E4DCC6] text-center">
              <div className="py-4"><p className="font-display text-4xl font-900 text-[#059669] leading-none">{score.w}</p><p className="font-mono text-xs text-[#8A7B5E] uppercase tracking-widest mt-1">Você</p></div>
              <div className="py-4"><p className="font-display text-4xl font-900 text-[#8A6D1F] leading-none">{score.d}</p><p className="font-mono text-xs text-[#8A7B5E] uppercase tracking-widest mt-1">Empates</p></div>
              <div className="py-4"><p className="font-display text-4xl font-900 text-[#B91C1C] leading-none">{score.l}</p><p className="font-mono text-xs text-[#8A7B5E] uppercase tracking-widest mt-1">Rival</p></div>
            </div>
          </div>
          <p className="font-mono text-xs text-[#6B5B3E] mt-3 text-center">Jogue quantas vezes quiser — o placar vai somando.</p>
        </div>
      </div>
      <div className="px-5 pb-8 pt-3 shrink-0 bg-[#F6F1E5] border-t-2 border-double border-[#C9BFA6]">
        <button onClick={onRematch}
          className="w-full py-4 rounded-2xl bg-[#D97706] text-[#FFFDF5] border-2 border-[#172033] font-display text-lg font-800 uppercase tracking-widest active:scale-95 transition-transform mb-2"
          style={{boxShadow:'3px 3px 0 rgba(23,32,51,0.22)'}}>Jogar novamente</button>
        <button onClick={onLeave}
          className="w-full py-3 rounded-2xl bg-[#FFFDF5] border-2 border-[#C9BFA6] font-display text-sm font-700 uppercase text-[#6B5B3E] active:scale-95 transition-transform">Sair da sala</button>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
const SCREEN_ORDER: Screen[] = [
  'home','team-selection','participant-selection','squad-builder','draw-setup','round-one','group-stage','bracket','pre-match','match-result','elimination','phase-overview','multiplayer'
]
// Telas do fluxo multiplayer: não entram na barra de progresso do torneio.
const MP_SCREENS: Screen[] = ['multiplayer','mp-team','mp-lineup','mp-match']

export default function App() {
  const [stack, setStack]       = useState<Screen[]>(['home'])
  const [team, setTeam]         = useState<TeamData>(TEAMS[0])
  const [lockedSquad, setLocked]= useState<Player[]>([])
  const [bracket, setBracket]   = useState<DrawnBracket|null>(null)
  const [stadium, setStadium]   = useState<Stadium|null>(null)
  const [phase, setPhase]       = useState<Phase>('qf')
  const [format, setFormat]     = useState<TournamentFormat>(8)
  const [gameMode, setGameMode] = useState<GameMode>('quick')
  const [selectedParticipants, setSelectedParticipants] = useState<PoolTeam[]|undefined>(undefined)
  const [currentGroupMatchId, setCurrentGroupMatchId] = useState<string|null>(null)
  // Escalação vive aqui para sobreviver de um jogo para o outro: a primeira
  // partida começa vazia e as seguintes herdam a anterior, só para ajustes.
  const [lineup, setLineup]   = useState<(Player|null)[]>([])
  const [formKey, setFormKey] = useState<FormKey>('4-4-2')
  const [cards, setCards]     = useState<Record<number, CardStatus>>({})
  const [matchesPlayed, setMatchesPlayed] = useState(0)
  // Estado da sala multiplayer: código, rival sorteado, escalação e o placar
  // acumulado que cresce a cada revanche.
  const [mpRoom, setMpRoom]     = useState<{ code: string; host: boolean }|null>(null)
  const [mpRival, setMpRival]   = useState<PoolTeam|null>(null)
  const [mpLineup, setMpLineup] = useState<(Player|null)[]>([])
  const [mpFormKey, setMpFormKey] = useState<FormKey>('4-4-2')
  const [mpScore, setMpScore]   = useState({ w: 0, d: 0, l: 0 })
  const [mpMatch, setMpMatch]   = useState<{ mine: number; rival: number }|null>(null)

  const currentGroupMatch = bracket && currentGroupMatchId
    ? bracket.groups.flatMap(group => group.matches).find(match => match.id === currentGroupMatchId)
    : undefined
  // Adversário do próximo jogo. No mata-mata ele sai do confronto da usuária na
  // fase atual — não dá para assumir as quartas de final 1, porque no modo
  // clássico a classificação pode colocá-la em qualquer posição da chave.
  const koTies  = bracket
    ? phase === 'sf' ? bracket.ko.sf
    : phase === 'third' ? [bracket.ko.third]
    : bracket.ko.qf
    : []
  const koTie   = koTies[koIndexOf(koTies, team.name)] ?? null
  const koRival = koTie ? (koTie.home?.name === team.name ? koTie.away : koTie.home) : null
  const currentOpponent: PoolTeam = currentGroupMatch
    ? (currentGroupMatch.home.name === team.name ? currentGroupMatch.away : currentGroupMatch.home)
    : koRival ?? { name:'Uruguai', flag:'🇺🇾' }

  // Para onde o resumo da fase leva depois de mostrar os resultados: a semifinal
  // se as quartas acabaram de ser jogadas, a disputa de 3º lugar depois da semi,
  // e nada se o torneio já terminou.
  const summaryCta = !bracket || bracket.ko.final.winner ? null
    : bracket.ko.sf.every(tie => tie.winner)
      ? { label: 'Disputar o 3º lugar', to: 'elimination' as Screen }
      : { label: 'Jogar a semifinal',  to: 'pre-match'   as Screen }

  const screen = stack[stack.length - 1]
  const idx    = SCREEN_ORDER.indexOf(screen)

  const nav    = (s: Screen) => setStack(prev => [...prev, s])
  const goBack = () => setStack(prev => prev.length > 1 ? prev.slice(0, -1) : prev)
  const reset  = () => {
    setStack(['home'])
    setTeam(TEAMS[0])
    setLocked([])
    setBracket(null)
    setStadium(null)
    setPhase('qf')
    setFormat(8)
    setGameMode('quick')
    setSelectedParticipants(undefined)
    setCurrentGroupMatchId(null)
    setLineup([])
    setFormKey('4-4-2')
    setCards({})
    setMatchesPlayed(0)
    setMpRoom(null)
    setMpRival(null)
    setMpLineup([])
    setMpFormKey('4-4-2')
    setMpScore({ w: 0, d: 0, l: 0 })
    setMpMatch(null)
  }

  // Sai da sala: volta ao menu do multiplayer e zera o estado da partida, mas
  // mantém a seleção escolhida à mão até o próximo reset geral.
  const leaveRoom = () => {
    setStack(['home', 'multiplayer'])
    setMpRoom(null)
    setMpRival(null)
    setMpLineup([])
    setMpFormKey('4-4-2')
    setMpScore({ w: 0, d: 0, l: 0 })
    setMpMatch(null)
  }

  // Resolve o duelo 1v1 no aparelho e já soma o resultado no placar da sala.
  const playMpMatch = () => {
    const mine   = lineupStrength(mpLineup, defaultSquad())
    const theirs = mpRival ? teamStrength(mpRival.name) : 85
    const result = simulateMpMatch(mine, theirs)
    setMpMatch(result)
    setMpScore(prev =>
      result.mine > result.rival ? { ...prev, w: prev.w + 1 }
      : result.mine < result.rival ? { ...prev, l: prev.l + 1 }
      : { ...prev, d: prev.d + 1 })
    nav('mp-match')
  }

  // Fecha a partida: registra os cartões da primeira partida, limpa da escalação
  // quem foi expulso e mantém o resto para a próxima escalação já vir preenchida.
  //
  // A narrativa do jogo nomeia Ronaldo 🟨 e Ronaldinho 🟥, mas esses dois podem
  // não estar no elenco montado. Por isso o cartão cai em quem realmente entrou
  // em campo — assim ele nunca some.
  const finishMatch = () => {
    if (matchesPlayed === 0) {
      const fielded = lineup.filter((player): player is Player => Boolean(player))
      const onField = fielded.length > 0 ? fielded : lockedSquad
      // Goleiro quase não leva cartão; se houver linha suficiente, sorteia entre
      // os jogadores de linha.
      const outfield = onField.filter(player => player.pos !== 'GK')
      const pool = outfield.length >= 2 ? outfield : onField

      const booked: Record<number, CardStatus> = {}
      const red = pool.find(player => FIRST_MATCH_CARDS[player.name] === 'red') ?? pool[pool.length - 1]
      if (red) booked[red.id] = 'red'
      const yellow = pool.find(player => FIRST_MATCH_CARDS[player.name] === 'yellow' && player.id !== red?.id)
        ?? pool.find(player => player.id !== red?.id)
      if (yellow) booked[yellow.id] = 'yellow'

      setCards(booked)
      setLineup(previous => previous.map(player => player && booked[player.id] === 'red' ? null : player))
    }
    setMatchesPlayed(count => count + 1)
  }

  return (
    <div className="readable-ui retro-shell flex items-center justify-center min-h-screen bg-[#E9EEF5]">
      <div className="relative flex flex-col overflow-hidden"
        style={{
          width:390, height:844,
          background:'#F5F7FA',
          borderRadius:42,
          boxShadow:'0 24px 60px rgba(23,32,51,0.22), 0 0 0 2px rgba(23,32,51,0.08)',
        }}>

        {/* Status bar */}
        <div className="flex items-center justify-between px-7 pt-3.5 pb-1 shrink-0 relative">
          <span className="font-mono text-sm text-[#64748B]">9:41</span>
          <div className="w-28 h-7 rounded-full bg-black absolute left-1/2 -translate-x-1/2 top-0"/>
          <div className="flex items-center gap-1">
            <span className="font-mono text-sm text-[#64748B]">●●●</span>
            <span className="font-mono text-sm text-[#64748B] ml-1">100%</span>
          </div>
        </div>

        {/* Progress bar */}
        {screen !== 'home' && !MP_SCREENS.includes(screen) && (
          <div className="flex gap-1 px-5 py-1.5 shrink-0">
            {SCREEN_ORDER.slice(1, 13).map((s, i) => (
              <div key={s} className={`flex-1 h-0.5 rounded-full transition-all duration-400 ${i <= Math.max(0, idx - 1) ? 'bg-[#B8860B]' : 'bg-[#C9BFA6]'}`}/>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-hidden">
          {screen === 'home' && (
            <HomeScreen
              onClassic={() => { setGameMode('normal'); setFormat(16); nav('team-selection') }}
              onQuick={() => { setGameMode('quick'); setFormat(8); nav('team-selection') }}
              onMultiplayer={() => nav('multiplayer')}/> 
          )}
          {screen === 'multiplayer' && (
            <MultiplayerScreen
              onBack={goBack}
              onReset={reset}
              onEnter={room => {
                setMpRoom(room)
                setMpLineup([])
                setMpMatch(null)
                setMpScore({ w: 0, d: 0, l: 0 })
                nav('mp-team')
              }}/>
          )}
          {/* Fluxo 1v1: escolhe a seleção, escala e joga — o rival entra com uma
              seleção sorteada pelo app. */}
          {screen === 'mp-team' && (
            <TeamSelection
              onNext={t => { setTeam(t); setMpRival(pickRivalTeam(t)); nav('mp-lineup') }}
              onBack={goBack}/>
          )}
          {screen === 'mp-lineup' && mpRival && (
            <PreMatchLineup
              team={team}
              opponent={mpRival}
              squad={[]}
              stadium={null}
              phase="qf"
              cards={{}}
              lineup={mpLineup}
              formKey={mpFormKey}
              onLineupChange={setMpLineup}
              onFormKeyChange={setMpFormKey}
              onNext={playMpMatch}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'mp-match' && mpRival && mpMatch && (
            <MultiplayerMatch
              team={team}
              rival={mpRival}
              match={mpMatch}
              score={mpScore}
              room={mpRoom}
              onRematch={() => setStack(['home', 'multiplayer', 'mp-team', 'mp-lineup'])}
              onLeave={leaveRoom}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'team-selection' && (
            <TeamSelection onNext={t => { setTeam(t); nav('squad-builder') }} onBack={goBack}/>
          )}
          {screen === 'participant-selection' && (
            <ParticipantSelection
              team={team}
              onNext={participants => { setSelectedParticipants(participants); nav('draw-setup') }}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'squad-builder' && (
            <SquadBuilder team={team} onNext={sq => { setLocked(sq); nav(gameMode === 'quick' ? 'participant-selection' : 'draw-setup') }} onBack={goBack} onReset={reset}/>
          )}
          {screen === 'draw-setup' && (
            <DrawSetup
              team={team}
              mode={gameMode}
              initialParticipants={gameMode === 'quick' ? selectedParticipants : undefined}
              onNext={b => {
                setBracket(b)
                setFormat(b.format)
                setStadium(STADIUMS[Math.floor(Math.random() * STADIUMS.length)])
                if (gameMode === 'quick') {
                  setPhase('qf')
                } else {
                  const first = b.groups.find(group => group.teams.some(item => item.name === team.name))?.matches.find(match => match.home.name === team.name || match.away.name === team.name)
                  setCurrentGroupMatchId(first?.id ?? null)
                  setPhase('group')
                }
                nav('pre-match')
              }}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'round-one' && bracket && (
            <RoundOneSetup
              stadium={stadium}
              onDraw={() => setStadium(STADIUMS[Math.floor(Math.random() * STADIUMS.length)])}
              onNext={() => nav(gameMode === 'quick' ? 'bracket' : 'group-stage')}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'group-stage' && bracket && (
            <GroupStage
              bracket={bracket}
              team={team}
              currentMatchId={currentGroupMatchId}
              onPlayNext={match => { setCurrentGroupMatchId(match.id); setPhase('group'); nav('pre-match') }}
              onQuarterfinals={() => { setPhase('qf'); nav('bracket') }}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'bracket' && bracket && (
            <TournamentBracket
              team={team}
              bracket={bracket}
              onAdvance={() => nav('pre-match')}
              onSummary={() => nav('phase-overview')}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'pre-match' && (
            <PreMatchLineup
              team={team}
              opponent={currentOpponent}
              squad={lockedSquad}
              stadium={stadium}
              phase={phase}
              cards={cards}
              lineup={lineup}
              formKey={formKey}
              onLineupChange={setLineup}
              onFormKeyChange={setFormKey}
              onNext={() => nav('match-result')}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'match-result' && bracket && (
            <MatchResult
              team={team}
              opponent={currentOpponent}
              groupMatch={phase === 'group' ? currentGroupMatch : undefined}
              phase={phase}
              squad={lockedSquad}
              onNext={() => {
                finishMatch()
                if (phase === 'group' && currentGroupMatchId) {
                  const match = bracket.groups.flatMap(group => group.matches).find(item => item.id === currentGroupMatchId)
                  if (match) {
                    const [homeGoals, awayGoals] = groupMatchScore(match)
                    const withCards = groupMatchCards(match)
                    const groups = bracket.groups.map(group => group.matches.some(item => item.id === match.id)
                      ? applyGroupResult(group, withCards, homeGoals, awayGoals)
                      : group)
                    const userGames = groups.flatMap(group => group.matches).filter(item => (item.home.name === team.name || item.away.name === team.name) && item.status === 'played').length
                    const nextBracket = userGames >= 3 ? completeGroupStage({ ...bracket, groups }) : { ...bracket, groups }
                    setBracket(nextBracket)
                    setCurrentGroupMatchId(null)
                    setPhase('group')
                    nav('group-stage')
                  }
                } else if (phase === 'sf' && koTie) {
                  // Cai na semifinal. A chave abre a final e a disputa de 3º
                  // lugar, mas nada é simulado: quem decide jogar é ela. A
                  // derrota leva direto à disputa de 3º lugar.
                  const settled = settleRound(bracket.ko, 'sf', koIndexOf(bracket.ko.sf, team.name),
                    decideTie(koTie, currentOpponent, 2, 1))
                  setBracket({ ...bracket, ko: settled })
                  setPhase('third')
                  nav('elimination')
                } else if (phase === 'third' && koTie) {
                  // Disputa de 3º lugar jogada. Só a final, que não é dela,
                  // fica por simular.
                  const third = decideTie(koTie, { name: team.name, flag: team.flag }, 2, 1)
                  setBracket({ ...bracket, ko: finishKnockout({ ...bracket.ko, third }) })
                  nav('phase-overview')
                } else if (koTie) {
                  // Vence a sua quarta e a chave inteira se resolve em volta
                  // disso. O chaveamento já mostra a semifinal preenchida, com o
                  // próximo confronto — é de lá que ela avança para a partida.
                  const settled = settleRound(bracket.ko, 'qf', koIndexOf(bracket.ko.qf, team.name),
                    decideTie(koTie, { name: team.name, flag: team.flag }, 2, 1))
                  setBracket({ ...bracket, ko: settled })
                  setPhase('sf')
                  nav('bracket')
                } else {
                  nav('elimination')
                }
              }}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'elimination' && bracket && (
            <Elimination
              team={team}
              bracket={bracket}
              onPlayThird={() => { setPhase('third'); nav('pre-match') }}
              // Sem entrar em campo: simula a disputa de 3º lugar e a final de
              // uma vez, e a tela passa a mostrar o campeão.
              onSimulateRest={() => setBracket({
                ...bracket,
                ko: finishKnockout({
                  ...bracket.ko,
                  third: simulateTie(bracket.ko.third),
                }),
              })}
              // "Ver resultados" abre o resumo do torneio, em vez de voltar para
              // o resultado da partida que ela acabou de ver.
              onSeeResults={() => nav('phase-overview')}
              onBack={goBack}
              onReset={reset}/>
          )}
          {screen === 'phase-overview' && bracket && (
            <PhaseOverview
              team={team}
              bracket={bracket}
              ctaLabel={summaryCta?.label}
              onNext={summaryCta ? () => nav(summaryCta.to) : undefined}
              onBack={goBack}
              onReset={reset}/>
          )}
        </div>
      </div>
    </div>
  )
}
