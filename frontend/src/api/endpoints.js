import client from './client';

// ---------- Auth ----------
export const authApi = {
  register: (data) => client.post('/auth/register/', data),
  login: (data) => client.post('/auth/login/', data),
  logout: (refresh) => client.post('/auth/logout/', { refresh }),
  profile: () => client.get('/auth/profile/'),
  updateProfile: (data) => client.patch('/auth/profile/', data),
  changePassword: (data) => client.post('/auth/change-password/', data),
  activity: () => client.get('/auth/activity/'),
  dashboard: () => client.get('/auth/dashboard/'),
};

// ---------- Projects ----------
export const projectsApi = {
  list: (params) => client.get('/projects/', { params }),
  get: (id) => client.get(`/projects/${id}/`),
  create: (data) => client.post('/projects/', data),
  update: (id, data) => client.patch(`/projects/${id}/`, data),
  remove: (id) => client.delete(`/projects/${id}/`),
  download: (id) =>
    client.get(`/projects/${id}/download/`, { responseType: 'blob' }),
  share: (id, data) => client.post(`/projects/${id}/share/`, data),
  members: (id) => client.get(`/projects/${id}/members/`),
  removeMember: (id, memberId) => client.delete(`/projects/${id}/members/${memberId}/`),
};

// ---------- Files ----------
export const filesApi = {
  list: (projectId) => client.get(`/projects/${projectId}/files/`),
  get: (projectId, fileId) => client.get(`/projects/${projectId}/files/${fileId}/`),
  create: (projectId, data) => client.post(`/projects/${projectId}/files/`, data),
  update: (projectId, fileId, data) => client.patch(`/projects/${projectId}/files/${fileId}/`, data),
  remove: (projectId, fileId) => client.delete(`/projects/${projectId}/files/${fileId}/`),
  upload: (projectId, formData) =>
    client.post(`/projects/${projectId}/files/upload/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  download: (projectId, fileId) =>
    client.get(`/projects/${projectId}/files/${fileId}/download/`, { responseType: 'blob' }),
  versions: (projectId, fileId) => client.get(`/projects/${projectId}/files/${fileId}/versions/`),
  restore: (projectId, fileId, versionNumber) =>
    client.post(`/projects/${projectId}/files/${fileId}/restore/${versionNumber}/`),
};

// ---------- Comments ----------
export const commentsApi = {
  list: (projectId) => client.get(`/projects/${projectId}/comments/`),
  create: (projectId, data) => client.post(`/projects/${projectId}/comments/`, data),
  update: (projectId, commentId, data) => client.patch(`/projects/${projectId}/comments/${commentId}/`, data),
  remove: (projectId, commentId) => client.delete(`/projects/${projectId}/comments/${commentId}/`),
};

// ---------- AI features ----------
export const aiApi = {
  explain: (payload) => client.post('/ai/explain/', payload),
  findBugs: (payload) => client.post('/ai/find-bugs/', payload),
  fixBugs: (payload) => client.post('/ai/fix-bugs/', payload),
  optimize: (payload) => client.post('/ai/optimize/', payload),
  generateCode: (payload) => client.post('/ai/generate-code/', payload),
  convert: (payload) => client.post('/ai/convert/', payload),
  generateComments: (payload) => client.post('/ai/generate-comments/', payload),
  generateDocs: (payload) => client.post('/ai/generate-docs/', payload),
  generateTests: (payload) => client.post('/ai/generate-tests/', payload),
  generateSql: (payload) => client.post('/ai/generate-sql/', payload),
  explainError: (payload) => client.post('/ai/explain-error/', payload),
  securityScan: (payload) => client.post('/ai/security-scan/', payload),
  qualityScore: (payload) => client.post('/ai/quality-score/', payload),
  complexity: (payload) => client.post('/ai/complexity/', payload),
  codeReview: (payload) => client.post('/ai/code-review/', payload),
  history: () => client.get('/ai/history/'),
};

// ---------- Collaboration ----------
export const collaborationApi = {
  sharedProjects: () => client.get('/collaboration/shared-projects/'),
  reviewHistory: (projectId) => client.get('/collaboration/review-history/', { params: { project_id: projectId } }),
  activity: (projectId) => client.get('/collaboration/activity/', { params: { project_id: projectId } }),
};

// ---------- Admin ----------
export const adminApi = {
  overview: () => client.get('/admin-panel/overview/'),
  users: (params) => client.get('/admin-panel/users/', { params }),
  updateUser: (id, data) => client.patch(`/admin-panel/users/${id}/`, data),
  deleteUser: (id) => client.delete(`/admin-panel/users/${id}/`),
  projects: (params) => client.get('/admin-panel/projects/', { params }),
  projectAction: (id, action) => client.post(`/admin-panel/projects/${id}/action/`, { action }),
  aiUsageStats: (days) => client.get('/admin-panel/stats/ai-usage/', { params: { days } }),
  reviewStats: () => client.get('/admin-panel/stats/reviews/'),
  settings: () => client.get('/admin-panel/settings/'),
  setSetting: (data) => client.post('/admin-panel/settings/', data),
};
