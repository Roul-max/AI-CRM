import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import axios from 'axios';

export interface InteractionData {
  hcp_name: string | null;
  hospital: string | null;
  specialization: string | null;
  interaction_date: string | null;
  interaction_type: string | null;
  duration: number | null;
  attendees: string[] | null;
  products_discussed: string[] | null;
  shared_materials: string[] | null;
  samples_requested: boolean;
  brochure_shared: boolean;
  competitor_mentioned: string | null;       // primary competitor (single)
  competitors_mentioned: string[] | null;    // all competitors (list)
  sentiment: string | null;
  risk: string | null;
  outcomes: string | null;
  follow_up_date: string | null;
  action_items: string[] | null;
  summary: string | null;
}

interface InteractionState {
  data: InteractionData;
  saveStatus: 'idle' | 'loading' | 'succeeded' | 'failed';
  saveError: string | null;
}

const initialData: InteractionData = {
  hcp_name: null,
  hospital: null,
  specialization: null,
  interaction_date: null,
  interaction_type: null,
  duration: null,
  attendees: [],
  products_discussed: [],
  shared_materials: [],
  samples_requested: false,
  brochure_shared: false,
  competitor_mentioned: null,
  competitors_mentioned: [],
  sentiment: null,
  risk: null,
  outcomes: null,
  follow_up_date: null,
  action_items: [],
  summary: null,
};

const initialState: InteractionState = {
  data: initialData,
  saveStatus: 'idle',
  saveError: null,
};

export const saveInteraction = createAsyncThunk(
  'interaction/saveInteraction',
  async (interactionData: InteractionData, { rejectWithValue }) => {
    try {
      const payload = {
        hcp_name: interactionData.hcp_name ?? 'Unknown HCP',
        hcp_specialization: interactionData.specialization,
        hcp_hospital: interactionData.hospital,
        notes: interactionData.summary || null,
        summary: interactionData.summary || null,
        outcomes: interactionData.outcomes,
        sentiment: interactionData.sentiment,
        risk_level: interactionData.risk,
        action_items: interactionData.action_items ?? [],
        interaction_type: interactionData.interaction_type,
        interaction_date: interactionData.interaction_date,
        duration: interactionData.duration,
        follow_up_date: interactionData.follow_up_date,
        brochure_shared: interactionData.brochure_shared,
        samples_requested: interactionData.samples_requested,
        products_discussed: interactionData.products_discussed ?? [],
        // prefer the full list; fall back to wrapping the single string
        competitors_mentioned: (
          interactionData.competitors_mentioned && interactionData.competitors_mentioned.length > 0
            ? interactionData.competitors_mentioned
            : interactionData.competitor_mentioned
              ? [interactionData.competitor_mentioned]
              : []
        ),
        shared_materials: interactionData.shared_materials ?? [],
        attendees: interactionData.attendees ?? [],
      };
      const response = await axios.post('/api/v1/interactions/', payload);
      return response.data;
    } catch (error: any) {
      if (axios.isAxiosError(error) && error.response) {
        return rejectWithValue(error.response.data);
      }
      return rejectWithValue('An unknown error occurred');
    }
  }
);

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    setInteractionData: (state, action: PayloadAction<InteractionData>) => {
      state.data = { ...initialData, ...action.payload };
      state.saveStatus = 'idle';
    },
    updateField: (
      state,
      action: PayloadAction<{ key: keyof InteractionData; value: InteractionData[keyof InteractionData] }>
    ) => {
      (state.data as any)[action.payload.key] = action.payload.value;
      state.saveStatus = 'idle';
    },
    clearInteractionData: (state) => {
      state.data = initialData;
      state.saveStatus = 'idle';
      state.saveError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(saveInteraction.pending, (state) => {
        state.saveStatus = 'loading';
        state.saveError = null;
      })
      .addCase(saveInteraction.fulfilled, (state) => {
        state.saveStatus = 'succeeded';
      })
      .addCase(saveInteraction.rejected, (state, action) => {
        state.saveStatus = 'failed';
        state.saveError = action.payload as string;
      });
  },
});

export const { setInteractionData, updateField, clearInteractionData } = interactionSlice.actions;
export default interactionSlice.reducer;
