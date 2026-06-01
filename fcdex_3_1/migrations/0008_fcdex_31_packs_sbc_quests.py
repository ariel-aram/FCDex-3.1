import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fcdex_3_0", "0007_merge_log_levels"), ("bd_models", "0015_alter_ballinstance_server_id_and_more")]

    operations = [
        migrations.CreateModel(
            name="PackClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "pack_type",
                    models.CharField(
                        choices=[("daily", "Daily Pack"), ("weekly", "Weekly Pack"), ("mascot", "Mascot Pack")],
                        max_length=16,
                    ),
                ),
                ("claimed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="pack_claims", to="bd_models.player"
                    ),
                ),
            ],
            options={"ordering": ("-claimed_at",)},
        ),
        migrations.AddIndex(
            model_name="packclaim",
            index=models.Index(fields=["player", "pack_type", "-claimed_at"], name="fcdex_pack_player_type_idx"),
        ),
        migrations.CreateModel(
            name="SBCRecipe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("required_count", models.PositiveSmallIntegerField(default=1)),
                ("reward_money", models.PositiveIntegerField(default=0)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "required_ball",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sbc_requirements",
                        to="bd_models.ball",
                    ),
                ),
                (
                    "reward_ball",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="sbc_rewards", to="bd_models.ball"
                    ),
                ),
            ],
            options={"verbose_name": "SBC recipe", "verbose_name_plural": "SBC recipes", "ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="PlayerQuestProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quest_key", models.CharField(max_length=32)),
                ("progress", models.PositiveIntegerField(default=0)),
                ("target", models.PositiveIntegerField(default=1)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("day", models.DateField()),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="fcdex_quests", to="bd_models.player"
                    ),
                ),
            ],
            options={"ordering": ("-day", "quest_key"), "unique_together": {("player", "quest_key", "day")}},
        ),
    ]
