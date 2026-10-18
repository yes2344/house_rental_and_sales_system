from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont, ImageOps


def _branding():
    from admin.models import BrokerageSettings

    settings = BrokerageSettings.objects.filter(pk=1).first()
    if settings is None:
        return 'Infinit House', None, ''
    name = settings.site_name.strip() or 'Infinit House'
    if not settings.site_logo:
        return name, None, settings.phone.strip()
    with settings.site_logo.open('rb') as logo_file:
        return name, logo_file.read(), settings.phone.strip()


def _fallback_logo(size):
    mark = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(mark)
    inset = max(3, size // 8)
    roof_y = size // 3
    draw.line(
        [(inset, roof_y), (size // 2, inset), (size - inset, roof_y)],
        fill=(21, 77, 129, 255),
        width=max(2, size // 12),
        joint='curve',
    )
    draw.rectangle(
        (size // 4, roof_y, size * 3 // 4, size - inset),
        fill=(21, 77, 129, 255),
    )
    door_width = max(3, size // 6)
    draw.rectangle(
        (size // 2 - door_width // 2, size * 2 // 3, size // 2 + door_width // 2, size - inset),
        fill=(255, 255, 255, 255),
    )
    return mark


def _brand_mark(size, logo_bytes):
    if not logo_bytes:
        return _fallback_logo(size)
    with Image.open(BytesIO(logo_bytes)) as source:
        logo = ImageOps.contain(source.convert('RGBA'), (size - 8, size - 8))
    mark = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    mark.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    return mark


def _watermark_layout(width, height, site_name, phone, logo_bytes):
    margin = max(8, round(min(width, height) * 0.025))
    padding = max(6, round(min(width, height) * 0.018))
    mark_size = max(22, min(58, round(min(width, height) * 0.075)))
    font_size = max(12, min(48, round(min(width, height) * 0.035)))
    available_text_width = max(1, width - margin * 2 - padding * 2 - mark_size - padding)
    font = ImageFont.load_default(size=font_size)
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    while font_size > 10 and draw.textbbox((0, 0), site_name, font=font)[2] > available_text_width:
        font_size -= 1
        font = ImageFont.load_default(size=font_size)
    text_box = draw.textbbox((0, 0), site_name, font=font)
    text_width = text_box[2] - text_box[0]
    if text_width > available_text_width:
        raise ValueError('The configured platform name does not fit on this property image.')
    phone_font = None
    phone_box = None
    phone_width = 0
    phone_height = 0
    text_gap = 0
    if phone:
        phone_font_size = max(10, round(font_size * 0.72))
        phone_font = ImageFont.load_default(size=phone_font_size)
        while (
            phone_font_size > 10
            and draw.textbbox((0, 0), phone, font=phone_font)[2] > available_text_width
        ):
            phone_font_size -= 1
            phone_font = ImageFont.load_default(size=phone_font_size)
        phone_box = draw.textbbox((0, 0), phone, font=phone_font)
        phone_width = phone_box[2] - phone_box[0]
        phone_height = phone_box[3] - phone_box[1]
        if phone_width > available_text_width:
            raise ValueError('The configured platform phone does not fit on this property image.')
        text_gap = max(2, round(font_size * 0.12))
    text_height = text_box[3] - text_box[1] + text_gap + phone_height
    panel_width = min(
        width - margin * 2,
        padding * 2 + mark_size + padding + max(text_width, phone_width),
    )
    panel_height = max(mark_size, text_height) + padding * 2
    return (
        margin,
        padding,
        mark_size,
        font,
        text_box,
        phone_font,
        phone_box,
        text_gap,
        text_height,
        panel_width,
        panel_height,
    )


def watermark_image(image_file):
    site_name, logo_bytes, phone = _branding()
    with Image.open(image_file) as opened:
        source_format = opened.format
        if source_format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError('Property photos must use JPEG, PNG, or WebP format.')
        image = ImageOps.exif_transpose(opened).convert('RGBA')

    width, height = image.size
    (
        margin,
        padding,
        mark_size,
        font,
        text_box,
        phone_font,
        phone_box,
        text_gap,
        text_height,
        panel_width,
        panel_height,
    ) = _watermark_layout(
        width,
        height,
        site_name,
        phone,
        logo_bytes,
    )
    if (
        panel_width <= 0
        or panel_height <= 0
        or panel_width + margin * 2 > width
        or panel_height + margin * 2 > height
    ):
        raise ValueError('The image is too small to apply the required property watermark.')

    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    left = width - margin - panel_width
    top = height - margin - panel_height
    radius = max(5, panel_height // 5)
    draw.rounded_rectangle(
        (left, top, width - margin, height - margin),
        radius=radius,
        fill=(13, 31, 49, 205),
        outline=(255, 255, 255, 235),
        width=max(1, round(min(width, height) * 0.002)),
    )
    mark = _brand_mark(mark_size, logo_bytes)
    mark_left = left + padding
    mark_top = top + (panel_height - mark_size) // 2
    overlay.alpha_composite(mark, (mark_left, mark_top))
    text_left = mark_left + mark_size + padding
    text_top = top + (panel_height - text_height) // 2 - text_box[1]
    draw.text(
        (text_left, text_top),
        site_name,
        font=font,
        fill=(255, 255, 255, 255),
        stroke_width=max(1, font.size // 16),
        stroke_fill=(0, 0, 0, 220),
    )
    if phone and phone_font is not None and phone_box is not None:
        phone_top = (
            top
            + (panel_height - text_height) // 2
            + text_box[3]
            - text_box[1]
            + text_gap
            - phone_box[1]
        )
        draw.text(
            (text_left, phone_top),
            phone,
            font=phone_font,
            fill=(255, 255, 255, 255),
            stroke_width=max(1, phone_font.size // 16),
            stroke_fill=(0, 0, 0, 220),
        )
    center_label = 'Infinit House'
    center_font_size = max(12, min(64, round(min(width, height) * 0.065)))
    center_font = ImageFont.load_default(size=center_font_size)
    center_box = draw.textbbox((0, 0), center_label, font=center_font)
    while (
        center_font_size > 10
        and center_box[2] - center_box[0] > width * 0.9
    ):
        center_font_size -= 1
        center_font = ImageFont.load_default(size=center_font_size)
        center_box = draw.textbbox((0, 0), center_label, font=center_font)
    center_text_width = center_box[2] - center_box[0]
    center_text_height = center_box[3] - center_box[1]
    center_text_left = (width - center_text_width) // 2 - center_box[0]
    center_text_top = (height - center_text_height) // 2 - center_box[1]
    draw.text(
        (center_text_left, center_text_top),
        center_label,
        font=center_font,
        fill=(243, 197, 201, 62),
        stroke_width=max(1, center_font.size // 20),
        stroke_fill=(0, 0, 0, 42),
    )
    image = Image.alpha_composite(image, overlay)
    output = BytesIO()
    if source_format == 'JPEG':
        image.convert('RGB').save(output, format='JPEG', quality=92, optimize=True)
    elif source_format == 'WEBP':
        image.save(output, format='WEBP', quality=92, method=6)
    else:
        image.save(output, format='PNG', optimize=True)
    return ContentFile(output.getvalue())


def image_content_type(image_file):
    with Image.open(image_file) as opened:
        return Image.MIME.get(opened.format, 'application/octet-stream')
