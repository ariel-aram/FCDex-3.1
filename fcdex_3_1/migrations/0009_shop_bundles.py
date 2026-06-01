import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fcdex_3_0", "0008_fcdex_31_packs_sbc_quests"),
        ("bd_models", "0015_alter_ballinstance_server_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShopBundle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("price", models.PositiveIntegerField(help_text="Coin price charged from Player.money")),
                ("enabled", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("emoji", models.CharField(blank=True, default="🛒", max_length=32)),
            ],
            options={
                "verbose_name": "Shop bundle",
                "verbose_name_plural": "Shop bundles",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="ShopBundleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveSmallIntegerField(default=1)),
                (
                    "ball",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shop_bundle_items",
                        to="bd_models.ball",
                    ),
                ),
                (
                    "bundle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="fcdex_3_0.shopbundle",
                    ),
                ),
            ],
            options={"ordering": ("pk",)},
        ),
        migrations.CreateModel(
            name="ShopPurchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purchased_at", models.DateTimeField(auto_now_add=True)),
                (
                    "bundle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="purchases",
                        to="fcdex_3_0.shopbundle",
                    ),
                ),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shop_purchases",
                        to="bd_models.player",
                    ),
                ),
            ],
            options={"ordering": ("-purchased_at",)},
        ),
    ]
