from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fcdex_3_0", "0005_tournament_match_verification")]

    operations = [
        migrations.AlterField(
            model_name="tournament",
            name="scheduled_start_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Planned start — blocks the host from starting group stage early. "
                    "Player registration stays open until the host starts or scheduled end passes."
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="tournament",
            name="scheduled_end_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Planned end — registration and new match activity close after this time.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="tournament",
            name="started_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Actual time the group stage was started via /tournament manage → Host.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="tournament",
            name="ended_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Actual time the tournament was completed via /tournament manage → Host → Advance round.",
                null=True,
            ),
        ),
    ]
