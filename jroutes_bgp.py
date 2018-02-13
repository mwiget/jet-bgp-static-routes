#!/usr/bin/env python

from __future__ import print_function

import socket
import time
import sys
import netaddr
import grpc
import argparse

import authentication_service_pb2
import bgp_route_service_pb2
import prpd_common_pb2
import jnx_addr_pb2


_JET_TIMEOUT = 10  # Timeout in seconds for an rpc to return back
DEFAULT_APP_COOKIE = 12345678

cookie = 12345678

routes = ['10.123.0.0', '10.123.1.0']
nexthops = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4']
prefix_len = 24
local_pref = 200
route_pref = 10
asPathStr = None
originator = '10.255.255.3'
cluster = '10.255.255.7'


parser = argparse.ArgumentParser()
parser.add_argument('-t', '--target', dest='target', default='vmx1')
parser.add_argument('-P', '--port', dest='port', type=int, default=50051)
parser.add_argument('-u', '--user', dest='username', default='lab')
parser.add_argument('-p', '--pass', dest='password', default='lab123')
args = parser.parse_args()

clientid = socket.gethostname()

try:
    # open gRPC channel
    print("")
    print(__file__)
    print("Trying to Login to", args.target, "port",
          args.port, "as user", args.username, "... ", end='')
    channel = grpc.insecure_channel('%s:%d' % (args.target, args.port))
    auth_stub = authentication_service_pb2.LoginStub(channel)
    login_response = auth_stub.LoginCheck(
        authentication_service_pb2.LoginRequest(
            user_name=args.username,
            password=args.password,
            client_id=clientid), _JET_TIMEOUT)

    if login_response.result == 1:
        print("Login successful")
    else:
        print("Login failed")
        sys.exit(1)

except Exception as tx:
    print(tx)

# Create the BGP service stub
bgp = bgp_route_service_pb2.BgpRouteStub(channel)
strBgpReq = bgp_route_service_pb2.BgpRouteInitializeRequest()
result = bgp.BgpRouteInitialize(strBgpReq, timeout=_JET_TIMEOUT)
if ((result.status != bgp_route_service_pb2.BgpRouteInitializeReply.SUCCESS) and
        (result.status != bgp_route_service_pb2.BgpRouteInitializeReply.SUCCESS_STATE_REBOUND)):
    print("Error on Initialize")
print("Successfully connected to BGP Route Service")

# Adding BGP static routes
rtlist = []
for r in routes:
    destPrefix = prpd_common_pb2.RoutePrefix(
        inet=jnx_addr_pb2.IpAddress(addr_string=r))
    path_cookie = cookie

    for nh in nexthops:
        # Build the route table objects
        nextHopIp = jnx_addr_pb2.IpAddress(addr_string=nh)
        rt_table = prpd_common_pb2.RouteTable(
            rtt_name=prpd_common_pb2.RouteTableName(name='inet.0'))
        routeParams = bgp_route_service_pb2.BgpRouteEntry(
            dest_prefix=destPrefix, dest_prefix_len=prefix_len,
            table=rt_table,
            protocol_nexthops=[nextHopIp],
            path_cookie=path_cookie,
            route_type=bgp_route_service_pb2.BGP_INTERNAL,
            local_preference=bgp_route_service_pb2.BgpAttrib32(
                value=local_pref),
            route_preference=bgp_route_service_pb2.BgpAttrib32(
                value=route_pref),
            protocol=bgp_route_service_pb2.PROTO_BGP_STATIC,
            aspath=bgp_route_service_pb2.AsPath(aspath_string=asPathStr))
        path_cookie = path_cookie + 1
        rtlist.append(routeParams)

routeUpdReq = bgp_route_service_pb2.BgpRouteUpdateRequest(
    bgp_routes=rtlist)
result = bgp.BgpRouteAdd(routeUpdReq, _JET_TIMEOUT)
if result.status > bgp_route_service_pb2.BgpRouteOperReply.SUCCESS:
    print("BgpRouteAdd failed with code", result.status)
    print("Check https://www.juniper.net/documentation/en_US/jet17.4/information-products/pathway-pages/bgp_route_service.html")
    print("for BgpRouteOperReply.BgpRouteOperStatus description")
else:
    print("routes successfully added")

