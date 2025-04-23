export interface MetadataSummaryResponse{
    session_name:string;
    run_number:string;
    data_collection_directory:string;
    aretomo3_processing_directory:string
    computed_metrics: ComputedMetric[];
}

export interface ComputedMetric{
    name:string;
    mean:number;
    median:number;
    std:number;
}