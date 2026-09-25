package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.model.Confederation
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.RetroIconButton
import com.mc857.copaamerica.ui.components.RetroPrimaryButton

/** Mirrors TeamSelection, App.tsx:705-793. */
@Composable
fun TeamSelectionScreen(teams: List<TeamData>, onNext: (TeamData) -> Unit, onBack: () -> Unit) {
    var selectedId by remember { mutableStateOf<String?>(null) }
    var search by remember { mutableStateOf("") }
    var confFilter by remember { mutableStateOf<Confederation?>(null) }

    val filtered = teams.filter {
        it.name.contains(search, ignoreCase = true) && (confFilter == null || it.conf == confFilter)
    }
    val selectedTeam = teams.firstOrNull { it.id == selectedId }

    Column(Modifier.fillMaxSize().retroPaper()) {
        Row(Modifier.padding(20.dp).padding(bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            RetroIconButton(onClick = onBack) {
                Text("‹", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 20.sp, color = AppColors.ink)
            }
            Spacer(Modifier.width(12.dp))
            Text("MODOS DE JOGO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 1.sp, color = AppColors.kicker)
        }

        Column(Modifier.padding(horizontal = 20.dp).padding(top = 12.dp, bottom = 16.dp)) {
            KickerLabel("Copa América")
            Spacer(Modifier.height(4.dp))
            Row {
                Text("ESCOLHA SEU ", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 34.sp, color = AppColors.ink, lineHeight = 32.sp)
                Text("PAÍS", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 34.sp, color = AppColors.antiqueGold, lineHeight = 32.sp)
            }
            Spacer(Modifier.height(4.dp))
            Text("16 seleções disponíveis", fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText)
        }

        Box(
            Modifier
                .padding(horizontal = 20.dp)
                .padding(bottom = 12.dp)
                .fillMaxWidth()
                .background(AppColors.cream, RoundedCornerShape(12.dp))
                .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(12.dp)),
        ) {
            BasicTextField(
                value = search,
                onValueChange = { search = it },
                textStyle = TextStyle(fontFamily = monoFontFamily(), fontSize = 14.sp, color = AppColors.ink),
                singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
                decorationBox = { inner ->
                    if (search.isEmpty()) {
                        Text("Buscar seleções…", fontFamily = monoFontFamily(), fontSize = 14.sp, color = AppColors.mutedText)
                    }
                    inner()
                },
            )
        }

        Row(Modifier.padding(horizontal = 20.dp).padding(bottom = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val options = listOf<Confederation?>(null, Confederation.CONMEBOL, Confederation.CONCACAF)
            options.forEach { conf ->
                val active = confFilter == conf
                Box(
                    Modifier
                        .background(if (active) AppColors.ink else AppColors.cream, RoundedCornerShape(8.dp))
                        .border(BorderStroke(2.dp, if (active) AppColors.ink else AppColors.paperBorder), RoundedCornerShape(8.dp))
                        .clickable { confFilter = conf }
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                ) {
                    Text(
                        text = conf?.name ?: "TODAS",
                        fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 1.sp,
                        color = if (active) AppColors.paper else AppColors.bodyText,
                    )
                }
            }
        }

        LazyVerticalGrid(
            columns = GridCells.Fixed(4),
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(filtered, key = { it.id }) { team ->
                val isSel = team.id == selectedId
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(if (isSel) AppColors.ticketOrangeBg else AppColors.cream, RoundedCornerShape(14.dp))
                        .border(BorderStroke(2.dp, if (isSel) AppColors.antiqueGold else AppColors.paperBorder), RoundedCornerShape(14.dp))
                        .clickable { selectedId = team.id }
                        .padding(8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(team.flag, fontSize = 22.sp)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 11.sp,
                        color = AppColors.ink, textAlign = androidx.compose.ui.text.style.TextAlign.Center, maxLines = 2,
                    )
                    Text(
                        team.conf.name, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 9.sp, letterSpacing = 0.5.sp,
                        color = if (team.conf == Confederation.CONMEBOL) AppColors.kicker else AppColors.ticketBlue,
                    )
                }
            }
        }

        Column(Modifier.padding(20.dp)) {
            RetroPrimaryButton(
                text = if (selectedTeam != null) "Confirmar · ${selectedTeam.name}" else "Selecione uma seleção",
                enabled = selectedTeam != null,
                onClick = { selectedTeam?.let(onNext) },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}
