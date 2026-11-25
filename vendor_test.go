// Copyright 2026 High Five Labs
// SPDX-License-Identifier: Apache-2.0

package extensions

import (
	"net/http"
	"testing"
)

func TestAuthorize(t *testing.T) {
	for _, tc := range []struct {
		name  string
		creds map[string]string
		want  map[string]string
	}{
		{"bearer", map[string]string{"token": "glsa_x"}, map[string]string{"Authorization": "Bearer glsa_x"}},
		{"basic", map[string]string{"token": "admin:admin"}, map[string]string{"Authorization": "Basic YWRtaW46YWRtaW4="}},
		{"oncall api token", map[string]string{"token": "abc", "scheme": "none"}, map[string]string{"Authorization": "abc"}},
		{"oncall with a service account", map[string]string{"token": "glsa_x", "scheme": "none", "grafanaURL": "https://g.example"},
			map[string]string{"Authorization": "glsa_x", "X-Grafana-URL": "https://g.example"}},
		{"frontend observability", map[string]string{"token": "123:glc_x", "scheme": "bearer", "scopeOrgID": "123"},
			map[string]string{"Authorization": "Bearer 123:glc_x", "X-Scope-OrgID": "123"}},
		{"k6", map[string]string{"token": "t", "stackID": "123"}, map[string]string{"Authorization": "Bearer t", "X-Stack-Id": "123"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			r, _ := http.NewRequest(http.MethodGet, "https://g.example/api/x", nil)
			Vendor.Authorize(r, tc.creds)
			for h, v := range tc.want {
				if got := r.Header.Get(h); got != v {
					t.Errorf("%s = %q, want %q", h, got, v)
				}
			}
			if id := r.Header.Get("X-Request-Id"); len(id) != 36 {
				t.Errorf("X-Request-Id = %q, want a UUID", id)
			}
		})
	}
}
