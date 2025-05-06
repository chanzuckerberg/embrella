import React from 'react';
import styles from './MetadataViz.module.css';

export const MiniHistogram: React.FC = () => {
  return (
    <div className={styles.miniHistogram}>
      <div className={styles.bar} style={{ height: '100%' }}></div>
      <div className={styles.bar} style={{ height: '80%' }}></div>
      <div className={styles.bar} style={{ height: '60%' }}></div>
      <div className={styles.bar} style={{ height: '40%' }}></div>
      <div className={styles.bar} style={{ height: '20%' }}></div>
    </div>
  );
};
