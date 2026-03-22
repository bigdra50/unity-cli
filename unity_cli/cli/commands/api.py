"""Dynamic Unity API invocation commands: call, schema."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from unity_cli.cli.context import CLIContext
from unity_cli.cli.helpers import _should_json, handle_cli_errors
from unity_cli.cli.output import print_json, print_plain_table, print_success

api_app = typer.Typer(help="Dynamic Unity API invocation")


@api_app.command("call")
@handle_cli_errors
def api_call(
    ctx: typer.Context,
    type_name: Annotated[
        str,
        typer.Argument(help="Fully qualified type name (e.g., UnityEditor.AssetDatabase)"),
    ],
    method: Annotated[
        str,
        typer.Argument(help="Static method name (e.g., Refresh)"),
    ],
    params: Annotated[
        str | None,
        typer.Option("--params", "-p", help="JSON array of arguments"),
    ] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Call a Unity static API method.

    Examples:
        u api call UnityEngine.Application get_unityVersion
        u api call UnityEditor.AssetDatabase Refresh
        u api call UnityEditor.AssetDatabase ImportAsset --params '["Assets/Prefabs/Player.prefab", 0]'
    """
    context: CLIContext = ctx.obj
    parsed_params: list[object] = []
    if params:
        try:
            parsed_params = json.loads(params)
        except json.JSONDecodeError as e:
            raise typer.BadParameter(f"Invalid JSON for --params: {e}") from e
        if not isinstance(parsed_params, list):
            raise typer.BadParameter("--params must be a JSON array, e.g. '[1, \"hello\"]'")
    result = context.client.dynamic_api.invoke(type_name, method, parsed_params)

    if _should_json(context, json_flag):
        print_json(result, None)
    else:
        ret = result.get("result")
        ret_type = result.get("returnType", "")
        if ret_type == "Void" or ret is None:
            print_success(f"{type_name}.{method}() completed")
        else:
            print_success(f"{type_name}.{method}() -> {ret}")


@api_app.command("schema")
@handle_cli_errors
def api_schema(
    ctx: typer.Context,
    namespace: Annotated[
        list[str] | None,
        typer.Option("--namespace", "-n", help="Filter by namespace prefix"),
    ] = None,
    type_name: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Filter by type name"),
    ] = None,
    method_name: Annotated[
        str | None,
        typer.Option("--method", "-m", help="Filter by method name"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max results per page"),
    ] = 100,
    offset: Annotated[
        int,
        typer.Option("--offset", help="Pagination offset"),
    ] = 0,
    offline: Annotated[
        bool,
        typer.Option("--offline", help="Use cached schema only (no Relay)"),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Skip cache, fetch from Relay"),
    ] = False,
    unity_version: Annotated[
        str | None,
        typer.Option("--version", help="Unity version (for offline cache lookup)"),
    ] = None,
    json_flag: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List available Unity static API methods."""
    context: CLIContext = ctx.obj
    result = context.client.dynamic_api.schema(
        namespace=namespace,
        type_name=type_name,
        method_name=method_name,
        limit=limit,
        offset=offset,
        offline=offline,
        no_cache=no_cache,
        version=unity_version,
    )

    if _should_json(context, json_flag):
        print_json(result, None)
    else:
        methods = result.get("methods", [])
        total = result.get("total", 0)
        has_more = result.get("hasMore", False)

        headers = ["Type", "Method", "Return", "Parameters"]
        rows: list[list[str]] = []
        for m in methods:
            params_str = ", ".join(f"{p['type']} {p['name']}" for p in m.get("parameters", []))
            rows.append([m["type"], m["method"], m["returnType"], params_str])

        print_plain_table(headers, rows)
        if has_more:
            print_success(f"Showing {len(methods)} of {total} (use --offset {offset + limit} for next page)")
