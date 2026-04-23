from django.db import migrations


CLUSTERS = [
    {
        "cluster_id": "czii",
        "name": "CZII",
        "http_base_url": "https://czii-onsite.czbiohub.org/",
        "ssh_hostname": "10.50.120.90",
        "ssh_port": 22,
    },
    {
        "cluster_id": "bruno",
        "name": "Bruno",
        "http_base_url": "https://onsite.czbiohub.org/group.czii/",
        "ssh_hostname": "192.168.98.229",
        "ssh_port": 22,
    },
]


def seed_clusters(apps, schema_editor):
    Cluster = apps.get_model("stores", "Cluster")
    for c in CLUSTERS:
        Cluster.objects.update_or_create(cluster_id=c["cluster_id"], defaults=c)


def unseed_clusters(apps, schema_editor):
    Cluster = apps.get_model("stores", "Cluster")
    Cluster.objects.filter(cluster_id__in=[c["cluster_id"] for c in CLUSTERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0009_cluster"),
    ]

    operations = [
        migrations.RunPython(seed_clusters, unseed_clusters),
    ]
