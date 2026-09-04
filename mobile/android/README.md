# Android platform folder

This tree was authored without the Flutter SDK on PATH, so the Gradle
project is not generated here.

From the parent `mobile/` directory:

    flutter create --org com.azieeliab --project-name azieltether .

That fills `android/` (and `ios/`) with the platform projects. Keep this
README or replace it; the generated Gradle tree is what Android Studio
opens.

Then:

    flutter pub get
    flutter run

Or open the generated `android/` folder in Android Studio.
Offline. No analytics. Application id: `com.azieeliab.azieltether`.
