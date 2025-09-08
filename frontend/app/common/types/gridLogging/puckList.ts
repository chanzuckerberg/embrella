export interface pucksListResponse {
    total_pucks_count: number;
    pucks: PucksList[];
  }
  
  export interface PucksList {
    id: number;
    name: string;
    color: string;
    color_display: string;
    position_in_cane: number;
    max_boxes: number;
    user_id: number;
    user_name: string;
    cane: number;
  }

  //Types for puck slots
  export interface PuckSlotsResponse{
    puck_id:number;
    puck_name:string;
    slots:PuckSlots[];
    slot_summary:{
        total:number;
        filled_count:number;
        empty_count:number;
    }  
  }

  export interface PuckSlots{
    position:number;
    status:string;
    grid_box_id?:number;
  }

  export interface GridBoxDetailResponse{
    puck_id:number;
    puckname:string;
    position_in_puck:number;
    status:'filled' | 'empty';
    max_grids?:number;
    grid_box?:GridBox;   
  }
  export interface GridBox{
    grid_box_id:number;
    name:string;
    color:string;
    color_display:string;
    numbering:string;
    numbering_display:string;
    max_grids:number;
    positions:Position[];
  }
  export interface Position{
    q:number;
    occupied:boolean;
    grid_id?:number;
    grid_name?:string;
  }