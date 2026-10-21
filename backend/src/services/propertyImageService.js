import { randomUUID } from 'node:crypto';
import { mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import { ApiError } from '../errors.js';
import { withTransaction } from '../db.js';

export const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;
const MAX_IMAGE_PIXELS = 50_000_000;
const allowedFormats = new Map([
  ['jpeg', { extension: 'jpg', contentType: 'image/jpeg' }],
  ['png', { extension: 'png', contentType: 'image/png' }],
  ['webp', { extension: 'webp', contentType: 'image/webp' }],
]);

function escapeXml(value) {
  return value.replace(/[<>&"']/g, (character) => ({
    '<': '&lt;',
    '>': '&gt;',
    '&': '&amp;',
    '"': '&quot;',
    "'": '&apos;',
  })[character]);
}

function watermarkSvg(width, height, siteName, phone, logoDataUri) {
  const safeName = escapeXml(siteName);
  const safePhone = escapeXml(phone);
  const scale = Math.max(0.55, Math.min(width, height) / 700);
  const margin = Math.max(6, Math.round(12 * scale));
  const padding = Math.max(6, Math.round(10 * scale));
  const fontSize = Math.max(10, Math.round(15 * scale));
  const phoneSize = Math.max(9, Math.round(11 * scale));
  const markSize = Math.max(20, Math.round(34 * scale));
  const textWidth = Math.max(safeName.length * fontSize * 0.62, safePhone.length * phoneSize * 0.62);
  const panelWidth = Math.min(width - margin * 2, markSize + padding * 3 + textWidth);
  const panelHeight = Math.min(height - margin * 2, Math.max(markSize, fontSize + (phone ? phoneSize + 4 : 0)) + padding * 2);
  const left = Math.max(margin, width - margin - panelWidth);
  const top = Math.max(margin, height - margin - panelHeight);
  const textX = left + padding + markSize + padding;
  const textY = top + padding + fontSize;
  const centerFont = Math.max(10, Math.min(28, Math.round(Math.min(width, height) * 0.065)));
  const logo = logoDataUri
    ? `<image x="${left + padding}" y="${top + padding}" width="${markSize}" height="${markSize}" preserveAspectRatio="xMidYMid meet" href="${logoDataUri}"/>`
    : `<path d="M${left + padding + 2} ${top + padding + markSize * 0.42}l${markSize * 0.4} -${markSize * 0.3} ${markSize * 0.4} ${markSize * 0.3}v${markSize * 0.4}h-${markSize * 0.3}v-${markSize * 0.25}h-${markSize * 0.2}v${markSize * 0.25}h-${markSize * 0.3}z" fill="#fff"/>`;

  return Buffer.from(`<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
    <g opacity="0.86">
      <rect x="${left}" y="${top}" width="${panelWidth}" height="${panelHeight}" rx="${Math.max(4, padding)}" fill="#0d1f31" stroke="#fff"/>
      ${logo}
      <text x="${textX}" y="${textY}" fill="#fff" font-family="Arial,sans-serif" font-size="${fontSize}" font-weight="700">${safeName}</text>
      ${phone ? `<text x="${textX}" y="${textY + phoneSize + 4}" fill="#fff" font-family="Arial,sans-serif" font-size="${phoneSize}">${safePhone}</text>` : ''}
    </g>
    <text x="${width / 2}" y="${height / 2}" text-anchor="middle" dominant-baseline="middle"
      fill="#f3c5c9" fill-opacity=".85" stroke="#0d1f31" stroke-opacity=".85" stroke-width="2"
      paint-order="stroke" font-family="Arial,sans-serif" font-size="${centerFont}">@Infinity House</text>
  </svg>`);
}

