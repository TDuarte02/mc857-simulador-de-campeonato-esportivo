package com.mc857.copaamerica.domain.data

import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.SlotCat.DEF
import com.mc857.copaamerica.domain.model.SlotCat.FW
import com.mc857.copaamerica.domain.model.SlotCat.GK
import com.mc857.copaamerica.domain.model.SlotCat.MID
import com.mc857.copaamerica.domain.model.SlotRole.CA
import com.mc857.copaamerica.domain.model.SlotRole.GOL
import com.mc857.copaamerica.domain.model.SlotRole.LD
import com.mc857.copaamerica.domain.model.SlotRole.LE
import com.mc857.copaamerica.domain.model.SlotRole.MC
import com.mc857.copaamerica.domain.model.SlotRole.MEI
import com.mc857.copaamerica.domain.model.SlotRole.PD
import com.mc857.copaamerica.domain.model.SlotRole.PE
import com.mc857.copaamerica.domain.model.SlotRole.VOL
import com.mc857.copaamerica.domain.model.SlotRole.ZAG

/** 52-player historic pool, mirroring design/src/App.tsx:103-160. */
val MOCK_PLAYER_POOL: List<Player> = listOf(
    // GKs (6)
    Player(1, "Gilmar", 91, "1950–66", GK, GOL),
    Player(2, "Taffarel", 89, "1988–98", GK, GOL),
    Player(3, "Marcos", 84, "1990–06", GK, GOL),
    Player(4, "Dida", 87, "1995–06", GK, GOL),
    Player(5, "Cássio", 82, "2011–23", GK, GOL),
    Player(6, "Weverton", 81, "2015–22", GK, GOL),
    // DEFs (14)
    Player(7, "Cafu", 93, "1990–06", DEF, LD),
    Player(8, "Roberto Carlos", 94, "1992–06", DEF, LE),
    Player(9, "Lúcio", 90, "2000–10", DEF, ZAG),
    Player(10, "Aldair", 88, "1989–02", DEF, ZAG),
    Player(11, "Júnior", 87, "1979–88", DEF, LE),
    Player(12, "Carlos Alberto", 92, "1964–77", DEF, LD),
    Player(13, "Bellini", 85, "1952–66", DEF, ZAG),
    Player(14, "Thiago Silva", 91, "2008–21", DEF, ZAG),
    Player(15, "Maicon", 89, "2003–14", DEF, LD),
    Player(16, "David Luiz", 86, "2010–21", DEF, ZAG),
    Player(17, "Marcelo", 88, "2006–18", DEF, LE),
    Player(18, "Djalma Santos", 90, "1952–68", DEF, LD),
    Player(19, "Nilton Santos", 91, "1949–64", DEF, LE),
    Player(20, "Roque Júnior", 84, "1999–06", DEF, ZAG),
    // MIDs (16)
    Player(21, "Zico", 97, "1976–88", MID, MEI),
    Player(22, "Sócrates", 93, "1979–86", MID, MC),
    Player(23, "Falcão", 93, "1976–86", MID, VOL),
    Player(24, "Rivaldo", 95, "1993–06", MID, MEI),
    Player(25, "Gerson", 91, "1961–72", MID, MC),
    Player(26, "Kaká", 93, "2002–13", MID, MEI),
    Player(27, "Didi", 92, "1952–66", MID, MC),
    Player(28, "Clodoaldo", 87, "1969–74", MID, VOL),
    Player(29, "Rivelino", 93, "1965–78", MID, MEI),
    Player(30, "Cerezo", 88, "1978–88", MID, MC),
    Player(31, "Oscar", 85, "2011–16", MID, MEI),
    Player(32, "Lucas Paquetá", 84, "2018–", MID, MEI),
    Player(33, "Serginho", 84, "1974–82", MID, MEI),
    Player(34, "Jorginho", 83, "1983–92", MID, VOL),
    Player(35, "Leandro", 83, "1979–88", MID, LD),
    Player(36, "Nené", 82, "1972–78", MID, MEI),
    // FWs (16)
    Player(37, "Pelé", 99, "1957–71", FW, CA),
    Player(38, "Ronaldo", 98, "1994–06", FW, CA),
    Player(39, "Ronaldinho", 97, "1999–10", FW, PE),
    Player(40, "Garrincha", 97, "1955–66", FW, PD),
    Player(41, "Romário", 96, "1987–98", FW, CA),
    Player(42, "Jairzinho", 93, "1964–74", FW, PD),
    Player(43, "Neymar", 93, "2010–23", FW, PE),
    Player(44, "Tostão", 91, "1966–72", FW, CA),
    Player(45, "Leônidas", 91, "1932–46", FW, CA),
    Player(46, "Bebeto", 90, "1985–98", FW, CA),
    Player(47, "Vavá", 89, "1952–62", FW, CA),
    Player(48, "Careca", 88, "1982–92", FW, CA),
    Player(49, "Ademir", 88, "1945–53", FW, CA),
    Player(50, "Dadá Maravilha", 85, "1965–76", FW, CA),
    Player(51, "Robinho", 84, "2003–14", FW, PE),
    Player(52, "Élber", 83, "1994–04", FW, CA),
)

/** Cards booked in the user's first match, mirroring FIRST_MATCH_CARDS (App.tsx:21-24). */
val FIRST_MATCH_CARDS: Map<String, com.mc857.copaamerica.domain.model.CardStatus> = mapOf(
    "Ronaldo" to com.mc857.copaamerica.domain.model.CardStatus.YELLOW,
    "Ronaldinho" to com.mc857.copaamerica.domain.model.CardStatus.RED,
)
