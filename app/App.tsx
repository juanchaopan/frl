import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { TouchableOpacity, Text } from 'react-native';
import ConversationScreen from './src/screens/ConversationScreen';
import HomeScreen from './src/screens/HomeScreen';
import SettingsScreen from './src/screens/SettingsScreen';

export type RootStackParamList = {
  Home: undefined;
  Conversation: { conversationId: string };
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="dark" />
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: '#fff' },
          headerTitleStyle: { fontWeight: '600', fontSize: 17 },
          headerTintColor: '#2563eb',
          contentStyle: { backgroundColor: '#f5f5f5' },
        }}
      >
        <Stack.Screen
          name="Home"
          component={HomeScreen}
          options={({ navigation }) => ({
            title: 'Conversations',
            headerRight: () => (
              <TouchableOpacity
                onPress={() => navigation.navigate('Settings')}
                style={{ paddingHorizontal: 4 }}
              >
                <Text style={{ fontSize: 22 }}>⚙️</Text>
              </TouchableOpacity>
            ),
          })}
        />
        <Stack.Screen
          name="Conversation"
          component={ConversationScreen}
          options={{ title: 'Chat' }}
        />
        <Stack.Screen
          name="Settings"
          component={SettingsScreen}
          options={{ title: 'Settings' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
