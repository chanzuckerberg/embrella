import React from 'react';
import styles from '../MetadataViz.module.css';

interface NanoScaleBarProps {
  angstrom: number;
  style?: React.CSSProperties;
}

export default function NanoScaleBar({ angstrom, style }: NanoScaleBarProps) {
  const ÅValueString = (angstrom * 4096).toFixed(2);
  const ÅValue = parseFloat(ÅValueString);

  const imageWidth = 230; //thumbnail width in px
  const scaleBarWidthInPixels = ((imageWidth * 1500) / ÅValue).toFixed(2);

  // Inline styles for the scale bar line
  const scaleBarLineStyle = {
    width: `${scaleBarWidthInPixels}px`,
    height: '5px',
    backgroundColor: '#000',
  };

  return (
    <div className={styles.scaleBarContainer} style={style}>
      <div className={styles.scaleBarValue}> 1500Å</div>

      <div style={scaleBarLineStyle} />
    </div>
  );
}
