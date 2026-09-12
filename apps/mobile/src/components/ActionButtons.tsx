import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';
import Svg, { Path, Circle } from 'react-native-svg';

interface ActionButtonsProps {
  onBlock?: () => void;
  onMonitor?: () => void;
}

const ActionButtons: React.FC<ActionButtonsProps> = ({ onBlock, onMonitor }) => {
  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.primaryBtn}
        onPress={onBlock}
        activeOpacity={0.8}
      >
        <Svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" width={16} height={16}>
          <Circle cx="12" cy="12" r="9" />
          <Path d="M8 8l8 8M16 8l-8 8" />
        </Svg>
        <Text style={styles.primaryBtnText}>Block & Report</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.secondaryBtn}
        onPress={onMonitor}
        activeOpacity={0.8}
      >
        <Svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" width={16} height={16}>
          <Path d="M12 2v4M12 18v4M4.9 4.9l2.9 2.9M16.2 16.2l2.9 2.9M2 12h4M18 12h4M4.9 19.1l2.9-2.9M16.2 7.8l2.9-2.9" />
        </Svg>
        <Text style={styles.secondaryBtnText}>Continue Monitoring</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'column',
    gap: 12,
    marginHorizontal: 20,
    marginBottom: 34,
  },
  primaryBtn: {
    width: '100%',
    paddingVertical: 16,
    borderRadius: 999,
    backgroundColor: 'rgba(255, 107, 120, 1)',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    shadowColor: 'rgba(255, 68, 87, 1)',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 24,
    elevation: 5,
  },
  primaryBtnText: {
    fontFamily: Fonts.body,
    fontSize: 14,
    fontWeight: '700',
    color: Colors.white,
    letterSpacing: 0.2,
  },
  secondaryBtn: {
    width: '100%',
    paddingVertical: 16,
    borderRadius: 999,
    backgroundColor: 'rgba(193, 232, 255, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(193, 232, 255, 0.25)',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    shadowColor: 'rgba(84, 131, 179, 0.4)',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 26,
    elevation: 5,
  },
  secondaryBtnText: {
    fontFamily: Fonts.body,
    fontSize: 14,
    fontWeight: '700',
    color: Colors.lightBlue,
    letterSpacing: 0.2,
  },
});

export default ActionButtons;
