import 'package:flutter/material.dart';

/// System light/dark with Aziel gold focus. No analytics.
const Color kMatteBlack = Color(0xFF12110E);
const Color kSurface = Color(0xFF1E1B16);
const Color kGold = Color(0xFFC9A227);
const Color kGoldDim = Color(0xFF8A7219);
const Color kIvory = Color(0xFFF4EFE6);
const Color kPaper = Color(0xFFF7F4EC);
const Color kInk = Color(0xFF1A1814);

ThemeData _base({
  required ColorScheme scheme,
  required Color scaffold,
  required Color field,
  required Color card,
}) {
  return ThemeData(
    useMaterial3: true,
    brightness: scheme.brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: scaffold,
    focusColor: kGold,
    appBarTheme: AppBarTheme(
      backgroundColor: scaffold,
      foregroundColor: scheme.onSurface,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: card,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0x59C9A227)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: field,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: kGold, width: 2),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: kGold,
        foregroundColor: kInk,
        minimumSize: const Size.fromHeight(48),
      ),
    ),
  );
}

ThemeData buildLightTheme() {
  const scheme = ColorScheme.light(
    primary: kGold,
    onPrimary: kInk,
    secondary: kGoldDim,
    onSecondary: kIvory,
    surface: Colors.white,
    onSurface: kInk,
    error: Color(0xFF9B2C2C),
    onError: Colors.white,
  );
  return _base(scheme: scheme, scaffold: kPaper, field: Colors.white, card: Colors.white);
}

ThemeData buildDarkTheme() {
  const scheme = ColorScheme.dark(
    primary: kGold,
    onPrimary: kMatteBlack,
    secondary: kGoldDim,
    onSecondary: kIvory,
    surface: kSurface,
    onSurface: kIvory,
    error: Color(0xFFF0B4AE),
    onError: kMatteBlack,
  );
  return _base(scheme: scheme, scaffold: kMatteBlack, field: const Color(0xFF16140F), card: kSurface);
}

/// Kept for callers that ask for one theme. Dark matches the previous default.
ThemeData buildAppTheme() => buildDarkTheme();
