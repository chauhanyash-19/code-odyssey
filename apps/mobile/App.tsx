import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import HomeScreen from './src/screens/HomeScreen';
import CallsScreen from './src/screens/CallsScreen';
import ReportsScreen from './src/screens/ReportsScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import { Colors } from './src/constants/Colors';
import TabBarIcon from './src/components/TabBarIcon';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={{
            headerShown: false,
            tabBarStyle: {
              backgroundColor: 'rgba(5, 38, 89, 0.55)',
              borderTopWidth: 1,
              borderTopColor: 'rgba(193, 232, 255, 0.14)',
              height: 80,
              paddingBottom: 16,
              paddingTop: 8,
            },
            tabBarActiveTintColor: Colors.lightBlue,
            tabBarInactiveTintColor: Colors.mediumBlue,
            tabBarLabelStyle: {
              fontSize: 9.5,
              fontWeight: '600',
              marginTop: 4,
            },
          }}
        >
          <Tab.Screen
            name="Home"
            component={HomeScreen}
            options={{
              tabBarIcon: ({ color }) => <TabBarIcon name="home" color={color} />,
            }}
          />
          <Tab.Screen
            name="Calls"
            component={CallsScreen}
            options={{
              tabBarIcon: ({ color }) => <TabBarIcon name="phone" color={color} />,
            }}
          />
          <Tab.Screen
            name="Reports"
            component={ReportsScreen}
            options={{
              tabBarIcon: ({ color }) => <TabBarIcon name="message-square" color={color} />,
            }}
          />
          <Tab.Screen
            name="Settings"
            component={SettingsScreen}
            options={{
              tabBarIcon: ({ color }) => <TabBarIcon name="settings" color={color} />,
            }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </GestureHandlerRootView>
  );
}
