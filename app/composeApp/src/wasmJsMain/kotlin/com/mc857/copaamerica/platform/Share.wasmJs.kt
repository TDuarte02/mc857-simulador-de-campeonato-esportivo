package com.mc857.copaamerica.platform

actual fun shareText(title: String, text: String) = browserShare(title, text)

/** Web Share API where available (mobile browsers), clipboard otherwise. */
private fun browserShare(title: String, text: String): Unit = js(
    """{
        if (navigator.share) {
            navigator.share({ title: title, text: text }).catch(function () {});
        } else if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(function () { alert('Resultado copiado!'); });
        }
    }"""
)
