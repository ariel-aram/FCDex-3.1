import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fcdex_3_0", "0012_merge_quota")]

    operations = [
        migrations.CreateModel(
            name="TournamentParticipationReward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(blank=True, default="", max_length=64)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "prize_type",
                    models.CharField(
                        choices=[
                            ("coins", "Coins"),
                            ("random_common", "Random Common Clubball"),
                            ("ball", "Specific Clubball"),
                        ],
                        max_length=16,
                    ),
                ),
                ("coins", models.PositiveIntegerField(default=0)),
                (
                    "ball",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="bd_models.ball"
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participation_rewards",
                        to="fcdex_3_0.tournament",
                    ),
                ),
            ],
            options={
                "verbose_name": "tournament participation reward",
                "verbose_name_plural": "tournament participation rewards",
                "ordering": ("pk",),
            },
        ),
        migrations.CreateModel(
            name="TournamentParticipantRewardClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participant_reward_claims",
                        to="bd_models.player",
                    ),
                ),
                (
                    "reward",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="claims",
                        to="fcdex_3_0.tournamentparticipationreward",
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participant_claims",
                        to="fcdex_3_0.tournament",
                    ),
                ),
            ],
            options={"ordering": ("-granted_at",), "unique_together": {("tournament", "player", "reward")}},
        ),
    ]
