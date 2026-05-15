import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { Image, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import BarcodeScannerScreen, { BookResult } from './src/screens/BarcodeScannerScreen';

export default function App() {
  const [scannedBook, setScannedBook] = useState<BookResult | null>(null);

  if (scannedBook) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar style="dark" />
        <ScrollView contentContainerStyle={styles.result}>
          {scannedBook.coverUrl ? (
            <Image source={{ uri: scannedBook.coverUrl }} style={styles.cover} resizeMode="contain" />
          ) : null}
          <Text style={styles.title}>{scannedBook.title}</Text>
          <Text style={styles.authors}>
            {scannedBook.authors.map((a) => a.name).join(', ')}
          </Text>
          {scannedBook.publisher ? (
            <Text style={styles.meta}>{scannedBook.publisher} · {scannedBook.publishedDate}</Text>
          ) : null}
          {scannedBook.pageCount ? (
            <Text style={styles.meta}>{scannedBook.pageCount} pages</Text>
          ) : null}
          {scannedBook.isbn13 ? (
            <Text style={styles.meta}>ISBN-13: {scannedBook.isbn13}</Text>
          ) : null}
          {scannedBook.description ? (
            <Text style={styles.description}>{scannedBook.description}</Text>
          ) : null}
          <Pressable style={styles.button} onPress={() => setScannedBook(null)}>
            <Text style={styles.buttonText}>Scan another book</Text>
          </Pressable>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <>
      <StatusBar style="light" />
      <BarcodeScannerScreen onBookFound={setScannedBook} />
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  result: {
    alignItems: 'center',
    padding: 24,
    gap: 10,
  },
  cover: {
    width: 160,
    height: 220,
    borderRadius: 6,
    marginBottom: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
    color: '#111',
  },
  authors: {
    fontSize: 15,
    color: '#555',
    textAlign: 'center',
  },
  meta: {
    fontSize: 13,
    color: '#888',
  },
  description: {
    fontSize: 14,
    color: '#444',
    lineHeight: 22,
    marginTop: 8,
  },
  button: {
    marginTop: 24,
    height: 48,
    paddingHorizontal: 28,
    backgroundColor: '#4F86C6',
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 16,
  },
});