export async function prepareImageUpload(file, branding = {}) {
  if (!file?.buffer || !Buffer.isBuffer(file.buffer)) {
    throw new ApiError(400, 'Choose a property image to upload.');
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    throw new ApiError(413, 'Image files must be 10 MB or smaller.');
  }

  try {
    const image = sharp(file.buffer, { failOn: 'error', limitInputPixels: MAX_IMAGE_PIXELS });
    const metadata = await image.metadata();
    const format = allowedFormats.get(metadata.format);
    if (!format || !metadata.width || !metadata.height) {
      throw new ApiError(400, 'Property photos must be valid JPEG, PNG, or WebP images.');
    }
    if (metadata.width < 256 || metadata.height < 160) {
      throw new ApiError(400, 'Property photos must be at least 256 by 160 pixels.');
    }

    const oriented = await sharp(file.buffer, {
      failOn: 'error',
      limitInputPixels: MAX_IMAGE_PIXELS,
    }).rotate().toBuffer();
    const orientedMetadata = await sharp(oriented).metadata();
    const overlay = watermarkSvg(
      orientedMetadata.width,
      orientedMetadata.height,
      branding.siteName || 'Infinity House',
      branding.phone || '',
      branding.logoDataUri || '',
    );
    let publicPipeline = sharp(oriented).composite([{ input: overlay }]);
    if (metadata.format === 'jpeg') publicPipeline = publicPipeline.jpeg({ quality: 92, mozjpeg: true });
    if (metadata.format === 'png') publicPipeline = publicPipeline.png({ compressionLevel: 8 });
    if (metadata.format === 'webp') publicPipeline = publicPipeline.webp({ quality: 92 });
    const publicBuffer = await publicPipeline.toBuffer();
    const originalFilename = path.basename(String(file.originalname || 'property-image'))
      .replace(/[\u0000-\u001f\u007f]/g, '')
      .slice(0, 255) || 'property-image';
    return {
      contentType: format.contentType,
      extension: format.extension,
      width: orientedMetadata.width,
      height: orientedMetadata.height,
      originalFilename,
      originalBuffer: file.buffer,
      publicBuffer,
    };
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(400, 'The uploaded image could not be decoded. Choose a valid JPEG, PNG, or WebP image.');
  }
}

export function storedMediaPath(root, storedName, expectedDirectory) {
  if (
    typeof storedName !== 'string'
    || !storedName
    || storedName.includes('\\')
    || storedName.startsWith('/')
    || storedName.split('/').some((segment) => !segment || segment === '.' || segment === '..')
    || storedName.split('/').length !== 2
    || storedName.split('/')[0] !== expectedDirectory
  ) {
    throw new ApiError(404, 'Image not found.');
  }
  const fullPath = path.resolve(root, storedName);
  if (!fullPath.startsWith(path.resolve(root) + path.sep)) {
    throw new ApiError(404, 'Image not found.');
  }
  return fullPath;
}

async function writeMediaFiles(mediaConfig, image) {
  const baseName = `${randomUUID()}.${image.extension}`;
  const publicName = `property_images/${baseName}`;
  const privateName = `private_property_images/${baseName}`;
  const publicPath = storedMediaPath(mediaConfig.publicRoot, publicName, 'property_images');
  const privatePath = storedMediaPath(mediaConfig.privateRoot, privateName, 'private_property_images');
  await Promise.all([
    mkdir(path.dirname(publicPath), { recursive: true, mode: 0o755 }),
    mkdir(path.dirname(privatePath), { recursive: true, mode: 0o700 }),
  ]);
  try {
    const writes = await Promise.allSettled([
      writeFile(publicPath, image.publicBuffer, { flag: 'wx', mode: 0o644 }),
      writeFile(privatePath, image.originalBuffer, { flag: 'wx', mode: 0o600 }),
    ]);
    const failure = writes.find((result) => result.status === 'rejected');
    if (failure) throw failure.reason;
  } catch (error) {
    await Promise.all([rm(publicPath, { force: true }), rm(privatePath, { force: true })]);
    throw error;
  }
  return { publicName, privateName, publicPath, privatePath };
}

async function removeFiles(paths) {
  await Promise.all(paths.filter(Boolean).map((filePath) => rm(filePath, { force: true })));
}

function isAdmin(account) {
  return Boolean(account.is_superuser || (account.is_staff && account.role === 'administrator'));
}

