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


def edges(connection, stage, require_page_info=True):
    connection = mapping(connection, stage)
    result = connection.get("edges")
    if not isinstance(result, list):
        fail(stage)
    info = connection.get("pageInfo")
    if require_page_info and info is None:
        fail(stage + " pagination unverified")
    if info is not None and mapping(info, stage).get("hasNextPage") is not False:
        fail(stage + " pagination incomplete")
    count = connection.get("totalCount")
    if count is not None and (type(count) is not int or count != len(result)):
        fail(stage + " pagination incomplete")
    if info is None and any(isinstance(edge, dict) and edge.get("cursor") is not None for edge in result):
        fail(stage + " pagination unverified")
    for edge in result:
        mapping(mapping(edge, stage).get("node"), stage)
    return result


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
        result = subprocess.run(["aws", "s3", "cp", name, f"s3://{BUCKET}/{key}",
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
    workspaces = mapping(data(gql('{ me { workspaces { projects { edges { node { id name } } pageInfo { hasNextPage } } } } }'), "enumeration").get("me"), "enumeration").get("workspaces")
    if not isinstance(workspaces, list):
        fail("enumeration")
    project_edges = []
    for workspace in workspaces:
        project_edges.extend(edges(mapping(workspace, "workspace").get("projects"), "projects"))
    if not project_edges:
        fail("enumeration returned zero projects")
    for project_edge in project_edges:
        node = project_edge["node"]
        pid, pname = named(node, "id", "project"), named(node, "name", "project")
        project = mapping(data(gql('query($id:String!){ project(id:$id){ name environments{edges{node{id name}} pageInfo{hasNextPage}} services{edges{node{id name}} pageInfo{hasNextPage}} } }', {"id": pid}), "project").get("project"), "project")
        env_edges = edges(project.get("environments"), "environments")
        service_edges = edges(project.get("services"), "services")
        envs = {named(e["node"], "name", "environment"): named(e["node"], "id", "environment") for e in env_edges}
        eid = envs.get("production") or (next(iter(envs.values())) if envs else None)
        if service_edges and not eid:
            fail("service environment missing")
        item = {"id": pid, "name": pname, "environments": list(envs.keys()), "prod_env_id": eid, "services": []}
        for service_edge in service_edges:
            node = service_edge["node"]
            sid, sname = named(node, "id", "service"), named(node, "name", "service")
            service = {"id": sid, "name": sname}
            deployments = edges(data(gql('query($e:String!,$s:String!){ deployments(first:1, input:{environmentId:$e, serviceId:$s}){ edges{ node{ status createdAt meta } } } }', {"e": eid, "s": sid}), "deployments").get("deployments"), "deployments", False)
            if deployments:
                deployment = deployments[0]["node"]
                meta = mapping(deployment.get("meta") or {}, "deployment meta")
                manifest = mapping(meta.get("serviceManifest") or {}, "service manifest")
                service["source"] = {"repo": meta.get("repo"), "branch": meta.get("branch")}
                service["configFile"] = meta.get("configFile")
                service["build"], service["deploy"] = manifest.get("build"), manifest.get("deploy")
                service["last_deploy"] = {"status": deployment.get("status"), "at": deployment.get("createdAt")}
            else:
                service["meta_note"] = "no deployment meta (e.g. database plugin) list index out of range"
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
