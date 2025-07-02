import React from 'react';
import styles from '../MetadataViz.module.css';

interface NanoScaleBarProps {
  angstrom: number;
  style?: React.CSSProperties;
  type?: 'realSpace' | 'ft'; 
}

export default function NanoScaleBar({ angstrom, style, type = 'realSpace' }: NanoScaleBarProps) {
  // Common values
  const imageWidth = 190; // thumbnail width in px
  const imageSize = 4096; // image size in px
  
  if (type === 'realSpace') {
    const fullImageWidthInAngstroms = angstrom * imageSize;
    const scaleBarPhysicalSizeInAngstroms = 1500;
    const scaleBarWidthInPixels = (imageWidth * scaleBarPhysicalSizeInAngstroms) / fullImageWidthInAngstroms;

    const scaleBarLineStyle = {
      width: `${scaleBarWidthInPixels}px`,
      height: '5px',
      backgroundColor: '#000',
      marginLeft: '16px'
    };

    return (
      <div className={styles.scaleBarContainer} style={style}>
        <div className={styles.scaleBarValue} style={{ marginLeft: '16px' }}>{scaleBarPhysicalSizeInAngstroms}Å</div>
        <div style={scaleBarLineStyle} />
      </div>
    );
  } else {
    const d_star_target = 1 / 10; 
    const samplingInterval = 1 / (angstrom * imageSize); // Å⁻¹ per pixel
    const widthInFTPixels = d_star_target / samplingInterval;
    const widthInThumbnailPixels = (widthInFTPixels / imageSize) * imageWidth;

    const ftScaleBarLineStyle = {
      width: `${widthInThumbnailPixels}px`,
      height: '5px',
      backgroundColor: '#000',
    };

    return (
      <div className={styles.scaleBarContainer} style={style}>
        <div className={styles.scaleBarValue}>1/10 Å⁻¹</div>
        <div style={ftScaleBarLineStyle} />
      </div>
    );
  }
}