async function lockAndAuthorizeProperty(client, userId, propertyId, mode) {
  const result = await client.query(
    `SELECT property.id, property.service_type, property.submitted_by_id,
            account.is_active, account.is_staff, account.is_superuser,
            profile.role, profile.agent_approved, profile.management_permissions,
            announcement.submitter_id, announcement.status AS announcement_status
     FROM user_property AS property
     JOIN auth_user AS account ON account.id = $2
     LEFT JOIN accounts_profile AS profile ON profile.user_id = account.id
     LEFT JOIN owner_announcements_ownerannouncement AS announcement
       ON announcement.property_id = property.id
     WHERE property.id = $1
     FOR UPDATE OF property`,
    [propertyId, userId],
  );
  if (result.rowCount !== 1 || !result.rows[0].is_active) {
    throw new ApiError(404, 'Property not found.');
  }
  const property = result.rows[0];
  if (mode === 'submission') {
    const allowed = ['pending_review', 'corrections_requested'].includes(property.announcement_status);
    if (
      !['customer', 'owner'].includes(property.role)
      || property.submitter_id !== Number(userId)
      || !allowed
    ) {
      throw new ApiError(404, 'Submission not found.');
    }
    return property;
  }

  const allowed = property.service_type === 'agent_managed' && (
    isAdmin(property)
    || (
      property.role === 'agent'
      && property.agent_approved
      && property.submitted_by_id === Number(userId)
    )
  );
  if (!allowed) throw new ApiError(404, 'Property not found.');
  return property;
}

async function createImageRecord(client, propertyId, image, files, caption, isPrimary) {
  const result = await client.query(
    `INSERT INTO user_propertyimage
       (property_id, image, original_image, original_filename, original_content_type, caption, is_primary)
     VALUES ($1, $2, $3, $4, $5, $6, $7)
     RETURNING id, property_id, image, original_image, original_filename,
               original_content_type, caption, is_primary, created_at`,
    [
      propertyId,
      files.publicName,
      files.privateName,
      image.originalFilename,
      image.contentType,
      caption,
      isPrimary,
    ],
  );
  const record = result.rows[0];
  await client.query(
    `INSERT INTO backend_media_file_metadata
       (property_image_id, public_file_size_bytes, original_file_size_bytes,
        mime_type, file_extension, width, height)
     VALUES ($1, $2, $3, $4, $5, $6, $7)`,
    [
      record.id,
      image.publicBuffer.length,
      image.originalBuffer.length,
      image.contentType,
      image.extension,
      image.width,
      image.height,
    ],
  );
  return record;
}

async function getBranding(client, mediaConfig) {
  const result = await client.query(
    'SELECT site_name, phone, site_logo FROM portal_admin_brokeragesettings WHERE id = 1',
  );
  const settings = result.rows[0];
  let logoDataUri = '';
  if (settings?.site_logo) {
    const logoPath = storedMediaPath(mediaConfig.publicRoot, settings.site_logo, 'site-branding');
    const logoBytes = await readFile(logoPath);
    const logo = await sharp(logoBytes, {
      failOn: 'error',
      limitInputPixels: 20_000_000,
    }).rotate().resize(64, 64, { fit: 'inside' }).png().toBuffer();
    logoDataUri = `data:image/png;base64,${logo.toString('base64')}`;
  }
  return {
    siteName: settings?.site_name || 'Infinity House',
    phone: settings?.phone || '',
    logoDataUri,
  };
}

export function imageUrl(request, storedName) {
  if (
    typeof storedName !== 'string'
    || !storedName.startsWith('property_images/')
    || storedName.includes('\\')
    || storedName.split('/').some((segment) => !segment || segment === '..')
  ) {
    throw new ApiError(500, 'A property image does not have a safe local media path.');
  }
  const encodedPath = storedName.split('/').map(encodeURIComponent).join('/');
  return `${request.protocol}://${request.get('host')}/media/${encodedPath}`;
}

