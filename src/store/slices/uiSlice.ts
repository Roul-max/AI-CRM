import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface Toast {
  id: string;
  type: 'success' | 'error';
  message: string;
}

interface UiState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  toasts: Toast[];
  isExtracting: boolean;
}

const initialState: UiState = {
  theme: 'light',
  sidebarOpen: true,
  toasts: [],
  isExtracting: false,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
    addToast: (state, action: PayloadAction<Omit<Toast, 'id'>>) => {
      state.toasts.push({ ...action.payload, id: Date.now().toString() });
    },
    removeToast: (state, action: PayloadAction<string>) => {
      state.toasts = state.toasts.filter((t) => t.id !== action.payload);
    },
    setExtracting: (state, action: PayloadAction<boolean>) => {
      state.isExtracting = action.payload;
    },
  },
});

export const { toggleTheme, toggleSidebar, setSidebarOpen, addToast, removeToast, setExtracting } = uiSlice.actions;
export default uiSlice.reducer;
