import axios from 'axios'
import type { AnnotationState, StartSessionRequest } from './types'

const http = axios.create({ baseURL: '/api', timeout: 30_000 })

http.interceptors.response.use(
  r => r,
  (error) => {
    const detail = error?.response?.data?.detail
    if (detail) {
      error.message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    return Promise.reject(error)
  }
)

// ── Session ────────────────────────────────────────────────────────────────
export const api = {
  session: {
    start: (req: StartSessionRequest) =>
      http.post<AnnotationState>('/session/start', req).then(r => r.data),
    state: () =>
      http.get<AnnotationState>('/session/state').then(r => r.data),
    stop: () => http.delete('/session'),
  },

  // ── Frame ────────────────────────────────────────────────────────────────
  frame: {
    get: () => http.get<AnnotationState>('/frame').then(r => r.data),
    accept: () => http.post<AnnotationState>('/frame/accept').then(r => r.data),
    reject: () => http.post<AnnotationState>('/frame/reject').then(r => r.data),
    undo: () => http.post<AnnotationState>('/frame/undo').then(r => r.data),
    addManual: (bbox: number[], category_id: number, track_id?: number) =>
      http.post<AnnotationState>('/frame/manual-detection', { bbox, category_id, track_id }).then(r => r.data),
    removeDetection: (source: string, index: number) =>
      http.delete<AnnotationState>('/frame/detection', { params: { source, index } }).then(r => r.data),
    editDetection: (source: string, index: number, patch: object) =>
      http.put<AnnotationState>('/frame/detection', { source, index, ...patch }).then(r => r.data),
    selectDetection: (source: string, index: number) =>
      http.post<AnnotationState>('/frame/select', null, { params: { source, index } }).then(r => r.data),
    clearSelection: () =>
      http.delete<AnnotationState>('/frame/select').then(r => r.data),
    setROI: (points: [number, number][]) =>
      http.post<AnnotationState>('/frame/roi', { points }).then(r => r.data),
    resetROI: () => http.delete<AnnotationState>('/frame/roi').then(r => r.data),
    rotate: (direction: 'cw' | 'ccw') =>
      http.post<AnnotationState>('/frame/rotate', null, { params: { direction } }).then(r => r.data),
  },

  // ── Export ───────────────────────────────────────────────────────────────
  export: {
    run: (opts: {
      output_dir?: string
      train_ratio?: number
      val_ratio?: number
      test_ratio?: number
      augmentation_factor?: number
    }) => http.post('/export', opts).then(r => r.data),
  },

  // ── Wizard ───────────────────────────────────────────────────────────────
  wizard: {
    modes: () => http.get<{ value: string; label: string }[]>('/wizard/modes').then(r => r.data),
    validatePath: (path: string, kind = 'dataset') =>
      http.post<{ exists: boolean; is_dir: boolean; is_file: boolean; path: string }>(
        '/wizard/validate-path', null, { params: { path, kind } }
      ).then(r => r.data),
    getCache: () => http.get<Record<string, unknown>>('/wizard/startup-cache').then(r => r.data),
    saveCache: (data: Record<string, unknown>) =>
      http.post('/wizard/startup-cache', { data }),
    outputStates: (data_root?: string) =>
      http.get('/wizard/output-states', { params: data_root ? { data_root } : {} }).then(r => r.data),
    loadAnnotations: (path: string) =>
      http.get('/wizard/load-annotations', { params: { path } }).then(r => r.data),
    browseFolder: () =>
      http.get<{ path: string }>('/wizard/browse-folder').then(r => r.data),
    browseFile: (kind = 'coco') =>
      http.get<{ path: string }>('/wizard/browse-file', { params: { kind } }).then(r => r.data),
  },
}
