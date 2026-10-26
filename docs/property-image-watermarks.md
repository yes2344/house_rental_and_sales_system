# Property image watermarks

Uploaded property photos are stored twice: the public image includes centered
`@Infinity House` watermark lettering at half the previous size and 50%
opacity, without a background. The white vector lettering does not depend on
fonts installed on the server and scales to fit the image. The unmodified
original is kept in private storage for authorized access.

New or replaced Node uploads are watermarked automatically. Existing public
images are not refreshed automatically. The former Django management
command for regenerating already-stored public images was removed; there is no
replacement bulk-refresh command yet. Back up both media roots before any
manual image processing.

The Node API also replaces an individual managed image while preserving its
record ID, caption, and primary status.
