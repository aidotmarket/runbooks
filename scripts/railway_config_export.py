#!/usr/bin/env python3
"""Export Railway topology, including variable names but never their values."""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

API = "https://backboard.railway.app/graphql/v2"
BUCKET = "aimarket-backups-prod"
REGION = "eu-north-1"
MAX_PAGES = 1000
TOK = os.environ.get("RAILWAY_API_TOKEN", "").strip()
H = {"Authorization": "Bearer " + TOK, "Content-Type": "application/json",
     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
     "Accept": "application/json"}


def fail(stage):
    raise RuntimeError("Railway export incomplete: " + stage)


def gql(query, variables=None, tries=4):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    for attempt in range(tries):
        try:
            request = urllib.request.Request(API, data=body, headers=H)
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError:
            fail("API HTTP error")
        except Exception:
            if attempt == tries - 1:
                fail("API unavailable or malformed")
            time.sleep(3 * (attempt + 1))


def mapping(value, stage):
    if not isinstance(value, dict):
        fail(stage)
    return value


def named(value, key, stage):
    result = mapping(value, stage).get(key)
    if not isinstance(result, str) or not result:
        fail(stage)
    return result


def data(response, stage):
    response = mapping(response, stage)
    if "errors" in response:
        fail(stage + " API error")
    return mapping(response.get("data"), stage)


def edges(connection, stage, latest=False):
    connection = mapping(connection, stage)
    result = connection.get("edges")
    if not isinstance(result, list):
        fail(stage)
    if latest:
        if len(result) > 1:
            fail(stage + " first:1 violated")
        for edge in result:
            mapping(mapping(edge, stage).get("node"), stage)
        return result
    info = connection.get("pageInfo")
    if type(mapping(info, stage).get("hasNextPage")) is not bool:
        fail(stage + " pagination malformed")
    for edge in result:
        mapping(mapping(edge, stage).get("node"), stage)
    return result


def pagination_fields():
    """Read field arguments from Railway's schema; never assume nested args."""
    schema = data(gql('query { workspaceType:__type(name:"Workspace"){fields{name args{name type{kind name ofType{kind name}}}}} projectType:__type(name:"Project"){fields{name args{name type{kind name ofType{kind name}}}}} }'), "schema")
    supported = {}
    for alias, fields in (("workspaceType", ("projects",)),
                          ("projectType", ("environments", "services"))):
        definition = mapping(schema.get(alias), "schema")
        entries = definition.get("fields")
        if not isinstance(entries, list):
            fail("schema")
        for field in fields:
            matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("name") == field]
            if len(matches) != 1 or not isinstance(matches[0].get("args"), list):
                fail("schema " + field)
            args = {arg.get("name"): arg.get("type") for arg in matches[0]["args"] if isinstance(arg, dict)}
            def scalar(argument):
                value = mapping(args[argument], "schema")
                if value.get("kind") == "NON_NULL":
                    value = mapping(value.get("ofType"), "schema")
                return value.get("name")
            pair = (scalar("first") == "Int" and scalar("after") == "String") if "first" in args and "after" in args else False
            if ("first" in args) != ("after" in args):
                fail("schema " + field)
            supported[field] = pair
    return supported


def collect(fetch, stage, paginated):
    all_edges, seen_ids, seen_cursors = [], set(), set()
    cursor = None
    for _ in range(MAX_PAGES):
        connection = mapping(fetch(cursor), stage)
        batch = edges(connection, stage)
        for edge in batch:
            identifier = named(edge["node"], "id", stage)
            if identifier in seen_ids:
                fail(stage + " duplicate resource")
            seen_ids.add(identifier)
        all_edges.extend(batch)
        count = connection.get("totalCount")
        if count is not None and (type(count) is not int or count < len(all_edges)):
            fail(stage + " count inconsistent")
        info = connection["pageInfo"]
        if info["hasNextPage"] is False:
            if count is not None and count != len(all_edges):
                fail(stage + " count inconsistent")
            return all_edges
        if not paginated:
            fail(stage + " pagination unsupported by schema")
        next_cursor = info.get("endCursor")
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
            fail(stage + " cursor stalled or malformed")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    fail(stage + " page bound exceeded")


def upload(out, now):
    payload = json.dumps(out, indent=2).encode()
    key = f"railway-config/{now:%Y%m%d}/railway-config-{now:%Y%m%dT%H%M%SZ}.json"
    env = dict(os.environ, AWS_ACCESS_KEY_ID=os.environ["AWS_BACKUP_WRITER_ACCESS_KEY_ID"].strip(),
               AWS_SECRET_ACCESS_KEY=os.environ["AWS_BACKUP_WRITER_SECRET"].strip(), AWS_DEFAULT_REGION=REGION)
    name = None
    try:
        with tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as tmp:
            name = tmp.name
            tmp.write(payload)
        result = subprocess.run(["rtk", "proxy", "aws", "s3", "cp", name, f"s3://{BUCKET}/{key}",
                                 "--content-type", "application/json"], env=env,
                                capture_output=True, text=True)
        if result.returncode:
            fail("upload failed")
    finally:
        if name is not None:
            os.unlink(name)
    print(f"uploaded s3://{BUCKET}/{key} ({len(payload)} bytes; {len(out['projects'])} projects)")


