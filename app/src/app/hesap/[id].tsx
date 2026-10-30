import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Notice } from '@/components/ui/notice';
import { ScreenHeader } from '@/components/ui/screen-header';
import { MaxContentWidth, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError, fetchMovements } from '@/lib/api';
import { formatIban } from '@/lib/banking';
import { debtKurus, type Movement } from '@/lib/models';
import { formatKurus } from '@/lib/money';
import { refreshCustomer, signOut, useSession } from '@/lib/session';

const dateFormatter = new Intl.DateTimeFormat('tr-TR', {
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
});

export default function AccountDetailScreen() {
  const theme = useTheme();
  const session = useSession();
  const { id } = useLocalSearchParams<{ id: string }>();
  const accountId = Number(id);

  const [items, setItems] = useState<Movement[]>([]);
  const [nextBeforeId, setNextBeforeId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Guards against onEndReached firing several times for the same page.
  const busy = useRef(false);

  const handleError = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      signOut();
      return;
    }
    setError(e instanceof ApiError ? e.message : 'Hareketler yüklenemedi.');
  }, []);

  const loadFirstPage = useCallback(async () => {
    setError(null);
    try {
      const page = await fetchMovements(accountId);
      setItems(page.items);
      setNextBeforeId(page.nextBeforeId);
    } catch (e) {
      handleError(e);
    }
  }, [accountId, handleError]);

  const signedIn = session.status === 'signedIn';
  useEffect(() => {
    if (!signedIn) return;
    // State is only set once the request settles, and dropped if the screen moved on.
    let cancelled = false;
    fetchMovements(accountId)
      .then(
        (page) => {
          if (cancelled) return;
          setItems(page.items);
          setNextBeforeId(page.nextBeforeId);
        },
        (e) => {
          if (!cancelled) handleError(e);
        },
      )
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [signedIn, accountId, handleError]);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={[styles.container, styles.center]}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  const account = session.customer.accounts.find((a) => a.id === accountId);
  if (!account) return <Redirect href="/hesabim" />;

  async function onRefresh() {
    setRefreshing(true);
    await Promise.all([loadFirstPage(), refreshCustomer().catch(() => {})]);
    setRefreshing(false);
  }

  async function loadMore() {
    if (busy.current || nextBeforeId === null) return;
    busy.current = true;
    setLoadingMore(true);
    try {
      const page = await fetchMovements(accountId, nextBeforeId);
      setItems((prev) => [...prev, ...page.items]);
      setNextBeforeId(page.nextBeforeId);
    } catch (e) {
      handleError(e);
    } finally {
      busy.current = false;
      setLoadingMore(false);
    }
  }

  const header = (
    <View style={styles.header}>
      <ScreenHeader fallback="/hesabim" />
      <View style={styles.copy}>
        <ThemedText themeColor="textSecondary">{account.name}</ThemedText>
        <ThemedText type="title">
          {account.kind === 'credit'
            ? `Borç ${formatKurus(debtKurus(account))}`
            : formatKurus(account.balanceKurus)}
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary" selectable>
          {formatIban(account.iban)}
        </ThemedText>
      </View>
      {account.kind === 'credit' ? (
        <Button
          title="Hesaplarıma aktar"
          onPress={() => router.push({ pathname: '/aktar', params: { hesap: String(account.id) } })}
        />
      ) : (
        <Button
          title="Bu hesaptan para gönder"
          onPress={() => router.push({ pathname: '/gonder', params: { hesap: String(account.id) } })}
        />
      )}
      <ThemedText type="subtitle">Hesap hareketleri</ThemedText>
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
          keyExtractor={(m) => String(m.id)}
          renderItem={({ item }) => <MovementRow movement={item} />}
          ListHeaderComponent={header}
          ListEmptyComponent={
            loading ? (
              <ActivityIndicator color={theme.primary} accessibilityLabel="Hareketler yükleniyor" />
            ) : !error ? (
              <ThemedText themeColor="textSecondary">Bu hesapta henüz hareket yok.</ThemedText>
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

function MovementRow({ movement }: { movement: Movement }) {
  const incoming = movement.amountKurus > 0;
  const amount = `${incoming ? '+' : '−'}${formatKurus(Math.abs(movement.amountKurus))}`;
  const when = dateFormatter.format(new Date(movement.createdAt));
  const title = movement.counterparty
    ? `${movement.description} · ${movement.counterparty}`
    : movement.description;

  return (
    <View
      style={styles.row}
      accessible
      accessibilityLabel={`${title}, ${incoming ? 'gelen' : 'giden'} ${formatKurus(
        Math.abs(movement.amountKurus),
      )}, ${when}`}>
      <View style={styles.rowText}>
        <ThemedText type="smallBold" numberOfLines={1}>
          {title}
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          {when}
        </ThemedText>
      </View>
      <View style={styles.rowAmount}>
        <ThemedText type="smallBold">{amount}</ThemedText>
        {movement.balanceAfterKurus !== null ? (
          <ThemedText type="small" themeColor="textSecondary">
            {formatKurus(movement.balanceAfterKurus)}
          </ThemedText>
        ) : null}
      </View>
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
    gap: Spacing.one,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    paddingVertical: Spacing.three,
  },
  rowText: {
    flex: 1,
    gap: Spacing.half,
  },
  rowAmount: {
    alignItems: 'flex-end',
    gap: Spacing.half,
  },
  separator: {
    height: StyleSheet.hairlineWidth,
  },
  footer: {
    marginTop: Spacing.three,
    borderRadius: Radius.card,
  },
});
