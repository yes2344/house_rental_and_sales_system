# Property image watermarks

Uploaded property photos are stored twice: the public image includes a
low-opacity, millennial-pink centered `Infinity House` watermark, plus the
current site name, logo, and configured contact phone in the lower-right
corner. The unmodified original is kept in private storage for authorized
access. The public corner watermark uses the phone configured under brokerage
contact settings. If no phone is configured, it displays the site name and
logo only.

New Node uploads are watermarked automatically. The former Django management
command for regenerating already-stored public images was removed; there is no
replacement bulk-refresh command yet. Back up both media roots before any
manual image processing.

The Node API also replaces an individual managed image while preserving its
record ID, caption, and primary status.
