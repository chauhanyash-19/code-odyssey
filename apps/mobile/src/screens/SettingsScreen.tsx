import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity, Switch } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Fonts } from '../constants/Colors';
import Header from '../components/Header';
import GlassCard from '../components/GlassCard';

interface SettingItem {
  id: string;
  title: string;
  description: string;
  type: 'toggle' | 'link';
  value?: boolean;
}

const SettingsScreen: React.FC = () => {
  const [settings, setSettings] = React.useState<SettingItem[]>([
    {
      id: '1',
      title: 'Real-Time Alerts',
      description: 'Receive instant notifications for suspicious calls',
      type: 'toggle',
      value: true,
    },
    {
      id: '2',
      title: 'Auto-Block High Risk',
      description: 'Automatically block calls with critical risk level',
      type: 'toggle',
      value: false,
    },
    {
      id: '3',
      title: 'Share Analytics',
      description: 'Help improve PhaseGuard by sharing anonymized call data',
      type: 'toggle',
      value: true,
    },
    {
      id: '4',
      title: 'Privacy Policy',
      description: 'View our data privacy and protection practices',
      type: 'link',
    },
    {
      id: '5',
      title: 'About PhaseGuard',
      description: 'Version 1.0.0 • Built for India',
      type: 'link',
    },
  ]);

  const handleToggle = (id: string) => {
    setSettings((prevSettings) =>
      prevSettings.map((setting) =>
        setting.id === id
          ? { ...setting, value: !setting.value }
          : setting
      )
    );
  };

  const renderSettingItem = (item: SettingItem) => (
    <GlassCard key={item.id} style={styles.settingItem}>
      <TouchableOpacity
        style={styles.settingContent}
        onPress={() => item.type === 'link' && console.log(`Navigate to ${item.title}`)}
      >
        <View style={styles.settingInfo}>
          <Text style={styles.settingTitle}>{item.title}</Text>
          <Text style={styles.settingDescription}>{item.description}</Text>
        </View>
        {item.type === 'toggle' && (
          <Switch
            value={item.value || false}
            onValueChange={() => handleToggle(item.id)}
            trackColor={{ false: 'rgba(193, 232, 255, 0.1)', true: Colors.safe }}
            thumbColor={Colors.white}
          />
        )}
        {item.type === 'link' && (
          <Text style={styles.linkArrow}>›</Text>
        )}
      </TouchableOpacity>
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
          <Text style={styles.title}>Settings</Text>
          <View style={styles.settingsContainer}>
            <Text style={styles.sectionTitle}>Notifications & Protection</Text>
            {settings.slice(0, 3).map((setting) => renderSettingItem(setting))}

            <Text style={[styles.sectionTitle, { marginTop: 20 }]}>
              Information
            </Text>
            {settings.slice(3).map((setting) => renderSettingItem(setting))}
          </View>
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
  settingsContainer: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  sectionTitle: {
    fontFamily: Fonts.display,
    fontSize: 13,
    fontWeight: '600',
    color: Colors.mediumBlue,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 12,
  },
  settingItem: {
    marginBottom: 12,
    padding: 16,
  },
  settingContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  settingInfo: {
    flex: 1,
  },
  settingTitle: {
    fontFamily: Fonts.display,
    fontSize: 14,
    fontWeight: '600',
    color: Colors.white,
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 11,
    color: Colors.mediumBlue,
    fontFamily: Fonts.body,
    lineHeight: 16,
  },
  linkArrow: {
    fontSize: 24,
    color: Colors.mediumBlue,
    marginLeft: 12,
  },
});

export default SettingsScreen;
