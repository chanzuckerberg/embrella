import { SidebarSection } from "../SidebarSection";

interface TomogramInfoProps {
    tomogramId: string;
}

export const TomogramInfo = ({ tomogramId }: TomogramInfoProps) => {
    return (
        <SidebarSection>
            <div>
                <h3>Current Tomogram Info</h3>
                <p>Organism: Mus musculus</p>
                <p>ID: {tomogramId}</p>
            </div>
        </SidebarSection>
    );
};