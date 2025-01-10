import { Metadata } from "next";
import { GridsView } from "@app/components/GridsView/GridsView";

export const metadata: Metadata = {
  title: "Embrella Grids",
};

const GridsPage = () => {
  return <GridsView />;
};

export default GridsPage;
