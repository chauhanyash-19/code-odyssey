import React from 'react';
import { View, Text, StyleSheet, Animated, Dimensions } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';

const Waveform: React.FC<{ bars?: number; isLive?: boolean }> = ({ bars = 40, isLive = false }) => {
  const [barHeights] = React.useState(
    Array.from({ length: bars }).map(() => new Animated.Value(Math.random() * 20 + 3))
  );

  React.useEffect(() => {
    const interval = setInterval(() => {
      barHeights.forEach((bar) => {
        Animated.timing(bar, {
          toValue: isLive ? Math.random() * 34 + 3 : Math.random() * 20 + 3,
          duration: 130,
          useNativeDriver: false,
        }).start();
      });
    }, 130);

    return () => clearInterval(interval);
  }, [barHeights, isLive]);

  return (
    <View
      style={[
        styles.container,
        isLive && styles.liveContainer,
      ]}
    >
      {barHeights.map((height, idx) => (
        <Animated.View
          key={idx}
          style={[
            styles.bar,
            {
              height: height,
              width: isLive ? 3 : 3,
            },
          ]}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    gap: 3,
    height: 26,
    opacity: 0.55,
  },
  liveContainer: {
    height: 44,
    marginVertical: 18,
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderRadius: 14,
    backgroundColor: 'rgba(2, 16, 36, 0.4)',
    opacity: 1,
  },
  bar: {
    borderRadius: 2,
    backgroundColor: Colors.lightBlue,
  },
});

export default Waveform;
