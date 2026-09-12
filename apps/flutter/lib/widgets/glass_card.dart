import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/tokens.dart';

class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.margin,
    this.gradient,
  });

  final Widget child;
  final EdgeInsets padding;
  final EdgeInsets? margin;
  final Gradient? gradient;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(PgRadii.glass),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(84, 131, 179, 0.28),
            blurRadius: 32,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(PgRadii.glass),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              gradient: gradient,
              color: gradient == null ? PgColors.glassBg : null,
              borderRadius: BorderRadius.circular(PgRadii.glass),
              border: Border.all(color: PgColors.glassBorder),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}
