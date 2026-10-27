/**
 * AB Bank design tokens. Source of truth: logo/brand/MARKA.md
 * Gece Laciverti is the main colour; Şafak Mercanı is reserved for the summit layer and "rise" moments.
 */

import { Platform } from 'react-native';

export const Brand = {
  navy: '#0E2A47',
  coral: '#FF6B4A',
  white: '#FFFFFF',
} as const;

export const Colors = {
  light: {
    text: Brand.navy,
    textSecondary: '#5B6B7F',
    background: Brand.white,
    backgroundElement: '#F3F5F8',
    border: '#D9DFE7',
    primary: Brand.navy,
    onPrimary: Brand.white,
    accent: Brand.coral,
    danger: '#C62828',
    logoBase: Brand.navy,
  },
  dark: {
    text: Brand.white,
    textSecondary: '#A9B7C8',
    background: Brand.navy,
    backgroundElement: '#16385C',
    border: '#2A4D73',
    primary: Brand.white,
    onPrimary: Brand.navy,
    accent: Brand.coral,
    danger: '#FF8A80',
    logoBase: Brand.white,
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

/** Manrope weights loaded in the root layout; names match the @expo-google-fonts/manrope exports. */
export const Fonts = {
  regular: 'Manrope_400Regular',
  medium: 'Manrope_500Medium',
  semiBold: 'Manrope_600SemiBold',
  bold: 'Manrope_700Bold',
  mono: Platform.select({ ios: 'ui-monospace', default: 'monospace' }),
} as const;

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const Radius = {
  card: 12,
  pill: 999,
} as const;

export const MaxContentWidth = 440;
