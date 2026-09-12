import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';
import GlassCard from './GlassCard';
import Svg, { Path, Circle } from 'react-native-svg';

interface FeatureCardProps {
  title: string;
  description: string;
  iconName: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ title, description, iconName }) => {
  const renderIcon = (name: string) => {
    const icons: { [key: string]: React.ReactNode } = {
      shield: (
        <Svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke={Colors.lightBlue} strokeLinecap="round" strokeLinejoin="round">
          <Path d="M12 2l8 3v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V5l8-3z" />
          <Path d="M9 12l2 2 4-4" />
        </Svg>
      ),
      trending: (
        <Svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke={Colors.lightBlue} strokeLinecap="round" strokeLinejoin="round">
          <Path d="M3 17l5-5 4 4 8-8" />
          <Path d="M14 8h6v6" />
        </Svg>
      ),
      search: (
        <Svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke={Colors.lightBlue} strokeLinecap="round" strokeLinejoin="round">
          <Circle cx="11" cy="11" r="7" />
          <Path d="M21 21l-4.3-4.3" />
        </Svg>
      ),
      message: (
        <Svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke={Colors.lightBlue} strokeLinecap="round" strokeLinejoin="round">
          <Path d="M4 4h16v12H7l-3 4V4z" />
          <Path d="M8 9h8M8 13h5" />
        </Svg>
      ),
    };
    return icons[name] || icons.shield;
  };

  return (
    <GlassCard style={styles.card}>
      <TouchableOpacity activeOpacity={0.7}>
        <View style={styles.iconContainer}>{renderIcon(iconName)}</View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>
      </TouchableOpacity>
    </GlassCard>
  );
};

const FeatureGrid: React.FC = () => {
  const features = [
    {
      title: 'Voice Deepfake Detection',
      description: 'Spectral AI flags synthetic or cloned voices in real time.',
      icon: 'shield',
    },
    {
      title: 'Real-Time Risk Score',
      description: 'Continuous scoring updates as the conversation unfolds.',
      icon: 'trending',
    },
    {
      title: 'Live Fact Checking',
      description: 'Cross-checks claims against verified public databases.',
      icon: 'search',
    },
    {
      title: 'Forensic Evidence',
      description: 'Secure, tamper-proof logs ready for reporting authorities.',
      icon: 'message',
    },
  ];

  return (
    <View style={styles.gridContainer}>
      <View style={styles.header}>
        <View style={styles.titleBar} />
        <Text style={styles.sectionTitle}>Defense Suite</Text>
      </View>
      <View style={styles.grid}>
        {features.map((feature, idx) => (
          <FeatureCard
            key={idx}
            title={feature.title}
            description={feature.description}
            iconName={feature.icon}
          />
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  gridContainer: {
    marginHorizontal: 20,
    marginBottom: 30,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 14,
  },
  titleBar: {
    width: 3,
    height: 14,
    borderRadius: 2,
    backgroundColor: Colors.lightBlue,
  },
  sectionTitle: {
    fontFamily: Fonts.display,
    fontSize: 14,
    fontWeight: '600',
    color: Colors.white,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 12,
  },
  card: {
    width: '48%',
    padding: 14,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: 'rgba(84, 131, 179, 0.4)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  title: {
    fontSize: 12.5,
    fontWeight: '600',
    color: Colors.white,
    marginBottom: 4,
    fontFamily: Fonts.display,
  },
  description: {
    fontSize: 10.5,
    color: Colors.mediumBlue,
    lineHeight: 14,
    fontFamily: Fonts.body,
  },
});

export default FeatureGrid;
