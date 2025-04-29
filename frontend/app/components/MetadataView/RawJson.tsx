import React, { useState } from 'react';
import ReactJson from 'react-json-view';
import styles from './MetadataViz.module.css';
import { Card, CardHeader } from "@mui/material";
import { Icon } from "@czi-sds/components";


// Mock data for demonstration
const mockData = {
    "Selected runs": [
        "Position_6_2",
        "Position_7_3"
    ],
    "Filtering range": {
        "Thickness": "2000-3000Å"
    }
};

interface RawJsonProps {
    isOpen: boolean;
    onClose: () => void;
}

export const RawJson: React.FC<RawJsonProps> = ({ isOpen, onClose }) => {

    const handleCopy = () => {
        const jsonString = JSON.stringify(mockData, null, 2);
        navigator.clipboard.writeText(jsonString);
    };

    const handleDownload = () => {
        const jsonString = JSON.stringify(mockData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'metadata.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className={`${styles.sidebar} ${isOpen ? styles.open : ''}`}>
            <div className={styles.sidebarContent}>
                <Card elevation={2}>
                    <CardHeader
                        title="Raw JSON"
                        sx={{
                            backgroundColor: '#f5f5f5',
                            borderBottom: '1px solid #e0e0e0',
                        }}
                        action={
                            <div style={{ display: 'flex', flexDirection: 'row' , gap: '9px'}}>
                                <div onClick={()=>{handleCopy()}}>
                                    <Icon color="green" sdsIcon="Copy" sdsSize="s" sdsType="interactive"  />
                                </div>
                                <div onClick={()=>{handleDownload()}}>
                                    <Icon color="green" sdsIcon="Download" sdsSize="s" sdsType="interactive" />
                                </div>
                                <div onClick={()=>{onClose()}}>
                                    <Icon color="green" sdsIcon="XMark" sdsSize="s" sdsType="interactive"/>
                                </div>
                            </div>
                        }
                    />
                    <div className={styles.jsonContainer}>
                        <ReactJson 
                            src={mockData}
                            theme="monokai"
                            displayDataTypes={true}
                            enableClipboard={false}
                            collapsed={1}
                            style={{padding:15}}
                        />
                    </div>
                </Card>
            </div>
        </div>
    );
};