import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL,
  withCredentials: true,
  headers: { Accept: 'application/json' },
});

export function getApiFieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError(error)) return {};
  const responseData = error.response?.data as
    | { error?: { details?: unknown } }
    | undefined;
  const details = responseData?.error?.details;
  if (!details || typeof details !== 'object') return {};

  const fieldErrors: Record<string, string> = {};
  for (const [field, value] of Object.entries(details)) {
    if (typeof value === 'string') fieldErrors[field] = value;
    else if (Array.isArray(value)) {
      const messages = value.filter((item): item is string => typeof item === 'string');
      if (messages.length) fieldErrors[field] = messages.join(' ');
    }
  }
  return fieldErrors;
}

apiClient.interceptors.request.use((config) => {
  if (config.method && !['get', 'head', 'options'].includes(config.method.toLowerCase())) {
    const csrfToken = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')
      .slice(1)
      .join('=');

    if (csrfToken) config.headers.set('X-CSRFToken', decodeURIComponent(csrfToken));
  }
  return config;
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const fieldErrors = getApiFieldErrors(error);
    if (Object.keys(fieldErrors).length) return Object.values(fieldErrors).join(' ');
    const apiMessage = error.response?.data?.error?.message;
    if (typeof apiMessage === 'string') return apiMessage;
    if (error.response) return `The server returned an error (${error.response.status}).`;
    return 'The server could not be reached. Check that the Django API is running.';
  }
  return 'Something went wrong. Please try again.';
}
