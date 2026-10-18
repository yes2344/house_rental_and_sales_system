from mimetypes import guess_extension
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from properties.image_processing import image_content_type, watermark_image
from properties.models import PropertyImage


class Command(BaseCommand):
    help = 'Watermark existing property photos and move their originals to private storage.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Regenerate public watermarks from stored private originals.',
        )

    def handle(self, *args, **options):
        refresh = options['refresh']
        queryset = PropertyImage.objects.select_related('property').order_by('pk')
        total = queryset.count()
        processed = 0
        skipped = 0

        for image in queryset.iterator():
            has_original = bool(image.original_image)
            if has_original and not refresh:
                skipped += 1
                continue
            if not image.image and not has_original:
                raise ValueError(f'Property image {image.pk} has no public source file.')

            source_field = image.original_image if has_original else image.image
            with source_field.open('rb') as source:
                original_content = source.read()
            original_content_file = ContentFile(original_content)
            content_type = image_content_type(original_content_file)
            watermarked_content = watermark_image(ContentFile(original_content))
            original_name = image.original_filename if has_original else image.image.name
            original_filename = PurePosixPath(original_name.replace('\\', '/')).name
            if not PurePosixPath(original_filename).suffix:
                original_filename = PurePosixPath(urlsplit(source_field.url).path).name
            if not PurePosixPath(original_filename).suffix:
                original_filename += guess_extension(content_type) or '.jpg'

            old_public_name = image.image.name
            saved_private_name = None
            saved_public_name = None
            try:
                if not has_original:
                    image.original_image.save(
                        original_filename,
                        ContentFile(original_content),
                        save=False,
                    )
                    saved_private_name = image.original_image.name
                image.image.save(
                    original_filename,
                    watermarked_content,
                    save=False,
                )
                saved_public_name = image.image.name

                with transaction.atomic():
                    if has_original:
                        updated = PropertyImage.objects.filter(
                            pk=image.pk,
                            original_image=image.original_image.name,
                            image=old_public_name,
                        ).update(image=saved_public_name)
                    else:
                        updated = PropertyImage.objects.filter(
                            pk=image.pk,
                            original_image='',
                        ).update(
                            image=saved_public_name,
                            original_image=saved_private_name,
                            original_filename=original_filename,
                            original_content_type=content_type,
                        )
                    if updated != 1:
                        raise RuntimeError(
                            f'Property image {image.pk} changed while it was being migrated.',
                        )
                    if old_public_name:
                        transaction.on_commit(
                            lambda: image.image.storage.delete(old_public_name),
                            robust=True,
                        )
            except Exception:
                if saved_public_name:
                    image.image.storage.delete(saved_public_name)
                if saved_private_name:
                    image.original_image.storage.delete(saved_private_name)
                raise

            processed += 1
            self.stdout.write(f'Watermarked property image {image.pk}.')

        self.stdout.write(self.style.SUCCESS(
            f'Processed {processed} of {total} property images; skipped {skipped} already migrated.',
        ))
