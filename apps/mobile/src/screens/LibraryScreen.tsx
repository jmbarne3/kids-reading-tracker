import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {
  getShelf,
  moveToShelf,
  removeFromShelf,
  SHELF_LABELS,
  SHELF_ORDER,
  type ShelfEntry,
  type ShelfType,
} from '../api/library';
import { useAuth } from '../context/AuthContext';

interface Props {
  onAddBook: () => void;
  /** Increment to trigger a re-fetch after a book is added. */
  refreshKey?: number;
}

// ---------------------------------------------------------------------------
// Book card
// ---------------------------------------------------------------------------

function BookCard({
  entry,
  onMove,
  onRemove,
}: {
  entry: ShelfEntry;
  onMove: (id: number, shelf: ShelfType) => void;
  onRemove: (id: number) => void;
}) {
  const { book } = entry;
  const otherShelves = SHELF_ORDER.filter((s) => s !== entry.shelf);

  function promptMove() {
    Alert.alert(
      'Move to shelf',
      undefined,
      [
        ...otherShelves.map((s) => ({
          text: SHELF_LABELS[s],
          onPress: () => onMove(entry.id, s),
        })),
        { text: 'Cancel', style: 'cancel' as const },
      ],
    );
  }

  function promptRemove() {
    Alert.alert(
      'Remove book',
      `Remove "${book.title}" from your library?`,
      [
        { text: 'Cancel', style: 'cancel' as const },
        { text: 'Remove', style: 'destructive' as const, onPress: () => onRemove(entry.id) },
      ],
    );
  }

  return (
    <View style={cardStyles.container}>
      {book.cover_image_url ? (
        <Image source={{ uri: book.cover_image_url }} style={cardStyles.cover} resizeMode="cover" />
      ) : (
        <View style={cardStyles.coverPlaceholder}>
          <Text style={cardStyles.coverPlaceholderIcon}>📖</Text>
        </View>
      )}
      <View style={cardStyles.info}>
        <Text style={cardStyles.title} numberOfLines={2}>{book.title}</Text>
        {book.author_names.length > 0 && (
          <Text style={cardStyles.authors} numberOfLines={1}>
            {book.author_names.join(', ')}
          </Text>
        )}
        {book.page_count ? (
          <Text style={cardStyles.meta}>{book.page_count} pages</Text>
        ) : null}
        <View style={cardStyles.actions}>
          <Pressable style={cardStyles.actionBtn} onPress={promptMove}>
            <Text style={cardStyles.actionBtnText}>Move</Text>
          </Pressable>
          <Pressable style={[cardStyles.actionBtn, cardStyles.actionBtnDanger]} onPress={promptRemove}>
            <Text style={[cardStyles.actionBtnText, cardStyles.actionBtnDangerText]}>Remove</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const cardStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    marginHorizontal: 16,
    marginBottom: 12,
    padding: 12,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  cover: {
    width: 64,
    height: 90,
    borderRadius: 6,
    backgroundColor: '#f0f0f0',
  },
  coverPlaceholder: {
    width: 64,
    height: 90,
    borderRadius: 6,
    backgroundColor: '#eef2f7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  coverPlaceholderIcon: {
    fontSize: 28,
  },
  info: {
    flex: 1,
    marginLeft: 12,
    justifyContent: 'space-between',
  },
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: '#111',
    marginBottom: 2,
  },
  authors: {
    fontSize: 13,
    color: '#666',
    marginBottom: 2,
  },
  meta: {
    fontSize: 12,
    color: '#999',
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  actionBtn: {
    paddingVertical: 5,
    paddingHorizontal: 14,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#4F86C6',
  },
  actionBtnText: {
    fontSize: 12,
    color: '#4F86C6',
    fontWeight: '500',
  },
  actionBtnDanger: {
    borderColor: '#e05c5c',
  },
  actionBtnDangerText: {
    color: '#e05c5c',
  },
});

