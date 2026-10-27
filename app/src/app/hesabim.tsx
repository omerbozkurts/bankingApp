import { Redirect, router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Logo } from '@/components/brand/logo';
import { LayerProgress } from '@/components/layer-progress';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { formatKurus, goalProgress, type Account } from '@/lib/demo-account';
import { signOut, useSession } from '@/lib/session';

export default function AccountScreen() {
  const customer = useSession();

  if (!customer) return <Redirect href="/giris" />;

  const total = customer.accounts.reduce((sum, a) => sum + a.balanceKurus, 0);
  const firstName = customer.fullName.split(' ')[0];

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <Logo variant="horizontal" size={32} />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Çıkış yap"
              hitSlop={12}
              onPress={() => {
                signOut();
                router.replace('/');
              }}>
              <ThemedText type="label">Çıkış yap</ThemedText>
            </Pressable>
          </View>

          <View style={styles.copy}>
            <ThemedText themeColor="textSecondary">Merhaba, {firstName}</ThemedText>
            <ThemedText type="title">{formatKurus(total)}</ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              Toplam varlığınız
            </ThemedText>
          </View>

          <View style={styles.list}>
            {customer.accounts.map((account) => (
              <AccountCard key={account.id} account={account} />
            ))}
          </View>

          <ThemedText type="small" themeColor="textSecondary" style={styles.demoNote}>
            Bu bir demo hesaptır; bakiyeler örnek verilerdir.
          </ThemedText>
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

function AccountCard({ account }: { account: Account }) {
  const theme = useTheme();
  const progress =
    account.goalKurus !== undefined ? goalProgress(account.balanceKurus, account.goalKurus) : null;

  return (
    <View style={[styles.card, { backgroundColor: theme.backgroundElement }]}>
      <ThemedText type="label" themeColor="textSecondary">
        {account.name}
      </ThemedText>
      <ThemedText type="subtitle">{formatKurus(account.balanceKurus)}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {account.iban}
      </ThemedText>

      {progress !== null && account.goalKurus !== undefined ? (
        <View style={styles.goal}>
          <LayerProgress
            progress={progress}
            label={`Birikim hedefinin yüzde ${Math.round(progress * 100)} kadarı tamamlandı`}
          />
          <ThemedText type="small" themeColor="textSecondary">
            Hedef {formatKurus(account.goalKurus)} · %{Math.round(progress * 100)} tamamlandı
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
  demoNote: {
    textAlign: 'center',
  },
});
