import React from 'react';
import { RotateCcw } from 'lucide-react';
import { colors } from '../theme/colors';

interface TopNavProps {
  activeTab: 'grid' | 'pipeline' | 'caregiver' | 'inspector';
  setActiveTab: (tab: 'grid' | 'pipeline' | 'caregiver' | 'inspector') => void;
  pendingCount: number;
  onResetDemo: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  activeTab,
  setActiveTab,
  pendingCount,
  onResetDemo
}) => {
  return (
    <header className="sticky top-0 z-40 bg-[#FAF9F6]/85 backdrop-blur-[20px] border-b border-[#EFE9DE] transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-6 px-6 py-4">
        {/* Zone 1: Three-Color Logo with Playfair Display Bold */}
        <div className="flex items-center gap-3.5 shrink-0">
          <a
            href="#home"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('grid');
            }}
            className="group flex items-center gap-3 focus:outline-none"
          >
            {/* The Three-Color Logo Icon: Deep Forest (#1A3226), Warm Sand (#D4A373), Emerald (#34D399) */}
            <div className="relative w-10 h-10 rounded-[14px] bg-[#1A3226] p-2 flex items-center justify-center shadow-[0_4px_12px_rgba(26,50,38,0.18)] transition-transform group-hover:scale-105">
              <div className="w-full h-full relative flex items-center justify-center">
                {/* Interlocking pebble water circles */}
                <div className="absolute w-4 h-4 rounded-full bg-[#D4A373] opacity-90 -translate-x-1 -translate-y-0.5" />
                <div className="absolute w-4 h-4 rounded-full bg-[#34D399] opacity-85 translate-x-1 translate-y-0.5 mix-blend-screen" />
                <div className="relative z-10 w-2 h-2 rounded-full bg-[#FAF9F6] shadow-sm" />
              </div>
            </div>

            <div className="flex flex-col">
              <span className="signature-kicker leading-none mb-1">
                AAC Physical Autonomy
              </span>
              <span className="font-logo text-xl text-[#1A3226] tracking-tight group-hover:text-[#14261d] transition-colors">
                Ripple <span className="text-[#D4A373] font-normal">&amp;</span> Pebble
              </span>
            </div>
          </a>
        </div>

        {/* Zone 2: Navigation Links in Manrope */}
        <nav className="hidden md:flex items-center gap-7 text-sm font-semibold font-body text-[#6B6B6B]">
          <button
            onClick={() => setActiveTab('grid')}
            className={`hover:text-[#141414] transition-colors whitespace-nowrap shrink-0 relative py-1 ${
              activeTab === 'grid' ? 'text-[#1A3226]' : ''
            }`}
          >
            Autonomy Grid
            {activeTab === 'grid' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1A3226] rounded-full" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('pipeline')}
            className={`hover:text-[#141414] transition-colors whitespace-nowrap shrink-0 relative py-1 ${
              activeTab === 'pipeline' ? 'text-[#1A3226]' : ''
            }`}
          >
            Activity Stream
            {activeTab === 'pipeline' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1A3226] rounded-full" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('caregiver')}
            className={`hover:text-[#141414] transition-colors whitespace-nowrap shrink-0 relative py-1 flex items-center gap-2 ${
              activeTab === 'caregiver' ? 'text-[#1A3226]' : ''
            }`}
          >
            <span>Caregiver Portal</span>
            {pendingCount > 0 ? (
              <span className="bg-[#FEF9C3] text-[#B8860B] border border-[#FDE047]/60 rounded-full px-2 py-0.5 text-[10px] font-bold animate-pulse">
                {pendingCount}
              </span>
            ) : (
              <span className="w-1.5 h-1.5 rounded-full bg-[#34D399]" />
            )}
            {activeTab === 'caregiver' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1A3226] rounded-full" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('inspector')}
            className={`hover:text-[#141414] transition-colors whitespace-nowrap shrink-0 relative py-1 ${
              activeTab === 'inspector' ? 'text-[#1A3226]' : ''
            }`}
          >
            Architecture &amp; API
            {activeTab === 'inspector' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1A3226] rounded-full" />
            )}
          </button>
        </nav>

        {/* Zone 3: Single Primary Action Recipe */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onResetDemo}
            title="Reset debounce memory and clear stream"
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-[12px] bg-[#F7F2EA] hover:bg-[#EFE9DE] border border-[#E6DFD2] text-[#141414] transition-all shadow-sm active:scale-95"
          >
            <RotateCcw className="w-3.5 h-3.5 text-[#1A3226]" />
            <span>Reset Stream</span>
          </button>
        </div>
      </div>
    </header>
  );
};
