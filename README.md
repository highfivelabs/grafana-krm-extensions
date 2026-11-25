# grafana-krm-extensions

Kubernetes kinds for the Grafana configuration that Terraform's
`grafana/grafana` provider manages and Grafana's operators do not. Grafana's official grafana-operator manages dashboards, folders, data sources, alerting, library panels and service accounts, on in-cluster or external (Grafana Cloud) instances.

By the numbers: `grafana/grafana` is the #27 Terraform provider by downloads
(247,802,715); version 4.55.0 has 130 resources. Operators
cover 11. This repository adds **111 kinds** standing in for
**116 more**. Each gap kind is listed below with its Terraform equivalent.

**Readiness: 30 of 111 kinds also proven against the real API** (Grafana OSS
13.3.1, the release nearest the pinned spec). Every kind passes create,
update, drift repair and delete against a fake built from the same
descriptors (`TestEveryKindOnFake`). The kinds in `hack/live/live.yaml` run
the same steps against a real Grafana (`TestEveryKindLive`, built only with
`-tags live`); `hack/live/records.json` holds each one's last result, and
`zz_generated.report.md` marks those that passed `live`. Report, Role and
RoleAssignment are Grafana Enterprise APIs (the open-source image answers
404): treat them as untested against the real API, like every kind added
since for Grafana Enterprise and Grafana Cloud APIs (readiness `fake`).

```sh
task live:grafana               # Grafana OSS in Docker (127.0.0.1:13000, admin/admin), every kind, records.json
task live:sandbox:grafana       # just the sandbox, with an Admin service-account token
task live:sandbox:grafana:down  # remove it
```

**Credentials.** The Connection Secret's `token` is a service-account token,
or `user:password` for basic auth (as the Terraform provider's `auth`). A
service account belongs to one organization and is never a Grafana server
administrator, so Organization, User and SsoSettings need a server
administrator's basic auth; the other kinds work with an Admin
service-account token.

## Grafana's other APIs: a Connection each

Most kinds call the Grafana HTTP API, through the namespace's `default`
Connection. The kinds below call another of Grafana's APIs, on another base
URL, and say which with `spec.connectionRef.name`: make one Connection (and
Secret) per API and name it in each object.

| Kinds | Connection `baseURL` | Secret |
| --- | --- | --- |
| `Apps*` (the app platform: dashboards v1beta1/v2beta1/v2, playlists, alert and recording rules, notification policies, secrets, provisioning, ...) and `ScimConfig` | the Grafana root URL, `https://<stack>.grafana.net` (not `/api`): these are its `/apis/...` APIs. Each object's `spec.namespace` is the Grafana namespace: `default` for org 1 on-premises, `stacks-<stack ID>` in Grafana Cloud | `token`: the same as the Grafana kinds |
| `Slo` | `https://<stack>.grafana.net/api/plugins/grafana-slo-app/resources` (the stack's Grafana, under the SLO app's path) | `token`: the same service-account token as the Grafana kinds |
| `CloudStack`, `CloudOrgMember`, `CloudPluginInstallation`, `CloudStackServiceAccount`, `CloudStackServiceAccountRotatingToken`, `CloudAccessPolicy`, `CloudAccessPolicyToken`, `CloudAccessPolicyRotatingToken` | `https://grafana.com/api` | `token`: an access policy token for Grafana Cloud, scoped to what the objects need (`stacks:*`, `orgs:*`, `stack-plugins:*`, `stack-service-accounts:write`, `accesspolicies:*`) |
| `Agento11y*` (AI Observability evaluators, evaluation and hook rules, rule actions, collections) | `https://<stack>.grafana.net/api/plugins/grafana-agento11y-app/resources/eval` | `token`: the same service-account token as the Grafana kinds |
| `Asserts*` (custom model rules; log, profile and trace drilldown configs; notification alert and suppressed assertion configs; the stack) | `https://<stack>.grafana.net/api/plugins/grafana-asserts-app/resources/asserts/api-server` | `token`: the same service-account token as the Grafana kinds; `scopeOrgID`: the stack's ID |
| `AssistantTermsAcceptance` | `https://<stack>.grafana.net/api/plugins/grafana-assistant-app/resources/api/v1` | `token`: the same service-account token as the Grafana kinds |
| `MachineLearning*` (forecast jobs, holidays, outlier detectors, their alerts) | `https://<stack>.grafana.net/api/plugins/grafana-ml-app/resources` | `token`: the same service-account token as the Grafana kinds |
| `CloudProvider*` (AWS accounts, AWS CloudWatch and resource metadata scrape jobs, Azure credentials) | the stack's Cloud Provider API URL (the stack's `cloud_provider_url` in Terraform), e.g. `https://cloud-provider-api-prod-us-central-0.grafana.net` | `token`: a Grafana Cloud access policy token with `integration-management:read`, `integration-management:write` and `stacks:read` |
| `ConnectionsMetricsEndpointScrapeJob` | the Connections API URL (the stack's `connections_api_url`), `https://connections-api.grafana.net` by default | `token`: a Grafana Cloud access policy token with `integration-management:read`, `integration-management:write` and `stacks:read` |
| `K6*` (projects, project limits, allowed load zones) | `https://api.k6.io` | `token`: a Grafana Cloud k6 personal or stack API token; `stackID`: the stack's numeric ID (sent as `X-Stack-Id`) |
| `SyntheticMonitoringCheck`, `SyntheticMonitoringProbe`, `SyntheticMonitoringCheckAlerts` | the stack's Synthetic Monitoring API URL, e.g. `https://synthetic-monitoring-api.grafana.net` | `token`: a Synthetic Monitoring access token |
| `FrontendO11yApp` | the stack region's Faro API URL, e.g. `https://faro-api-prod-us-central-0.grafana.net/faro` | `token`: `<stack ID>:<Grafana Cloud access policy token>`, with `scheme: bearer` and `scopeOrgID: <stack ID>` |
| `Oncall*` | the stack's OnCall API URL (Grafana IRM, Settings: e.g. `https://oncall-prod-us-central-0.grafana.net/oncall`) | `token`: an OnCall API token, with `scheme: none`; or a Grafana service-account token, with `scheme: none` and `grafanaURL: https://<stack>.grafana.net` |
| `FleetManagementCollector`, `FleetManagementPipeline` | the stack's Fleet Management URL (Terraform's `fleet_management_url`), e.g. `https://fleet-management-prod-001.grafana.net` | `token`: `<Fleet Management instance ID>:<Grafana Cloud access policy token>` (basic auth; the token needs `fleet-management:read` and `fleet-management:write`) |

