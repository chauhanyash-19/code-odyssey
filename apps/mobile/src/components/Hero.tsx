import React from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';
import ShieldLogo from './ShieldLogo';
import Waveform from './Waveform';

const Hero: React.FC = () => {
  const scaleAnim = React.useRef(new Animated.Value(1)).current;

  React.useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(scaleAnim, {
          toValue: 1.06,
          duration: 3000,
          useNativeDriver: true,
        }),
        Animated.timing(scaleAnim, {
          toValue: 1,
          duration: 3000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, [scaleAnim]);

  return (
    <View style={styles.container}>
      <View style={styles.visual}>
        <Animated.View style={[styles.ring, { transform: [{ scale: scaleAnim }] }]} />
        <ShieldLogo size={64} />
      </View>
      <Text style={styles.title}>Real-Time Scam Protection</Text>
      <Text style={styles.subtitle}>AI Voice Deepfake Detection • Live Call Analysis • India-First Security</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginBottom: 30,
  },
  visual: {
    width: 180,
    height: 180,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  ring: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(193, 232, 255, 0.25)',
  },
  title: {
    fontFamily: Fonts.display,
    fontSize: 24,
    fontWeight: '700',
    color: Colors.white,
    letterSpacing: -0.3,
    marginBottom: 10,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 12.5,
    color: Colors.mediumBlue,
    fontWeight: '500',
    letterSpacing: 0.2,
    lineHeight: 18,
    paddingHorizontal: 6,
    textAlign: 'center',
  },
});

export default Hero;
