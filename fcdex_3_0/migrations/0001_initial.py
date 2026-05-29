# Generated manually for FCDex 3.0

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("bd_models", "0015_alter_ballinstance_server_id_and_more")]

    operations = [
        migrations.CreateModel(
            name="Achievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                ("description", models.TextField()),
                ("emoji", models.CharField(default="🏆", max_length=32)),
                (
                    "achievement_type",
                    models.CharField(
                        choices=[
                            ("battles_won", "Battles Won"),
                            ("merges", "Merges Completed"),
                            ("tournament_win", "Tournament Wins"),
                            ("tournament_participate", "Tournament Participation"),
                            ("balls_owned", "Clubballs Owned"),
                            ("custom", "Custom (manual)"),
                        ],
                        max_length=32,
                    ),
                ),
                ("required_count", models.PositiveIntegerField(default=1)),
                ("reward_money", models.PositiveBigIntegerField(default=0)),
                ("hidden", models.BooleanField(default=False)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "reward_ball",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="bd_models.ball"
                    ),
                ),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="PlayerStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("battles_won", models.PositiveIntegerField(default=0)),
                ("battles_played", models.PositiveIntegerField(default=0)),
                ("merges_completed", models.PositiveIntegerField(default=0)),
                ("tournament_wins", models.PositiveIntegerField(default=0)),
                ("tournament_participations", models.PositiveIntegerField(default=0)),
                (
                    "player",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="fcdex_stats", to="bd_models.player"
                    ),
                ),
            ],
            options={"verbose_name": "FCDex player stats", "verbose_name_plural": "FCDex player stats"},
        ),
        migrations.CreateModel(
            name="Tournament",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("registration", "Registration"),
                            ("group_stage", "Group Stage"),
                            ("semifinals", "Semifinals"),
                            ("finals", "Finals"),
                            ("completed", "Completed"),
                        ],
                        default="registration",
                        max_length=16,
                    ),
                ),
                (
                    "semifinal_cutoff",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Minimum group score required to reach semifinals. Lowest scorers are eliminated.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "host",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hosted_tournaments",
                        to="bd_models.player",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PlayerAchievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("progress", models.PositiveIntegerField(default=0)),
                ("unlocked_at", models.DateTimeField(blank=True, null=True)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "achievement",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="fcdex_3_0.achievement"),
                ),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fcdex_achievements",
                        to="bd_models.player",
                    ),
                ),
            ],
            options={"unique_together": {("player", "achievement")}},
        ),
        migrations.CreateModel(
            name="MergeLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="merge_logs", to="bd_models.player"
                    ),
                ),
                (
                    "result_ball",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="merge_results",
                        to="bd_models.ballinstance",
                    ),
                ),
                (
                    "source_ball1",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="merge_source1",
                        to="bd_models.ballinstance",
                    ),
                ),
                (
                    "source_ball2",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="merge_source2",
                        to="bd_models.ballinstance",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="TournamentRegistration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("group", models.CharField(choices=[("legacy", "Legacy"), ("main", "Main")], max_length=8)),
                ("score", models.IntegerField(default=0)),
                ("eliminated", models.BooleanField(default=False)),
                ("semifinal_eligible", models.BooleanField(default=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tournament_registrations",
                        to="bd_models.player",
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registrations",
                        to="fcdex_3_0.tournament",
                    ),
                ),
            ],
            options={"unique_together": {("tournament", "player")}},
        ),
        migrations.CreateModel(
            name="TournamentMatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "round",
                    models.CharField(
                        choices=[("group", "Group"), ("semifinal", "Semifinal"), ("final", "Final")], max_length=12
                    ),
                ),
                (
                    "group",
                    models.CharField(
                        blank=True, choices=[("legacy", "Legacy"), ("main", "Main")], max_length=8, null=True
                    ),
                ),
                ("score1", models.IntegerField(default=0)),
                ("score2", models.IntegerField(default=0)),
                ("completed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "player1",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tournament_matches_as_p1",
                        to="bd_models.player",
                    ),
                ),
                (
                    "player2",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tournament_matches_as_p2",
                        to="bd_models.player",
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="matches", to="fcdex_3_0.tournament"
                    ),
                ),
                (
                    "winner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tournament_wins",
                        to="bd_models.player",
                    ),
                ),
            ],
            options={"ordering": ("created_at",)},
        ),
    ]
