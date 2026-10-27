import { View } from 'react-native';
import Svg, { Path, Rect } from 'react-native-svg';

import { Brand } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

import { WORDMARK_AB, WORDMARK_BANK } from './wordmark-paths';

// Symbol geometry from logo/brand/ab-bank-symbol.svg: three layers rising to a coral summit.
const LAYERS = [
  { x: 88, y: 44, w: 80, summit: true },
  { x: 56, y: 104, w: 144, summit: false },
  { x: 24, y: 164, w: 92, summit: false },
  { x: 140, y: 164, w: 92, summit: false },
];
const LAYER_H = 44;

function Layers({ base }: { base: string }) {
  return LAYERS.map((l) => (
    <Rect
      key={`${l.x}-${l.y}`}
      x={l.x}
      y={l.y}
      width={l.w}
      height={LAYER_H}
      rx={LAYER_H / 2}
      fill={l.summit ? Brand.coral : base}
    />
  ));
}

type LogoProps = {
  variant?: 'symbol' | 'horizontal' | 'stacked';
  /** Height of the symbol in dp; the wordmark scales with it. */
  size?: number;
};

/** AB Bank logo. Colours follow the theme: navy layers on light, white layers on dark; the summit is always coral. */
export function Logo(props: LogoProps) {
  // The wrapper makes the logo a single labelled image for screen readers on every platform.
  return (
    <View accessible accessibilityRole="image" accessibilityLabel="AB Bank">
      <LogoArt {...props} />
    </View>
  );
}

function LogoArt({ variant = 'horizontal', size = 48 }: LogoProps) {
  const base = useTheme().logoBase;

  if (variant === 'symbol') {
    return (
      <Svg width={size} height={size} viewBox="0 0 256 256">
        <Layers base={base} />
      </Svg>
    );
  }

  if (variant === 'horizontal') {
    return (
      <Svg width={(size * 789) / 256} height={size} viewBox="0 0 789 256">
        <Layers base={base} />
        <Path d={WORDMARK_AB} fill={base} />
        <Path d={WORDMARK_BANK} fill={base} />
      </Svg>
    );
  }

  // Stacked: symbol above the wordmark; `size` is the symbol's ink height (layers span y 44–208).
  // The wordmark occupies x 276–766, y 76–174 of the horizontal master.
  const wmW = 490;
  const wmH = 98;
  const gap = 40;
  const width = Math.max(256, wmW);
  const height = 164 + gap + wmH;
  return (
    <Svg
      width={(size * width) / 164}
      height={(size * height) / 164}
      viewBox={`0 44 ${width} ${height}`}>
      <Svg x={(width - 256) / 2} y={0} width={256} height={256} viewBox="0 0 256 256">
        <Layers base={base} />
      </Svg>
      <Svg x={0} y={208 + gap} width={wmW} height={wmH} viewBox={`276 76 ${wmW} ${wmH}`}>
        <Path d={WORDMARK_AB} fill={base} />
        <Path d={WORDMARK_BANK} fill={base} />
      </Svg>
    </Svg>
  );
}
