all: build

build: proto
	docker build -t jet .

proto: jet-idl-17.4R1.16.tar.gz
	tar zxf jet-idl*tar.gz

jet-idl-17.4R1.16.tar.gz:
	@echo "Please download jet-idl-17.4R1.16.tar.gz from https://www.juniper.net/support/downloads/?p=jet#sw"

run:
	chmod a+rx jroutes_bgp.py
	docker run -ti --rm -v ${PWD}:/root jet -c ./jroutes_bgp.py

shell:
	docker run -ti --rm -v ${PWD}:/root jet 

clean:
	docker system prune -f
