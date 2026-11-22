package com.mc857.copaamerica.platform

import platform.UIKit.UIActivityViewController
import platform.UIKit.UIApplication

actual fun shareText(title: String, text: String) {
    val activityController = UIActivityViewController(listOf(text), null)
    val rootViewController = UIApplication.sharedApplication.keyWindow?.rootViewController
    rootViewController?.presentViewController(activityController, animated = true, completion = null)
}
