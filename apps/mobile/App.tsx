import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import LoginScreen from './src/screens/LoginScreen';
import LibraryScreen from './src/screens/LibraryScreen';
import AddBookScreen from './src/screens/AddBookScreen';
import { type ShelfEntry } from './src/api/library';

type Screen = 'library' | 'add-book';

function AppInner() {
  const { user, loading } = useAuth();
  const [screen, setScreen] = useState<Screen>('library');
  const [refreshKey, setRefreshKey] = useState(0);

  if (loading) {
    return (
      <View style={styles.splash}>
        <StatusBar style="dark" />
        <ActivityIndicator size="large" color="#4F86C6" />
      </View>
    );
  }

  if (!user) {
    return (
      <>
        <StatusBar style="dark" />
        <LoginScreen />
      </>
    );
  }

  if (screen === 'add-book') {
    return (
      <>
        <StatusBar style="light" />
        <AddBookScreen
          onAdded={(_entry: ShelfEntry) => {
            setRefreshKey((k) => k + 1);
            setScreen('library');
          }}
          onCancel={() => setScreen('library')}
        />
      </>
    );
  }

  return (
    <>
      <StatusBar style="dark" />
      <LibraryScreen
        onAddBook={() => setScreen('add-book')}
        refreshKey={refreshKey}
      />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f0f4f8',
  },
});
