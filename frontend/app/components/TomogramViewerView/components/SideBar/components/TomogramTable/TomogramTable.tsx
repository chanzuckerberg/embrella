import React, { useEffect, useRef } from 'react';
import { ReviewTomogramSummary } from '../../../../types';

interface TomogramTableProps {
  tomograms: ReviewTomogramSummary[];
  selectedTomogram?: string | undefined;
  onSelectTomogram: (tomogramId: string) => void;
}
const CONTEXT_ROWS_ABOVE = 2; // Rows of context kept above the selected tomogram
const NARROW_ROW_HEIGHT = 40;
const NARROW_VISIBLE_ROWS = 4;

export const TomogramTable = ({ tomograms, selectedTomogram, onSelectTomogram }: TomogramTableProps) => {
  const listRef = useRef<HTMLDivElement>(null);
  const selectedRowRef = useRef<HTMLDivElement>(null);

  // Park the selected tomogram a couple of rows down instead of at the very top
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;

    const scrollSelectedIntoPosition = () => {
      const row = selectedRowRef.current;
      if (!row) return;
      const rowOffsetInList = row.getBoundingClientRect().top - list.getBoundingClientRect().top;
      list.scrollTop += rowOffsetInList - CONTEXT_ROWS_ABOVE * row.offsetHeight;
    };
    scrollSelectedIntoPosition();
    const observer = new ResizeObserver(scrollSelectedIntoPosition);
    observer.observe(list);
    return () => observer.disconnect();
  }, [selectedTomogram]);

  return (
    <div className="flex flex-col min-h-0 gap-2">
      <div className="grid grid-cols-3 gap-2 font-bold p-2 bg-gray-100 rounded">
        <div>Tomogram</div>
        <div>Status</div>
        <div className="text-center">Reviewed</div>
      </div>

      <div
        ref={listRef}
        className="overflow-y-auto max-lg:max-h-[var(--narrow-list-max-h)]"
        style={{ '--narrow-list-max-h': `${NARROW_ROW_HEIGHT * NARROW_VISIBLE_ROWS}px` } as React.CSSProperties}
      >
        {tomograms.map((tomogram) => {
          const isSelected = selectedTomogram === tomogram.tomogramId;
          const isReviewed = tomogram.status !== 'pending';
          return (
            <div
              key={tomogram.tomogramId}
              ref={isSelected ? selectedRowRef : undefined}
              onClick={() => onSelectTomogram(tomogram.tomogramId)}
              className={`grid grid-cols-3 gap-2 p-2 max-lg:!py-[10px] cursor-pointer rounded ${
                isSelected ? 'bg-blue-100' : 'hover:bg-gray-100 transition-colors duration-100'
              }`}
            >
              <div>{tomogram.position}</div>
              <div>{tomogram.status}</div>
              <div className="flex justify-center items-center">
                <div
                  className={`w-4 h-4 rounded-full border-1 ${
                    isReviewed ? 'bg-gray-300 border-gray-400' : 'border-gray-300'
                  }`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