The Secret's optional keys, beside `token`: `scheme: none` sends the token as
the whole `Authorization` header (OnCall's API tokens), `scheme: bearer`
sends it as a Bearer token even when it holds a colon (which otherwise means
`user:password`), `grafanaURL` is sent as `X-Grafana-URL`, `stackID` as
`X-Stack-Id` and `scopeOrgID` as `X-Scope-OrgID`.

Their specs: Grafana SLO's, Grafana Cloud's, k6's and Asserts' own OpenAPI specs, at the
commits `terraform-provider-grafana` 4.55.0 pins
(`hack/gen/fetch-specs.sh`), and, where Grafana publishes none, a
supplement in `hack/gen/supplement/` that cites its sources (Synthetic
Monitoring, Frontend Observability, AI Observability, OnCall, Machine
Learning, Cloud Provider, Connections, Assistant). The Assistant kinds call
the stack's Grafana API through the `default` Connection, under
`/plugins/grafana-assistant-app/resources/api/v1`; so do the `Incident*`
kinds (severities, roles, custom fields), under Grafana IRM's
`/plugins/grafana-irm-app/resources/api/v1`. The `Incident*` and
`FleetManagement*` kinds are written by hand (`hack/gen/kinds/`, sources in
each) from the API clients Terraform's provider uses: their APIs are RPCs,
each call a POST naming the object in its body. The app platform's
(`supplement/apps.yaml`) is written by `supplement/apps.py` from Grafana's
own OpenAPI snapshots of each API group, at the commit of the pinned
`openapi3.json`.

## How it works

The kinds are generated, not hand-written. `hack/gen/vendor.yaml` pins
Grafana's OpenAPI spec; [krm-rest-runtime](https://github.com/highfivelabs/krm-rest-runtime)'s
generator finds every resource the API exposes in a create/read/update/delete
shape, keeps those that stand in for a Terraform resource in the gap list
(`hack/gen/terraform-gaps.json`), and writes:

- `types.yaml`: per kind, its API calls, path parameters and Terraform equivalents
- `config/crds/`: one CRD per kind, its spec the API's request body
- `zz_generated.report.md`: the full list

One generic manager (`cmd/manager`) runs every kind on krm-rest-runtime's
reconciler: it creates the resource, reads it back every 10 minutes and
puts back anything changed outside Kubernetes, and deletes it with the
object. Spec fields keep Grafana's own names, so the API reference
applies field for field. Path parameters are spec fields too.

Hand corrections to the automatic matching (a Terraform type matched to
the wrong API path, or not matched) are in `vendor.yaml`'s `overrides`.

## Install

```sh
kubectl kustomize config/default | KO_DOCKER_REPO=<registry> ko resolve -f - | kubectl apply --server-side -f -
```

Then, in each namespace that manages Grafana, a Secret with
`token` (a service-account token, or `user:password`) and a Connection named `default`
(`config/samples/connection.yaml`). Objects use it unless
`spec.connectionRef.name` names another. Secret values (tokens, passwords,
secret values) go in a Kubernetes Secret, not the spec:
`spec.secretRefs: {<field>: {name, key}}` fills that body field.

To run only some API groups, install those groups' CRDs from `config/crds`
and pass `--groups` to the manager.

## Kinds

| Kind | Terraform equivalent | Shape | Read |
| --- | --- | --- | --- |
| `agento11y.grafana.hfl.dev/v1alpha1` `Agento11yCollection` | `grafana_agento11y_collection` | crud | `GET /collections/{collection_id}` |
| `agento11y.grafana.hfl.dev/v1alpha1` `Agento11yEvaluationRule` | `grafana_agento11y_evaluation_rule` | crud | `GET /rules/{rule_id}` |
| `agento11y.grafana.hfl.dev/v1alpha1` `Agento11yEvaluator` | `grafana_agento11y_evaluator` | crud | `GET /evaluators/{evaluator_id}` |
| `agento11y.grafana.hfl.dev/v1alpha1` `Agento11yHookRule` | `grafana_agento11y_hook_rule` | crud | `GET /hook-rules/{rule_id}` |
| `agento11y.grafana.hfl.dev/v1alpha1` `Agento11yRuleAction` | `grafana_agento11y_rule_action` | crud | `GET /rules/{rule_id}/actions/{action_id}` |
| `annotation.grafana.hfl.dev/v1alpha1` `Annotation` | `grafana_annotation` | crud | `GET /annotations/{annotation_id}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsAlertenrichmentAlertenrichmentV1beta1` | `grafana_apps_alertenrichment_alertenrichment_v1beta1` | crud | `GET /apis/alertenrichment.grafana.app/v1beta1/namespaces/{namespace}/alertenrichments/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsDashboardDashboardV1beta1` | `grafana_apps_dashboard_dashboard_v1beta1` | crud | `GET /apis/dashboard.grafana.app/v1beta1/namespaces/{namespace}/dashboards/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsDashboardDashboardV2` | `grafana_apps_dashboard_dashboard_v2` | crud | `GET /apis/dashboard.grafana.app/v2/namespaces/{namespace}/dashboards/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsDashboardDashboardV2beta1` | `grafana_apps_dashboard_dashboard_v2beta1` | crud | `GET /apis/dashboard.grafana.app/v2beta1/namespaces/{namespace}/dashboards/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsGenericResource` | `grafana_apps_generic_resource` | crud | `GET /apis/{group}/{version}/namespaces/{namespace}/{plural}/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsNotificationsInhibitionruleV1beta1` | `grafana_apps_notifications_inhibitionrule_v1beta1` | crud | `GET /apis/notifications.alerting.grafana.app/v1beta1/namespaces/{namespace}/inhibitionrules/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsNotificationsRoutingtreeV1beta1` | `grafana_apps_notifications_routingtree_v1beta1` | crud | `GET /apis/notifications.alerting.grafana.app/v1beta1/namespaces/{namespace}/routingtrees/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsNotificationsTimeintervalV1beta1` | `grafana_apps_notifications_timeinterval_v1beta1` | crud | `GET /apis/notifications.alerting.grafana.app/v1beta1/namespaces/{namespace}/timeintervals/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsPlaylistPlaylistV0alpha1` | `grafana_apps_playlist_playlist_v0alpha1` | crud | `GET /apis/playlist.grafana.app/v0alpha1/namespaces/{namespace}/playlists/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsPlaylistPlaylistV1` | `grafana_apps_playlist_playlist_v1` | crud | `GET /apis/playlist.grafana.app/v1/namespaces/{namespace}/playlists/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsProductactivationAppo11yconfigV1alpha1` | `grafana_apps_productactivation_appo11yconfig_v1alpha1` | crud | `GET /apis/productactivation.ext.grafana.com/v1alpha1/namespaces/{namespace}/appo11yconfigs/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsProductactivationDbo11yconfigV1alpha1` | `grafana_apps_productactivation_dbo11yconfig_v1alpha1` | crud | `GET /apis/productactivation.ext.grafana.com/v1alpha1/namespaces/{namespace}/dbo11yconfigs/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsProductactivationK8so11yconfigV1alpha1` | `grafana_apps_productactivation_k8so11yconfig_v1alpha1` | crud | `GET /apis/productactivation.ext.grafana.com/v1alpha1/namespaces/{namespace}/k8so11yconfigs/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsProvisioningConnectionV0alpha1` | `grafana_apps_provisioning_connection_v0alpha1` | crud | `GET /apis/provisioning.grafana.app/v0alpha1/namespaces/{namespace}/connections/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsProvisioningRepositoryV0alpha1` | `grafana_apps_provisioning_repository_v0alpha1` | crud | `GET /apis/provisioning.grafana.app/v0alpha1/namespaces/{namespace}/repositories/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsQueriesQueryV1` | `grafana_apps_queries_query_v1` | crud | `GET /apis/queries.grafana.app/v1/namespaces/{namespace}/queries/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsRulesAlertruleV0alpha1` | `grafana_apps_rules_alertrule_v0alpha1` | crud | `GET /apis/rules.alerting.grafana.app/v0alpha1/namespaces/{namespace}/alertrules/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsRulesAlertruleV1beta1` | `grafana_apps_rules_alertrule_v1beta1` | crud | `GET /apis/rules.alerting.grafana.app/v1beta1/namespaces/{namespace}/alertrules/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsRulesRecordingruleV0alpha1` | `grafana_apps_rules_recordingrule_v0alpha1` | crud | `GET /apis/rules.alerting.grafana.app/v0alpha1/namespaces/{namespace}/recordingrules/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsRulesRecordingruleV1beta1` | `grafana_apps_rules_recordingrule_v1beta1` | crud | `GET /apis/rules.alerting.grafana.app/v1beta1/namespaces/{namespace}/recordingrules/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsRulesRulesequenceV0alpha1` | `grafana_apps_rules_rulesequence_v0alpha1` | crud | `GET /apis/rules.alerting.grafana.app/v0alpha1/namespaces/{namespace}/rulesequences/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsRulesRulesequenceV1beta1` | `grafana_apps_rules_rulesequence_v1beta1` | crud | `GET /apis/rules.alerting.grafana.app/v1beta1/namespaces/{namespace}/rulesequences/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsSecretKeeperActivationV1beta1` | `grafana_apps_secret_keeper_activation_v1beta1` | settings | `GET /apis/secret.grafana.app/v1beta1/namespaces/{namespace}/keepers/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsSecretKeeperV1beta1` | `grafana_apps_secret_keeper_v1beta1` | crud | `GET /apis/secret.grafana.app/v1beta1/namespaces/{namespace}/keepers/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsSecretSecurevalueV1beta1` | `grafana_apps_secret_securevalue_v1beta1` | crud | `GET /apis/secret.grafana.app/v1beta1/namespaces/{namespace}/securevalues/{name}` |
| `apps.grafana.hfl.dev/v1alpha1` `AppsServicemodelComponentV1alpha1` | `grafana_apps_servicemodel_component_v1alpha1` | crud | `GET /apis/servicemodel.ext.grafana.com/v1alpha1/namespaces/{namespace}/components/{name}` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsCustomModelRules` | `grafana_asserts_custom_model_rules` | upsert | `GET /v1/config/model-rules/{name}` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsLogConfig` | `grafana_asserts_log_config` | crud | `GET /v2/config/log` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsNotificationAlertsConfig` | `grafana_asserts_notification_alerts_config` | crud | `GET /v1/config/alerts` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsProfileConfig` | `grafana_asserts_profile_config` | crud | `GET /v2/config/profile` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsPromRuleFile` | `grafana_asserts_prom_rule_file` | crud | `GET /v1/config/prom-rules/{name}` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsStack` | `grafana_asserts_stack` | settings | `GET /v1/stack/status` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsSuppressedAssertionsConfig` | `grafana_asserts_suppressed_assertions_config` | crud | `GET /v1/config/disabled-alerts` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsThresholdsConfig` | `grafana_asserts_thresholds` | upsert | `GET /v2/config/threshold` |
| `asserts.grafana.hfl.dev/v1alpha1` `AssertsTraceConfig` | `grafana_asserts_trace_config` | crud | `GET /v2/config/trace` |
| `assistant.grafana.hfl.dev/v1alpha1` `AssistantAutomation` | `grafana_assistant_automation` | crud | `GET /plugins/grafana-assistant-app/resources/api/v1/automations/{id}` |
| `assistant.grafana.hfl.dev/v1alpha1` `AssistantMcpServer` | `grafana_assistant_mcp_server` | crud | `GET /plugins/grafana-assistant-app/resources/api/v1/integrations/{id}` |
| `assistant.grafana.hfl.dev/v1alpha1` `AssistantQuickstart` | `grafana_assistant_quickstart` | crud | `GET /plugins/grafana-assistant-app/resources/api/v1/quickstarts/{id}` |
| `assistant.grafana.hfl.dev/v1alpha1` `AssistantRule` | `grafana_assistant_rule` | crud | `GET /plugins/grafana-assistant-app/resources/api/v1/rules/{id}` |
| `assistant.grafana.hfl.dev/v1alpha1` `AssistantSkill` | `grafana_assistant_skill` | crud | `GET /plugins/grafana-assistant-app/resources/api/v1/skills/{id}` |
| `assistant.grafana.hfl.dev/v1alpha1` `AssistantTermsAcceptance` | `grafana_assistant_terms_acceptance` | settings | `GET /settings/terms` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudAccessPolicy` | `grafana_cloud_access_policy`, `grafana_cloud_private_data_source_connect_network` | crud | `GET /v1/accesspolicies/{id}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudAccessPolicyRotatingToken` | `grafana_cloud_access_policy_rotating_token` | crud | `GET /v1/tokens/{id}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudAccessPolicyToken` | `grafana_cloud_access_policy_token`, `grafana_cloud_private_data_source_connect_network_token` | crud | `GET /v1/tokens/{id}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudOrgMember` | `grafana_cloud_org_member` | crud | `GET /orgs/{slugOrId}/members/{usernameOrId}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudPluginInstallation` | `grafana_cloud_plugin_installation` | crud | `GET /instances/{instanceId}/plugins/{pluginSlugOrId}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudProviderAwsAccount` | `grafana_cloud_provider_aws_account` | crud | `GET /api/v2/stacks/{stack_id}/aws/accounts/{account_id}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudProviderAwsCloudwatchScrapeJob` | `grafana_cloud_provider_aws_cloudwatch_scrape_job` | crud | `GET /api/v2/stacks/{stack_id}/aws/jobs/cloudwatch/{job_name}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudProviderAwsResourceMetadataScrapeJob` | `grafana_cloud_provider_aws_resource_metadata_scrape_job` | crud | `GET /api/v2/stacks/{stack_id}/aws/jobs/resources/{job_name}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudProviderAzureCredential` | `grafana_cloud_provider_azure_credential` | crud | `GET /api/v2/stacks/{stack_id}/azure/credentials/{credential_id}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudStack` | `grafana_cloud_stack` | crud | `GET /v1/stacks/{idOrSlug}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudStackServiceAccount` | `grafana_cloud_stack_service_account` | crud | `GET /instances/{instanceId}/api/serviceaccounts/{serviceAccountId}` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudStackServiceAccountRotatingToken` | `grafana_cloud_stack_service_account_rotating_token` | crud | `GET /instances/{instanceId}/api/serviceaccounts/{serviceAccountId}/tokens` |
| `cloud.grafana.hfl.dev/v1alpha1` `CloudStackServiceAccountToken` | `grafana_cloud_stack_service_account_token` | crud | `GET /instances/{instanceId}/api/serviceaccounts/{serviceAccountId}/tokens` |
| `connections.grafana.hfl.dev/v1alpha1` `ConnectionsMetricsEndpointScrapeJob` | `grafana_connections_metrics_endpoint_scrape_job` | upsert | `GET /api/v1/stacks/{stack_id}/metrics-endpoint/jobs/{job_name}` |
| `dashboard.grafana.hfl.dev/v1alpha1` `DashboardPermission` | `grafana_dashboard_permission` | settings | `GET /dashboards/uid/{uid}/permissions` |
| `dashboard.grafana.hfl.dev/v1alpha1` `DashboardPublic` | `grafana_dashboard_public` | crud | `GET /dashboards/uid/{dashboardUid}/public-dashboards` |
| `data.grafana.hfl.dev/v1alpha1` `DataSourceCacheConfig` | `grafana_data_source_cache_config` | settings | `GET /datasources/{dataSourceUID}/cache` |
| `data.grafana.hfl.dev/v1alpha1` `DataSourceConfig` | `grafana_data_source_config` | upsert | `GET /datasources/uid/{uid}` |
| `data.grafana.hfl.dev/v1alpha1` `DataSourceConfigLbacRules` | `grafana_data_source_config_lbac_rules` | settings | `GET /datasources/uid/{uid}/lbac/teams` |
| `fleet.grafana.hfl.dev/v1alpha1` `FleetManagementCollector` | `grafana_fleet_management_collector` | upsert | `POST /collector.v1.CollectorService/GetCollector` |
| `fleet.grafana.hfl.dev/v1alpha1` `FleetManagementPipeline` | `grafana_fleet_management_pipeline` | crud | `POST /pipeline.v1.PipelineService/GetPipeline` |
| `folder.grafana.hfl.dev/v1alpha1` `FolderPermission` | `grafana_folder_permission` | settings | `GET /folders/{folder_uid}/permissions` |
| `frontend.grafana.hfl.dev/v1alpha1` `FrontendO11yApp` | `grafana_frontend_o11y_app` | crud | `GET /api/v1/app/{id}` |
| `incident.grafana.hfl.dev/v1alpha1` `IncidentCustomField` | `grafana_incident_custom_field` | crud | `POST /plugins/grafana-irm-app/resources/api/v1/FieldsService.GetField` |
| `incident.grafana.hfl.dev/v1alpha1` `IncidentRole` | `grafana_incident_role` | crud | `POST /plugins/grafana-irm-app/resources/api/v1/RolesService.GetRoles` (finds `roleID`) |
| `incident.grafana.hfl.dev/v1alpha1` `IncidentSeverity` | `grafana_incident_severity` | crud | `POST /plugins/grafana-irm-app/resources/api/v1/SeveritiesService.GetSeverityByID` |
| `k6.grafana.hfl.dev/v1alpha1` `K6LoadTest` | `grafana_k6_load_test` | crud | `GET /cloud/v6/load_tests/{id}` |
| `k6.grafana.hfl.dev/v1alpha1` `K6Project` | `grafana_k6_project` | crud | `GET /cloud/v6/projects/{id}` |
| `k6.grafana.hfl.dev/v1alpha1` `K6ProjectAllowedLoadZones` | `grafana_k6_project_allowed_load_zones` | settings | `GET /cloud/v6/projects/{id}/allowed_load_zones` |
| `k6.grafana.hfl.dev/v1alpha1` `K6ProjectLimits` | `grafana_k6_project_limits` | settings | `GET /cloud/v6/projects/{id}/limits` |
| `k6.grafana.hfl.dev/v1alpha1` `K6Schedule` | `grafana_k6_schedule` | upsert | `GET /cloud/v6/load_tests/{id}/schedule` |
| `machine.grafana.hfl.dev/v1alpha1` `MachineLearningAlert` | `grafana_machine_learning_alert` | crud | `GET /manage/api/v1/{parent}/{parent_id}/alerts/{alertId}` |
| `machine.grafana.hfl.dev/v1alpha1` `MachineLearningHoliday` | `grafana_machine_learning_holiday` | crud | `GET /manage/api/v1/holidays/{id}` |
| `machine.grafana.hfl.dev/v1alpha1` `MachineLearningJob` | `grafana_machine_learning_job` | crud | `GET /manage/api/v1/jobs/{id}` |
| `machine.grafana.hfl.dev/v1alpha1` `MachineLearningOutlierDetector` | `grafana_machine_learning_outlier_detector` | crud | `GET /manage/api/v1/outliers/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallEscalation` | `grafana_oncall_escalation` | crud | `GET /api/v1/escalation_policies/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallEscalationChain` | `grafana_oncall_escalation_chain` | crud | `GET /api/v1/escalation_chains/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallIntegration` | `grafana_oncall_integration` | crud | `GET /api/v1/integrations/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallOnCallShift` | `grafana_oncall_on_call_shift` | crud | `GET /api/v1/on_call_shifts/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallOutgoingWebhook` | `grafana_oncall_outgoing_webhook` | crud | `GET /api/v1/webhooks/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallRoute` | `grafana_oncall_route` | crud | `GET /api/v1/routes/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallSchedule` | `grafana_oncall_schedule` | crud | `GET /api/v1/schedules/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallTeamAccessManagement` | `grafana_oncall_team_access_management` | settings | `GET /api/v1/teams/{id}` |
| `oncall.grafana.hfl.dev/v1alpha1` `OncallUserNotificationRule` | `grafana_oncall_user_notification_rule` | crud | `GET /api/v1/personal_notification_rules/{id}` |
| `organization.grafana.hfl.dev/v1alpha1` `Organization` | `grafana_organization` | crud | `GET /orgs/{org_id}` |
| `organization.grafana.hfl.dev/v1alpha1` `OrganizationPreferences` | `grafana_organization_preferences` | settings | `GET /org/preferences` |
| `permission.grafana.hfl.dev/v1alpha1` `PermissionItemRole` | `grafana_dashboard_permission_item`, `grafana_data_source_permission`, `grafana_data_source_permission_item`, `grafana_folder_permission_item`, `grafana_service_account_permission`, `grafana_service_account_permission_item` | upsert | `GET /access-control/{resource}/{resourceID}` |
| `permission.grafana.hfl.dev/v1alpha1` `PermissionItemTeam` | `grafana_dashboard_permission_item`, `grafana_data_source_permission`, `grafana_data_source_permission_item`, `grafana_folder_permission_item`, `grafana_service_account_permission`, `grafana_service_account_permission_item` | upsert | `GET /access-control/{resource}/{resourceID}` |
| `permission.grafana.hfl.dev/v1alpha1` `PermissionItemUser` | `grafana_dashboard_permission_item`, `grafana_data_source_permission`, `grafana_data_source_permission_item`, `grafana_folder_permission_item`, `grafana_service_account_permission`, `grafana_service_account_permission_item` | upsert | `GET /access-control/{resource}/{resourceID}` |
| `playlist.grafana.hfl.dev/v1alpha1` `Playlist` | `grafana_playlist` | crud | `GET /playlists/{uid}` |
| `report.grafana.hfl.dev/v1alpha1` `Report` | `grafana_report` | crud | `GET /reports/{id}` |
| `role.grafana.hfl.dev/v1alpha1` `Role` | `grafana_role` | crud | `GET /access-control/roles/{roleUID}` |
| `role.grafana.hfl.dev/v1alpha1` `RoleAssignment` | `grafana_role_assignment` | settings | `GET /access-control/roles/{roleUID}/assignments` |
| `role.grafana.hfl.dev/v1alpha1` `RoleAssignmentItem` | `grafana_role_assignment_item` | upsert | `GET /access-control/roles/{roleUID}/assignments` |
| `scim.grafana.hfl.dev/v1alpha1` `ScimConfig` | `grafana_scim_config` | upsert | `GET /apis/scim.grafana.app/v0alpha1/namespaces/{namespace}/config/default` |
| `service.grafana.hfl.dev/v1alpha1` `ServiceAccountRotatingToken` | `grafana_service_account_rotating_token` | crud | `GET /serviceaccounts/{serviceAccountId}/tokens` |
| `slo.grafana.hfl.dev/v1alpha1` `Slo` | `grafana_slo` | crud | `GET /v1/slo/{id}` |
| `sso.grafana.hfl.dev/v1alpha1` `SsoSettings` | `grafana_sso_settings` | upsert | `GET /v1/sso-settings/{key}` |
| `synthetic.grafana.hfl.dev/v1alpha1` `SyntheticMonitoringCheck` | `grafana_synthetic_monitoring_check` | crud | `GET /api/v1/check/{id}` |
| `synthetic.grafana.hfl.dev/v1alpha1` `SyntheticMonitoringCheckAlerts` | `grafana_synthetic_monitoring_check_alerts` | settings | `GET /api/v1/check/{checkID}/alerts` |
| `synthetic.grafana.hfl.dev/v1alpha1` `SyntheticMonitoringProbe` | `grafana_synthetic_monitoring_probe` | crud | `GET /api/v1/probe/{id}` |
| `team.grafana.hfl.dev/v1alpha1` `Team` | `grafana_team` | crud | `GET /teams/{team_id}` |
| `team.grafana.hfl.dev/v1alpha1` `TeamExternalGroup` | `grafana_team_external_group` | assoc | `GET /teams/{teamId}/groups` |
| `user.grafana.hfl.dev/v1alpha1` `User` | `grafana_user` | crud | `GET /users/{user_id}` |

The Asserts log, profile, trace, notification alert and suppressed
assertion configs have no read or update of their own: they are written by
an upsert POST to the collection, read by finding their name in the
tenant's list, and deleted by name. A changed spec is reported as drift
(delete and recreate the object); Terraform updates them in place.
`CloudAccessPolicy` and `CloudAccessPolicyToken` take the stack's region in
`spec.region` (sent as `?region=` on every call, never in the body). A
private data source connect network is a `CloudAccessPolicy` with the
`set:pdc-signing` scope and a `stack` realm, and its token a
`CloudAccessPolicyToken`; a token's value, answered once by its create, goes
to `spec.writeSecretRef`, as does a `SyntheticMonitoringProbe`'s access
token. `CloudAccessPolicyRotatingToken`, `CloudStackServiceAccountRotatingToken`
and `ServiceAccountRotatingToken` are a token replaced before it expires, as
the provider's `*_rotating_token`: each token is named
`<name_prefix>-<expiry in Unix seconds>` and lives `expire_after` (or
`seconds_to_live`); once its time left is within `early_rotation_window`
(`early_rotation_window_seconds`) a new one is made, written to
`spec.writeSecretRef`, and the old one deleted. The controller wakes for
that time (`status.rotation.rotateAt`). A changed lifetime or prefix applies
to the next token. Deleting the object leaves the last token to expire
unless `delete_on_destroy` is true. `PermissionItemUser`, `PermissionItemTeam` and `PermissionItemRole`
are one permission on a dashboard, folder, data source or service account
(`spec.resource`: `dashboards`, `folders`, `datasources` or
`serviceaccounts`; `spec.resourceid` its UID or ID), written by a POST to
`/access-control/{resource}/{resourceID}/{users,teams,builtInRoles}/{target}`,
read in the resource's permission list and removed by the same POST with
`{"permission": ""}`. The Assistant kinds' updates and deletes send
`X-Resource-Scope` with the scope the object has now. `AssertsPromRuleFile`
is created and replaced by a PUT of the whole file to
`/v1/config/prom-rules`; `AssertsThresholdsConfig` is the tenant's custom
thresholds, whose delete sends them to `DELETE /v2/config/threshold`.
`AssertsStack` provisions the Asserts stack's tokens (`PUT /v2/stack`:
`gcomToken`, `mimirToken`, `assertionDetectorToken`, where Terraform sends
its one `cloud_access_policy_token` as all three, and `grafanaToken`) and,
with `enabled: "true"`, auto-configures its datasets and enables it
(`POST /v2/stack/datasets/auto-setup`, `POST /v2/stack/enable`); the status
is read from `GET /v1/stack/status`, and deleting the object disables the
stack. Manual datasets (Terraform's `dataset` blocks) are not taken.
`AppsSecretKeeperActivationV1beta1` makes a secrets keeper the active one
(`POST .../keepers/{name}/activate`) and reads it back from the keeper's
`status.active`, so an activation of another keeper is put back; deleting
it activates the `system` keeper, as Terraform does.
`MachineLearningAlert`'s `spec.parent` says what it alerts on: `jobs` (a
forecast job) or `outliers` (an outlier detector), with `spec.parentID` its
ID, as Terraform's `job_id` or `outlier_id`.

