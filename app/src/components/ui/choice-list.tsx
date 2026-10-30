import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

export type Choice<T extends string | number> = {
  value: T;
  title: string;
  detail?: string;
};

type ChoiceListProps<T extends string | number> = {
  label: string;
  choices: Choice<T>[];
  value: T | null;
  onChange: (value: T) => void;
};

/** Single-choice list announced as a radio group; the selected row gets a primary border. */
export function ChoiceList<T extends string | number>({
  label,
  choices,
  value,
  onChange,
}: ChoiceListProps<T>) {
  const theme = useTheme();

  return (
    <View style={styles.container}>
      <ThemedText type="label">{label}</ThemedText>
      <View accessibilityRole="radiogroup" accessibilityLabel={label} style={styles.list}>
        {choices.map((choice) => {
          const selected = choice.value === value;
          return (
            <Pressable
              key={choice.value}
              accessibilityRole="radio"
              accessibilityState={{ checked: selected }}
              accessibilityLabel={choice.detail ? `${choice.title}, ${choice.detail}` : choice.title}
              onPress={() => onChange(choice.value)}
              style={[
                styles.row,
                {
                  backgroundColor: theme.backgroundElement,
                  borderColor: selected ? theme.primary : theme.border,
                },
              ]}>
              <View
                style={[
                  styles.dot,
                  { borderColor: selected ? theme.primary : theme.border },
                  selected && { backgroundColor: theme.primary },
                ]}
              />
              <View style={styles.text}>
                <ThemedText type="smallBold">{choice.title}</ThemedText>
                {choice.detail ? (
                  <ThemedText type="small" themeColor="textSecondary">
                    {choice.detail}
                  </ThemedText>
                ) : null}
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.two,
  },
  list: {
    gap: Spacing.two,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
    borderWidth: 1.5,
    borderRadius: Radius.card,
    padding: Spacing.three,
    minHeight: 56,
  },
  dot: {
    width: 18,
    height: 18,
    borderRadius: Radius.pill,
    borderWidth: 2,
  },
  text: {
    flex: 1,
    gap: Spacing.half,
  },
});
