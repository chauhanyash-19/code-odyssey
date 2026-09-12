import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';
import GlassCard from './GlassCard';

interface StatItemProps {
  label: string;
  value: string | number;
  unit?: string;
  isLive?: boolean;
  fillPercentage?: number;
  riskLevel?: 'low' | 'medium' | 'high';
}

const ProtectionCard: React.FC = () => {
  const [stats, setStats] = React.useState({
    callStatus: 'Live',
    voiceAuth: 98,
    scamRisk: 'Low',
    latency: 150,
  });

  React.useEffect(() => {
    const interval = setInterval(() => {
      setStats((prev) => ({
        ...prev,
        latency: 118 + Math.floor(Math.random() * 54),
      }));
    }, 1400);

    return () => clearInterval(interval);
  }, []);

  const StatItem: React.FC<StatItemProps> = ({
    label,
    value,
    unit,
    isLive,
    fillPercentage = 50,
    riskLevel,
  }) => (
    <View style={styles.statContainer}>
      <Text style={styles.statLabel}>{label}</Text>
      <View style={styles.statValueRow}>
        {isLive && <View style={styles.liveDot} />}
        <Text style={[styles.statValue, riskLevel === 'low' && { color: Colors.safe }]}>
          {value}
          {unit && <Text style={styles.unit}>{unit}</Text>}
        </Text>
      </View>
      <View style={styles.barTrack}>
        <View
          style={[
            styles.barFill,
            {
              width: `${fillPercentage}%`,
              backgroundColor: riskLevel === 'low' ? Colors.safe : Colors.lightBlue,
            },
          ]}
        />
      </View>
    </View>
  );

  return (
    <GlassCard style={styles.card}>
      <View style={styles.header}>
        <View style={styles.titleBar} />
        <Text style={styles.title}>Live Protection</Text>
      </View>

      <View style={styles.grid}>
        <StatItem label="Call Status" value={stats.callStatus} isLive />
        <StatItem label="Voice Authenticity" value={stats.voiceAuth} unit="%" fillPercentage={98} />
        <StatItem
          label="Scam Risk"
          value={stats.scamRisk}
          riskLevel="low"
          fillPercentage={18}
        />
        <StatItem label="Latency" value={stats.latency} unit="ms" fillPercentage={64} />
      </View>
    </GlassCard>
  );
};

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 20,
    marginBottom: 28,
    padding: 20,
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
  grid: {
    display: 'flex',
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statContainer: {
    width: '48%',
    marginBottom: 16,
  },
  statLabel: {
    fontSize: 10.5,
    color: Colors.mediumBlue,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    fontWeight: '600',
    marginBottom: 4,
    fontFamily: Fonts.body,
  },
  statValueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.safe,
    shadowColor: Colors.safe,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 6,
    elevation: 3,
  },
  statValue: {
    fontFamily: Fonts.display,
    fontSize: 18,
    fontWeight: '700',
    color: Colors.white,
  },
  unit: {
    fontSize: 11,
    color: Colors.mediumBlue,
    fontWeight: '500',
  },
  barTrack: {
    width: '100%',
    height: 5,
    borderRadius: 4,
    backgroundColor: 'rgba(193, 232, 255, 0.1)',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
    shadowColor: 'rgba(193, 232, 255, 0.6)',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 10,
    elevation: 3,
  },
});

export default ProtectionCard;
