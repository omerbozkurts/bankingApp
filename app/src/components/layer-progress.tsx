import { StyleSheet, View } from 'react-native';

import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

const LAYERS = 5;

/**
 * Savings progress drawn as brand layers (MARKA.md §7): filled layers use the primary colour,
 * and the summit layer turns coral only when the goal is reached.
 */
export function LayerProgress({ progress, label }: { progress: number; label: string }) {
  const theme = useTheme();
  const filled = Math.floor(progress * LAYERS);
  const reached = progress >= 1;

  return (
    <View
      style={styles.row}
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityValue={{ min: 0, max: 100, now: Math.round(progress * 100) }}>
      {Array.from({ length: LAYERS }, (_, i) => {
        const isSummit = i === LAYERS - 1;
        const color =
          i < filled ? (isSummit && reached ? theme.accent : theme.primary) : theme.border;
        return <View key={i} style={[styles.layer, { backgroundColor: color }]} />;
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  layer: {
    flex: 1,
    height: 10,
    borderRadius: Radius.pill,
  },
});
