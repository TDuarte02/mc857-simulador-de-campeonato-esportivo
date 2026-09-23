package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.theme.ticketStripe
import com.mc857.copaamerica.ui.components.KickerLabel

private data class ModeTicket(
    val title: String,
    val desc: String,
    val bar: Color,
    val bg: Color,
    val border: Color,
    val ctaColor: Color,
    val enabled: Boolean,
    val onClick: (() -> Unit)?,
)

/** Mirrors HomeScreen, App.tsx:2351-2454. */
@Composable
fun HomeScreen(onClassic: () -> Unit) {
    val tickets = listOf(
        ModeTicket(
            title = "Modo clássico", desc = "16 seleções. Conquiste o continente.",
            bar = AppColors.ticketOrange, bg = AppColors.ticketOrangeBg, border = AppColors.ticketOrange,
            ctaColor = AppColors.ticketOrangeText, enabled = true, onClick = onClassic,
        ),
        ModeTicket(
            title = "Modo rápido", desc = "8 seleções. Mata-mata direto.",
            bar = AppColors.ticketGreen, bg = AppColors.ticketGreenBg, border = AppColors.ticketGreen,
            ctaColor = AppColors.ticketGreenText, enabled = false, onClick = null,
        ),
        ModeTicket(
            title = "Multiplayer", desc = "1vs1. Quem escala melhor?",
            bar = AppColors.ticketBlue, bg = AppColors.ticketBlueBg, border = AppColors.ticketBlue,
            ctaColor = AppColors.ticketBlueText, enabled = false, onClick = null,
        ),
    )

    Column(Modifier.fillMaxSize().retroPaper()) {
        // Masthead
        Column(Modifier.padding(horizontal = 20.dp).padding(top = 20.dp, bottom = 12.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Row {
                    Text("COPA ", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 40.sp, color = AppColors.ink, lineHeight = 36.sp)
                    Text("AMÉRICA", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 40.sp, color = AppColors.antiqueGold, lineHeight = 36.sp)
                }
                Box(
                    Modifier
                        .size(40.dp)
                        .hardShadow(cornerRadius = 100.dp)
                        .background(AppColors.cream, CircleShape)
                        .border(BorderStroke(2.dp, AppColors.antiqueGold), CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("👤", fontSize = 16.sp)
                }
            }
            Spacer(Modifier.height(8.dp))
            KickerLabel(text = "Campeonato das seleções históricas", modifier = Modifier.fillMaxWidth(), color = AppColors.kicker)
        }

        // Stats scoreboard
        Column(
            Modifier
                .padding(horizontal = 20.dp)
                .padding(bottom = 12.dp)
                .fillMaxWidth()
                .hardShadow(cornerRadius = 16.dp)
                .background(AppColors.cream, RoundedCornerShape(16.dp))
                .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(16.dp)),
        ) {
            Row(
                Modifier.fillMaxWidth().background(AppColors.ink).padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("SUAS ESTATÍSTICAS", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.paper)
                Text("TEMPORADA 2026", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.antiqueGold)
            }
            Box(Modifier.fillMaxWidth().height(2.dp).background(AppColors.antiqueGold))
            Row(Modifier.fillMaxWidth()) {
                StatColumn("SINGLE PLAYER", Modifier.weight(1f))
                Box(Modifier.width(2.dp).height(70.dp).background(AppColors.rowBorder))
                StatColumn("MULTIPLAYER", Modifier.weight(1f))
            }
        }

        // Section label
        Row(
            Modifier.padding(horizontal = 20.dp).padding(bottom = 10.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            KickerLabel(text = "Selecione seu modo de jogo")
        }

        // Tickets
        Column(
            Modifier.weight(1f).padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            tickets.forEach { ticket -> ModeTicketCard(ticket, Modifier.weight(1f)) }
        }

        Column(Modifier.padding(20.dp)) {
            Text(
                "BOA SORTE, TREINADOR!",
                fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.5.sp,
                color = AppColors.kicker, modifier = Modifier.fillMaxWidth(), textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
        }
    }
}

@Composable
private fun StatColumn(label: String, modifier: Modifier) {
    Column(modifier.padding(vertical = 10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
        Text("0", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 34.sp, color = AppColors.ink)
        Text("VITÓRIAS", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
    }
}

@Composable
private fun ModeTicketCard(ticket: ModeTicket, modifier: Modifier) {
    val alpha = if (ticket.enabled) 1f else 0.55f
    Column(
        modifier = modifier
            .fillMaxWidth()
            .hardShadow(cornerRadius = 16.dp)
            .background(ticket.bg.copy(alpha = alpha.coerceAtLeast(0.85f)), RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, ticket.border.copy(alpha = alpha)), RoundedCornerShape(16.dp))
            .then(if (ticket.enabled) Modifier.clickable(onClick = ticket.onClick!!) else Modifier),
    ) {
        Box(Modifier.fillMaxWidth().height(10.dp).background(ticket.bar.copy(alpha = alpha), RoundedCornerShape(topStart = 14.dp, topEnd = 14.dp)).ticketStripe())
        Column(Modifier.weight(1f).padding(horizontal = 20.dp, vertical = 12.dp), verticalArrangement = Arrangement.Center) {
            Text(ticket.title.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 22.sp, color = AppColors.ink.copy(alpha = alpha.coerceAtLeast(0.8f)))
            Spacer(Modifier.height(4.dp))
            Text(ticket.desc, fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText.copy(alpha = alpha.coerceAtLeast(0.8f)))
        }
        Box(Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 10.dp), contentAlignment = Alignment.CenterEnd) {
            Text(
                text = if (ticket.enabled) "▶ JOGAR" else "EM BREVE",
                fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 1.sp,
                color = if (ticket.enabled) ticket.ctaColor else AppColors.mutedText,
            )
        }
    }
}
