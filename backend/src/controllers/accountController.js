import {
  accountActivity,
  getAuthenticatedAccount,
  getPreferences,
  login,
  register,
  revokeSession,
  updateAccount,
  updatePreferences,
} from '../services/accountService.js';
import { createCsrfToken, csrfTokenController } from '../middleware/csrf.js';

export function accountController({ pool }) {
  return {
    csrf: csrfTokenController,
    register: async (request, response) => {
      const account = await register(pool, request.validated.body);
      response.status(201).json(account);
    },
    login: async (request, response) => {
      const credentials = request.validated.body;
      const result = await login(
        pool,
        credentials.identifier || credentials.username,
        credentials.password,
      );
      const csrfToken = createCsrfToken(response);
      response.status(200).json({
        ...result.account,
        csrf_token: csrfToken,
        session_token: result.sessionToken,
      });
    },
    logout: async (request, response) => {
      await revokeSession(pool, request.auth.session_id);
      response.status(204).end();
    },
    me: async (request, response) => {
      if (request.method === 'GET') {
        response.json(await getAuthenticatedAccount(pool, request.userId));
        return;
      }
      response.json(await updateAccount(pool, request.userId, request.validated.body));
    },
    preferences: async (request, response) => {
      if (request.method === 'GET') {
        response.json(await getPreferences(pool, request.userId));
        return;
      }
      response.json(await updatePreferences(pool, request.userId, request.validated.body));
    },
    resetPreferences: async (request, response) => {
      response.json(await updatePreferences(pool, request.userId, {}, true));
    },
    activity: async (request, response) => {
      response.json(await accountActivity(pool, request.userId));
    },
  };
}