def main():
    if not TOK:
        fail("missing RAILWAY_API_TOKEN")
    now = datetime.datetime.now(datetime.timezone.utc)
    out = {"exported_at": now.isoformat(),
           "note": "Railway topology for DR rebuild. Secret VALUES excluded (live in Infisical, backed up separately). Variable NAMES only.",
           "projects": []}
    supported = pagination_fields()
    workspaces = mapping(data(gql('{ me { workspaces { id } } }'), "enumeration").get("me"), "enumeration").get("workspaces")
    if not isinstance(workspaces, list):
        fail("enumeration")
    project_edges = []
    seen_workspaces = set()
    for workspace in workspaces:
        wid = named(workspace, "id", "workspace")
        if wid in seen_workspaces:
            fail("duplicate workspace")
        seen_workspaces.add(wid)
        def projects(cursor):
            args = '(first:50,after:$after)' if supported["projects"] else ''
            signature = '($w:String!,$after:String)' if supported["projects"] else '($w:String!)'
            query = 'query' + signature + '{ workspace(workspaceId:$w){ projects' + args + '{edges{node{id name}} pageInfo{hasNextPage endCursor}}}}'
            variables = {"w": wid, "after": cursor} if supported["projects"] else {"w": wid}
            return mapping(data(gql(query, variables), "projects").get("workspace"), "projects").get("projects")
        project_edges.extend(collect(projects, "projects", supported["projects"]))
    if not project_edges:
        fail("enumeration returned zero projects")
    if len({edge["node"]["id"] for edge in project_edges}) != len(project_edges):
        fail("duplicate project")
    for project_edge in project_edges:
        node = project_edge["node"]
        pid, pname = named(node, "id", "project"), named(node, "name", "project")
        def resource(field):
            def fetch(cursor):
                args = '(first:50,after:$after)' if supported[field] else ''
                signature = '($id:String!,$after:String)' if supported[field] else '($id:String!)'
                query = 'query' + signature + '{project(id:$id){' + field + args + '{edges{node{id name}} pageInfo{hasNextPage endCursor}}}}'
                variables = {"id": pid, "after": cursor} if supported[field] else {"id": pid}
                return mapping(data(gql(query, variables), field).get("project"), field).get(field)
            return collect(fetch, field, supported[field])
        env_edges = resource("environments")
        service_edges = resource("services")
        envs = {named(e["node"], "name", "environment"): named(e["node"], "id", "environment") for e in env_edges}
        eid = envs.get("production") or (next(iter(envs.values())) if envs else None)
        if service_edges and not eid:
            fail("service environment missing")
        item = {"id": pid, "name": pname, "environments": list(envs.keys()), "prod_env_id": eid, "services": []}
        for service_edge in service_edges:
            node = service_edge["node"]
            sid, sname = named(node, "id", "service"), named(node, "name", "service")
            service = {"id": sid, "name": sname}
            deployments = edges(data(gql('query($e:String!,$s:String!){ deployments(first:1, input:{environmentId:$e, serviceId:$s}){ edges{ node{ status createdAt meta } } } }', {"e": eid, "s": sid}), "deployments").get("deployments"), "deployments", True)
            if deployments:
                deployment = deployments[0]["node"]
                meta = mapping(deployment.get("meta") or {}, "deployment meta")
                manifest = mapping(meta.get("serviceManifest") or {}, "service manifest")
                service["source"] = {"repo": meta.get("repo"), "branch": meta.get("branch")}
                service["configFile"] = meta.get("configFile")
                service["build"], service["deploy"] = manifest.get("build"), manifest.get("deploy")
                service["last_deploy"] = {"status": deployment.get("status"), "at": deployment.get("createdAt")}
            else:
                service["meta_note"] = "no deployment returned by successful first:1 query"
            variables = data(gql('query($p:String!,$e:String!,$s:String!){ variables(projectId:$p, environmentId:$e, serviceId:$s) }', {"p": pid, "e": eid, "s": sid}), "variables").get("variables")
            service["variable_names"] = sorted(mapping(variables, "variables").keys())
            item["services"].append(service)
        out["projects"].append(item)
    upload(out, now)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        sys.exit(str(exc))
    except (KeyError, TypeError, ValueError, OSError):
        sys.exit("Railway export incomplete: local export failure")
