// Copyright 2015 Canonical Ltd.
// Licensed under the AGPLv3, see LICENCE file for details.

package context

import (
	"fmt"
	"strings"

	"github.com/juju/cmd"
	"github.com/juju/errors"
	"gopkg.in/juju/charm.v5"
	goyaml "gopkg.in/yaml.v1"
)

func dumpAll(ctx *cmd.Context, ids []string, values map[string]interface{}) error {
	if len(ids) == 0 {
		return nil
	}
	if err := dump(ctx, ids[0], values); err != nil {
		return errors.Trace(err)
	}
	for _, id := range ids[1:] {
		// TODO(ericsnow) Separate each entry or dump as a YAML list?
		if err := dump(ctx, id, values); err != nil {
			return errors.Trace(err)
		}
	}
	return nil
}

func dump(ctx *cmd.Context, id string, values map[string]interface{}) error {
	// TODO(ericsnow) support passing in an indent size?

	value := values[id]
	output := fmt.Sprintf("[%q not found]", id)
	if value != nil {
		data, err := goyaml.Marshal(value)
		if err != nil {
			return errors.Trace(err)
		}
		output = string(data)
	}

	if _, err := fmt.Fprintln(ctx.Stdout, output); err != nil {
		return errors.Trace(err)
	}
	return nil
}

func parseDefinition(name string, data []byte) (*charm.Process, error) {
	raw := make(map[interface{}]interface{})
	if err := goyaml.Unmarshal(data, raw); err != nil {
		return nil, errors.Trace(err)
	}
	definition, err := charm.ParseProcess(name, raw)
	if err != nil {
		return nil, errors.Trace(err)
	}
	if definition.Name == "" {
		definition.Name = name
	} else if definition.Name != name {
		return nil, errors.Errorf("process name mismatch; %q != %q", definition.Name, name)
	}
	return definition, nil
}

// parseUpdate builds a charm.ProcessFieldValue from an update string.
func parseUpdate(update string) (charm.ProcessFieldValue, error) {
	var pfv charm.ProcessFieldValue

	parts := strings.SplitN(update, ":", 2)
	if len(parts) == 1 {
		return pfv, errors.Errorf("missing value")
	}
	pfv.Field, pfv.Value = parts[0], parts[1]

	if pfv.Field == "" {
		return pfv, errors.Errorf("missing field")
	}
	if pfv.Value == "" {
		return pfv, errors.Errorf("missing value")
	}

	fieldParts := strings.SplitN(pfv.Field, "/", 2)
	if len(fieldParts) == 2 {
		pfv.Field = fieldParts[0]
		pfv.Subfield = fieldParts[1]
	}

	return pfv, nil
}

// parseUpdates parses the updates list in to a charm.ProcessFieldValue list.
func parseUpdates(updates []string) ([]charm.ProcessFieldValue, error) {
	var results []charm.ProcessFieldValue
	for _, update := range updates {
		pfv, err := parseUpdate(update)
		if err != nil {
			return nil, errors.Trace(err)
		}
		results = append(results, pfv)
	}
	return results, nil
}
