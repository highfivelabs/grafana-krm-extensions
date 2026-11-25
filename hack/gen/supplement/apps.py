#!/usr/bin/env python3
# Copyright 2026 High Five Labs
# SPDX-License-Identifier: Apache-2.0
"""Write supplement/apps.yaml: Grafana's app platform APIs (/apis/...), the
Kubernetes-style APIs terraform-provider-grafana's grafana_apps_* resources
(and grafana_scim_config) manage.

Each kind is a namespaced object: POST the collection to create it (the caller
names it in metadata.name), GET, PUT (the whole object; without
metadata.resourceVersion it is an unconditional update, as the provider's
options.overwrite sends it) and DELETE the item.

Spec schemas come from Grafana's own OpenAPI snapshots of each API group
(pkg/tests/apis/openapi_snapshots, at the commit of the pinned
public/openapi3.json). Groups with no snapshot there are described below from
the Go types the provider 4.55.0 builds against (cited at each).

Run from the repository root: python3 hack/gen/supplement/apps.py
"""
import copy
import json
import os
import sys
import urllib.request

import yaml

COMMIT = "3f36380cfd6240f348c2a6226f6fb07647746d60"
SNAP = f"https://raw.githubusercontent.com/grafana/grafana/{COMMIT}/pkg/tests/apis/openapi_snapshots/{{}}.json"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "specs", "apps")

# (Terraform type, API group, version, plural, kind): from the snapshots.
FROM_SNAPSHOTS = [
    ("grafana_apps_dashboard_dashboard_v1beta1", "dashboard.grafana.app", "v1beta1", "dashboards", "Dashboard"),
    ("grafana_apps_dashboard_dashboard_v2beta1", "dashboard.grafana.app", "v2beta1", "dashboards", "Dashboard"),
    ("grafana_apps_dashboard_dashboard_v2", "dashboard.grafana.app", "v2", "dashboards", "Dashboard"),
    ("grafana_apps_playlist_playlist_v0alpha1", "playlist.grafana.app", "v0alpha1", "playlists", "Playlist"),
    ("grafana_apps_playlist_playlist_v1", "playlist.grafana.app", "v1", "playlists", "Playlist"),
    ("grafana_apps_notifications_routingtree_v1beta1", "notifications.alerting.grafana.app", "v1beta1", "routingtrees", "RoutingTree"),
    ("grafana_apps_notifications_timeinterval_v1beta1", "notifications.alerting.grafana.app", "v1beta1", "timeintervals", "TimeInterval"),
    ("grafana_apps_notifications_inhibitionrule_v1beta1", "notifications.alerting.grafana.app", "v1beta1", "inhibitionrules", "InhibitionRule"),
    ("grafana_apps_rules_alertrule_v0alpha1", "rules.alerting.grafana.app", "v0alpha1", "alertrules", "AlertRule"),
    ("grafana_apps_rules_alertrule_v1beta1", "rules.alerting.grafana.app", "v1beta1", "alertrules", "AlertRule"),
    ("grafana_apps_rules_recordingrule_v0alpha1", "rules.alerting.grafana.app", "v0alpha1", "recordingrules", "RecordingRule"),
    ("grafana_apps_rules_recordingrule_v1beta1", "rules.alerting.grafana.app", "v1beta1", "recordingrules", "RecordingRule"),
    ("grafana_apps_rules_rulesequence_v0alpha1", "rules.alerting.grafana.app", "v0alpha1", "rulesequences", "RuleSequence"),
    ("grafana_apps_rules_rulesequence_v1beta1", "rules.alerting.grafana.app", "v1beta1", "rulesequences", "RuleSequence"),
    ("grafana_apps_provisioning_repository_v0alpha1", "provisioning.grafana.app", "v0alpha1", "repositories", "Repository"),
    ("grafana_apps_provisioning_connection_v0alpha1", "provisioning.grafana.app", "v0alpha1", "connections", "Connection"),
]

S, A, B, O = "string", "array", "boolean", "object"


def strs():
    return {"type": A, "items": {"type": S}}


ANY = {"type": O, "additionalProperties": True}

