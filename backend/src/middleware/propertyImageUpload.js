import multer from 'multer';
import { ApiError } from '../errors.js';
import { MAX_IMAGE_SIZE_BYTES } from '../services/propertyImageService.js';

const parseMultipart = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: MAX_IMAGE_SIZE_BYTES,
    files: 1,
    fields: 2,
    parts: 3,
    fieldNameSize: 100,
    fieldSize: 2048,
  },
}).single('image');

export function propertyImageUpload(request, response, next) {
  parseMultipart(request, response, (error) => {
    if (!error) {
      next();
      return;
    }
    if (error.code === 'LIMIT_FILE_SIZE') {
      next(new ApiError(413, 'Image files must be 10 MB or smaller.'));
      return;
    }
    if (error.code === 'LIMIT_UNEXPECTED_FILE') {
      next(new ApiError(400, 'Upload one image using the image field.'));
      return;
    }
    if (error instanceof multer.MulterError) {
      next(new ApiError(400, 'The image upload request is invalid.'));
      return;
    }
    next(error);
  });
}
