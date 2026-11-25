// Copyright 2026 High Five Labs
// SPDX-License-Identifier: Apache-2.0

package extensions

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"strings"

	"github.com/highfivelabs/krm-rest-runtime/rest"
)

// Vendor is how the manager reaches Grafana.
//
// token is a service-account token (Bearer), or "user:password" (basic auth),
// as the Terraform provider's auth takes either. A service account belongs to
// one organization and can never be a Grafana server administrator, so the
// kinds that need one (Organization, and anything outside the token's own
// organization) need a server administrator's basic auth. Grafana's tokens
// (glsa_..., and the legacy base64 API keys) never hold a colon.
//
// The kinds for Grafana's other APIs (Grafana Cloud, OnCall, k6, ...) reach
// them through a Connection of their own (README), whose Secret may also hold:
//
//   - scheme: "none" sends the token as the whole Authorization header, as
//     OnCall's API tokens are sent; "bearer" sends it as a Bearer token even
//     though it holds a colon (Frontend Observability's "<stack ID>:<token>");
//     otherwise it is a Bearer token, or user:password.
//   - grafanaURL: sent as X-Grafana-URL, which OnCall needs to accept a
//     Grafana service-account token.
//   - stackID: sent as X-Stack-Id, the Grafana Cloud stack k6's API acts on.
//   - scopeOrgID: sent as X-Scope-OrgID (Frontend Observability: the stack ID).
//
// Every request carries a fresh X-Request-Id, which Grafana Cloud's API
// (grafana.com/api) asks writes for.
var Vendor = &rest.Vendor{
	Name:           "grafana",
	DefaultBaseURL: "", // every Connection names its Grafana
	CredentialKeys: []string{"token"},
	Authorize: func(r *http.Request, c map[string]string) {
		if r.Header.Get("X-Request-Id") == "" {
			r.Header.Set("X-Request-Id", requestID())
		}
		if v := c["grafanaURL"]; v != "" {
			r.Header.Set("X-Grafana-URL", v)
		}
		if v := c["stackID"]; v != "" {
			r.Header.Set("X-Stack-Id", v)
		}
		if v := c["scopeOrgID"]; v != "" {
			r.Header.Set("X-Scope-OrgID", v)
		}
		if c["scheme"] == "bearer" {
			r.Header.Set("Authorization", "Bearer "+c["token"])
			return
		}
		if user, pass, ok := strings.Cut(c["token"], ":"); ok {
			r.SetBasicAuth(user, pass)
			return
		}
		if c["scheme"] == "none" {
			r.Header.Set("Authorization", c["token"])
			return
		}
		r.Header.Set("Authorization", "Bearer "+c["token"])
	},
}

// requestID is a random UUID (version 4).
func requestID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	b[6] = b[6]&0x0f | 0x40
	b[8] = b[8]&0x3f | 0x80
	h := hex.EncodeToString(b[:])
	return h[:8] + "-" + h[8:12] + "-" + h[12:16] + "-" + h[16:20] + "-" + h[20:]
}
