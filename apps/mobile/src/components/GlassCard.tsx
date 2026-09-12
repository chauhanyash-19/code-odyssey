import React from 'react';
import { View, StyleSheet } from 'react-native';
import { BlurView } from 'expo-blur';
import { Colors } from '../constants/Colors';

interface GlassCardProps {
  children: React.ReactNode;
  style?: any;
}

const GlassCard: React.FC<GlassCardProps> = ({ children, style }) => {
  return (
    <BlurView intensity={80} style={[styles.container, style]}>
      <View style={styles.card}>{children}</View>
    </BlurView>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 22,
    overflow: 'hidden',
  },
  card: {
    backgroundColor: Colors.glassBg,
    borderWidth: 1,
    borderColor: Colors.glassBorder,
    borderRadius: 22,
  },
});

export default GlassCard;