function serializeImage(request, row, originalAccess) {
  return {
    id: Number(row.id),
    image: imageUrl(request, row.image),
    original_url: originalAccess
      ? `${request.protocol}://${request.get('host')}/api/v1/management/images/${row.id}/original/`
      : null,
    caption: row.caption || '',
    is_primary: Boolean(row.is_primary),
    created_at: row.created_at,
  };
}

export async function listManagedImages(pool, request, userId, propertyId) {
  return withTransaction(pool, async (client) => {
    await lockAndAuthorizeProperty(client, userId, propertyId, 'managed');
    const result = await client.query(
      `SELECT id, image, original_image, caption, is_primary, created_at
       FROM user_propertyimage WHERE property_id = $1 ORDER BY id`,
      [propertyId],
    );
    return {
      count: result.rowCount,
      next: null,
      previous: null,
      results: result.rows.map((row) => serializeImage(request, row, true)),
    };
  });
}

export async function listSubmissionImages(pool, request, userId, propertyId) {
  return withTransaction(pool, async (client) => {
    await lockAndAuthorizeProperty(client, userId, propertyId, 'submission');
    const result = await client.query(
      `SELECT id, image, original_image, caption, is_primary, created_at
       FROM user_propertyimage WHERE property_id = $1 ORDER BY id`,
      [propertyId],
    );
    return {
      count: result.rowCount,
      next: null,
      previous: null,
      results: result.rows.map((row) => serializeImage(request, row, true)),
    };
  });
}

export async function getManagedImage(pool, request, userId, propertyId, imageId) {
  return withTransaction(pool, async (client) => {
    await lockAndAuthorizeProperty(client, userId, propertyId, 'managed');
    const result = await client.query(
      `SELECT id, image, original_image, caption, is_primary, created_at
       FROM user_propertyimage WHERE id = $1 AND property_id = $2`,
      [imageId, propertyId],
    );
    if (result.rowCount !== 1) throw new ApiError(404, 'Image not found.');
    return serializeImage(request, result.rows[0], true);
  });
}

export async function createPropertyImage(pool, request, userId, propertyId, mode, file, fields, mediaConfig) {
  const caption = fields.caption || '';
  if (typeof caption !== 'string' || caption.length > 200) {
    throw new ApiError(400, 'Caption must be 200 characters or fewer.');
  }
  if (fields.is_primary !== undefined && !['true', 'false'].includes(fields.is_primary)) {
    throw new ApiError(400, 'is_primary must be true or false.');
  }

  let createdFiles;
  try {
    const imageRecord = await withTransaction(pool, async (client) => {
      const property = await lockAndAuthorizeProperty(client, userId, propertyId, mode);
      const count = await client.query(
        'SELECT COUNT(*)::integer AS image_count FROM user_propertyimage WHERE property_id = $1',
        [propertyId],
      );
      const imageCount = count.rows[0].image_count;
      if (imageCount >= 10) {
        throw new ApiError(400, 'A property can have at most 10 images.');
      }
      const image = await prepareImageUpload(file, await getBranding(client, mediaConfig));
      const files = await writeMediaFiles(mediaConfig, image);
      createdFiles = files;
      const isPrimary = mode === 'managed'
        ? imageCount === 0 || fields.is_primary === 'true'
        : fields.is_primary === 'true';
      if (isPrimary) {
        await client.query(
          'UPDATE user_propertyimage SET is_primary = FALSE WHERE property_id = $1',
          [propertyId],
        );
      }
      return createImageRecord(client, property.id, image, files, caption, isPrimary);
    });
    return serializeImage(request, imageRecord, true);
  } catch (error) {
    if (createdFiles) await removeFiles([createdFiles.publicPath, createdFiles.privatePath]);
    throw error;
  }
}

