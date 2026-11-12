plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Notifications are switched on automatically once google-services.json is present
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
}

// ---- Change these when you release an update ----
val appVersionCode = (System.getenv("VERSION_CODE") ?: "1").toInt()
val appVersionName = System.getenv("VERSION_NAME") ?: "1.0.$appVersionCode"
val siteUrl = System.getenv("SITE_URL") ?: "https://salfa-bdaqiqa.vercel.app"

android {
    namespace = "com.salfa.bdaqiqa"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.salfa.bdaqiqa"
        minSdk = 24
        targetSdk = 35
        versionCode = appVersionCode
        versionName = appVersionName
        buildConfigField("String", "SITE_URL", "\"$siteUrl\"")
    }

    signingConfigs {
        create("release") {
            // A fixed key so every new APK installs as an update over the old one.
            // Secrets (if set in GitHub) override the key stored in the private repo.
            storeFile = file(System.getenv("KEYSTORE_PATH") ?: "salfa-release.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD") ?: "salfa-bdaqiqa-2026"
            keyAlias = System.getenv("KEY_ALIAS") ?: "salfa"
            keyPassword = System.getenv("KEY_PASSWORD") ?: "salfa-bdaqiqa-2026"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("release")
        }
    }

    buildFeatures { buildConfig = true }

    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-messaging")
}
