import React from 'react';
import styles from '../MetadataViz.module.css';

interface NanoScaleBarProps {
  angstrom: number;
  style?: React.CSSProperties;
}

export default function NanoScaleBar({ angstrom, style }: NanoScaleBarProps) {
  const nm = (angstrom * 4096).toFixed(3);

  return (
    <div className={styles.scaleBarContainer} style={style}>
      <div className={styles.scaleBarValue}>{nm} nm</div>
      <div className={styles.scaleBarLine} />
    </div>
  );
}