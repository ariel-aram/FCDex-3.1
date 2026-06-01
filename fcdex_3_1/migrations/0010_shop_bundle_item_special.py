from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fcdex_3_0", "0009_shop_bundles"), ("bd_models", "0015_alter_ballinstance_server_id_and_more")]

    operations = [
        migrations.AddField(
            model_name="shopbundleitem",
            name="special",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional special applied to each granted clubball",
                null=True,
                on_delete=models.SET_NULL,
                to="bd_models.special",
            ),
        )
    ]