# Groups with no snapshot at COMMIT: (Terraform type, group, version, plural,
# kind, spec schema, source).
HAND = [
    ("grafana_apps_secret_keeper_v1beta1", "secret.grafana.app", "v1beta1", "keepers", "Keeper", {
        "type": O, "required": ["description"], "properties": {
            "description": {"type": S},
            "aws": {"type": O, "required": ["region"], "properties": {
                "region": {"type": S},
                "assumeRole": {"type": O, "required": ["assumeRoleArn", "externalID"], "properties": {
                    "assumeRoleArn": {"type": S}, "externalID": {"type": S}}}}}}},
     "grafana/grafana@75b1e0cf0f79 apps/secret/pkg/apis/secret/v1beta1/keeper_spec_gen.go"),
    ("grafana_apps_secret_securevalue_v1beta1", "secret.grafana.app", "v1beta1", "securevalues", "SecureValue", {
        "type": O, "required": ["description"], "properties": {
            "description": {"type": S},
            "value": {"type": S},
            "ref": {"type": S},
            "decrypters": strs()}},
     "grafana/grafana@75b1e0cf0f79 apps/secret/pkg/apis/secret/v1beta1/securevalue_spec_gen.go"),
    ("grafana_apps_alertenrichment_alertenrichment_v1beta1", "alertenrichment.grafana.app", "v1beta1", "alertenrichments", "AlertEnrichment", {
        "type": O, "required": ["title", "steps"], "properties": {
            "title": {"type": S},
            "description": {"type": S},
            "alertRuleUids": strs(),
            "labelMatchers": {"type": A, "items": {"$ref": "#/components/schemas/AlertEnrichmentMatcher"}},
            "annotationMatchers": {"type": A, "items": {"$ref": "#/components/schemas/AlertEnrichmentMatcher"}},
            "receivers": strs(),
            "steps": {"type": A, "items": dict(ANY)}}},
     "grafana/grafana@89b988ca553e apps/alerting/alertenrichment/pkg/apis/alertenrichment/v1beta1/types.go"),
    ("grafana_apps_queries_query_v1", "queries.grafana.app", "v1", "queries", "Query", {
        "type": O, "required": ["targets"], "properties": {
            "title": {"type": S}, "description": {"type": S}, "isVisible": {"type": B}, "isLocked": {"type": B},
            "tags": strs(),
            "vars": {"type": A, "items": ANY},
            "targets": {"type": A, "items": {"type": O, "required": ["properties"], "properties": {
                "dataType": {"type": S}, "variables": ANY, "properties": dict(ANY)}}}}},
     "terraform-provider-grafana v4.55.0 internal/resources/appplatform/query_resource.go"),
    ("grafana_apps_productactivation_appo11yconfig_v1alpha1", "productactivation.ext.grafana.com", "v1alpha1", "appo11yconfigs", "AppO11yConfig", {
        "type": O, "required": ["enabled"], "properties": {"enabled": {"type": B}}},
     "terraform-provider-grafana v4.55.0 internal/resources/appplatform/appo11y_config_resource.go"),
    ("grafana_apps_productactivation_dbo11yconfig_v1alpha1", "productactivation.ext.grafana.com", "v1alpha1", "dbo11yconfigs", "DbO11yConfig", {
        "type": O, "required": ["enabled"], "properties": {"enabled": {"type": B}}},
     "terraform-provider-grafana v4.55.0 internal/resources/appplatform/dbo11y_config_resource.go"),
    ("grafana_apps_productactivation_k8so11yconfig_v1alpha1", "productactivation.ext.grafana.com", "v1alpha1", "k8so11yconfigs", "K8sO11yConfig", {
        "type": O, "required": ["enabled"], "properties": {"enabled": {"type": B}}},
     "terraform-provider-grafana v4.55.0 internal/resources/appplatform/k8so11y_config_resource.go"),
    ("grafana_apps_servicemodel_component_v1alpha1", "servicemodel.ext.grafana.com", "v1alpha1", "components", "Component", {
        "type": O, "required": ["type"], "properties": {
            "type": {"type": S},
            "title": {"type": S}, "description": {"type": S},
            "identifiers": {"type": A, "items": {"type": O, "required": ["key", "value"], "properties": {"key": {"type": S}, "value": {"type": S}}}},
            "metadata": {"type": O, "required": ["name"], "properties": {
                "name": {"type": S},
                "links": {"type": A, "items": {"type": O, "required": ["url"], "properties": {
                    "url": {"type": S}, "title": {"type": S}, "icon": {"type": S}, "type": {"type": S}}}}}},
            "ownerRef": {"$ref": "#/components/schemas/ServiceModelRef"},
            "dependsOnRefs": {"type": A, "items": {"$ref": "#/components/schemas/ServiceModelRef"}}}},
     "terraform-provider-grafana v4.55.0 internal/resources/appplatform/servicemodel_component_resource.go"),
]
EXTRA_SCHEMAS = {
    "AlertEnrichmentMatcher": {"type": O, "required": ["type", "name", "value"], "properties": {
        "type": {"type": S, "enum": ["=", "!=", "=~", "!~"]}, "name": {"type": S}, "value": {"type": S}}},
    "ServiceModelRef": {"type": O, "required": ["apiVersion", "kind", "name"], "properties": {
        "apiVersion": {"type": S}, "kind": {"type": S}, "name": {"type": S}}},
}

