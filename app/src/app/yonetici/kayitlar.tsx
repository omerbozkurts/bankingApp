import { Redirect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Notice } from '@/components/ui/notice';
import { ScreenHeader } from '@/components/ui/screen-header';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { actionAuthor, describeAction, type AdminAction } from '@/lib/admin';
import { adminFetchActions, ApiError } from '@/lib/api';
import { signOut, useSession } from '@/lib/session';

const dateFormatter = new Intl.DateTimeFormat('tr-TR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

/** The admin audit log, newest first. Read-only: entries can't be edited or removed. */
export default function AuditLogScreen() {
  const theme = useTheme();
  const session = useSession();
  const [items, setItems] = useState<AdminAction[]>([]);
  const [nextBeforeId, setNextBeforeId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);
  // Bumped by a refresh: a next page requested before it belongs to the old list.
  const generation = useRef(0);

  const handleError = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) return void signOut();
    setError(e instanceof ApiError ? e.message : 'Kayıtlar yüklenemedi.');
  }, []);

  const loadFirstPage = useCallback(async () => {
    const started = ++generation.current;
    setError(null);
    try {
      const page = await adminFetchActions();
      if (started !== generation.current) return;
      setItems(page.items);
      setNextBeforeId(page.nextBeforeId);
    } catch (e) {
      if (started === generation.current) handleError(e);
    } finally {
      // A refresh during the first load replaces it, so it also ends the first-load spinner.
      if (started === generation.current) setLoading(false);
    }
  }, [handleError]);

  const isAdmin = session.status === 'signedIn' && session.customer.isAdmin;
  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false;
    const started = ++generation.current;
    adminFetchActions()
      .then(
        (page) => {
          if (cancelled || started !== generation.current) return;
          setItems(page.items);
          setNextBeforeId(page.nextBeforeId);
        },
        (e) => {
          if (!cancelled && started === generation.current) handleError(e);
        },
      )
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin, handleError]);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={[styles.container, styles.center]}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;
  if (!session.customer.isAdmin) return <Redirect href="/hesabim" />;

  async function onRefresh() {
    setRefreshing(true);
    await loadFirstPage();
    setRefreshing(false);
  }

  async function loadMore() {
    if (busy.current || refreshing || nextBeforeId === null) return;
    const started = generation.current;
    busy.current = true;
    setLoadingMore(true);
    try {
      const page = await adminFetchActions(nextBeforeId);
      if (started !== generation.current) return;
      setItems((prev) => [...prev, ...page.items]);
      setNextBeforeId(page.nextBeforeId);
    } catch (e) {
      if (started === generation.current) handleError(e);
    } finally {
      busy.current = false;
      setLoadingMore(false);
    }
  }

  const header = (
    <View style={styles.header}>
      <ScreenHeader fallback="/yonetici" />
      <View style={styles.copy}>
        <ThemedText type="title">İşlem kayıtları</ThemedText>
        <ThemedText themeColor="textSecondary">
          Yöneticilerin yaptığı her değişiklik, kimin yaptığı ve gerekçesiyle burada. Kayıtlar
          değiştirilemez.
        </ThemedText>
      </View>
      {error ? (
        <Notice tone="error">
          <ThemedText type="small">{error}</ThemedText>
        </Notice>
      ) : null}
    </View>
  );

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <FlatList
          data={items}
          keyExtractor={(a) => String(a.id)}
          renderItem={({ item }) => <ActionRow action={item} />}
          ListHeaderComponent={header}
          ListEmptyComponent={
            loading ? (
              <ActivityIndicator color={theme.primary} accessibilityLabel="Kayıtlar yükleniyor" />
            ) : !error ? (
              <ThemedText themeColor="textSecondary">Henüz kayıt yok.</ThemedText>
            ) : undefined
          }
          ListFooterComponent={
            loadingMore ? <ActivityIndicator color={theme.primary} style={styles.footer} /> : undefined
          }
          ItemSeparatorComponent={() => (
            <View style={[styles.separator, { backgroundColor: theme.border }]} />
          )}
          onEndReached={loadMore}
          onEndReachedThreshold={0.4}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
          }
          contentContainerStyle={styles.list}
        />
      </SafeAreaView>
    </ThemedView>
  );
}

function ActionRow({ action }: { action: AdminAction }) {
  return (
    <View style={styles.row} accessible>
      <ThemedText type="smallBold">{describeAction(action)}</ThemedText>
      <ThemedText type="small">{action.reason}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {dateFormatter.format(new Date(action.createdAt))} · yapan {actionAuthor(action)}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
  },
  center: {
    justifyContent: 'center',
  },
  safeArea: {
    flex: 1,
    width: '100%',
    maxWidth: MaxContentWidth,
  },
  list: {
    padding: Spacing.four,
  },
  header: {
    gap: Spacing.four,
    marginBottom: Spacing.three,
  },
  copy: {
    gap: Spacing.two,
  },
  row: {
    gap: Spacing.half,
    paddingVertical: Spacing.three,
  },
  separator: {
    height: StyleSheet.hairlineWidth,
  },
  footer: {
    marginTop: Spacing.three,
  },
});
