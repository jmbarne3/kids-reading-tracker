import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  addBookByISBN,
  SHELF_LABELS,
  SHELF_ORDER,
  type ShelfEntry,
  type ShelfType,
} from '../api/library';

interface Props {
  onAdded: (entry: ShelfEntry) => void;
  onCancel: () => void;
}

export default function AddBookScreen({ onAdded, onCancel }: Props) {
  const [permission, requestPermission] = useCameraPermissions();
  const [manualIsbn, setManualIsbn] = useState('');
  const [selectedShelf, setSelectedShelf] = useState<ShelfType>('want_to_read');
  const [loading, setLoading] = useState(false);
  const processingRef = useRef(false);

  async function handleIsbn(rawIsbn: string) {
    if (processingRef.current || loading) return;
    const clean = rawIsbn.replace(/[^0-9Xx]/g, '').toUpperCase();
    if (clean.length < 10) return;
    processingRef.current = true;
    setLoading(true);
    try {
      const result = await addBookByISBN(clean, selectedShelf);
      const verb = result.imported ? 'Imported and added' : 'Added';
      Alert.alert(
        'Book added!',
        `${verb} "${result.shelf_entry.book.title}" to ${SHELF_LABELS[selectedShelf]}.`,
        [{ text: 'Done', onPress: () => onAdded(result.shelf_entry) }],
      );
    } catch (err) {
      Alert.alert(
        'Could not add book',
        err instanceof Error ? err.message : 'Something went wrong.',
      );
    } finally {
      setLoading(false);
      processingRef.current = false;
    }
  }

  // ------------------------------------------------------------------
  // Shelf selector (shared between permission states)
  // ------------------------------------------------------------------

  function ShelfPicker() {
    return (
      <View style={styles.shelfSection}>
        <Text style={styles.shelfLabel}>Add to shelf</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.shelfChips}
        >
          {SHELF_ORDER.map((shelf) => (
            <Pressable
              key={shelf}
              style={[styles.chip, selectedShelf === shelf && styles.chipActive]}
              onPress={() => setSelectedShelf(shelf)}
            >
              <Text style={[styles.chipText, selectedShelf === shelf && styles.chipTextActive]}>
                {SHELF_LABELS[shelf]}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>
    );
  }

  // ------------------------------------------------------------------
  // Loading overlay
  // ------------------------------------------------------------------

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#4F86C6" />
          <Text style={styles.loadingText}>Looking up book…</Text>
        </View>
      </SafeAreaView>
    );
  }

  // ------------------------------------------------------------------
  // Camera not yet resolved
  // ------------------------------------------------------------------

  if (!permission) {
    return <SafeAreaView style={styles.container} />;
  }

  // ------------------------------------------------------------------
  // Camera permission denied — manual entry only
  // ------------------------------------------------------------------

  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.container}>
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Add Book</Text>
            <Pressable onPress={onCancel}>
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
          </View>

          <View style={styles.permissionBox}>
            <Text style={styles.permissionText}>
              Camera access lets you scan barcodes. You can also enter an ISBN manually below.
            </Text>
            <Pressable style={styles.permissionButton} onPress={requestPermission}>
              <Text style={styles.permissionButtonText}>Allow Camera</Text>
            </Pressable>
          </View>

          <ShelfPicker />

          <View style={styles.manualSection}>
            <Text style={styles.shelfLabel}>Enter ISBN manually</Text>
            <View style={styles.manualRow}>
              <TextInput
                style={styles.manualInput}
                placeholder="e.g. 9780747532699"
                placeholderTextColor="#aaa"
                value={manualIsbn}
                onChangeText={setManualIsbn}
                keyboardType="number-pad"
                returnKeyType="go"
                onSubmitEditing={() => handleIsbn(manualIsbn)}
              />
              <Pressable
                style={[styles.manualButton, !manualIsbn.trim() && styles.manualButtonDisabled]}
                onPress={() => handleIsbn(manualIsbn)}
                disabled={!manualIsbn.trim()}
              >
                <Text style={styles.manualButtonText}>Add</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  // ------------------------------------------------------------------
  // Camera granted — scanner view with manual fallback
  // ------------------------------------------------------------------

  return (
    <View style={styles.flex}>
      {/* Full-screen camera */}
      <CameraView
        style={styles.camera}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e'] }}
        onBarcodeScanned={({ data }) => handleIsbn(data)}
      />

      {/* Overlay */}
      <SafeAreaView style={styles.overlay} pointerEvents="box-none">
        {/* Top bar */}
        <View style={styles.overlayTopBar}>
          <Text style={styles.overlayTitle}>Scan Barcode</Text>
          <Pressable style={styles.cancelButton} onPress={onCancel}>
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </Pressable>
        </View>

        {/* Scan window hint */}
        <View style={styles.scanWindow} pointerEvents="none">
          <View style={styles.scanCornerTL} />
          <View style={styles.scanCornerTR} />
          <View style={styles.scanCornerBL} />
          <View style={styles.scanCornerBR} />
        </View>

        {/* Bottom panel */}
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.overlayBottom}
        >
          <ShelfPicker />

          <View style={styles.manualSection}>
            <Text style={[styles.shelfLabel, { color: '#fff' }]}>Or enter ISBN</Text>
            <View style={styles.manualRow}>
              <TextInput
                style={[styles.manualInput, styles.manualInputDark]}
                placeholder="e.g. 9780747532699"
                placeholderTextColor="#888"
                value={manualIsbn}
                onChangeText={setManualIsbn}
                keyboardType="number-pad"
                returnKeyType="go"
                onSubmitEditing={() => handleIsbn(manualIsbn)}
              />
              <Pressable
                style={[styles.manualButton, !manualIsbn.trim() && styles.manualButtonDisabled]}
                onPress={() => handleIsbn(manualIsbn)}
                disabled={!manualIsbn.trim()}
              >
                <Text style={styles.manualButtonText}>Add</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </View>
  );
}

