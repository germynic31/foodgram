# Generated by Django 4.2.11 on 2024-06-08 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foods', '0008_alter_ingredientrecipe_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='tags',
            field=models.ManyToManyField(related_name='tags', to='foods.tag'),
        ),
    ]
