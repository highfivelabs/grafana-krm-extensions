#!/usr/bin/env bash
# Copyright 2026 High Five Labs
# SPDX-License-Identifier: Apache-2.0
# Download the vendor's OpenAPI specs at the commits vendor.yaml pins.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p specs
[ -s specs/grafana.json ] || curl -fsSL -o specs/grafana.json "https://raw.githubusercontent.com/grafana/grafana/3f36380cfd6240f348c2a6226f6fb07647746d60/public/openapi3.json"
# Grafana SLO (a Grafana Cloud app plugin on the same Grafana, under
# /api/plugins/grafana-slo-app/resources), at the commit of
# github.com/grafana/slo-openapi-client that terraform-provider-grafana 4.55.0 pins.
[ -s specs/slo.yaml ] || curl -fsSL -o specs/slo.yaml "https://raw.githubusercontent.com/grafana/slo-openapi-client/75fe08b09d871ab45cb4a5eeca91dbbe43c66672/openapi.yaml"
# Grafana Cloud's own API (https://grafana.com/api), at the commit of
# github.com/grafana/grafana-com-public-clients that the provider pins.
[ -s specs/gcom.json ] || curl -fsSL -o specs/gcom.json "https://raw.githubusercontent.com/grafana/grafana-com-public-clients/7fe3d665bcc0eaf4e0d5804d1d5afefaac29acef/openapi.json"
# Grafana Cloud k6's API (https://api.k6.io), at the commit of
# github.com/grafana/k6-cloud-openapi-client-go that the provider pins.
[ -s specs/k6.yaml ] || curl -fsSL -o specs/k6.yaml "https://raw.githubusercontent.com/grafana/k6-cloud-openapi-client-go/c48eae4f9a18caed970a1e165762b99660429bc5/schema.yaml"
# Grafana Asserts (Knowledge Graph) API server, at the commit of
# github.com/grafana/grafana-asserts-public-clients that the provider pins.
[ -s specs/asserts.yaml ] || curl -fsSL -o specs/asserts.yaml "https://raw.githubusercontent.com/grafana/grafana-asserts-public-clients/433280da6996a16ed7c6810ad400bcac52100be6/openapi.yaml"
