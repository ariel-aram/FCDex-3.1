from django.db import migrations, models

DEFAULT_QUESTS = (
    ("pack_daily", "Open your daily pack", 1, 500, "pack_daily", 0),
    ("battle_play", "Play a battle", 1, 300, "battle_play", 1),
    ("merge_once", "Complete a merge", 1, 400, "merge_once", 2),
)


def seed_quest_definitions(apps, schema_editor):
    QuestDefinition = apps.get_model("fcdex_3_0", "QuestDefinition")
    for quest_key, label, target, reward_coins, hook_key, sort_order in DEFAULT_QUESTS:
        QuestDefinition.objects.update_or_create(
            quest_key=quest_key,
            defaults={
                "label": label,
                "target": target,
                "reward_coins": reward_coins,
                "hook_key": hook_key,
                "enabled": True,
                "sort_order": sort_order,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("fcdex_3_0", "0010_shop_bundle_item_special")]

    operations = [
        migrations.CreateModel(
            name="QuestDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "quest_key",
                    models.CharField(
                        help_text="Unique slug shown in /fcdex quests.", max_length=32, unique=True
                    ),
                ),
                ("label", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, default="")),
                ("target", models.PositiveIntegerField(default=1)),
                ("reward_coins", models.PositiveIntegerField(default=0)),
                (
                    "hook_key",
                    models.CharField(
                        choices=[
                            ("pack_daily", "Open daily pack"),
                            ("battle_play", "Play a battle"),
                            ("merge_once", "Complete a merge"),
                        ],
                        help_text="Progress hook — must match game events (pack, battle, merge).",
                        max_length=32,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Daily quest definition",
                "verbose_name_plural": "Daily quest definitions",
                "ordering": ("sort_order", "quest_key"),
            },
        ),
        migrations.RunPython(seed_quest_definitions, migrations.RunPython.noop),
    ]
