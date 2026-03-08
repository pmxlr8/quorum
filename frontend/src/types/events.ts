export type ClientEvent =
  | { type: 'audio'; data: string }
  | { type: 'text'; text: string }
  | { type: 'turn_complete' }
  | { type: 'grant_speaking_turn'; agent: string }
  | { type: 'cast_vote'; vote: 'yes' | 'no' | 'abstain' }

export type ServerEvent =
  | { type: 'meeting_status'; payload: { status: string } }
  | { type: 'transcript_update'; payload: { speaker: string; text: string; partial: boolean } }
  | { type: 'audio_chunk'; payload: { data: string; mime: string } }
  | { type: 'turn_complete'; payload: Record<string, never> }
  | { type: 'error'; payload: { message: string } }
  | { type: 'vote_result'; payload: { votes: Record<string, { vote: string }>; result: string } }
  | { type: 'agent_speaking'; payload: { agent: string } }
