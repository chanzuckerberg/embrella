from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("depositions", "0011_alter_dataset_title_alter_deposition_title"),
    ]

    operations = [
        migrations.AlterField(
            model_name="deposition",
            name="authors_json",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Ordered list of {author_id, is_primary, is_corresponding, author_list_order}; "
                "author_id soft-references people.Person (not a FK). Identity fields live in the people directory.",
            ),
        ),
    ]
