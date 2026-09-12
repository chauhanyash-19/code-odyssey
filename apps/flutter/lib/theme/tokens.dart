import 'package:flutter/material.dart';

/// Exact tokens from index.html `:root` and component CSS.
class PgColors {
  static const bgPrimary = Color(0xFF021024);
  static const bgSecondary = Color(0xFF052659);
  static const accentBlue = Color(0xFF5483B3);
  static const mediumBlue = Color(0xFF7DA0CA);
  static const lightBlue = Color(0xFFC1E8FF);
  static const safe = Color(0xFF5EE1C4);
  static const warn = Color(0xFFF4C95D);
  static const crit = Color(0xFFFF5D6C);
  static const white = Color(0xFFFFFFFF);
  static const screenBottom = Color(0xFF010A18);

  static const glassBg = Color.fromRGBO(193, 232, 255, 0.05);
  static const glassBgStrong = Color.fromRGBO(193, 232, 255, 0.08);
  static const glassBorder = Color.fromRGBO(193, 232, 255, 0.14);

  static const screenGradient = [
    Color(0xFF5483B3),
    Color(0xFF052659),
    Color(0xFF021024),
    Color(0xFF010A18),
  ];

  static const primaryBtn = [Color(0xFFFF6B78), Color(0xFFFF4457)];
}

class PgRadii {
  static const glass = 22.0;
  static const pill = 999.0;
  static const nav = 26.0;
  static const icon = 10.0;
  static const bar = 4.0;
}

class PgSpace {
  static const screenH = 20.0;
  static const section = 28.0;
  static const titleGap = 14.0;
  static const navBottom = 120.0;
}
