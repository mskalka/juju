// Copyright 2015 Canonical Ltd.
// Licensed under the AGPLv3, see LICENCE file for details.

package openstack

import (
	"fmt"
	"strings"

	"github.com/juju/errors"
	"github.com/juju/juju/version"
	"gopkg.in/goose.v1/nova"
)

// RunUpgradeStepsFor implements provider.Upgradable
func (e *Environ) RunUpgradeStepsFor(ver version.Number) error {
	switch ver {
	case version.Number{Major: 1, Minor: 26}:
		if err := addUUIDToSecurityGroupNames(e); err != nil {
			return errors.Annotate(err, "upgrading security group names in upgrade step for version 1.26")
		}
		if err := addUUIDToMachineNames(e); err != nil {
			return errors.Annotate(err, "upgrading security machine names in upgrade step for version 1.26")
		}
	}
	return nil
}

func replaceNameWithID(oldName, envName, eUUID string) (string, error, bool) {
	nameStart := strings.LastIndex(oldName, envName)
	if nameStart <= -1 {
		uuidPresent := strings.LastIndex(oldName, eUUID)
		if uuidPresent < 0 {
			return "", nil, false
		}
		return oldName, nil, false
	}
	partial := oldName[nameStart:]
	return fmt.Sprintf("%s%s", oldName[:nameStart], strings.Replace(partial, envName, eUUID, -1)), nil, true
}

func addUUIDToSecurityGroupNames(e *Environ) error {
	nova := e.nova()
	groups, err := nova.ListSecurityGroups()
	if err != nil {
		return errors.Annotate(err, "upgrading instance names")
	}
	cfg := e.Config()
	eName := cfg.Name()
	eUUID, ok := cfg.UUID()
	if !ok {
		return errors.NotFoundf("environment uuid for environment %q", eName)
	}
	for _, group := range groups {
		newName, err, ok := replaceNameWithID(group.Name, eName, eUUID)
		if err != nil {
			return errors.Annotate(err, "generating the new security group name")
		}
		if !ok {
			continue
		}
		// Name should have uuid instead of name
		_, err = nova.UpdateSecurityGroup(group.Id, newName, group.Description)
		if err != nil {
			return errors.Annotatef(err, "upgrading security group name from %q to %q", group.Name, newName)
		}

	}
	return nil
}

// oldMachinesFilter returns a nova.Filter matching all machines in the environment
// that use the old name schema (juju-EnvironmentName-number).
func oldMachinesFilter(e *Environ) *nova.Filter {
	filter := nova.NewFilter()
	filter.Set(nova.FilterServer, fmt.Sprintf("juju-%s-machine-\\d*", e.Config().Name()))
	return filter
}

func addUUIDToMachineNames(e *Environ) error {
	nova := e.nova()
	servers, err := nova.ListServers(oldMachinesFilter(e))
	if err != nil {
		return errors.Annotate(err, "upgrading server names")
	}
	cfg := e.Config()
	eName := cfg.Name()
	eUUID, ok := cfg.UUID()
	if !ok {
		return errors.NotFoundf("environment uuid for environment %q", eName)
	}
	for _, server := range servers {
		newName, err, ok := replaceNameWithID(server.Name, eName, eUUID)
		if err != nil {
			return errors.Annotate(err, "generating the new server name")
		}
		if !ok {
			continue
		}
		// Name should have uuid instead of name
		_, err = nova.UpdateServerName(server.Id, newName)
		if err != nil {
			return errors.Annotatef(err, "upgrading machine name from %q to %q", server.Name, newName)
		}

	}
	return nil
}
