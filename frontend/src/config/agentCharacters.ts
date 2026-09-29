export interface AgentCharacterConfig {
  key: string;
  name: string;
  role: string;
  friendTitle: string;
  characterName: string;
  characterSpecies: string;
  image: string;
  meaning: string;
  greeting: string;
  uiTone: string;
}

/**
 * Official CLARIO Six-Agent Character Visual Mapping
 * 
 * NOVA   → 🦑 Octopus  (octopus.png)  - Multi-source exploration, research & knowledge gathering
 * MIRA   → 🐼 Panda    (panda.png)    - Friendly, approachable & supportive teaching
 * AYAN   → 🦊 Fox      (fox.png)      - Clever thinking, reasoning & problem solving
 * KIRA   → 🐦⬛ Crow   (crow.png)     - Intelligence, adaptability & practical problem solving
 * ZAYN   → 🐿️ Squirrel (squirrel.png) - Energetic, playful & challenging assessment activities
 * ELARA  → 🦅 Eagle    (101.png)      - Sharp observation, evidence analysis & performance evaluation
 */
export const AGENT_CHARACTERS: Record<string, AgentCharacterConfig> = {
  nova: {
    key: 'nova',
    name: 'Nova',
    role: 'Research Agent',
    friendTitle: 'Research Friend',
    characterName: 'Octopus',
    characterSpecies: '🦑 Octopus',
    image: '/characters/octopus.png',
    meaning: 'Multi-source exploration, research and knowledge gathering.',
    greeting: "I'll find the knowledge we need.",
    uiTone: 'Researching verified curriculum and domain foundations...',
  },
  mira: {
    key: 'mira',
    name: 'Mira',
    role: 'Teaching Agent',
    friendTitle: 'Teaching Friend',
    characterName: 'Panda',
    characterSpecies: '🐼 Panda',
    image: '/characters/panda.png',
    meaning: 'Friendly, approachable and supportive teaching.',
    greeting: "Let's understand this step by step.",
    uiTone: 'Explaining concepts with friendly, approachable clarity.',
  },
  ayan: {
    key: 'ayan',
    name: 'Ayan',
    role: 'Critical Thinking Agent',
    friendTitle: 'Thinking Friend',
    characterName: 'Fox',
    characterSpecies: '🦊 Fox',
    image: '/characters/fox.png',
    meaning: 'Clever thinking, reasoning and problem solving.',
    greeting: "Let's see how you think about this.",
    uiTone: 'Challenging your reasoning, causal connections, and trade-offs.',
  },
  kira: {
    key: 'kira',
    name: 'Kira',
    role: 'Real-World Application Agent',
    friendTitle: 'Real-World Friend',
    characterName: 'Crow',
    characterSpecies: '🐦⬛ Crow',
    image: '/characters/crow.png',
    meaning: 'Intelligence, adaptability and practical problem solving.',
    greeting: "Okay. Now let's use this in the real world.",
    uiTone: 'Connecting theoretical concepts into practical solutions.',
  },
  zayn: {
    key: 'zayn',
    name: 'Zayn',
    role: 'Quiz Agent',
    friendTitle: 'Quiz Friend',
    characterName: 'Squirrel',
    characterSpecies: '🐿️ Squirrel',
    image: '/characters/squirrel.png',
    meaning: 'Energetic, playful and challenging learning activities.',
    greeting: "Ready? Let's test what you know.",
    uiTone: '10-question standardized assessment (5 Easy • 3 Med • 2 Hard).',
  },
  elara: {
    key: 'elara',
    name: 'Elara',
    role: 'Evaluation Agent',
    friendTitle: 'Evaluation Friend',
    characterName: 'Eagle',
    characterSpecies: '🦅 Eagle',
    image: '/characters/101.png',
    meaning: 'Sharp observation, evidence analysis and performance evaluation.',
    greeting: "Let's see what you've actually mastered.",
    uiTone: 'Objective evidence aggregation across all four learning activities.',
  },
};

export const getAgentCharacter = (agentKey: string): AgentCharacterConfig => {
  const normalized = (agentKey || '').toLowerCase().replace(/[-_\s]/g, '');
  if (normalized.includes('nova')) return AGENT_CHARACTERS.nova;
  if (normalized.includes('mira')) return AGENT_CHARACTERS.mira;
  if (normalized.includes('ayan')) return AGENT_CHARACTERS.ayan;
  if (normalized.includes('kira')) return AGENT_CHARACTERS.kira;
  if (normalized.includes('zayn')) return AGENT_CHARACTERS.zayn;
  if (normalized.includes('elara')) return AGENT_CHARACTERS.elara;
  return AGENT_CHARACTERS.mira;
};
