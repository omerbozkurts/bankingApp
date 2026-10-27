import { Redirect, router } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Logo } from '@/components/brand/logo';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useSession } from '@/lib/session';

export default function WelcomeScreen() {
  const session = useSession();
  if (session.status === 'signedIn') return <Redirect href="/hesabim" />;

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.hero}>
          <Logo variant="stacked" size={88} />
          <View style={styles.copy}>
            <ThemedText type="title" style={styles.center}>
              Katman katman yükselin.
            </ThemedText>
            <ThemedText themeColor="textSecondary" style={styles.center}>
              Birikiminizi adım adım, güvenle büyütün.
            </ThemedText>
          </View>
        </View>

        <View style={styles.actions}>
          <Button title="Giriş yap" onPress={() => router.push('/giris')} />
        </View>
      </SafeAreaView>
    </ThemedView>
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
    paddingHorizontal: Spacing.four,
    paddingBottom: Spacing.four,
  },
  hero: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.five,
  },
  copy: {
    gap: Spacing.two,
  },
  center: {
    textAlign: 'center',
  },
  actions: {
    gap: Spacing.three,
  },
});
