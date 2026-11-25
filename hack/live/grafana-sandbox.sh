#!/usr/bin/env bash
# Copyright 2026 High Five Labs
# SPDX-License-Identifier: Apache-2.0
#
# Grafana OSS in Docker on 127.0.0.1: no account, no secret. The live tests
# point at it (task live:grafana); so can a person applying the samples by hand.
#
#   hack/live/grafana-sandbox.sh up      # container, admin service account, token
#   hack/live/grafana-sandbox.sh creds   # the credentials JSON KRM_LIVE_CREDS takes
#   hack/live/grafana-sandbox.sh run     # up, then TestEveryKindLive (-tags live)
#   hack/live/grafana-sandbox.sh down    # remove the container
#
# The pinned spec (hack/gen/vendor.yaml, grafana/grafana@3f36380c) is main
# after 13.3, versioned 13.4.0-pre; 13.3.1 is the newest release, and every
# path and schema the kinds use is the same in both (the Annotation read
# schema gains only alertUID). The image is OSS: Enterprise-only APIs
# (reports, custom RBAC roles) answer 404 here.
#
# Grafana keeps its database inside the container: down forgets everything.
set -o errexit -o nounset -o pipefail
cd "$(dirname "$0")/../.."

name=${GRAFANA_SANDBOX_NAME:-hfl-live-grafana}
image=${GRAFANA_IMAGE:-grafana/grafana:13.3.1}
port=${GRAFANA_PORT:-13000}
admin=admin:admin # the server administrator; the server listens on 127.0.0.1 only
addr="http://127.0.0.1:${port}"
state=.grafana-sandbox # the token, so creds answers without making another (gitignored)

api() { # METHOD PATH [BODY]
  curl -fsS -u "$admin" -X "$1" -H 'Content-Type: application/json' ${3:+-d "$3"} "${addr}/api/$2"
}

up() {
  if ! docker ps --format '{{.Names}}' | grep -qx "$name"; then
    docker rm -f "$name" >/dev/null 2>&1 || true
    rm -f "$state"
    docker run -d --name "$name" -p "127.0.0.1:${port}:3000" \
      -e GF_SECURITY_ADMIN_USER=admin -e GF_SECURITY_ADMIN_PASSWORD=admin \
      -e GF_ANALYTICS_REPORTING_ENABLED=false -e GF_ANALYTICS_CHECK_FOR_UPDATES=false \
      -e GF_NEWS_NEWS_FEED_ENABLED=false \
      "$image" >/dev/null
  fi
  for _ in $(seq 120); do
    curl -fsS "${addr}/api/health" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -fsS "${addr}/api/health" >/dev/null
  # Basic auth must answer too: the health endpoint is up before the users are.
  for _ in $(seq 30); do
    api GET org >/dev/null 2>&1 && break
    sleep 1
  done
  if [[ ! -s "$state" ]]; then
    local sa
    sa=$(api POST serviceaccounts '{"name":"hfl-live","role":"Admin"}' | jq -r .id)
    api POST "serviceaccounts/${sa}/tokens" '{"name":"hfl-live"}' | jq -r .key >"$state"
  fi
  echo "grafana: ${addr} (admin/admin; service-account token in ${state}; container ${name})" >&2
}

down() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  rm -f "$state"
}

# The service-account token is org-scoped and can never be a Grafana server
# administrator, which the Organization and User kinds need; the live run
# therefore authenticates as the server administrator (vendor.go takes
# "user:password" in token as basic auth, as the Terraform provider's auth
# does). CREDS=token prints the service-account token instead. rootURL is
# for the app platform's kinds (/apis/..., live.yaml's connection "root").
creds() {
  if [[ "${CREDS:-admin}" == token ]]; then
    printf '{"token":"%s","baseURL":"%s/api","rootURL":"%s"}\n' "$(cat "$state")" "$addr" "$addr"
  else
    printf '{"token":"%s","baseURL":"%s/api","rootURL":"%s"}\n' "$admin" "$addr" "$addr"
  fi
}

run() {
  up
  local status=0
  KRM_LIVE=1 KRM_LIVE_CREDS="$(creds)" \
    go test -tags live -run '^TestEveryKindLive$' -count=1 -v . "$@" || status=$?
  [[ -f hack/live/records.json ]] && cat hack/live/records.json
  return "$status"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  creds) creds ;;
  run) shift; run "$@" ;;
  *) echo "usage: $0 up|down|creds|run [go test args]" >&2; exit 2 ;;
esac
