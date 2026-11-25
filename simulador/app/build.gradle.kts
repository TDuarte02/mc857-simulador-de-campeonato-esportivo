plugins {
    alias(libs.plugins.androidApplication) apply false
    alias(libs.plugins.kotlinMultiplatform) apply false
    alias(libs.plugins.composeMultiplatform) apply false
    alias(libs.plugins.composeCompiler) apply false
    alias(libs.plugins.kotlinSerialization)
}
commonMain.dependencies { implementation(libs.ktor.client.core); implementation(libs.ktor.client.content.negotiation); implementation(libs.ktor.serialization.json); implementation(libs.kotlinx.serialization.json) }
androidMain.dependencies { implementation(libs.ktor.client.okhttp) }
iosMain.dependencies { implementation(libs.ktor.client.darwin) } (criar o source set com val iosMain by creating se ainda não existir)
wasmJsMain.dependencies { implementation(libs.ktor.client.js) }