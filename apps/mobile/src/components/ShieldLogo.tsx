import React from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Path, Circle, Defs, LinearGradient, Stop } from 'react-native-svg';
import { Colors } from '../constants/Colors';

interface ShieldLogoProps {
  size?: number;
}

const ShieldLogo: React.FC<ShieldLogoProps> = ({ size = 48 }) => {
  return (
    <Svg width={size} height={size} viewBox="0 0 48 48" fill="none">
      <Defs>
        <LinearGradient id="lg1" x1="8" y1="4" x2="40" y2="44">
          <Stop offset="0%" stopColor={Colors.lightBlue} />
          <Stop offset="100%" stopColor={Colors.accentBlue} />
        </LinearGradient>
      </Defs>
      <Path
        d="M24 4L40 10V22C40 32.6 33.4 40.9 24 44C14.6 40.9 8 32.6 8 22V10L24 4Z"
        fill="url(#lg1)"
        stroke={Colors.lightBlue}
        strokeWidth="1.5"
      />
      <Path
        d="M17 24L22 29L31 19"
        stroke={Colors.bgPrimary}
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
};

export default ShieldLogo;
