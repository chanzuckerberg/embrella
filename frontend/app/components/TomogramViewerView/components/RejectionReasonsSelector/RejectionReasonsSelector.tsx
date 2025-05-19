import { Button } from '@czi-sds/components';
import React from 'react';

interface RejectionReasonsSelectorProps {
  selectedReasons: string[];
  setSelectedReasons: (reasons: string[]) => void;
  onChange: (status: string, selected: string[]) => void;
}

const REJECTION_REASONS = ['No features of interest', 'Bad tomogram quality', 'Blurry', 'Other'];

export const RejectionReasonsSelector: React.FC<RejectionReasonsSelectorProps> = ({
  selectedReasons,
  setSelectedReasons,
  onChange,
}) => {
  return (
    <div className="mt-4 flex flex-col gap-2">
      <h3 className="m-0 text-base font-semibold">Reason (Optional)</h3>
      <div className="text-sm mb-2">Select all that apply</div>
      {REJECTION_REASONS.map((reason) => (
        <label key={reason} className="flex items-center mb-1 cursor-pointer">
          <input
            type="checkbox"
            checked={selectedReasons.map((r) => r.toLowerCase()).includes(reason.toLowerCase())}
            onChange={() => setSelectedReasons([...selectedReasons, reason])}
            className="!mr-3"
          />
          {reason}
        </label>
      ))}
      <Button
        sdsStyle="square"
        sdsType="secondary"
        fullWidth
        onClick={() => onChange('rejected', [...selectedReasons, 'rejected'])}
      >
        Submit
      </Button>
    </div>
  );
};
