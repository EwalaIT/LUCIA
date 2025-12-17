import React, { useRef } from 'react';
import { SidePanelProvider } from "~/Providers/SidePanelContext";
import SidePanelGroup from "~/components/SidePanel/SidePanelGroup";
import ZonesDashboard from '~/components/HomeAssistant/ZonesDashboard';

const ZonesDashboardLayout: React.FC = () => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    return (
        <div className="relative flex w-full grow overflow-hidden bg-presentation">
            <SidePanelProvider>
                <SidePanelGroup defaultCollapsed={false}>
                    <main className="flex h-full flex-col overflow-hidden" role="main">
                        <div
                            ref={scrollContainerRef}
                            className="scrollbar-gutter-stable relative flex h-full flex-col overflow-y-auto overflow-x-hidden"
                        >
                            <ZonesDashboard />
                        </div>
                    </main>
                </SidePanelGroup>
            </SidePanelProvider>
        </div>
    );
};

export default ZonesDashboardLayout;