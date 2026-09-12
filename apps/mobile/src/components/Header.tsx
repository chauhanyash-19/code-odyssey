import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Fonts } from '../constants/Colors';
import PulseDot from './PulseDot';

const Header: React.FC = () => {
  return (
    <View style={styles.container}>
      <View style={styles.brand}>
        <View style={styles.logoContainer}>
          <Text style={styles.brandName}>PhaseGuard</Text>
        </View>
      </View>
      <View style={styles.statusBadge}>
        <PulseDot size={7} />
        <Text style={styles.statusText}>Protection Active</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 10,
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  logoContainer: {
    justifyContent: 'center',
  },
  brandName: {
    fontFamily: Fonts.display,
    fontSize: 17,
    fontWeight: '700',
    color: Colors.white,
    letterSpacing: 0.3,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 999,
    backgroundColor: 'rgba(94, 225, 196, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(94, 225, 196, 0.35)',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.safe,
    fontFamily: Fonts.body,
  },
});

export default Header;