const CORNER = 24;
const CORNER_THICKNESS = 3;
const CORNER_SIZE = 28;

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flex: 1, backgroundColor: '#f5f7fa' },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  loadingText: { fontSize: 15, color: '#555' },

  // Header (no-camera mode)
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#1a1a2e' },
  cancelText: { fontSize: 15, color: '#4F86C6' },

  // Permission box
  permissionBox: {
    margin: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    alignItems: 'center',
    gap: 12,
  },
  permissionText: { fontSize: 14, color: '#555', textAlign: 'center', lineHeight: 20 },
  permissionButton: {
    backgroundColor: '#4F86C6',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  permissionButtonText: { color: '#fff', fontWeight: '600', fontSize: 14 },

  // Shelf picker
  shelfSection: { paddingHorizontal: 16, paddingTop: 16, paddingBottom: 8 },
  shelfLabel: { fontSize: 13, fontWeight: '600', color: '#555', marginBottom: 8 },
  shelfChips: { gap: 8, paddingRight: 4 },
  chip: {
    paddingVertical: 7,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: '#c8d8ea',
    backgroundColor: '#fff',
  },
  chipActive: { backgroundColor: '#4F86C6', borderColor: '#4F86C6' },
  chipText: { fontSize: 13, color: '#4F86C6', fontWeight: '500' },
  chipTextActive: { color: '#fff' },

  // Manual entry
  manualSection: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 16 },
  manualRow: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  manualInput: {
    flex: 1,
    height: 46,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    paddingHorizontal: 14,
    fontSize: 15,
    backgroundColor: '#fafafa',
    color: '#111',
  },
  manualInputDark: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderColor: 'rgba(255,255,255,0.25)',
    color: '#fff',
  },
  manualButton: {
    height: 46,
    paddingHorizontal: 20,
    backgroundColor: '#4F86C6',
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  manualButtonDisabled: { opacity: 0.45 },
  manualButtonText: { color: '#fff', fontWeight: '600', fontSize: 14 },

  // Camera
  camera: { flex: 1 },

  // Overlay
  overlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
  },
  overlayTopBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
  },
  overlayTitle: { fontSize: 18, fontWeight: '700', color: '#fff' },
  cancelButton: {
    backgroundColor: 'rgba(0,0,0,0.45)',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  cancelButtonText: { color: '#fff', fontWeight: '600', fontSize: 14 },

  // Scan window corners
  scanWindow: {
    width: 220,
    height: 140,
    alignSelf: 'center',
    position: 'relative',
  },
  scanCornerTL: {
    position: 'absolute', top: 0, left: 0,
    width: CORNER_SIZE, height: CORNER_SIZE,
    borderTopWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS,
    borderColor: '#fff', borderTopLeftRadius: CORNER,
  },
  scanCornerTR: {
    position: 'absolute', top: 0, right: 0,
    width: CORNER_SIZE, height: CORNER_SIZE,
    borderTopWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS,
    borderColor: '#fff', borderTopRightRadius: CORNER,
  },
  scanCornerBL: {
    position: 'absolute', bottom: 0, left: 0,
    width: CORNER_SIZE, height: CORNER_SIZE,
    borderBottomWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS,
    borderColor: '#fff', borderBottomLeftRadius: CORNER,
  },
  scanCornerBR: {
    position: 'absolute', bottom: 0, right: 0,
    width: CORNER_SIZE, height: CORNER_SIZE,
    borderBottomWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS,
    borderColor: '#fff', borderBottomRightRadius: CORNER,
  },

  overlayBottom: {
    backgroundColor: 'rgba(0,0,0,0.72)',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingTop: 4,
  },
});