META = {
    "ObjectMeta": {"type": O, "required": ["name"], "properties": {
        "name": {"type": S},
        "labels": {"type": O, "additionalProperties": {"type": S}},
        "annotations": {"type": O, "additionalProperties": {"type": S}},
        "uid": {"type": S, "readOnly": True},
        "namespace": {"type": S, "readOnly": True},
        "resourceVersion": {"type": S, "readOnly": True},
        "generation": {"type": "integer", "readOnly": True},
        "creationTimestamp": {"type": S, "readOnly": True}}},
}


class NoAliases(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def snapshot(name):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, name + ".json")
    if not os.path.exists(p):
        with urllib.request.urlopen(SNAP.format(name)) as r, open(p, "wb") as f:
            f.write(r.read())
    return json.load(open(p))


def closure(doc, root, out):
    """Copy component root and every component it refers to into out."""
    todo = [root]
    while todo:
        n = todo.pop()
        if n in out:
            continue
        s = doc["components"]["schemas"][n]
        out[n] = s
        for ref in refs(s):
            todo.append(ref.split("/")[-1])


def refs(s):
    if isinstance(s, dict):
        for k, v in s.items():
            if k == "$ref":
                yield v
            else:
                yield from refs(v)
    elif isinstance(s, list):
        for v in s:
            yield from refs(v)


def obj(name, group, version, kind, spec, status=True):
    gv = f"{group}/{version}"
    w = {"type": O, "required": ["apiVersion", "kind", "metadata", "spec"], "properties": {
        "apiVersion": {"type": S, "enum": [gv], "default": gv},
        "kind": {"type": S, "enum": [kind], "default": kind},
        "metadata": {"$ref": "#/components/schemas/ObjectMeta"},
        "spec": spec}}
    r = copy.deepcopy(w)
    if status:
        r["properties"]["status"] = {"type": O, "readOnly": True, "additionalProperties": True}
    return {name + "Write": w, name: r}


def body(ref):
    return {"required": True, "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{ref}"}}}}


def ok(ref, code="200"):
    return {code: {"content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{ref}"}}}}}


def crud(paths, name, group, version, plural, tf):
    coll = f"/apis/{group}/{version}/namespaces/{{namespace}}/{plural}"
    ns = {"in": "path", "name": "namespace", "required": True, "schema": {"type": S}}
    paths[coll] = {"parameters": [ns], "post": {"operationId": f"create{name}", "requestBody": body(name + "Write"), "responses": ok(name, "201")}}
    paths[coll + "/{name}"] = {
        "parameters": [ns, {"in": "path", "name": "name", "required": True, "schema": {"type": S}}],
        "get": {"operationId": f"get{name}", "responses": ok(name)},
        "put": {"operationId": f"replace{name}", "requestBody": body(name + "Write"), "responses": ok(name)},
        "delete": {"operationId": f"delete{name}", "responses": {"200": {"description": "Deleted"}}}}


