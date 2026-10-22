export function errorHandler({ logger = console }) {
  return (error, request, response, _next) => {
    const statusCode = Number.isInteger(error.statusCode)
      ? error.statusCode
      : Number.isInteger(error.status) && error.status >= 400 && error.status <= 599
        ? error.status
      : error.type === 'entity.parse.failed'
        ? 400
        : error.type === 'entity.too.large'
          ? 413
          : 500;
    if (statusCode >= 500) {
      logger.error('Unhandled API error:', {
        method: request.method,
        path: request.path,
        code: error.code || error.name,
      });
    }
    response.status(statusCode).json({
      error: {
        status_code: statusCode,
        message: statusCode >= 500 ? 'The server encountered an error.' : error.message,
        details: error.details || {},
      },
    });
  };
}
