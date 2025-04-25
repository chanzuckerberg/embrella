import React, { useState } from 'react';
import styles from './MetadataViz.module.css';


export const MetadataViz = ({ vizResponse, isSuccess, error, isLoading }) => {
    console.log(vizResponse, isSuccess, error,'Viz data aapi response');
     
  return (
    <div className={styles.container}>
      <div className={styles.leftColumn}>
        {/* Filters section */}
        <h2>Filters</h2>
        {/* Add your filter components here */}
      </div>
      <div className={styles.middleColumn}>
        {/* AreTomo Metrics section */}
        <h2>AreTomo Metrics</h2>
        {/* Add your metrics components here */}
      </div>
     
    </div>
  );
};