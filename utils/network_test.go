// Copyright 2013 Canonical Ltd.
// Licensed under the AGPLv3, see LICENCE file for details.

package utils_test

import (
	"net"

	gc "launchpad.net/gocheck"
	"launchpad.net/juju-core/utils"
)

type networkSuite struct {
}

var _ = gc.Suite(&networkSuite{})

type fakeAddress struct {
	address string
}

func (fake fakeAddress) Network() string {
	return "ignored"
}

func (fake fakeAddress) String() string {
	return fake.address
}

func makeAddresses(values ...string) (result []net.Addr) {
	for _, v := range values {
		result = append(result, &fakeAddress{v})
	}
	return
}

func (*networkSuite) TestGetIPv4Address(c *gc.C) {
	for _, test := range []struct {
		addresses []net.Addr
		expected  string
		fail      bool
	}{{
		addresses: makeAddresses(
			"complete",
			"nonsense"),
		fail: true,
	}, {
		addresses: makeAddresses(
			"fe80::90cf:9dff:fe6e:ece/64",
			"10.0.3.1/24",
		),
		expected: "10.0.3.1",
	}, {
		addresses: makeAddresses(
			"10.0.3.1/24",
			"fe80::90cf:9dff:fe6e:ece/64",
		),
		expected: "10.0.3.1",
	}} {
		ip, err := utils.GetIPv4Address(test.addresses)
		if test.fail {
			c.Assert(err, gc.ErrorMatches, `no addresses match`)
			c.Assert(ip, gc.Equals, "")
		} else {
			c.Assert(err, gc.IsNil)
			c.Assert(ip, gc.Equals, test.expected)
		}
	}
}
