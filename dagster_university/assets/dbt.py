import json

import dagster as dg
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

from ..partitions import daily_partition
from ..project import dbt_project

INCREMENTAL_SELECTOR = "config.materialized:incremental"


class CustomizeDagsterDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props: dict):
        resource_type = dbt_resource_props["resource_type"]
        name = dbt_resource_props["name"]

        if resource_type == "source":
            return dg.AssetKey(f"taxi_{name}")
        else:
            return super().get_asset_key(dbt_resource_props)

    def get_group_name(self, dbt_resource_props: dict):
        dbt_layer = dbt_resource_props["fqn"][1]

        return dbt_layer


@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=CustomizeDagsterDbtTranslator(),
    exclude=INCREMENTAL_SELECTOR,
)
def dbt_analytics(context: dg.AssetExecutionContext, dbt_cli: DbtCliResource):
    """The output of the dbt analytics run."""
    yield from dbt_cli.cli(["build"], context=context).stream()


@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=CustomizeDagsterDbtTranslator(),
    select=INCREMENTAL_SELECTOR,
    partitions_def=daily_partition,
)
def incremental_dbt_models(
    context: dg.AssetExecutionContext,
    dbt_cli: DbtCliResource,
):
    time_window = context.partition_time_window
    dbt_vars = {
        "min_date": time_window.start.strftime("%Y-%m-%d"),
        "max_date": time_window.end.strftime("%Y-%m-%d"),
    }
    yield from dbt_cli.cli(
        ["build", "--vars", json.dumps(dbt_vars)], context=context
    ).stream()