import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BookResult {
  workId: string;
  editionId: string;
  title: string;
  authors: { olid: string; name: string }[];
  isbn10: string;
  isbn13: string;
  description: string;
  pageCount: number | null;
  publisher: string;
  publishedDate: string;
  language: string;
  coverUrl: string;
}

interface Props {
  /** Called when a book is successfully resolved from the API. */
  onBookFound: (book: BookResult) => void;
  /** Base URL of the Django API, e.g. "http://localhost:8000" */
  apiBaseUrl?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEFAULT_API_BASE = 'http://localhost:8000';

async function lookupIsbn(isbn: string, apiBaseUrl: string): Promise<BookResult> {
  const url = `${apiBaseUrl}/api/catalog/books/lookup/?isbn=${encodeURIComponent(isbn)}`;
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API error ${response.status}: ${text}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BarcodeScannerScreen({
  onBookFound,
  apiBaseUrl = DEFAULT_API_BASE,
}: Props) {
  const [permission, requestPermission] = useCameraPermissions();
  const [loading, setLoading] = useState(false);
  const [manualIsbn, setManualIsbn] = useState('');
  // Prevent duplicate scans while the API call is in flight.
  const processingRef = useRef(false);

  // ------------------------------------------------------------------
  // Core lookup — shared by both scanner and manual input paths
  // ------------------------------------------------------------------

  async function handleIsbn(isbn: string) {
    if (processingRef.current) return;
    processingRef.current = true;
    setLoading(true);

    try {
      const book = await lookupIsbn(isbn.replace(/[^0-9X]/gi, ''), apiBaseUrl);
      onBookFound(book);
    } catch (err) {
      Alert.alert(
        'Book not found',
        err instanceof Error ? err.message : 'Could not look up that ISBN.',
      );
    } finally {
      setLoading(false);
      processingRef.current = false;
    }
  }

  // ------------------------------------------------------------------
  // Permission states
  // ------------------------------------------------------------------

  if (!permission) {
    // Permissions still loading.
    return <View style={styles.centered} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.centered}>
        <Text style={styles.permissionText}>
          Camera access is needed to scan book barcodes.
        </Text>
        <Pressable style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Allow camera</Text>
        </Pressable>
        <ManualEntry
          value={manualIsbn}
          onChange={setManualIsbn}
          onSubmit={() => handleIsbn(manualIsbn)}
          loading={loading}
        />
      </View>
    );
  }

  // ------------------------------------------------------------------
  // Camera view
  // ------------------------------------------------------------------

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {/* Full-screen camera with viewfinder overlay */}
      <CameraView
        style={styles.camera}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8'] }}
        onBarcodeScanned={loading ? undefined : ({ data }) => handleIsbn(data)}
      >
        <View style={styles.overlay}>
          <View style={styles.viewfinder} />
          <Text style={styles.hint}>Point the camera at the barcode on the back of the book</Text>
        </View>
      </CameraView>

      {/* Loading spinner */}
      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#ffffff" />
          <Text style={styles.loadingText}>Looking up book…</Text>
        </View>
      )}

      {/* Manual ISBN input — useful in the iOS Simulator and as a fallback */}
      <View style={styles.manualContainer}>
        <ManualEntry
          value={manualIsbn}
          onChange={setManualIsbn}
          onSubmit={() => handleIsbn(manualIsbn)}
          loading={loading}
        />
      </View>
    </KeyboardAvoidingView>
  );
}

// ---------------------------------------------------------------------------
// ManualEntry sub-component
// ---------------------------------------------------------------------------

interface ManualEntryProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

function ManualEntry({ value, onChange, onSubmit, loading }: ManualEntryProps) {
  return (
    <View style={styles.manualEntry}>
      <Text style={styles.manualLabel}>Or enter ISBN manually</Text>
      <View style={styles.manualRow}>
        <TextInput
          style={styles.manualInput}
          placeholder="e.g. 9780143133223"
          placeholderTextColor="#999"
          value={value}
          onChangeText={onChange}
          keyboardType="numeric"
          returnKeyType="search"
          onSubmitEditing={onSubmit}
          editable={!loading}
        />
        <Pressable
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={onSubmit}
          disabled={loading || value.trim().length === 0}
        >
          <Text style={styles.buttonText}>Look up</Text>
        </Pressable>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const TINT = '#4F86C6';

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#fff',
  },
  camera: {
    flex: 1,
  },
  overlay: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 24,
  },
  viewfinder: {
    width: 260,
    height: 120,
    borderWidth: 2,
    borderColor: '#fff',
    borderRadius: 8,
    backgroundColor: 'transparent',
  },
  hint: {
    color: '#fff',
    fontSize: 13,
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    color: '#fff',
    fontSize: 15,
  },
  manualContainer: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 8,
  },
  manualEntry: {
    padding: 20,
    gap: 8,
  },
  manualLabel: {
    fontSize: 13,
    color: '#555',
    fontWeight: '500',
  },
  manualRow: {
    flexDirection: 'row',
    gap: 10,
  },
  manualInput: {
    flex: 1,
    height: 44,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 12,
    fontSize: 15,
    color: '#111',
    backgroundColor: '#fafafa',
  },
  permissionText: {
    fontSize: 15,
    textAlign: 'center',
    color: '#333',
    marginBottom: 20,
  },
  button: {
    height: 44,
    paddingHorizontal: 18,
    backgroundColor: TINT,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 15,
  },
});
