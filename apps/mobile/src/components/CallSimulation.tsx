import React from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';
import GlassCard from './GlassCard';
import Svg, { Path, Circle, Line } from 'react-native-svg';
import Waveform from './Waveform';

const CallSimulation: React.FC = () => {
  const needleRotation = React.useRef(new Animated.Value(-95)).current;

  React.useEffect(() => {
    setTimeout(() => {
      Animated.timing(needleRotation, {
        toValue: -4,
        duration: 500,
        useNativeDriver: true,
      }).start();
    }, 500);

    const interval = setInterval(() => {
      const jitter = -4 + Math.random() * 10 - 5;
      Animated.timing(needleRotation, {
        toValue: jitter,
        duration: 600,
        useNativeDriver: true,
      }).start();
    }, 3400);

    return () => clearInterval(interval);
  }, [needleRotation]);

  return (
    <GlassCard style={styles.card}>
      <View style={styles.header}>
        <View style={styles.titleBar} />
        <Text style={styles.title}>Live Call Simulation</Text>
      </View>

      <View style={styles.callerRow}>
        <View style={styles.callerAvatar}>
          <Svg viewBox="0 0 24 24" fill="none" stroke={Colors.lightBlue} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width={20} height={20}>
            <Path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.7a2 2 0 0 1-.4 2.1L8 9.9a16 16 0 0 0 6 6l1.4-1.4a2 2 0 0 1 2.1-.4c.9.3 1.8.5 2.7.6a2 2 0 0 1 1.8 2z" />
          </Svg>
        </View>
        <View style={styles.callerInfo}>
          <Text style={styles.label}>Incoming Call</Text>
          <Text style={styles.name}>Unknown Government Number</Text>
        </View>
        <View style={styles.callTag}>
          <Text style={styles.callTagText}>Analyzing</Text>
        </View>
      </View>

      <Waveform bars={44} isLive={true} />

      <View style={styles.gaugeContainer}>
        <Svg viewBox="0 0 200 120" width="100%" height={140}>
          <Path
            d="M10,110 A90,90 0 0 1 55,32.06"
            fill="none"
            stroke={Colors.safe}
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.9"
          />
          <Path
            d="M55,32.06 A90,90 0 0 1 145,32.06"
            fill="none"
            stroke={Colors.warn}
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.9"
          />
          <Path
            d="M145,32.06 A90,90 0 0 1 190,110"
            fill="none"
            stroke={Colors.crit}
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.9"
          />
          <Circle cx="100" cy="110" r="6" fill={Colors.lightBlue} />
          <Animated.View
            style={{
              transform: [{
                rotate: needleRotation.interpolate({
                  inputRange: [-95, 0, 360],
                  outputRange: ['-95deg', '0deg', '360deg'],
                  extrapolate: 'clamp',
                })
              }],
              transformOrigin: '100px 110px',
            }}
          >
            <Line
              x1="100"
              y1="110"
              x2="100"
              y2="34"
              stroke="#ffffff"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </Animated.View>
        </Svg>
      </View>

      <View style={styles.gaugeCaption}>
        <Text style={styles.riskState}>Suspicious</Text>
        <Text style={styles.riskNote}>"Scammer may be using urgency tactics."</Text>
      </View>
    </GlassCard>
  );
};

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 20,
    marginBottom: 28,
    padding: 22,
    backgroundColor: 'rgba(193, 232, 255, 0.07)',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  titleBar: {
    width: 3,
    height: 14,
    borderRadius: 2,
    backgroundColor: Colors.lightBlue,
  },
  title: {
    fontFamily: Fonts.display,
    fontSize: 14,
    fontWeight: '600',
    color: Colors.white,
  },
  callerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  callerAvatar: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: Colors.accentBlue,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: Colors.accentBlue,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 16,
    elevation: 5,
  },
  callerInfo: {
    flex: 1,
  },
  label: {
    fontSize: 10,
    color: Colors.mediumBlue,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    fontWeight: '600',
    marginBottom: 2,
    fontFamily: Fonts.body,
  },
  name: {
    fontSize: 14.5,
    fontWeight: '700',
    color: Colors.white,
    fontFamily: Fonts.display,
  },
  callTag: {
    paddingVertical: 4,
    paddingHorizontal: 9,
    borderRadius: 999,
    backgroundColor: 'rgba(244, 201, 93, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(244, 201, 93, 0.35)',
  },
  callTagText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.warn,
    fontFamily: Fonts.body,
  },
  gaugeContainer: {
    marginBottom: 14,
  },
  gaugeCaption: {
    alignItems: 'center',
  },
  riskState: {
    fontFamily: Fonts.display,
    fontSize: 17,
    fontWeight: '700',
    color: Colors.warn,
    letterSpacing: 0.3,
  },
  riskNote: {
    fontSize: 11.5,
    color: Colors.mediumBlue,
    marginTop: 4,
    lineHeight: 18,
    paddingHorizontal: 10,
    textAlign: 'center',
    fontFamily: Fonts.body,
  },
});

export default CallSimulation;
