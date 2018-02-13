# BGP static routes in Junos via JET API

This example shows a programmatic solution to inject static routes with multiple next hops directly into BGP to load balance traffic via ECMP. 

The [Juniper Extension Toolkit](https://www.juniper.net/documentation/en_US/jet17.4/information-products/pathway-pages/product/17.4/index.html) offers 2 APIs to manage routes: 

- [RIB Services API](https://www.juniper.net/documentation/en_US/jet17.4/information-products/pathway-pages/rib_service.html): Manage static routes 
- [BGP Route Services API](https://www.juniper.net/documentation/en_US/jet17.4/information-products/pathway-pages/bgp_route_service.html): Manage BGP static routes 

The RIB Services API can't be used, because Junos doesn't allow exporting static routes with add-path for multiple next hops into BGP. The BGP Route Services API on the other hand allows multiple equal routes with different cookies and next hops. 
## Requirements

- Junos device, e.g. vMX
- [JET Cilent IDL library](https://www.juniper.net/support/downloads/?p=jet#sw) from Juniper Networks
- [Docker](https://docs.docker.com/install/) (to build and run this example)


## Junos configuration

Enable gRPC API in clear-text with basic authentication (username/password) via:

```
set system services extension-service request-response grpc clear-text port 50051
set routing-options programmable-rpd purge-timeout 120
```

The purge-timeout defines the purge timeout for all programmable-rpd clients in seconds, when expired, will purge all routes added form a given gRPC client after its connection to the router terminated.

In addition to enabling gRPC on the router, a basic BGP configuration is required:

```
set routing-options autonomous-system 64512
set protocols bgp group internal type internal
set protocols bgp group internal family inet unicast add-path send path-count 6
set protocols bgp group internal allow 0.0.0.0/0
```

## Build the Container

Download the latest JET client IDL library from Juniper Networks at https://www.juniper.net/support/downloads/?p=jet#sw and place the file in the cloned repo directory:

```
$ clone https://github.com/mwiget/jet-bgp-static-routes.git
$ cd jet-bgp-static-routes
$ cp ~/Downloads/jet-idl-17.4R1.16.tar.gz .
```

Now run 'make' to build the container:

```
$ make
docker build -t jet .
Sending build context to Docker daemon  2.226MB
. . .
Successfully built a27b6c83bcd4
Successfully tagged jet:latest
```

Verify the container image. It contains the python modules built from the JET IDL files, ready to be used. The container isn't optimised for size, allowing additional Python modules to be added via 'pip'.

```
$ docker images |head
REPOSITORY            TAG             IMAGE ID         CREATED          SIZE
jet                   latest          a27b6c83bcd4     1 min ago        245MB
```

## Run the Container and routes_bgp.py script

'make shell' launches the container jet with the current directory mounted into the container, allowing you direct access to the [jroutes_bgp.py](jroutes_bgp.py) script to execute with parameters for the target router, port, username and password. 

The script will add routes to 10.123.0.0/24 and 10.123.1.0/24 via the next-hops 10.0.0.1, 10.0.0.2, 10.0.0.3, 10.0.0.4. These are defined via the arrays 'routes' and 'nexthops':

```
$ make shell
docker run -ti --rm -v /Users/mwiget/git/jet-bgp-static-routes:/root jet
root@89b73fd45577:~# ./jroutes_bgp.py --help
usage: jroutes_bgp.py [-h] [-t TARGET] [-P PORT] [-u USERNAME] [-p PASSWORD]

optional arguments:
  -h, --help            show this help message and exit
  -t TARGET, --target TARGET
  -P PORT, --port PORT
  -u USERNAME, --user USERNAME
  -p PASSWORD, --pass PASSWORD
root@89b73fd45577:~#

root@89b73fd45577:~# ./jroutes_bgp.py --t 192.168.1.33 --port 50051 --user lab --pass lab123

./jroutes_bgp.py
Trying to Login to 192.168.1.33 port 50051 as user lab ... Login successful
Successfully connected to BGP Route Service
routes successfully added
root@89b73fd45577:~#
```

If you run the app again within less than 120 seconds (or whatever the devices purge-timeout is set to), you'll will get  error ROUTE_EXISTS(17) back, which means the request contained routes that are already present in the table:

```
root@89b73fd45577:~# ./jroutes_bgp.py --t 192.168.1.33 --port 50051 --user lab --pass lab123

./jroutes_bgp.py
Trying to Login to 192.168.1.33 port 50051 as user lab ... Login successful
Successfully connected to BGP Route Service
BgpRouteAdd failed with code 17
Check https://www.juniper.net/documentation/en_US/jet17.4/information-products/pathway-pages/bgp_route_service.html
for BgpRouteOperReply.BgpRouteOperStatus description
root@89b73fd45577:~#
```

A more useful jroutes_bgp.py application will keep the gRPC session alive and add/update/remove routes as required.  

Check the route in Junos:

```
mwiget@vmxdockerlight_vmx1_1> show route 10/8

inet.0: 9 destinations, 15 routes (9 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.123.0.0/24      *[BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
                    [BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
                    [BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
                    [BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
10.123.1.0/24      *[BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
                    [BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
                    [BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
                    [BGP-Static/10/-201] 00:00:03, metric2 0
                    > to 172.21.0.1 via fxp0.0
```

You might wonder, why the next hops all show 172.21.0.1. This is a result of next hop resolution done by Junos and this system only has one default route via fxp0 (yes, that wouldn't actually work). Looking at the route details will expose the actual programmed next hops, which will be shared with BGP neighbors:

```
mwiget@vmxdockerlight_vmx1_1> show route 10/8 detail

inet.0: 9 destinations, 15 routes (9 active, 0 holddown, 0 hidden)
10.123.0.0/24 (4 entries, 1 announced)
        *BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xb676590
                Next-hop reference count: 5
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.1
                Indirect next hop: 0xbdb6980 344 INH Session ID: 0x0
                State: <Active Int Ext AlwaysFlash NSR-incapable Programmed>
                Age: 3 	Metric2: 0
                Validation State: unverified
                Announcement bits (2): 0-KRT 2-Resolve tree 1
                AS path: I
         BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xb6757b0
                Next-hop reference count: 3
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.2
                Indirect next hop: 0xbdb6b00 - INH Session ID: 0x0
                State: <Int Ext AlwaysFlash NSR-incapable Programmed>
                Inactive reason: Nexthop address
                Age: 3 	Metric2: 0
                Validation State: unverified
                AS path: I
         BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xcde6370
                Next-hop reference count: 3
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.3
                Indirect next hop: 0xbdb6500 - INH Session ID: 0x0
                State: <Int Ext AlwaysFlash NSR-incapable Programmed>
                Inactive reason: Nexthop address
                Age: 3 	Metric2: 0
                Validation State: unverified
                AS path: I
         BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xcde6190
                Next-hop reference count: 3
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.4
                Indirect next hop: 0xbdb6680 - INH Session ID: 0x0
                State: <Int Ext AlwaysFlash NSR-incapable Programmed>
                Inactive reason: Nexthop address
                Age: 3 	Metric2: 0
                Validation State: unverified
                AS path: I

10.123.1.0/24 (4 entries, 1 announced)
        *BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xb676590
                Next-hop reference count: 5
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.1
                Indirect next hop: 0xbdb6980 344 INH Session ID: 0x0
                State: <Active Int Ext AlwaysFlash NSR-incapable Programmed>
                Age: 3 	Metric2: 0
                Validation State: unverified
                Announcement bits (2): 0-KRT 2-Resolve tree 1
                AS path: I
         BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xb6757b0
                Next-hop reference count: 3
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.2
                Indirect next hop: 0xbdb6b00 - INH Session ID: 0x0
                State: <Int Ext AlwaysFlash NSR-incapable Programmed>
                Inactive reason: Nexthop address
                Age: 3 	Metric2: 0
                Validation State: unverified
                AS path: I
         BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xcde6370
                Next-hop reference count: 3
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.3
                Indirect next hop: 0xbdb6500 - INH Session ID: 0x0
                State: <Int Ext AlwaysFlash NSR-incapable Programmed>
                Inactive reason: Nexthop address
                Age: 3 	Metric2: 0
                Validation State: unverified
                AS path: I
         BGP-Static Preference: 10/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xcde6190
                Next-hop reference count: 3
                Next hop type: Router, Next hop index: 343
                Next hop: 172.21.0.1 via fxp0.0, selected
                Session Id: 0x0
                Protocol next hop: 10.0.0.4
                Indirect next hop: 0xbdb6680 - INH Session ID: 0x0
                State: <Int Ext AlwaysFlash NSR-incapable Programmed>
                Inactive reason: Nexthop address
                Age: 3 	Metric2: 0
                Validation State: unverified
                AS path: I
```



The BGP Services API also contains functions to Update and Delete routes. Check out https://www.juniper.net/documentation/en_US/jet17.4/information-products/pathway-pages/bgp_route_service.html for more information.