def main():
    paths, schemas = {}, dict(META)
    for tf, group, version, plural, kind in FROM_SNAPSHOTS:
        doc = snapshot(f"{group}-{version}")
        it = doc["paths"][f"/apis/{group}/{version}/namespaces/{{namespace}}/{plural}/{{name}}"]
        full = it["put"]["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
        spec = doc["components"]["schemas"][full]["properties"]["spec"]
        for ref in refs(spec):
            closure(doc, ref.split("/")[-1], schemas)
        name = tf[len("grafana_apps_"):].title().replace("_", "")
        schemas.update(obj(name, group, version, kind, spec))
        crud(paths, name, group, version, plural, tf)
    for tf, group, version, plural, kind, spec, _ in HAND:
        name = tf[len("grafana_apps_"):].title().replace("_", "")
        schemas.update(obj(name, group, version, kind, spec))
        crud(paths, name, group, version, plural, tf)
    schemas.update(EXTRA_SCHEMAS)

    # Any app platform object, named by its group, version and plural
    # (grafana_apps_generic_resource).
    ns = {"in": "path", "name": "namespace", "required": True, "schema": {"type": S}}
    gvp = [{"in": "path", "name": n, "required": True, "schema": {"type": S}, "description": d} for n, d in (
        ("group", "The API group, e.g. dashboard.grafana.app."), ("version", "The API version, e.g. v1beta1."),
        ("plural", "The resource's plural name, e.g. dashboards."))]
    schemas["GenericResourceWrite"] = {"type": O, "required": ["apiVersion", "kind", "metadata"], "properties": {
        "apiVersion": {"type": S},
        "kind": {"type": S}, "metadata": {"$ref": "#/components/schemas/ObjectMeta"},
        "spec": dict(ANY)}}
    schemas["GenericResource"] = copy.deepcopy(schemas["GenericResourceWrite"])
    schemas["GenericResource"]["properties"]["status"] = {"type": O, "readOnly": True, "additionalProperties": True}
    coll = "/apis/{group}/{version}/namespaces/{namespace}/{plural}"
    paths[coll] = {"parameters": gvp[:2] + [ns, gvp[2]], "post": {"operationId": "createGenericResource", "requestBody": body("GenericResourceWrite"), "responses": ok("GenericResource", "201")}}
    paths[coll + "/{name}"] = {"parameters": gvp[:2] + [ns, gvp[2], {"in": "path", "name": "name", "required": True, "schema": {"type": S}}],
                               "get": {"operationId": "getGenericResource", "responses": ok("GenericResource")},
                               "put": {"operationId": "replaceGenericResource", "requestBody": body("GenericResourceWrite"), "responses": ok("GenericResource")},
                               "delete": {"operationId": "deleteGenericResource", "responses": {"200": {"description": "Deleted"}}}}

    # SCIM settings: one object, named default (grafana_scim_config; Grafana
    # Enterprise and Cloud). terraform-provider-grafana v4.55.0
    # internal/resources/grafana/resource_scim_config.go: GET, PUT (creates or
    # replaces) and DELETE on .../config/default.
    schemas.update(obj("ScimConfig", "scim.grafana.app", "v0alpha1", "SCIMConfig", {
        "type": O, "properties": {
            "enableUserSync": {"type": B},
            "enableGroupSync": {"type": B},
            "rejectNonProvisionedUsers": {"type": B}}}, status=False))
    schemas["ScimConfigWrite"]["properties"]["metadata"] = {"type": O, "required": ["name"], "properties": {
        "name": {"type": S, "enum": ["default"], "default": "default"}}}
    schemas["ScimConfig"]["properties"]["metadata"] = schemas["ScimConfigWrite"]["properties"]["metadata"]
    paths["/apis/scim.grafana.app/v0alpha1/namespaces/{namespace}/config/default"] = {
        "parameters": [ns],
        "get": {"operationId": "getScimConfig", "responses": ok("ScimConfig")},
        "put": {"operationId": "replaceScimConfig", "requestBody": body("ScimConfigWrite"), "responses": ok("ScimConfig")},
        "delete": {"operationId": "deleteScimConfig", "responses": {"200": {"description": "Deleted"}}}}

    for s in schemas.values():
        # A snapshot's spec references its own components; nothing else.
        for r in refs(s):
            if r.split("/")[-1] not in schemas:
                sys.exit(f"unresolved {r}")
    head = "\n".join("# " + line if line else "#" for line in (
        "Code generated by hack/gen/supplement/apps.py. DO NOT EDIT.",
        "",
        "Grafana's app platform APIs (/apis/...), for krm-rest-runtime's generator.",
        "Paths are relative to the Grafana root URL (https://<stack>.grafana.net),",
        "not its /api: a second Connection (README).",
        "",
        f"Spec schemas: Grafana's OpenAPI snapshots at grafana/grafana@{COMMIT}",
        "(pkg/tests/apis/openapi_snapshots/<group>-<version>.json), and:",
        *[f"- {k}: {src}" for _, _, _, _, k, _, src in HAND],
        "- SCIMConfig: terraform-provider-grafana v4.55.0 internal/resources/grafana/resource_scim_config.go",
        "Methods: the provider's app platform client (internal/resources/appplatform/resource.go,",
        "Create, Update with options.overwrite, Delete). Written 2026-11-22.",
    ))
    out = {"openapi": "3.0.3", "info": {"title": "Grafana app platform APIs (supplement)", "version": COMMIT[:12]},
           "paths": paths, "components": {"schemas": schemas}}
    with open(os.path.join(HERE, "apps.yaml"), "w") as f:
        f.write(head + "\n")
        yaml.dump(out, f, Dumper=NoAliases, sort_keys=False, width=1000)


if __name__ == "__main__":
    main()
