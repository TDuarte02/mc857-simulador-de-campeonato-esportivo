package com.mc857.copaamerica.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.mc857.copaamerica.state.UiError
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.monoFontFamily
import kotlinx.coroutines.delay

/** A squad's flag, loaded from the URL the API sends. [url] null draws an empty slot. */
@Composable
fun FlagImage(url: String?, height: Dp, modifier: Modifier = Modifier, description: String? = null) {
    val shape = RoundedCornerShape(height / 8)
    val frame = modifier
        .size(width = height * 1.5f, height = height)
        .clip(shape)
        .background(AppColors.rowBorder)
        .border(BorderStroke(1.dp, AppColors.ink.copy(alpha = 0.18f)), shape)
    if (url == null) {
        Box(frame)
    } else {
        AsyncImage(model = url, contentDescription = description, modifier = frame, contentScale = ContentScale.Crop)
    }
}

/**
 * Covers the screen while a request runs (blocking taps) or after it failed.
 * The spinner only appears if the request takes a moment, to avoid flicker.
 */
@Composable
fun RequestOverlay(busy: Boolean, error: UiError?, onDismiss: () -> Unit, onRestart: () -> Unit) {
    if (busy) {
        var slow by remember { mutableStateOf(false) }
        LaunchedEffect(Unit) {
            delay(250)
            slow = true
        }
        Scrim(if (slow) Color.Black.copy(alpha = 0.35f) else Color.Transparent) {
            if (slow) {
                MessageCard {
                    CircularProgressIndicator(Modifier.size(32.dp), color = AppColors.antiqueGold)
                    Message("Falando com o servidor…")
                }
            }
        }
    } else if (error != null) {
        Scrim(Color.Black.copy(alpha = 0.45f)) {
            MessageCard {
                KickerLabel("Algo deu errado")
                Message(error.message)
                if (error.mustRestart) {
                    RetroPrimaryButton("Novo torneio", onClick = onRestart, modifier = Modifier.fillMaxWidth())
                } else {
                    error.retry?.let {
                        RetroPrimaryButton("Tentar novamente", onClick = it, modifier = Modifier.fillMaxWidth())
                    }
                    RetroSecondaryButton("Fechar", onClick = onDismiss, modifier = Modifier.fillMaxWidth())
                }
            }
        }
    }
}

@Composable
private fun Scrim(color: Color, content: @Composable () -> Unit) {
    Box(
        Modifier
            .fillMaxSize()
            .background(color)
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) {},
        contentAlignment = Alignment.Center,
    ) { content() }
}

@Composable
private fun MessageCard(content: @Composable () -> Unit) {
    Column(
        Modifier
            .padding(24.dp)
            .widthIn(max = 360.dp)
            .background(AppColors.cream, RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(16.dp))
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) { content() }
}

@Composable
private fun Message(text: String) {
    Text(
        text, fontFamily = monoFontFamily(), fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 19.sp,
        color = AppColors.bodyText, textAlign = TextAlign.Center,
    )
}
