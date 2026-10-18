# Property image watermarks

Uploaded property photos are stored twice: the public image includes a low-opacity, millennial-pink centered `@habeshapropertycenter` watermark, plus the current site name, logo, and configured contact phone in the lower-right corner. The unmodified original is kept in private storage for authorized access. The public corner watermark uses the phone configured under the administrator's brokerage contact settings. If no phone is configured, it displays the site name and logo only.

New uploads are watermarked automatically. After changing the site name, logo, or contact phone, regenerate public versions from the preserved private originals:

```powershell
python manage.py watermark_property_images --refresh
```

The refresh replaces only each public image. It preserves the private original and its metadata. Running the command without `--refresh` processes legacy images that do not yet have a stored original and skips images already migrated.
