package com.mc857.copaamerica.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.monoFontFamily

/** Mirrors the shared `TopBar` in App.tsx:670-702: back arrow, title/kicker, optional reset. */
@Composable
fun TopBar(
    title: String,
    sub: String? = null,
    onBack: (() -> Unit)? = null,
    onReset: (() -> Unit)? = null,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(AppColors.paper)
            .border(BorderStroke(2.dp, AppColors.paperBorder))
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (onBack != null) {
            RetroIconButton(onClick = onBack) {
                Text("‹", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 20.sp, color = AppColors.ink)
            }
            Spacer(Modifier.width(10.dp))
        }
        androidx.compose.foundation.layout.Column(Modifier.weight(1f)) {
            if (sub != null) {
                KickerLabel(text = sub)
                Spacer(Modifier.width(2.dp))
            }
            Text(
                text = title.uppercase(),
                fontFamily = displayFontFamily(),
                fontWeight = FontWeight.Black,
                fontSize = 24.sp,
                color = AppColors.ink,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (onReset != null) {
            Row(
                modifier = Modifier
                    .background(AppColors.cream, RoundedCornerShape(8.dp))
                    .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(8.dp))
                    .clickable(onClick = onReset)
                    .padding(horizontal = 10.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("↺", color = AppColors.kicker, fontSize = 14.sp)
                Text(
                    "Novo",
                    fontFamily = monoFontFamily(),
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp,
                    letterSpacing = 1.sp,
                    color = AppColors.kicker,
                )
            }
        }
    }
}
