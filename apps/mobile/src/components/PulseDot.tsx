import React from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';

interface PulseDotProps {
  size?: number;
}

const PulseDot: React.FC<PulseDotProps> = ({ size = 7 }) => {
  const pulseAnim = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1800,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0,
          duration: 0,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, [pulseAnim]);

  const scale = pulseAnim.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [0.5, 2, 2.4],
  });

  const opacity = pulseAnim.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [0.9, 0.5, 0],
  });

  return (
    <View style={styles.container}>
      <View
        style={[
          styles.dot,
          {
            width: size,
            height: size,
            backgroundColor: Colors.safe,
            shadowColor: Colors.safe,
            shadowOffset: { width: 0, height: 0 },
            shadowOpacity: 1,
            shadowRadius: 6,
            elevation: 3,
          },
        ]}
      />
      <Animated.View
        style={[
          styles.ring,
          {
            width: size + 8,
            height: size + 8,
            borderColor: Colors.safe,
            transform: [{ scale }],
            opacity,
          },
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  dot: {
    borderRadius: 999,
  },
  ring: {
    position: 'absolute',
    borderRadius: 999,
    borderWidth: 1.5,
  },
});

export default PulseDot;
