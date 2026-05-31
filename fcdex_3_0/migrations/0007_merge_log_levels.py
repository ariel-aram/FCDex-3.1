from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fcdex_3_0", "0006_tournament_schedule_help_text")]

    operations = [
        migrations.AddField(
            model_name="mergelog", name="merge_level", field=models.PositiveSmallIntegerField(default=1)
        ),
        migrations.AddField(model_name="mergelog", name="source_ids", field=models.JSONField(blank=True, default=list)),
    ]
