import React from 'react';
import { Button } from '@czi-sds/components';

interface FilterControlsProps {
  onReset: () => void;
  onUncheckAll: () => void;
  onApplyFilters: () => void;
}

export const FilterControls: React.FC<FilterControlsProps> = ({ onReset, onUncheckAll, onApplyFilters }) => {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
      <Button sdsType="secondary" sdsStyle="rounded" onClick={onReset}>
        Reset
      </Button>
      <Button sdsType="secondary" sdsStyle="rounded" onClick={onUncheckAll}>
        Uncheck All
      </Button>
      <Button sdsType="primary" sdsStyle="rounded" onClick={onApplyFilters}>
        Apply Filter
      </Button>
    </div>
  );
};
