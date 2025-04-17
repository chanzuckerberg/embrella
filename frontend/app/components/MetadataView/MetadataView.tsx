"use client";

import React from "react";
import { useFetchData } from "@hooks/useFetchData/useFetchData";
import configs from "@configs/local";
import { API } from "@app/common/constants/api";

interface MetadataViewProps {
  sessionId: string;
}

export const MetadataView = ({ sessionId }: MetadataViewProps): React.JSX.Element => {
  console.log('MetadataView component with session:', sessionId );
  
  
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Metadata View</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl mb-2">Session: </h2>
       "METADATA VIZ"
      </div>
    </div>
  );
};