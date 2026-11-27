// Copyright 2026 High Five Labs
// SPDX-License-Identifier: Apache-2.0

package extensions

import (
	"encoding/json"
	"os"
	"sort"
	"strings"
	"testing"

	"github.com/highfivelabs/krm-rest-runtime/descriptor"
)

// grafanaSpec is Grafana's own OpenAPI spec, which hack/gen/fetch-specs.sh
// downloads at the commit hack/gen/vendor.yaml pins (hack/ci.sh fetches it
// before the tests).
const grafanaSpec = "hack/gen/specs/grafana.json"

// Every kind made by a call the pinned Grafana spec describes takes its ID
// from a field that call's answer has. The fake API answers whatever field
// a descriptor names, so only the spec can show a wrong one: Role took
// status.id from "id", but Grafana answers a RoleDTO, which has uid and no
// id (HFL-699).
func TestIDsAreFieldsOfTheCreateAnswer(t *testing.T) {
	data, err := os.ReadFile(grafanaSpec)
	if os.IsNotExist(err) && os.Getenv("CI") == "" {
		t.Skipf("%s not fetched: run hack/gen/fetch-specs.sh", grafanaSpec)
	}
	if err != nil {
		t.Fatal(err)
	}
	var spec map[string]any
	if err := json.Unmarshal(data, &spec); err != nil {
		t.Fatal(err)
	}
	f, err := descriptor.Parse(Types)
	if err != nil {
		t.Fatal(err)
	}
	checked := map[string]bool{}
	for i := range f.Kinds {
		k := &f.Kinds[i]
		if k.Create == nil || k.ID == nil || k.ID.IsTemplate() {
			continue
		}
		op, _ := dig(spec, "paths", k.Create.Path, strings.ToLower(k.Create.Method)).(map[string]any)
		if op == nil {
			continue // a call of another of the vendor's APIs
		}
		props := createAnswer(spec, op)
		env := k.Envelope
		if k.Create.Envelope != "" {
			env = k.Create.Envelope
		}
		for _, e := range strings.Split(env, "/") {
			if e != "" && props != nil {
				props = schemaProps(spec, props[e])
			}
		}
		if props == nil {
			continue // the spec gives the answer no fields
		}
		checked[k.Kind] = true
		from := strings.Split(k.ID.From, "/")[0]
		if _, ok := props[from]; !ok {
			names := make([]string, 0, len(props))
			for n := range props {
				names = append(names, n)
			}
			sort.Strings(names)
			t.Errorf("%s: id.from %q is not a field of %s %s's answer (%s): set overrides.idFrom in hack/gen/vendor.yaml",
				k.Kind, k.ID.From, k.Create.Method, k.Create.Path, strings.Join(names, ", "))
		}
	}
	if !checked["Role"] {
		t.Errorf("Role was not checked against %s; checked %d kinds", grafanaSpec, len(checked))
	}
}

// createAnswer is the fields of a call's first 2xx JSON answer, nil where
// the spec gives it no schema with fields.
func createAnswer(spec, op map[string]any) map[string]any {
	resp, _ := op["responses"].(map[string]any)
	codes := make([]string, 0, len(resp))
	for c := range resp {
		codes = append(codes, c)
	}
	sort.Strings(codes)
	for _, c := range codes {
		if !strings.HasPrefix(c, "2") {
			continue
		}
		r, _ := deref(spec, resp[c]).(map[string]any)
		if s := dig(r, "content", "application/json", "schema"); s != nil {
			return schemaProps(spec, s)
		}
	}
	return nil
}

// schemaProps is a schema's properties, with those of its allOf parts.
func schemaProps(spec map[string]any, s any) map[string]any {
	m, _ := deref(spec, s).(map[string]any)
	if m == nil {
		return nil
	}
	var out map[string]any
	add := func(p map[string]any) {
		if p == nil {
			return
		}
		if out == nil {
			out = map[string]any{}
		}
		for n, v := range p {
			out[n] = v
		}
	}
	if all, ok := m["allOf"].([]any); ok {
		for _, a := range all {
			add(schemaProps(spec, a))
		}
	}
	p, _ := m["properties"].(map[string]any)
	add(p)
	return out
}

// deref follows a local $ref ("#/components/...").
func deref(spec map[string]any, v any) any {
	for {
		m, ok := v.(map[string]any)
		if !ok {
			return v
		}
		ref, ok := m["$ref"].(string)
		if !ok {
			return v
		}
		v = dig(spec, strings.Split(strings.TrimPrefix(ref, "#/"), "/")...)
	}
}

func dig(v any, keys ...string) any {
	for _, k := range keys {
		m, ok := v.(map[string]any)
		if !ok {
			return nil
		}
		v = m[k]
	}
	return v
}
