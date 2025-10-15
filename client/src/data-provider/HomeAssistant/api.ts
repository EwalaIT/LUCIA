import {
  HAZone,
  HAState,
  HAEvent,
  HAConfig,
  HACommand,
  HAService,
  HAComponent,
  HAHistoryEntry,
  HALogbookEntry,
  HADashboardData,
  HACommandResponse,
} from '@/common/home-assistant-types';

/**
 * Helper genérico para manejar respuestas de fetch
 */
const handleResponse = async <T>(res: Response): Promise<T> => {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Failed request');
  }
  return res.json() as Promise<T>;
};

/**
 * --- API fetchers ---
 */

// Dashboard
export const fetchDashboardData = async (): Promise<HADashboardData> =>
  handleResponse(await fetch('/api/homeassistant/dashboard'));

// States
export const fetchStates = async (): Promise<HAState[]> =>
  handleResponse(await fetch('/api/homeassistant/states'));

export const fetchState = async (entityId: string): Promise<HAState> =>
  handleResponse(await fetch(`/api/homeassistant/states/${entityId}`));

// Services
export const fetchServices = async (): Promise<HAService[]> =>
  handleResponse(await fetch('/api/homeassistant/services'));

// Events
export const fetchEvents = async (): Promise<HAEvent[]> =>
  handleResponse(await fetch('/api/homeassistant/events'));

// Config
export const fetchConfig = async (): Promise<HAConfig> =>
  handleResponse(await fetch('/api/homeassistant/config'));

// Components
export const fetchComponents = async (): Promise<HAComponent[]> =>
  handleResponse(await fetch('/api/homeassistant/components'));

// History
export const fetchHistory = async (
  timestamp?: string,
): Promise<HAHistoryEntry[]> =>
  handleResponse(
    await fetch(`/api/homeassistant/history/period/${timestamp ?? ''}`),
  );

// Logbook
export const fetchLogbook = async (
  timestamp?: string,
): Promise<HALogbookEntry[]> =>
  handleResponse(await fetch(`/api/homeassistant/logbook/${timestamp ?? ''}`));

// Error log (texto plano)
export const fetchErrorLog = async (): Promise<string> => {
  const res = await fetch('/api/homeassistant/error_log');
  if (!res.ok) throw new Error('Failed to fetch error log');
  return res.text();
};

// Camera stream (binario)
export const fetchCameraStream = async (entityId: string): Promise<Blob> => {
  const res = await fetch(`/api/homeassistant/camera_proxy/${entityId}`);
  if (!res.ok) throw new Error(`Failed to fetch camera stream for ${entityId}`);
  return res.blob();
};

// Command
export const executeCommand = async (
  command: HACommand,
): Promise<HACommandResponse> =>
  handleResponse(
    await fetch('/api/homeassistant/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    }),
  );
