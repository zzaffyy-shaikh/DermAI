import 'package:flutter/material.dart';

const kPatient = Color(0xFF2563EB);
const kDoctor = Color(0xFF0D9488);
const kAdmin = Color(0xFF7C3AED);
const kOk = Color(0xFF16A34A);
const kWarn = Color(0xFFEA580C);
const kErr = Color(0xFFDC2626);

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: kPatient);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: const Color(0xFFF1F5F9),
    inputDecorationTheme: const InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.all(Radius.circular(12)),
        borderSide: BorderSide(color: Color(0xFFE2E8F0)),
      ),
    ),
    cardTheme: CardTheme(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
      ),
    ),
  );
}

Color colorForMode(String mode) {
  switch (mode) {
    case 'normal':
      return kOk;
    case 'ood':
      return kWarn;
    case 'healthy':
      return kPatient;
    default:
      return Colors.grey;
  }
}
