import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, FlatList } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Fonts } from '../constants/Colors';
import Header from '../components/Header';
import GlassCard from '../components/GlassCard';

interface CallRecord {
  id: string;
  caller: string;
  time: string;
  duration: string;
  riskLevel: 'low' | 'medium' | 'high';
  status: 'blocked' | 'monitored' | 'safe';
}

const CallsScreen: React.FC = () => {
  const [calls, setCalls] = React.useState<CallRecord[]>([
    {
      id: '1',
      caller: 'Unknown Number +91-XXXX123456',
      time: '2 hours ago',
      duration: '2:34',
      riskLevel: 'high',
      status: 'blocked',
    },
    {
      id: '2',
      caller: 'Bank Customer Service',
      time: '5 hours ago',
      duration: '5:12',
      riskLevel: 'low',
      status: 'safe',
    },
    {
      id: '3',
      caller: 'Government Portal',
      time: '1 day ago',
      duration: '3:45',
      riskLevel: 'high',
      status: 'monitored',
    },
  ]);

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low':
        return Colors.safe;
      case 'medium':
        return Colors.warn;
      case 'high':
        return Colors.crit;
      default:
        return Colors.mediumBlue;
    }
  };

  const renderCallItem = ({ item }: { item: CallRecord }) => (
    <GlassCard style={styles.callItem}>
      <View style={styles.callHeader}>
        <View style={styles.callInfo}>
          <Text style={styles.caller}>{item.caller}</Text>
          <Text style={styles.meta}>{item.time} • {item.duration}</Text>
        </View>
        <View
          style={[
            styles.riskBadge,
            { backgroundColor: `${getRiskColor(item.riskLevel)}20` },
          ]}
        >
          <Text style={[styles.riskText, { color: getRiskColor(item.riskLevel) }]}>
            {item.riskLevel.toUpperCase()}
          </Text>
        </View>
      </View>
      <View style={styles.statusBar}>
        <View
          style={[
            styles.statusIndicator,
            { backgroundColor: getRiskColor(item.riskLevel) },
          ]}
        />
        <Text style={styles.statusLabel}>
          {item.status === 'blocked' && 'Blocked & Reported'}
          {item.status === 'safe' && 'Safe Call'}
          {item.status === 'monitored' && 'Monitored'}
        </Text>
      </View>
    </GlassCard>
  );

  return (
    <SafeAreaView style={styles.container}>
      <LinearGradient
        colors={['#5483B3', '#052659', '#021024', '#010a18']}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 1 }}
        style={styles.gradient}
      >
        <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
          <Header />
          <Text style={styles.title}>Call History</Text>
          <FlatList
            data={calls}
            renderItem={renderCallItem}
            keyExtractor={(item) => item.id}
            scrollEnabled={false}
            contentContainerStyle={styles.listContainer}
          />
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
  },
  title: {
    fontFamily: Fonts.display,
    fontSize: 20,
    fontWeight: '700',
    color: Colors.white,
    marginHorizontal: 20,
    marginTop: 20,
    marginBottom: 16,
  },
  listContainer: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  callItem: {
    padding: 16,
    marginBottom: 12,
  },
  callHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  callInfo: {
    flex: 1,
    marginRight: 12,
  },
  caller: {
    fontFamily: Fonts.display,
    fontSize: 14,
    fontWeight: '600',
    color: Colors.white,
    marginBottom: 4,
  },
  meta: {
    fontSize: 11,
    color: Colors.mediumBlue,
    fontFamily: Fonts.body,
  },
  riskBadge: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  riskText: {
    fontSize: 9,
    fontWeight: '700',
    fontFamily: Fonts.body,
  },
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.lightBlue,
    fontFamily: Fonts.body,
  },
});

export default CallsScreen;
