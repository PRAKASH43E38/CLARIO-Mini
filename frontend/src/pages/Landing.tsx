import React from 'react';
import { AGENT_CHARACTERS } from '../config/agentCharacters';

export const Landing: React.FC<{
  onStart: () => void;
}> = ({ onStart }) => {
  const characters = [
    AGENT_CHARACTERS.nova,
    AGENT_CHARACTERS.mira,
    AGENT_CHARACTERS.ayan,
    AGENT_CHARACTERS.kira,
    AGENT_CHARACTERS.zayn,
    AGENT_CHARACTERS.elara,
  ];

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col items-center justify-center p-6 relative">
      <main className="max-w-4xl w-full text-center space-y-8 p-6 md:p-10 flex flex-col items-center">
        {/* Playful Static Brand Badge (Strictly No Animation) */}
        <div className="relative">
          <div className="w-20 h-20 rounded-3xl bg-[#58cc02] border-b-6 border-[#46a302] flex items-center justify-center text-4xl text-white shadow-sm">
            🌱
          </div>
        </div>

        {/* Tagline Pill */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-black tracking-wider uppercase border-2 border-emerald-200 bg-[#f0fdf4] text-[#15803d]">
          CLARIO-AI • MAIN ORCHESTRATOR & 6 LEARNING COMPANIONS
        </div>

        {/* Brand Headline */}
        <div className="space-y-2">
          <h1 className="text-5xl md:text-7xl font-black tracking-tight text-slate-900">
            CLARIO
          </h1>
          <p className="text-2xl md:text-3xl font-extrabold text-[#46a302]">
            &ldquo;Come confused. Leave with clarity.&rdquo;
          </p>
        </div>

        <p className="text-base md:text-lg text-slate-600 max-w-2xl mx-auto font-medium leading-relaxed">
          Master any subject with <strong className="text-slate-900">CLARIO-AI</strong> and your 6 dedicated animal learning companions — from exploration and socratic reasoning to practical problem solving and objective evaluation.
        </p>

        {/* Official 6 Agent Characters Display (Static, Clean, Responsive) */}
        <div className="w-full pt-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {characters.map((char) => (
              <div
                key={char.key}
                className="card-duo p-4 text-center bg-white flex flex-col items-center justify-between"
              >
                <img
                  src={char.image}
                  alt={char.name}
                  className="w-24 h-24 sm:w-28 sm:h-28 object-contain mb-2"
                />
                <h4 className="font-black text-sm text-slate-900">{char.name}</h4>
                <p className="text-[11px] font-bold text-[#46a302]">{char.characterSpecies}</p>
                <p className="text-[10px] text-slate-400 font-extrabold uppercase mt-0.5">{char.friendTitle}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4 w-full max-w-sm">
          <button
            onClick={onStart}
            className="btn-duo-green w-full py-4 text-base tracking-wider cursor-pointer"
          >
            GET STARTED 🚀
          </button>
        </div>
      </main>
    </div>
  );
};
