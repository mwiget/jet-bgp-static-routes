FROM ubuntu:17.10
RUN apt-get update \
  && apt-get install -y --no-install-recommends python-pip \
  protobuf-compiler-grpc vim-tiny

RUN pip install protobuf grpcio netaddr

COPY /proto /proto
RUN mkdir pylib \
  && protoc --proto_path=proto \
  --python_out=/usr/lib/python2.7/  --grpc_out=/usr/lib/python2.7/ \
  --plugin=protoc-gen-grpc=/usr/bin/grpc_python_plugin proto/*proto

WORKDIR /root

ENTRYPOINT ["/bin/bash"]
