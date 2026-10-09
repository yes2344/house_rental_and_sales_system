# Preserve the tables created by user.0001 without recreating or copying data.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('user', '0003_property_listing_type'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='Property',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=200)),
                        ('slug', models.SlugField(blank=True, unique=True)),
                        ('location', models.CharField(max_length=200)),
                        ('property_type', models.CharField(choices=[('house', 'House'), ('villa', 'Villa'), ('apartment', 'Apartment'), ('land', 'Land')], default='house', max_length=50)),
                        ('price', models.DecimalField(decimal_places=2, max_digits=12)),
                        ('bedrooms', models.PositiveIntegerField(default=0)),
                        ('bathrooms', models.PositiveIntegerField(default=0)),
                        ('area_sqft', models.PositiveIntegerField(default=0)),
                        ('description', models.TextField()),
                        ('features', models.TextField(blank=True)),
                        ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active', max_length=20)),
                        ('is_featured', models.BooleanField(default=False)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('listing_type', models.CharField(choices=[('sale', 'For Sale'), ('rent', 'For Rent')], default='sale', max_length=20)),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'user_property',
                    },
                ),
                migrations.CreateModel(
                    name='PropertyImage',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('image', models.ImageField(upload_to='property_images/')),
                        ('caption', models.CharField(blank=True, max_length=200)),
                        ('is_primary', models.BooleanField(default=False)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='properties.property')),
                    ],
                    options={
                        'db_table': 'user_propertyimage',
                    },
                ),
            ],
        ),
    ]
