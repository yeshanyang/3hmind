export type MessageRole = 'user' | 'agent' | 'system';

export interface Message {
  id: string;
  text: string;
  role: MessageRole;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface Goal {
  id: number;
  goal: string;
  progress: number;
  priority: number;
  created_at?: string;
}

export interface InquiryQuestion {
  index: number;
  text: string;
  asked: boolean;
  answer_summary?: string;
}

export interface Profile {
  role: string;
  current_situation: string;
  emotional_state: string;
}

export type ConvState = 'idle' | 'listening' | 'processing' | 'speaking';