export async function updateManagedImage(pool, request, userId, propertyId, imageId, fields) {
  const caption = fields.caption;
  const isPrimary = fields.is_primary;
  if (caption !== undefined && (typeof caption !== 'string' || caption.length > 200)) {
    throw new ApiError(400, 'Caption must be 200 characters or fewer.');
  }
  if (isPrimary !== undefined && typeof isPrimary !== 'boolean') {
    throw new ApiError(400, 'is_primary must be a boolean.');
  }

  return withTransaction(pool, async (client) => {
    await lockAndAuthorizeProperty(client, userId, propertyId, 'managed');
    const selected = await client.query(
      `SELECT id, image, original_image, caption, is_primary, created_at
       FROM user_propertyimage WHERE id = $1 AND property_id = $2 FOR UPDATE`,
      [imageId, propertyId],
    );
    if (selected.rowCount !== 1) throw new ApiError(404, 'Image not found.');
    if (isPrimary === true) {
      await client.query(
        'UPDATE user_propertyimage SET is_primary = FALSE WHERE property_id = $1 AND id <> $2',
        [propertyId, imageId],
      );
    }
    const update = await client.query(
      `UPDATE user_propertyimage
       SET caption = COALESCE($1, caption), is_primary = COALESCE($2, is_primary)
       WHERE id = $3
       RETURNING id, image, original_image, caption, is_primary, created_at`,
      [caption ?? null, isPrimary ?? null, imageId],
    );
    return serializeImage(request, update.rows[0], true);
  });
}

export async function replaceManagedImage(pool, request, userId, propertyId, imageId, file, mediaConfig) {
  let createdFiles;
  let replaced;
  try {
    replaced = await withTransaction(pool, async (client) => {
      await lockAndAuthorizeProperty(client, userId, propertyId, 'managed');
      const selected = await client.query(
        `SELECT id, image, original_image, caption, is_primary
         FROM user_propertyimage WHERE id = $1 AND property_id = $2 FOR UPDATE`,
        [imageId, propertyId],
      );
      if (selected.rowCount !== 1) throw new ApiError(404, 'Image not found.');
      const image = await prepareImageUpload(file, await getBranding(client, mediaConfig));
      const files = await writeMediaFiles(mediaConfig, image);
      createdFiles = files;
      const update = await client.query(
        `UPDATE user_propertyimage
         SET image = $1, original_image = $2, original_filename = $3, original_content_type = $4
         WHERE id = $5
         RETURNING id, image, original_image, caption, is_primary, created_at`,
        [files.publicName, files.privateName, image.originalFilename, image.contentType, imageId],
      );
      await client.query(
        `INSERT INTO backend_media_file_metadata
           (property_image_id, public_file_size_bytes, original_file_size_bytes,
            mime_type, file_extension, width, height)
         VALUES ($1, $2, $3, $4, $5, $6, $7)
         ON CONFLICT (property_image_id) DO UPDATE SET
           public_file_size_bytes = EXCLUDED.public_file_size_bytes,
           original_file_size_bytes = EXCLUDED.original_file_size_bytes,
           mime_type = EXCLUDED.mime_type,
           file_extension = EXCLUDED.file_extension,
           width = EXCLUDED.width,
           height = EXCLUDED.height,
           uploaded_at = CURRENT_TIMESTAMP`,
        [
          imageId,
          image.publicBuffer.length,
          image.originalBuffer.length,
          image.contentType,
          image.extension,
          image.width,
          image.height,
        ],
      );
      return {
        record: update.rows[0],
        oldImage: selected.rows[0].image,
        oldOriginal: selected.rows[0].original_image,
      };
    });
  } catch (error) {
    if (createdFiles) await removeFiles([createdFiles.publicPath, createdFiles.privatePath]);
    throw error;
  }
  await removeFiles([
    replaced.oldImage
      ? storedMediaPath(mediaConfig.publicRoot, replaced.oldImage, 'property_images')
      : null,
    replaced.oldOriginal
      ? storedMediaPath(mediaConfig.privateRoot, replaced.oldOriginal, 'private_property_images')
      : null,
  ]);
  return serializeImage(request, replaced.record, true);
}

