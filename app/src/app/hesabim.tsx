import { Redirect } from 'expo-router';
import { useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Logo } from '@/components/brand/logo';
import { LayerProgress } from '@/components/layer-progress';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError } from '@/lib/api';
import { totalBalance, type Account } from '@/lib/models';
import { formatKurus, goalProgress } from '@/lib/money';
import { refreshCustomer, signOut, useSession } from '@/lib/session';

export default function AccountScreen() {
  const theme = useTheme();
  const session = useSession();
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={[styles.container, styles.center]}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  const { customer } = session;
  const firstName = customer.fullName.split(' ')[0];

  async function onRefresh() {
    setRefreshing(true);
    setRefreshError(null);
    try {
      await refreshCustomer();
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Bilgiler yenilenemedi. Lütfen tekrar deneyin.';
      setRefreshError(message);
      AccessibilityInfo.announceForAccessibility(message);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
          }>
          <View style={styles.header}>
            <Logo variant="horizontal" size={32} />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Çıkış yap"
              hitSlop={12}
              onPress={signOut}>
              <ThemedText type="label">Çıkış yap</ThemedText>
            </Pressable>
          </View>

          <View style={styles.copy}>
            <ThemedText themeColor="textSecondary">Merhaba, {firstName}</ThemedText>
            <ThemedText type="title">{formatKurus(totalBalance(customer))}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              Toplam varlığınız
            </ThemedText>
          </View>

          {refreshError ? (
            <View
              style={[styles.notice, { backgroundColor: theme.backgroundElement, borderLeftColor: theme.danger }]}
              accessibilityLiveRegion="polite">
              <ThemedText type="small">{refreshError}</ThemedText>
            </View>
          ) : null}

          <View style={styles.list}>
            {customer.accounts.map((account) => (
              <AccountCard key={account.id} account={account} />
            ))}
            {customer.accounts.length === 0 ? (
              <ThemedText themeColor="textSecondary">Henüz bir hesabınız yok.</ThemedText>
            ) : null}
          </View>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

function AccountCard({ account }: { account: Account }) {
  const theme = useTheme();
  const goal = account.goalKurus;
  const progress = goal !== null ? goalProgress(account.balanceKurus, goal) : null;

  return (
    <View style={[styles.card, { backgroundColor: theme.backgroundElement }]}>
      <ThemedText type="label" themeColor="textSecondary">
        {account.name}
      </ThemedText>
      <ThemedText type="subtitle">{formatKurus(account.balanceKurus)}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {account.iban}
      </ThemedText>

      {goal !== null && progress !== null ? (
        <View style={styles.goal}>
          <LayerProgress
            progress={progress}
            label={`Birikim hedefinin yüzde ${Math.round(progress * 100)} kadarı tamamlandı`}
          />
          <ThemedText type="small" themeColor="textSecondary">
            Hedef {formatKurus(goal)} · %{Math.round(progress * 100)} tamamlandı
          </ThemedText>
        </View>
      ) : null}
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
  scroll: {
    padding: Spacing.four,
    gap: Spacing.five,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  copy: {
    gap: Spacing.one,
  },
  notice: {
    borderRadius: Radius.card,
    borderLeftWidth: 4,
    padding: Spacing.three,
  },
  list: {
    gap: Spacing.three,
  },
  card: {
    borderRadius: Radius.card,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  goal: {
    gap: Spacing.two,
    marginTop: Spacing.two,
  },
});
