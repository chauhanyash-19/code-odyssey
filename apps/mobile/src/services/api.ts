import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

interface CallAnalysisResult {
  callId: string;
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  deepfakeDetected: boolean;
  voiceAuthenticity: number;
  latency: number;
  transcript?: string;
  flaggedPhrases?: string[];
}

interface ReportSubmission {
  callId: string;
  callerId: string;
  scamType: string;
  description: string;
  timestamp: string;
}

interface CallHistory {
  id: string;
  callerId: string;
  callerNumber: string;
  duration: number;
  riskLevel: string;
  timestamp: string;
  status: 'blocked' | 'monitored' | 'safe';
}

class PhaseGuardAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth tokens
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.status, error.message);
        return Promise.reject(error);
      }
    );
  }

  async analyzeCall(callMetadata: {
    callerId: string;
    callerNumber: string;
    audioStream?: Blob;
  }): Promise<ApiResponse<CallAnalysisResult>> {
    try {
      const formData = new FormData();
      formData.append('callerId', callMetadata.callerId);
      formData.append('callerNumber', callMetadata.callerNumber);
      if (callMetadata.audioStream) {
        formData.append('audio', callMetadata.audioStream);
      }

      const response = await this.client.post<ApiResponse<CallAnalysisResult>>(
        '/calls/analyze',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Analysis failed',
      };
    }
  }

  async blockAndReport(report: ReportSubmission): Promise<ApiResponse<{ reportId: string }>> {
    try {
      const response = await this.client.post<ApiResponse<{ reportId: string }>>(
        '/calls/block-report',
        report
      );
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Report submission failed',
      };
    }
  }

  async getCallHistory(limit: number = 50): Promise<ApiResponse<CallHistory[]>> {
    try {
      const response = await this.client.get<ApiResponse<CallHistory[]>>(
        `/calls/history?limit=${limit}`
      );
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch call history',
      };
    }
  }

  async getReports(limit: number = 50): Promise<ApiResponse<ReportSubmission[]>> {
    try {
      const response = await this.client.get<ApiResponse<ReportSubmission[]>>(
        `/reports?limit=${limit}`
      );
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch reports',
      };
    }
  }

  async getProtectionStatus(): Promise<ApiResponse<{
    isActive: boolean;
    lastUpdate: string;
    callsMonitored: number;
    threatsBlocked: number;
  }>> {
    try {
      const response = await this.client.get(
        '/status/protection'
      );
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch protection status',
      };
    }
  }

  async continueMonitoring(callId: string): Promise<ApiResponse<{ monitoringId: string }>> {
    try {
      const response = await this.client.post<ApiResponse<{ monitoringId: string }>>(
        `/calls/${callId}/monitor`
      );
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to start monitoring',
      };
    }
  }

  async getFactCheckResults(claim: string): Promise<ApiResponse<{
    claim: string;
    verdict: 'true' | 'false' | 'unverified';
    confidence: number;
    sources: string[];
  }>> {
    try {
      const response = await this.client.post(
        '/verify/fact-check',
        { claim }
      );
      return response.data;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Fact check failed',
      };
    }
  }
}

export default new PhaseGuardAPI();
