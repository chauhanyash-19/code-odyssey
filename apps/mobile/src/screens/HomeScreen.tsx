import React from 'react';
import { View, ScrollView, StyleSheet, SafeAreaView } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors } from '../constants/Colors';
import Header from '../components/Header';
import Hero from '../components/Hero';
import ProtectionCard from '../components/ProtectionCard';
import FeatureGrid from '../components/FeatureGrid';
import CallSimulation from '../components/CallSimulation';
import Timeline from '../components/Timeline';
import ActionButtons from '../components/ActionButtons';

const HomeScreen: React.FC = () => {
  const handleBlockReport = () => {
    // API call to block and report
    console.log('Block & Report action triggered');
  };

  const handleContinueMonitoring = () => {
    // API call to continue monitoring
    console.log('Continue Monitoring action triggered');
  };

  return (
    <SafeAreaView style={styles.container}>
      <LinearGradient
        colors={['#5483B3', '#052659', '#021024', '#010a18']}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 1 }}
        style={styles.gradient}
      >
        <ScrollView
          style={styles.scrollView}
          showsVerticalScrollIndicator={false}
          scrollEventThrottle={16}
        >
          <Header />
          <Hero />
          <ProtectionCard />
          <FeatureGrid />
          <CallSimulation />
          <Timeline />
          <ActionButtons
            onBlock={handleBlockReport}
            onMonitor={handleContinueMonitoring}
          />
          <View style={styles.bottomPadding} />
        </ScrollView>
      </LinearGradient>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bgPrimary,
  },
  gradient: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
    paddingBottom: 120,
  },
  bottomPadding: {
    height: 50,
  },
});

export default HomeScreen;
