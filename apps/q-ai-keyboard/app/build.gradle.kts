plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ai.quangquy.qkeyboard"
    compileSdk = 35

    defaultConfig {
        applicationId = "ai.quangquy.qkeyboard"
        minSdk = 23
        targetSdk = 35
        versionCode = 4
        versionName = "0.4.0-alpha"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("com.google.mlkit:translate:17.0.3")
}
