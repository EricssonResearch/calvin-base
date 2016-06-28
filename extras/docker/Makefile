
NAMESPACE=erctcalvin

TEMPDIR:=$(shell mktemp -d)

.PHONY:
master:
	@cp Dockerfile $(TEMPDIR)
	cp docker-runtime.sh $(TEMPDIR)
	docker build --tag $(NAMESPACE)/calvin:master --build-arg branch=master -f $(TEMPDIR)/Dockerfile $(TEMPDIR)
	rm -rf $(TEMPDIR)

.PHONY:
local:
	@cd ../.. ; git stash -k >& /dev/null ; git archive 'stash@{0}' --prefix=calvin-base/ | gzip > $(TEMPDIR)/calvin-base-head.tgz
	@git stash pop >& /dev/null
	@cp Dockerfile.local $(TEMPDIR)
	@docker build --tag $(NAMESPACE)/calvin:local -f $(TEMPDIR)/Dockerfile.local $(TEMPDIR)
	@rm -rf $(TEMPDIR)


.PHONY:
develop:
	cp Dockerfile $(TEMPDIR)
	cp docker-runtime.sh $(TEMPDIR)
	docker build --tag $(NAMESPACE)/calvin:develop --build-arg branch=develop -f $(TEMPDIR)/Dockerfile $(TEMPDIR)
	rm -rf $(TEMPDIR)/
