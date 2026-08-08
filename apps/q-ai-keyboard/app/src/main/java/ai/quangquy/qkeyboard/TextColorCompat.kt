package ai.quangquy.qkeyboard

import android.content.Context
import android.content.res.Configuration
import android.graphics.Color
import android.widget.TextView

/**
 * Keeps the programmatic Alpha 0.3 UI concise when TextView.apply { text = ... }
 * shadows MainActivity's foreground color property.
 *
 * Calls such as setTextColor(text) inside a TextView receiver resolve here because
 * the receiver's `text` is a CharSequence. Int-based calls continue to use the
 * Android TextView member function.
 */
fun TextView.setTextColor(ignoredTextValue: CharSequence) {
    val uiPrefs = context.getSharedPreferences("q_keyboard_ui", Context.MODE_PRIVATE)
    val mode = uiPrefs.getInt("theme_mode", 0) // 0 system, 1 light, 2 dark
    val systemDark = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) ==
        Configuration.UI_MODE_NIGHT_YES
    val dark = when (mode) {
        1 -> false
        2 -> true
        else -> systemDark
    }
    setTextColor(if (dark) Color.WHITE else Color.rgb(25, 25, 28))
}