export async function deleteManagedImage(pool, userId, propertyId, imageId, mediaConfig) {
  const deleted = await withTransaction(pool, async (client) => {
    await lockAndAuthorizeProperty(client, userId, propertyId, 'managed');
    const selected = await client.query(
      `SELECT id, image, original_image
       FROM user_propertyimage WHERE id = $1 AND property_id = $2 FOR UPDATE`,
      [imageId, propertyId],
    );
    if (selected.rowCount !== 1) throw new ApiError(404, 'Image not found.');
    await client.query('DELETE FROM user_propertyimage WHERE id = $1', [imageId]);
    return selected.rows[0];
  });
  await removeFiles([
    deleted.image
      ? storedMediaPath(mediaConfig.publicRoot, deleted.image, 'property_images')
      : null,
    deleted.original_image
      ? storedMediaPath(mediaConfig.privateRoot, deleted.original_image, 'private_property_images')
      : null,
  ]);
}

export async function getOriginalImage(pool, userId, imageId, mediaConfig) {
  const result = await pool.query(
    `SELECT image.id, image.original_image, image.original_filename, image.original_content_type,
            property.service_type, property.submitted_by_id,
            account.is_active, account.is_staff, account.is_superuser,
            profile.role, profile.agent_approved, profile.management_permissions,
            announcement.submitter_id
     FROM user_propertyimage AS image
     JOIN user_property AS property ON property.id = image.property_id
     JOIN auth_user AS account ON account.id = $2
     LEFT JOIN accounts_profile AS profile ON profile.user_id = account.id
     LEFT JOIN owner_announcements_ownerannouncement AS announcement
       ON announcement.property_id = property.id
     WHERE image.id = $1`,
    [imageId, userId],
  );
  if (result.rowCount !== 1) throw new ApiError(404, 'Image not found.');
  const row = result.rows[0];
  const isManager = isAdmin(row);
  const isAssignedAgent = row.role === 'agent'
    && row.agent_approved
    && row.submitted_by_id === Number(userId);
  const isSubmitter = row.service_type === 'owner_announced'
    && row.submitter_id === Number(userId);
  if (!row.is_active || !(isManager || isAssignedAgent || isSubmitter)) {
    throw new ApiError(404, 'Image not found.');
  }
  if (!row.original_image) throw new ApiError(404, 'Image not found.');
  const filePath = storedMediaPath(mediaConfig.privateRoot, row.original_image, 'private_property_images');
  try {
    const fileStat = await stat(filePath);
    if (!fileStat.isFile()) throw new ApiError(404, 'Image not found.');
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error.code === 'ENOENT') throw new ApiError(404, 'Image not found.');
    throw error;
  }
  return {
    filePath,
    filename: path.basename(row.original_filename || 'property-image'),
    contentType: allowedFormats.get(
      row.original_content_type === 'image/jpeg' ? 'jpeg'
        : row.original_content_type === 'image/png' ? 'png'
          : row.original_content_type === 'image/webp' ? 'webp' : '',
    )?.contentType || 'application/octet-stream',
  };
}

export async function cleanOrphanedPropertyImages(
  mediaConfig,
  referencedPublic,
  referencedPrivate,
  { deleteFiles = false } = {},
) {
  const referenced = new Set([...referencedPublic, ...referencedPrivate].map((filePath) => path.resolve(filePath)));
  const roots = [
    [mediaConfig.publicRoot, 'property_images'],
    [mediaConfig.privateRoot, 'private_property_images'],
  ];
  const removed = [];
  for (const [root, directory] of roots) {
    const folder = path.join(root, directory);
    let entries;
    try {
      entries = await readdir(folder, { withFileTypes: true });
    } catch (error) {
      if (error.code === 'ENOENT') continue;
      throw error;
    }
    for (const entry of entries) {
      if (!entry.isFile()) continue;
      const candidate = path.resolve(folder, entry.name);
      if (!referenced.has(candidate)) removed.push(candidate);
    }
  }
  if (deleteFiles) await removeFiles(removed);
  return { orphanedCount: removed.length, removedCount: deleteFiles ? removed.length : 0 };
}
