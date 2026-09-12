import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../theme/tokens.dart';

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: PgSpace.titleGap),
      child: Row(
        children: [
          Container(
            width: 3,
            height: 14,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(2),
              gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [PgColors.lightBlue, PgColors.accentBlue],
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(text, style: PgTheme.display(size: 14, weight: FontWeight.w600)),
        ],
      ),
    );
  }
}
