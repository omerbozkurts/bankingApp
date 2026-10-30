import { router, type Href } from 'expo-router';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';

type ScreenHeaderProps = {
  /** Where to go when there is no history to go back to (e.g. after a web reload). */
  fallback: Href;
  right?: ReactNode;
};

export function ScreenHeader({ fallback, right }: ScreenHeaderProps) {
  return (
    <View style={styles.header}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Geri"
        hitSlop={12}
        onPress={() => (router.canGoBack() ? router.back() : router.replace(fallback))}>
        <ThemedText type="label">← Geri</ThemedText>
      </Pressable>
      {right}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 32,
  },
});
