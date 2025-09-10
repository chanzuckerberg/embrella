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