import { Router } from 'express';
import { siteWorkflowController } from '../controllers/siteWorkflowController.js';
import { authenticate } from '../middleware/authenticate.js';
import { rateLimit } from '../middleware/rateLimit.js';
import { validateRequest } from '../middleware/validateRequest.js';
import {
  brokerageContactPatchSchema,
  favoriteCreateSchema,
  listingReportSchema,
  locationPatchSchema,
  locationWriteSchema,
  managedLocationQuerySchema,
  publicLocationQuerySchema,
} from '../validators/siteWorkflows.js';

export function siteWorkflowsRouter({ pool }) {
  const router = Router();
  const controller = siteWorkflowController({ pool });

  router.get('/homepage-notes/', controller.homepageNotes);
  router.get('/public-pages/:page/', controller.publicInformationPage);
  router.route('/brokerage/contact/')
    .get(controller.brokerageContact)
    .patch(
      authenticate({ pool }),
      validateRequest(brokerageContactPatchSchema),
      controller.patchBrokerageContact,
    );
  router.post(
    '/reports/',
    rateLimit({ limit: 10, windowMs: 60 * 60 * 1000 }),
    validateRequest(listingReportSchema),
    controller.listingReport,
  );
  router.route('/favorites/')
    .get(authenticate({ pool }), controller.favorites)
    .post(
      authenticate({ pool }),
      validateRequest(favoriteCreateSchema),
      controller.createFavorite,
    );
  router.delete('/favorites/:propertyId/', authenticate({ pool }), controller.deleteFavorite);
  router.get(
    '/locations/',
    validateRequest(publicLocationQuerySchema, 'query'),
    controller.publicLocations,
  );
  router.route('/management/locations/')
    .get(
      authenticate({ pool }),
      validateRequest(managedLocationQuerySchema, 'query'),
      controller.managedLocations,
    )
    .post(
      authenticate({ pool }),
      validateRequest(locationWriteSchema),
      controller.createManagedLocation,
    );
  router.route('/management/locations/:id/')
    .get(authenticate({ pool }), controller.managedLocation)
    .patch(
      authenticate({ pool }),
      validateRequest(locationPatchSchema),
      controller.updateManagedLocation,
    )
    .delete(authenticate({ pool }), controller.deleteManagedLocation);

  return router;
}
