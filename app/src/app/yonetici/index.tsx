import { Redirect, router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Notice } from '@/components/ui/notice';
import { ScreenHeader } from '@/components/ui/screen-header';
import { TextField } from '@/components/ui/text-field';
import { MaxContentWidth, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { AdminCustomer } from '@/lib/admin';
import { adminSearchCustomers, ApiError } from '@/lib/api';
import { signOut, useSession } from '@/lib/session';

const SEARCH_DELAY_MS = 300;

/** Admin panel home: find a customer by number or name. */
export default function AdminScreen() {
  const theme = useTheme();
  const session = useSession();
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<AdminCustomer[]>([]);
  const [nextBeforeId, setNextBeforeId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The query the shown results belong to; answers for an older query are dropped.
  const latest = useRef('');
  const busy = useRef(false);

  const handleError = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) return void signOut();
    setError(e instanceof ApiError ? e.message : 'Müşteriler yüklenemedi.');
  }, []);

  const isAdmin = session.status === 'signedIn' && session.customer.isAdmin;
  useEffect(() => {
    if (!isAdmin) return;
    const term = query.trim();
    latest.current = term;
    const timer = setTimeout(() => {
      adminSearchCustomers(term)
        .then(
          (page) => {
            if (latest.current !== term) return;
            setError(null);
            setItems(page.items);
            setNextBeforeId(page.nextBeforeId);
          },
          (e) => {
            if (latest.current !== term) return;
            setItems([]);
            setNextBeforeId(null);
            handleError(e);
          },
        )
        .finally(() => {
          if (latest.current === term) setLoading(false);
        });
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [isAdmin, query, handleError]);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={[styles.container, styles.center]}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;
  if (!session.customer.isAdmin) return <Redirect href="/hesabim" />;

  async function loadMore() {
    const term = latest.current;
    if (busy.current || loading || nextBeforeId === null) return;
    busy.current = true;
    setLoadingMore(true);
    try {
      const page = await adminSearchCustomers(term, nextBeforeId);
      if (latest.current !== term) return;
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
        <ThemedText type="title">Yönetici paneli</ThemedText>
        <ThemedText themeColor="textSecondary">
          Müşterileri görüntüleyin, hesap dondurun veya giriş kilidini açın. Her işlem gerekçesiyle
          kayda geçer.
        </ThemedText>
      </View>
      <Button
        title="İşlem kayıtları"
        variant="secondary"
        onPress={() => router.push('/yonetici/kayitlar')}
      />
      <TextField
        label="Müşteri ara"
        placeholder="Müşteri numarası veya ad"
        value={query}
        onChangeText={(v) => {
          setQuery(v);
          setLoading(true);
        }}
        autoCapitalize="none"
        autoCorrect={false}
        maxLength={120}
      />
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
          keyExtractor={(c) => String(c.id)}
          renderItem={({ item }) => <CustomerRow customer={item} />}
          ListHeaderComponent={header}
          ListEmptyComponent={
            loading ? (
              <ActivityIndicator color={theme.primary} accessibilityLabel="Müşteriler yükleniyor" />
            ) : !error ? (
              <ThemedText themeColor="textSecondary">Eşleşen müşteri yok.</ThemedText>
            ) : undefined
          }
          ListFooterComponent={
            loadingMore ? <ActivityIndicator color={theme.primary} style={styles.footer} /> : undefined
          }
          ItemSeparatorComponent={() => <View style={styles.gap} />}
          onEndReached={loadMore}
          onEndReachedThreshold={0.4}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.list}
        />
      </SafeAreaView>
    </ThemedView>
  );
}

function CustomerRow({ customer }: { customer: AdminCustomer }) {
  const theme = useTheme();
  const tags = [
    `${customer.accountCount} hesap`,
    customer.isAdmin ? 'Yönetici' : null,
    customer.locked ? 'Giriş kilitli' : null,
  ].filter(Boolean);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${customer.fullName}, müşteri no ${customer.customerNo}, ${tags.join(', ')}`}
      onPress={() =>
        router.push({ pathname: '/yonetici/musteri/[id]', params: { id: String(customer.id) } })
      }
      style={({ pressed }) => [
        styles.card,
        { backgroundColor: theme.backgroundElement },
        pressed && styles.pressed,
      ]}>
      <ThemedText type="smallBold">{customer.fullName}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {customer.customerNo} · {tags.join(' · ')}
      </ThemedText>
    </Pressable>
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
    marginBottom: Spacing.four,
  },
  copy: {
    gap: Spacing.two,
  },
  card: {
    borderRadius: Radius.card,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  pressed: {
    opacity: 0.85,
  },
  gap: {
    height: Spacing.two,
  },
  footer: {
    marginTop: Spacing.three,
  },
});
