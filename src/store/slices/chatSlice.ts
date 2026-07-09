import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
}

interface ChatState {
  messages: ChatMessage[];
  isTyping: boolean;
  isOpen: boolean;
}

const initialState: ChatState = {
  messages: [
    { id: '1', sender: 'ai', text: 'Hello! I am your AI HCP CRM Assistant. How can I help you log your interaction today?', timestamp: new Date().toISOString() }
  ],
  isTyping: false,
  isOpen: false,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },
    setTyping: (state, action: PayloadAction<boolean>) => {
      state.isTyping = action.payload;
    },
    toggleChat: (state) => {
      state.isOpen = !state.isOpen;
    }
  },
});

export const { addMessage, setTyping, toggleChat } = chatSlice.actions;
export default chatSlice.reducer;
