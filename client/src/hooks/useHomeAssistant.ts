// client/src/hooks/useHomeAssistant.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    HAZone,    
    HAEvent,
    HAState,
    HAConfig,
    HAService,
    HACommand,
    HAErrorLog,
    HAComponent,
    HACameraStream,
    HAHistoryEntry,
    HALogbookEntry,
    HADashboardData,
    HACommandResponse,
} from '@/common/home-assistant-types';

import * as HAApi from '../data-provider/HomeAssistant/api';

/**
 * --- Queries (React Query) ---
 */

// Dashboard
export const useHADashboard = () =>
    useQuery<HADashboardData, Error>({
        queryKey: ['ha-dashboard'],
        queryFn: HAApi.fetchDashboardData,
        staleTime: 5000,
        refetchInterval: 10000,
    });
    
// Devices
export const useHADevices = () =>
    useQuery<HAState[]>({
        queryKey: ['haDevices'],
        queryFn: async () => {
            const states = await HAApi.fetchStates();
            // filtrar solo dispositivos
            return states.filter(state => state.entity_id.startsWith('device_'));
        },
        refetchInterval: 5000,
    });

// States
export const useHAStates = () =>
    useQuery<HAState[]>({
        queryKey: ['haStates'],
        queryFn: HAApi.fetchStates,
        refetchInterval: 5000,
    });

export const useHAState = (entityId: string) =>
    useQuery<HAState>({
        queryKey: ['haState', entityId],
        queryFn: () => HAApi.fetchState(entityId),
        enabled: !!entityId,
        refetchInterval: 5000,
    });

// Services
export const useHAServices = () =>
    useQuery<HAService[]>({
        queryKey: ['haServices'],
        queryFn: HAApi.fetchServices,
    });

// Events
export const useHAEvents = () =>
    useQuery<HAEvent[]>({
        queryKey: ['haEvents'],
        queryFn: HAApi.fetchEvents,
    });

// Config
export const useHAConfig = () =>
    useQuery<HAConfig>({
        queryKey: ['haConfig'],
        queryFn: HAApi.fetchConfig,
    });

// Components
export const useHAComponents = () =>
    useQuery<HAComponent[]>({
        queryKey: ['haComponents'],
        queryFn: HAApi.fetchComponents,
    });

// History
export const useHAHistory = (timestamp?: string) =>
    useQuery<HAHistoryEntry[]>({
        queryKey: ['haHistory', timestamp ?? 'latest'],
        queryFn: () => HAApi.fetchHistory(timestamp),
    });

// Logbook
export const useHALogbook = (timestamp?: string) =>
    useQuery<HALogbookEntry[]>({
        queryKey: ['haLogbook', timestamp ?? 'latest'],
        queryFn: () => HAApi.fetchLogbook(timestamp),
    });

// Error log
export const useHAErrorLog = () =>
    useQuery<HAErrorLog>({
        queryKey: ['haErrorLog'],
        queryFn: HAApi.fetchErrorLog,
    });

// Camera stream
export const useHACameraStream = (entityId: string) =>
    useQuery<HACameraStream>({
        queryKey: ['haCameraStream', entityId],
        queryFn: () => HAApi.fetchCameraStream(entityId),
        enabled: !!entityId,
    });

/**
 * --- Mutations ---
 */
export const useHACommand = () => {
    const queryClient = useQueryClient();

    return useMutation<HACommandResponse, Error, HACommand>({
        mutationFn: HAApi.executeCommand,
        onSuccess: async () => {
            // Refresca dashboard y states para sincronizar
            await queryClient.invalidateQueries({ queryKey: ['ha-dashboard'] });
            await queryClient.invalidateQueries({ queryKey: ['haStates'] });
        },
        onError: (error) => {
            console.error('Command execution failed:', error);
            // aquí puedes disparar un toast o notificación
        },
    });
};
