"use client";

import React from "react";
import { MetadataSummary } from "./MetadataSummary";

interface MetadataViewProps {
  sessionName: string;
  runNumber: string;
}

export const MetadataView = ({
  sessionName,
  runNumber,
}: MetadataViewProps): React.JSX.Element => {
  return (
    <div>
      <MetadataSummary sessionName={sessionName} runNumber={runNumber} />
    </div>
  );
};
