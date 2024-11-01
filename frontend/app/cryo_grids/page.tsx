import { GridsView } from "@/views/GridsView";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Embrella Cryogrids",
};

const CryoGridsPage = () => {
  return <GridsView />;
};

export default CryoGridsPage;