`K6LoadTest` is uploaded as a multipart form to its project
(`spec.projectID`), its `script` a file (`{name, content}`), and changed by
a JSON PATCH, which takes no script: the script is sent once, when the
load test is made (the provider changes it with `PUT .../script`), and is
not read back.

`PermissionItemUser`, `PermissionItemTeam` and `PermissionItemRole` stand in
for the whole permission sets of a data source and a service account
(`grafana_data_source_permission`, `grafana_service_account_permission`) one
object per user, team or role: a permission no object names is left as it
is, where Terraform's set removes it. `RoleAssignmentItem` is one user, team
or service account (`spec.user_id`, `team_id` or `service_account_id`: set
exactly one) among a role's assignments: it reads them, adds or removes the
one and writes all three lists back. `K6Schedule` is deleted by the ID its
read answers (`DELETE /cloud/v6/schedules/{id}`).

### Not covered

<!-- BEGIN generated: not covered (krmgen.py, from vendor.yaml hardBlocks and draftNotes) -->
3 of the 119 Terraform gap types have no kind: 3 are not built (`hardBlocks` in `hack/gen/vendor.yaml`).

| Terraform | Status | Why |
| --- | --- | --- |
| `grafana_cloud_integration` | not built | An install the provider performs itself: it fetches the integration's dashboards and alert rules, creates a folder, the dashboards and the rules in Grafana, then records the install (`POST .../integrations/{slug}/install`); uninstalling deletes them the same way. Not one API resource. |
| `grafana_k6_installation` | not built | One-off actions that answer a new token: k6's `PUT /v3/account/grafana-app/start` and Synthetic Monitoring's `POST .../register/install`. Terraform reads nothing back ("management of the installation is a one-off operation"); destroying the k6 installation does nothing, and destroying Synthetic Monitoring's deletes the token it answered (`.../token/delete`). |
| `grafana_synthetic_monitoring_installation` | not built | One-off actions that answer a new token: k6's `PUT /v3/account/grafana-app/start` and Synthetic Monitoring's `POST .../register/install`. Terraform reads nothing back ("management of the installation is a one-off operation"); destroying the k6 installation does nothing, and destroying Synthetic Monitoring's deletes the token it answered (`.../token/delete`). |
<!-- END generated: not covered -->

## For agents (MCP)

`cmd/mcp` serves this repository's kinds over the Model Context Protocol
(stdio), from `types.yaml`, `config/crds` and the live tests' records.
`.mcp.json` registers it, so an agent session opened in this repository
has it without setup. Elsewhere, run it from the repository root:

```sh
go run ./cmd/mcp
```

Its tools: `list_kinds`, `find_kinds_for_terraform`, `describe_kind` (every
field, the REST calls, the live record), `example` (the live-tested spec
where there is one), `validate_manifest` (the CRD schema, as the API server
checks it) and `plan_on_fake` (the controller run against the fake API,
with every REST call it makes). Nothing it does reaches the real API.
krm-rest-runtime's README ("For agents") has the details.

## Regenerate

```sh
hack/gen/generate.sh   # needs python3 + pyyaml, and krm-rest-runtime beside this repo
go test ./...
```

`hack/gen/supplement/apps.yaml` is itself generated: after changing
`hack/gen/supplement/apps.py`, run `python3 hack/gen/supplement/apps.py`
first. The other supplements are written by hand.
