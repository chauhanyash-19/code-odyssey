import { create } from 'zustand';
import PhaseGuardAPI from '../services/api';

interface CallAnalysis {
  callId: string;
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  deepfakeDetected: boolean;
  voiceAuthenticity: number;
  latency: number;
}

interface AppState {
  // Call monitoring
  currentCall: CallAnalysis | null;
  callHistory: any[];
  reports: any[];

  // Protection status
  isProtectionActive: boolean;
  threatsBlocked: number;
  callsMonitored: number;

  // UI state
  isLoading: boolean;
  error: string | null;

  // Actions
  analyzeCall: (metadata: any) => Promise<void>;
  blockAndReport: (report: any) => Promise<void>;
  fetchCallHistory: () => Promise<void>;
  fetchReports: () => Promise<void>;
  fetchProtectionStatus: () => Promise<void>;
  continueMonitoring: (callId: string) => Promise<void>;
  clearError: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentCall: null,
  callHistory: [],
  reports: [],
  isProtectionActive: true,
  threatsBlocked: 0,
  callsMonitored: 0,
  isLoading: false,
  error: null,

  analyzeCall: async (metadata) => {
    set({ isLoading: true, error: null });
    try {
      const result = await PhaseGuardAPI.analyzeCall(metadata);
      if (result.success && result.data) {
        set({
          currentCall: result.data,
          isLoading: false,
        });
      } else {
        set({
          error: result.error || 'Analysis failed',
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      });
    }
  },

  blockAndReport: async (report) => {
    set({ isLoading: true, error: null });
    try {
      const result = await PhaseGuardAPI.blockAndReport(report);
      if (result.success) {
        set({ isLoading: false });
        // Refresh reports
        const reportsResult = await PhaseGuardAPI.getReports();
        if (reportsResult.success && reportsResult.data) {
          set({ reports: reportsResult.data });
        }
      } else {
        set({
          error: result.error || 'Report submission failed',
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      });
    }
  },

  fetchCallHistory: async () => {
    set({ isLoading: true, error: null });
    try {
      const result = await PhaseGuardAPI.getCallHistory();
      if (result.success && result.data) {
        set({
          callHistory: result.data,
          isLoading: false,
        });
      } else {
        set({
          error: result.error || 'Failed to fetch call history',
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      });
    }
  },

  fetchReports: async () => {
    set({ isLoading: true, error: null });
    try {
      const result = await PhaseGuardAPI.getReports();
      if (result.success && result.data) {
        set({
          reports: result.data,
          isLoading: false,
        });
      } else {
        set({
          error: result.error || 'Failed to fetch reports',
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      });
    }
  },

  fetchProtectionStatus: async () => {
    try {
      const result = await PhaseGuardAPI.getProtectionStatus();
      if (result.success && result.data) {
        set({
          isProtectionActive: result.data.isActive,
          callsMonitored: result.data.callsMonitored,
          threatsBlocked: result.data.threatsBlocked,
        });
      }
    } catch (error) {
      console.error('Failed to fetch protection status:', error);
    }
  },

  continueMonitoring: async (callId) => {
    set({ isLoading: true, error: null });
    try {
      const result = await PhaseGuardAPI.continueMonitoring(callId);
      if (result.success) {
        set({ isLoading: false });
      } else {
        set({
          error: result.error || 'Monitoring failed',
          isLoading: false,
        });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));
