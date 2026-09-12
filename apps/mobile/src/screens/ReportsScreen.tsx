import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, FlatList } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Fonts } from '../constants/Colors';
import Header from '../components/Header';
import GlassCard from '../components/GlassCard';

interface Report {
  id: string;
  title: string;
  date: string;
  callCount: number;
  riskLevel: string;
  status: 'submitted' | 'pending' | 'investigating';
}

const ReportsScreen: React.FC = () => {
  const [reports, setReports] = React.useState<Report[]>([
    {
      id: '1',
      title: 'Government Impersonation Scam',
      date: '2 hours ago',
      callCount: 3,
      riskLevel: 'Critical',
      status: 'submitted',
    },
    {
      id: '2',
      title: 'Bank Phishing Attempt',
      date: '1 day ago',
      callCount: 1,
      riskLevel: 'High',
      status: 'investigating',
    },
    {
      id: '3',
      title: 'Prize Scam',
      date: '3 days ago',
      callCount: 2,
      riskLevel: 'Medium',
      status: 'pending',
    },
  ]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'submitted':
        return Colors.safe;
      case 'investigating':
        return Colors.warn;
      case 'pending':
        return Colors.mediumBlue;
      default:
        return Colors.mediumBlue;
    }
  };

  const renderReportItem = ({ item }: { item: Report }) => (
    <GlassCard style={styles.reportItem}>
      <View style={styles.reportHeader}>
        <View style={styles.reportInfo}>
          <Text style={styles.reportTitle}>{item.title}</Text>
          <Text style={styles.reportDate}>{item.date}</Text>
        </View>
        <View style={styles.reportMeta}>
          <Text style={styles.callCount}>{item.callCount} calls</Text>
        </View>
      </View>
      <View style={styles.reportFooter}>
        <View
          style={[
            styles.riskLevel,
            {
              backgroundColor: item.riskLevel === 'Critical'
                ? 'rgba(255, 93, 108, 0.15)'
                : item.riskLevel === 'High'
                ? 'rgba(244, 201, 93, 0.15)'
                : 'rgba(125, 160, 202, 0.15)',
            },
          ]}
        >
          <Text
            style={[
              styles.riskLevelText,
              {
                color: item.riskLevel === 'Critical'
                  ? Colors.crit
                  : item.riskLevel === 'High'
                  ? Colors.warn
                  : Colors.mediumBlue,
              },
            ]}
          >
            {item.riskLevel}
          </Text>
        </View>
        <View
          style={[
            styles.statusBadge,
            { borderColor: getStatusColor(item.status) },
          ]}
        >
          <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
          </Text>
        </View>
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
          <Text style={styles.title}>Reports & Submissions</Text>
          <FlatList
            data={reports}
            renderItem={renderReportItem}
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
  reportItem: {
    padding: 16,
    marginBottom: 12,
  },
  reportHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  reportInfo: {
    flex: 1,
    marginRight: 12,
  },
  reportTitle: {
    fontFamily: Fonts.display,
    fontSize: 14,
    fontWeight: '600',
    color: Colors.white,
    marginBottom: 4,
  },
  reportDate: {
    fontSize: 11,
    color: Colors.mediumBlue,
    fontFamily: Fonts.body,
  },
  reportMeta: {
    alignItems: 'flex-end',
  },
  callCount: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.lightBlue,
    fontFamily: Fonts.body,
  },
  reportFooter: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
  },
  riskLevel: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  riskLevelText: {
    fontSize: 10,
    fontWeight: '700',
    fontFamily: Fonts.body,
  },
  statusBadge: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '600',
    fontFamily: Fonts.body,
  },
});

export default ReportsScreen;