// ---------------------------------------------------------------------------
// Library screen
// ---------------------------------------------------------------------------

export default function LibraryScreen({ onAddBook, refreshKey }: Props) {
  const { user, logout } = useAuth();
  const [activeShelf, setActiveShelf] = useState<ShelfType>('currently_reading');
  const [entries, setEntries] = useState<ShelfEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchShelf = useCallback(async (shelf: ShelfType, silent = false) => {
    if (!silent) setLoading(true);
    try {
      setEntries(await getShelf(shelf));
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not load shelf.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Fetch whenever the active shelf changes or the parent signals a refresh.
  useEffect(() => {
    fetchShelf(activeShelf);
  }, [activeShelf, fetchShelf, refreshKey]);

  const handleMove = async (id: number, shelf: ShelfType) => {
    try {
      await moveToShelf(id, shelf);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not move book.');
    }
  };

  const handleRemove = async (id: number) => {
    try {
      await removeFromShelf(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Could not remove book.');
    }
  };

  const displayName = user?.first_name || user?.username || '';

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>My Library</Text>
          {displayName ? (
            <Text style={styles.headerSub}>Hi, {displayName}!</Text>
          ) : null}
        </View>
        <View style={styles.headerRight}>
          <Pressable style={styles.addButton} onPress={onAddBook}>
            <Text style={styles.addButtonText}>+ Add Book</Text>
          </Pressable>
          <Pressable
            onPress={() =>
              Alert.alert('Sign out', 'Are you sure?', [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Sign out', style: 'destructive', onPress: logout },
              ])
            }
          >
            <Text style={styles.signOutText}>Sign out</Text>
          </Pressable>
        </View>
      </View>

      {/* Shelf tabs */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.tabsRow}
        contentContainerStyle={styles.tabsContent}
      >
        {SHELF_ORDER.map((shelf) => (
          <Pressable
            key={shelf}
            style={[styles.tab, activeShelf === shelf && styles.tabActive]}
            onPress={() => setActiveShelf(shelf)}
          >
            <Text style={[styles.tabText, activeShelf === shelf && styles.tabTextActive]}>
              {SHELF_LABELS[shelf]}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* Book list */}
      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#4F86C6" />
        </View>
      ) : (
        <FlatList
          data={entries}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={[
            styles.listContent,
            entries.length === 0 && styles.listEmpty,
          ]}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); fetchShelf(activeShelf, true); }}
              tintColor="#4F86C6"
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>📚</Text>
              <Text style={styles.emptyTitle}>No books here yet</Text>
              <Text style={styles.emptySub}>
                Tap <Text style={styles.emptyHighlight}>+ Add Book</Text> to scan or enter an ISBN.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <BookCard entry={item} onMove={handleMove} onRemove={handleRemove} />
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#1a1a2e',
  },
  headerSub: {
    fontSize: 13,
    color: '#888',
    marginTop: 2,
  },
  headerRight: {
    alignItems: 'flex-end',
    gap: 8,
  },
  addButton: {
    backgroundColor: '#4F86C6',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  addButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  signOutText: {
    fontSize: 13,
    color: '#888',
  },
  tabsRow: {
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    maxHeight: 48,
  },
  tabsContent: {
    paddingHorizontal: 12,
    gap: 4,
    alignItems: 'center',
  },
  tab: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: '#4F86C6',
  },
  tabText: {
    fontSize: 13,
    color: '#888',
    fontWeight: '500',
  },
  tabTextActive: {
    color: '#4F86C6',
    fontWeight: '600',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listContent: {
    paddingTop: 16,
    paddingBottom: 32,
  },
  listEmpty: {
    flex: 1,
    justifyContent: 'center',
  },
  emptyState: {
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  emptyIcon: {
    fontSize: 52,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  emptySub: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    lineHeight: 22,
  },
  emptyHighlight: {
    color: '#4F86C6',
    fontWeight: '600',
  },
});
